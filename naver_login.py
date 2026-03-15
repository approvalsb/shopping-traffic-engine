"""
Naver Account Manager — login, account rotation, daily limit tracking.

Loads accounts from accounts.json, rotates usage, and handles Naver login
via undetected-chromedriver.
"""

import json
import time
import random
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

log = logging.getLogger("naver_login")

ACCOUNTS_FILE = Path(__file__).parent / "accounts.json"
NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login?mode=form&url=https%3A%2F%2Fwww.naver.com"


class AccountManager:
    """Manages Naver account pool with rotation and daily limits."""

    def __init__(self, accounts_path: Path = ACCOUNTS_FILE):
        self.accounts_path = accounts_path
        self.accounts = self._load()

    def _load(self) -> list[dict]:
        if not self.accounts_path.exists():
            log.warning("accounts.json not found at %s", self.accounts_path)
            return []
        with open(self.accounts_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        with open(self.accounts_path, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def get_available_account(self) -> Optional[dict]:
        """Get next available account respecting daily limits."""
        today = date.today().isoformat()
        candidates = []

        for acc in self.accounts:
            if acc.get("status") != "active":
                continue

            last_used = acc.get("last_used")
            daily_count = acc.get("daily_count", 0)
            last_date = acc.get("last_date", "")

            # Reset daily count if new day
            if last_date != today:
                acc["daily_count"] = 0
                acc["last_date"] = today
                daily_count = 0

            limit = acc.get("daily_limit", 2)
            if daily_count >= limit:
                continue

            candidates.append(acc)

        if not candidates:
            log.warning("No available accounts (all at daily limit)")
            return None

        # Pick least recently used
        candidates.sort(key=lambda a: a.get("last_used") or "")
        return candidates[0]

    def mark_used(self, account_id: str, success: bool = True):
        """Mark account as used, increment daily count."""
        for acc in self.accounts:
            if acc["id"] == account_id:
                acc["last_used"] = datetime.now().isoformat()
                acc["daily_count"] = acc.get("daily_count", 0) + 1
                acc["last_date"] = date.today().isoformat()
                if not success:
                    acc["fail_count"] = acc.get("fail_count", 0) + 1
                    # Auto-suspend after 3 consecutive failures
                    if acc.get("fail_count", 0) >= 3:
                        acc["status"] = "suspended"
                        log.warning("Account %s suspended (3 failures)", account_id)
                else:
                    acc["fail_count"] = 0
                break
        self._save()

    def get_stats(self) -> dict:
        """Get account pool statistics."""
        today = date.today().isoformat()
        total = len(self.accounts)
        active = sum(1 for a in self.accounts if a.get("status") == "active")
        used_today = sum(
            1 for a in self.accounts
            if a.get("last_date") == today and a.get("daily_count", 0) > 0
        )
        remaining = sum(
            max(0, a.get("daily_limit", 2) - a.get("daily_count", 0))
            for a in self.accounts
            if a.get("status") == "active"
            and (a.get("last_date", "") != today or a.get("daily_count", 0) < a.get("daily_limit", 2))
        )
        return {
            "total": total,
            "active": active,
            "used_today": used_today,
            "remaining_actions": remaining,
        }


def naver_login(driver, account: dict) -> bool:
    """
    Log into Naver using clipboard paste method (bypasses key logging detection).

    Returns True on success, False on failure.
    """
    account_id = account["id"]
    account_pw = account["pw"]

    try:
        log.info("Logging into Naver as [%s]...", account_id)
        driver.get(NAVER_LOGIN_URL)
        time.sleep(random.uniform(2.0, 3.5))

        # Wait for login form
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id"))
        )

        # Clear and fill ID field using JavaScript (bypass keylogger detection)
        id_field = driver.find_element(By.ID, "id")
        driver.execute_script(
            "arguments[0].focus(); arguments[0].value = arguments[1];",
            id_field, account_id
        )
        # Trigger input event so Naver JS recognizes the value
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            id_field
        )
        time.sleep(random.uniform(0.5, 1.0))

        # Clear and fill PW field
        pw_field = driver.find_element(By.ID, "pw")
        driver.execute_script(
            "arguments[0].focus(); arguments[0].value = arguments[1];",
            pw_field, account_pw
        )
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            pw_field
        )
        time.sleep(random.uniform(0.5, 1.2))

        # Click login button
        login_btn = driver.find_element(By.ID, "log.login")
        login_btn.click()
        time.sleep(random.uniform(3.0, 5.0))

        # Check login result
        current_url = driver.current_url

        # Success indicators
        if "naver.com" in current_url and "nidlogin" not in current_url:
            log.info("Login successful: %s", account_id)
            return True

        # Check for captcha or 2FA
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "새로운 환경" in page_text or "기기" in page_text:
            # New device verification — try to skip or handle
            log.warning("New device verification required for %s", account_id)
            # Try clicking "다음에 하기" or similar skip button
            try:
                skip_btns = driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(),'다음에') or contains(text(),'나중에') or contains(text(),'건너뛰기')]"
                )
                for btn in skip_btns:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(2.0)
                        break
            except Exception:
                pass

            # Re-check
            current_url = driver.current_url
            if "naver.com" in current_url and "nidlogin" not in current_url:
                log.info("Login successful after device check: %s", account_id)
                return True

        if "captcha" in page_text.lower() or "자동입력" in page_text:
            log.error("Captcha required during login for %s", account_id)
            return False

        if "아이디" in page_text and "비밀번호" in page_text and "확인" in page_text:
            log.error("Login failed (wrong credentials?) for %s", account_id)
            return False

        log.warning("Login status unclear for %s (url=%s)", account_id, current_url[:80])
        return False

    except TimeoutException:
        log.error("Login page timeout for %s", account_id)
        return False
    except Exception as e:
        log.error("Login error for %s: %s", account_id, str(e))
        return False


def check_logged_in(driver) -> bool:
    """Check if currently logged into Naver."""
    try:
        driver.get("https://www.naver.com")
        time.sleep(2.0)
        # Logged-in users have a profile/logout element
        page = driver.page_source
        return "로그아웃" in page or "MY" in page or "내 프로필" in page
    except Exception:
        return False
