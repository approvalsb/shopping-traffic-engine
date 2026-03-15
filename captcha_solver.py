"""
Captcha Solver - Auto-solve Naver captchas using CapSolver API.
Supports: image captcha, reCAPTCHA v2, hCaptcha.
Fallback: 2Captcha API.

Usage:
    solver = CaptchaSolver(api_key="your-capsolver-key")
    solved = solver.solve_if_needed(driver)  # True if solved or no captcha
"""

import os
import time
import base64
import logging
import requests
from typing import Optional
from pathlib import Path

# Load .env if python-dotenv available, otherwise manual load
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().strip().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

log = logging.getLogger("captcha_solver")

# Env vars for API keys
CAPSOLVER_KEY = os.getenv("CAPSOLVER_API_KEY", "")
TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_API_KEY", "")

CAPSOLVER_API = "https://api.capsolver.com"
TWOCAPTCHA_API = "https://2captcha.com"


class CaptchaSolver:
    """Auto-detect and solve captchas on Naver pages."""

    # Naver captcha signals
    BLOCKED_SIGNALS = [
        "확인을 완료해 주세요",
        "일시적으로 제한",
        "비정상적인 접근",
        "자동 입력 방지",
        "보안문자",
    ]

    def __init__(
        self,
        capsolver_key: Optional[str] = None,
        twocaptcha_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 120,
    ):
        self.capsolver_key = capsolver_key or CAPSOLVER_KEY
        self.twocaptcha_key = twocaptcha_key or TWOCAPTCHA_KEY
        self.max_retries = max_retries
        self.timeout = timeout

        if not self.capsolver_key and not self.twocaptcha_key:
            log.warning("No captcha API key set. Set CAPSOLVER_API_KEY or TWOCAPTCHA_API_KEY env var.")

    @property
    def enabled(self) -> bool:
        return bool(self.capsolver_key or self.twocaptcha_key)

    def detect_captcha(self, driver) -> Optional[str]:
        """Detect captcha type on current page.
        Returns: 'image', 'recaptcha', 'hcaptcha', or None.
        """
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            has_block_signal = any(s in body_text for s in self.BLOCKED_SIGNALS)

            if not has_block_signal:
                return None

            # Check for reCAPTCHA iframe
            recaptcha_frames = driver.find_elements(
                By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[title*='reCAPTCHA']"
            )
            if recaptcha_frames:
                return "recaptcha"

            # Check for hCaptcha iframe
            hcaptcha_frames = driver.find_elements(
                By.CSS_SELECTOR, "iframe[src*='hcaptcha']"
            )
            if hcaptcha_frames:
                return "hcaptcha"

            # Check for image captcha input
            captcha_inputs = driver.find_elements(
                By.CSS_SELECTOR,
                "input[name*='captcha'], input[id*='captcha'], "
                "input[name*='answer'], input[placeholder*='입력']"
            )
            captcha_images = driver.find_elements(
                By.CSS_SELECTOR,
                "img[src*='captcha'], img[alt*='captcha'], "
                "img[src*='ncaptcha'], img[class*='captcha']"
            )
            if captcha_inputs or captcha_images:
                return "image"

            # Block detected but captcha type unknown
            log.warning("Block detected but captcha type unknown")
            return "unknown"

        except Exception as e:
            log.error("Captcha detection error: %s", e)
            return None

    def solve_if_needed(self, driver) -> bool:
        """Detect and solve captcha if present.
        Returns True if no captcha or captcha solved successfully.
        Returns False if captcha present but couldn't solve.
        """
        captcha_type = self.detect_captcha(driver)

        if captcha_type is None:
            return True  # No captcha

        if not self.enabled:
            log.error("Captcha detected (%s) but no API key configured", captcha_type)
            return False

        log.info("Captcha detected: %s — attempting to solve...", captcha_type)

        for attempt in range(1, self.max_retries + 1):
            log.info("Solve attempt %d/%d", attempt, self.max_retries)

            try:
                if captcha_type == "image":
                    solved = self._solve_image_captcha(driver)
                elif captcha_type == "recaptcha":
                    solved = self._solve_recaptcha(driver)
                elif captcha_type == "hcaptcha":
                    solved = self._solve_hcaptcha(driver)
                else:
                    # Unknown type — try image captcha as fallback
                    solved = self._solve_image_captcha(driver)

                if solved:
                    # Wait and verify captcha is gone
                    time.sleep(3)
                    if self.detect_captcha(driver) is None:
                        log.info("Captcha solved successfully!")
                        return True
                    else:
                        log.warning("Captcha still present after solve attempt")
                else:
                    log.warning("Solve attempt returned False")

            except Exception as e:
                log.error("Solve attempt %d failed: %s", attempt, e)

            time.sleep(2)

        log.error("Failed to solve captcha after %d attempts", self.max_retries)
        return False

    # ── Image Captcha ──────────────────────────────────────────────

    def _solve_image_captcha(self, driver) -> bool:
        """Solve image-based captcha (screenshot → OCR → submit)."""
        # Find captcha image
        captcha_img = self._find_captcha_image(driver)
        if not captcha_img:
            log.warning("Could not find captcha image element")
            return False

        # Get image as base64
        img_b64 = self._get_element_screenshot_b64(driver, captcha_img)
        if not img_b64:
            return False

        # Solve via API
        solution = None
        if self.capsolver_key:
            solution = self._capsolver_image(img_b64)
        if not solution and self.twocaptcha_key:
            solution = self._twocaptcha_image(img_b64)

        if not solution:
            return False

        log.info("Got captcha solution: %s", solution[:20])

        # Find input field and submit
        return self._submit_captcha_answer(driver, solution)

    def _find_captcha_image(self, driver):
        """Find the captcha image element."""
        selectors = [
            "img[src*='captcha']",
            "img[src*='ncaptcha']",
            "img[class*='captcha']",
            "img[alt*='captcha']",
            "img[alt*='보안']",
            "#captchaImg",
            ".captcha_img",
        ]
        for sel in selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed() and el.size["width"] > 50:
                        return el
            except Exception:
                continue
        return None

    def _get_element_screenshot_b64(self, driver, element) -> Optional[str]:
        """Get base64 screenshot of a specific element."""
        try:
            return element.screenshot_as_base64
        except Exception:
            # Fallback: full page screenshot
            try:
                return base64.b64encode(driver.get_screenshot_as_png()).decode()
            except Exception as e:
                log.error("Screenshot failed: %s", e)
                return None

    def _submit_captcha_answer(self, driver, answer: str) -> bool:
        """Find captcha input, type answer, submit."""
        input_selectors = [
            "input[name*='captcha']",
            "input[id*='captcha']",
            "input[name*='answer']",
            "input[placeholder*='입력']",
            "input[type='text'][class*='captcha']",
        ]

        for sel in input_selectors:
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR, sel)
                for inp in inputs:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(answer)
                        log.info("Entered captcha answer in: %s", sel)

                        # Find and click submit button
                        return self._click_captcha_submit(driver)
            except Exception:
                continue

        log.warning("Could not find captcha input field")
        return False

    def _click_captcha_submit(self, driver) -> bool:
        """Click the captcha submit/confirm button."""
        button_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:contains('확인')",
            "a:contains('확인')",
            ".btn_submit",
            "#submit",
        ]

        # Try CSS selectors
        for sel in button_selectors:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in btns:
                    if btn.is_displayed():
                        btn.click()
                        log.info("Clicked submit button: %s", sel)
                        return True
            except Exception:
                continue

        # Try XPath for text-based buttons
        xpath_patterns = [
            "//*[contains(text(),'확인')]",
            "//*[contains(text(),'제출')]",
            "//*[contains(text(),'입력')]",
        ]
        for xp in xpath_patterns:
            try:
                btns = driver.find_elements(By.XPATH, xp)
                for btn in btns:
                    if btn.is_displayed() and btn.tag_name in ("button", "a", "input", "span"):
                        btn.click()
                        log.info("Clicked submit via xpath: %s", xp)
                        return True
            except Exception:
                continue

        # Last resort: press Enter on the input
        try:
            from selenium.webdriver.common.keys import Keys
            active = driver.switch_to.active_element
            active.send_keys(Keys.RETURN)
            log.info("Pressed Enter as submit fallback")
            return True
        except Exception:
            pass

        log.warning("Could not find submit button")
        return False

    # ── reCAPTCHA v2 ───────────────────────────────────────────────

    def _solve_recaptcha(self, driver) -> bool:
        """Solve reCAPTCHA v2 using token injection."""
        # Find sitekey
        sitekey = self._find_recaptcha_sitekey(driver)
        if not sitekey:
            log.warning("Could not find reCAPTCHA sitekey")
            return False

        page_url = driver.current_url
        log.info("Solving reCAPTCHA (sitekey=%s...)", sitekey[:20])

        token = None
        if self.capsolver_key:
            token = self._capsolver_recaptcha(sitekey, page_url)
        if not token and self.twocaptcha_key:
            token = self._twocaptcha_recaptcha(sitekey, page_url)

        if not token:
            return False

        # Inject token
        driver.execute_script(
            'document.getElementById("g-recaptcha-response").innerHTML = arguments[0];',
            token,
        )
        # Try to trigger callback
        driver.execute_script(
            """
            if (typeof ___grecaptcha_cfg !== 'undefined') {
                Object.entries(___grecaptcha_cfg.clients).forEach(([k,v]) => {
                    try {
                        Object.entries(v).forEach(([kk,vv]) => {
                            if (vv && vv.callback) vv.callback(arguments[0]);
                        });
                    } catch(e) {}
                });
            }
            """,
            token,
        )
        return True

    def _find_recaptcha_sitekey(self, driver) -> Optional[str]:
        """Extract reCAPTCHA sitekey from page."""
        try:
            el = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
            return el.get_attribute("data-sitekey")
        except Exception:
            pass
        try:
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            for f in frames:
                src = f.get_attribute("src") or ""
                if "k=" in src:
                    return src.split("k=")[1].split("&")[0]
        except Exception:
            pass
        return None

    # ── hCaptcha ───────────────────────────────────────────────────

    def _solve_hcaptcha(self, driver) -> bool:
        """Solve hCaptcha using token injection."""
        sitekey = self._find_hcaptcha_sitekey(driver)
        if not sitekey:
            log.warning("Could not find hCaptcha sitekey")
            return False

        page_url = driver.current_url
        log.info("Solving hCaptcha (sitekey=%s...)", sitekey[:20])

        token = None
        if self.capsolver_key:
            token = self._capsolver_hcaptcha(sitekey, page_url)
        if not token and self.twocaptcha_key:
            token = self._twocaptcha_hcaptcha(sitekey, page_url)

        if not token:
            return False

        driver.execute_script(
            """
            document.querySelector('[name="h-captcha-response"]').value = arguments[0];
            document.querySelector('[name="g-recaptcha-response"]').value = arguments[0];
            """,
            token,
        )
        return True

    def _find_hcaptcha_sitekey(self, driver) -> Optional[str]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
            return el.get_attribute("data-sitekey")
        except Exception:
            pass
        try:
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
            for f in frames:
                src = f.get_attribute("src") or ""
                if "sitekey=" in src:
                    return src.split("sitekey=")[1].split("&")[0]
        except Exception:
            pass
        return None

    # ── CapSolver API ──────────────────────────────────────────────

    def _capsolver_image(self, img_b64: str) -> Optional[str]:
        """Solve image captcha via CapSolver."""
        try:
            resp = requests.post(
                f"{CAPSOLVER_API}/createTask",
                json={
                    "appId": "6A5CADA4-C0B1-4E40-A2C7-6F492E1AEB1B",
                    "clientKey": self.capsolver_key,
                    "task": {
                        "type": "ImageToTextTask",
                        "body": img_b64,
                    },
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("errorId", 1) != 0:
                log.error("CapSolver create error: %s", data.get("errorDescription"))
                return None

            task_id = data.get("taskId")
            if not task_id:
                # Instant result
                return data.get("solution", {}).get("text")

            # Poll for result
            return self._capsolver_poll(task_id)

        except Exception as e:
            log.error("CapSolver image error: %s", e)
            return None

    def _capsolver_recaptcha(self, sitekey: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA v2 via CapSolver."""
        try:
            resp = requests.post(
                f"{CAPSOLVER_API}/createTask",
                json={
                    "appId": "6A5CADA4-C0B1-4E40-A2C7-6F492E1AEB1B",
                    "clientKey": self.capsolver_key,
                    "task": {
                        "type": "ReCaptchaV2TaskProxyLess",
                        "websiteURL": page_url,
                        "websiteKey": sitekey,
                    },
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("errorId", 1) != 0:
                log.error("CapSolver reCAPTCHA error: %s", data.get("errorDescription"))
                return None
            return self._capsolver_poll(data.get("taskId"))
        except Exception as e:
            log.error("CapSolver reCAPTCHA error: %s", e)
            return None

    def _capsolver_hcaptcha(self, sitekey: str, page_url: str) -> Optional[str]:
        """Solve hCaptcha via CapSolver."""
        try:
            resp = requests.post(
                f"{CAPSOLVER_API}/createTask",
                json={
                    "appId": "6A5CADA4-C0B1-4E40-A2C7-6F492E1AEB1B",
                    "clientKey": self.capsolver_key,
                    "task": {
                        "type": "HCaptchaTaskProxyLess",
                        "websiteURL": page_url,
                        "websiteKey": sitekey,
                    },
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("errorId", 1) != 0:
                log.error("CapSolver hCaptcha error: %s", data.get("errorDescription"))
                return None
            return self._capsolver_poll(data.get("taskId"))
        except Exception as e:
            log.error("CapSolver hCaptcha error: %s", e)
            return None

    def _capsolver_poll(self, task_id: str) -> Optional[str]:
        """Poll CapSolver for task result."""
        if not task_id:
            return None

        for _ in range(self.timeout // 5):
            try:
                resp = requests.post(
                    f"{CAPSOLVER_API}/getTaskResult",
                    json={"clientKey": self.capsolver_key, "taskId": task_id},
                    timeout=15,
                )
                data = resp.json()

                if data.get("status") == "ready":
                    solution = data.get("solution", {})
                    return (
                        solution.get("text")
                        or solution.get("gRecaptchaResponse")
                        or solution.get("token")
                    )

                if data.get("errorId", 0) != 0:
                    log.error("CapSolver poll error: %s", data.get("errorDescription"))
                    return None

            except Exception as e:
                log.error("CapSolver poll error: %s", e)

            time.sleep(5)

        log.error("CapSolver timeout after %ds", self.timeout)
        return None

    # ── 2Captcha API (fallback) ────────────────────────────────────

    def _twocaptcha_image(self, img_b64: str) -> Optional[str]:
        """Solve image captcha via 2Captcha."""
        try:
            resp = requests.post(
                f"{TWOCAPTCHA_API}/in.php",
                data={
                    "key": self.twocaptcha_key,
                    "method": "base64",
                    "body": img_b64,
                    "json": 1,
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("status") != 1:
                log.error("2Captcha create error: %s", data.get("request"))
                return None
            return self._twocaptcha_poll(data["request"])
        except Exception as e:
            log.error("2Captcha image error: %s", e)
            return None

    def _twocaptcha_recaptcha(self, sitekey: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA v2 via 2Captcha."""
        try:
            resp = requests.post(
                f"{TWOCAPTCHA_API}/in.php",
                data={
                    "key": self.twocaptcha_key,
                    "method": "userrecaptcha",
                    "googlekey": sitekey,
                    "pageurl": page_url,
                    "json": 1,
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("status") != 1:
                log.error("2Captcha reCAPTCHA error: %s", data.get("request"))
                return None
            return self._twocaptcha_poll(data["request"])
        except Exception as e:
            log.error("2Captcha reCAPTCHA error: %s", e)
            return None

    def _twocaptcha_hcaptcha(self, sitekey: str, page_url: str) -> Optional[str]:
        """Solve hCaptcha via 2Captcha."""
        try:
            resp = requests.post(
                f"{TWOCAPTCHA_API}/in.php",
                data={
                    "key": self.twocaptcha_key,
                    "method": "hcaptcha",
                    "sitekey": sitekey,
                    "pageurl": page_url,
                    "json": 1,
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("status") != 1:
                log.error("2Captcha hCaptcha error: %s", data.get("request"))
                return None
            return self._twocaptcha_poll(data["request"])
        except Exception as e:
            log.error("2Captcha hCaptcha error: %s", e)
            return None

    def _twocaptcha_poll(self, request_id: str) -> Optional[str]:
        """Poll 2Captcha for result."""
        time.sleep(10)  # 2Captcha needs initial wait

        for _ in range(self.timeout // 5):
            try:
                resp = requests.get(
                    f"{TWOCAPTCHA_API}/res.php",
                    params={
                        "key": self.twocaptcha_key,
                        "action": "get",
                        "id": request_id,
                        "json": 1,
                    },
                    timeout=15,
                )
                data = resp.json()

                if data.get("status") == 1:
                    return data.get("request")

                if data.get("request") != "CAPCHA_NOT_READY":
                    log.error("2Captcha poll error: %s", data.get("request"))
                    return None

            except Exception as e:
                log.error("2Captcha poll error: %s", e)

            time.sleep(5)

        log.error("2Captcha timeout after %ds", self.timeout)
        return None
