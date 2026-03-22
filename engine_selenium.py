"""
Naver Shopping Traffic Engine - Selenium + undetected-chromedriver version.
Uses real Chrome binary with automatic bot detection bypass.
"""

import time
import random
import logging
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import quote

import undetected_chromedriver as uc
from proxy_auth import setup_proxy, cleanup_proxy_extension
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

from human_behavior_selenium import HumanBehavior
from fingerprint import generate_fingerprint
from captcha_solver import CaptchaSolver
from visit_persona import Persona, PersonaBrowser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("engine")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class Campaign:
    product_url: str
    keyword: str
    product_name: str
    daily_target: int = 100
    dwell_time_min: float = 30.0
    dwell_time_max: float = 90.0
    options: list = None  # L2/L3 paid option keys


@dataclass
class ExecutionResult:
    campaign_keyword: str
    timestamp: str
    success: bool
    duration_sec: float
    proxy_ip: Optional[str] = None
    error: Optional[str] = None
    fingerprint_ua: Optional[str] = None


class NaverShoppingEngine:
    """Naver Shopping traffic engine using undetected-chromedriver."""

    # Use integrated search (not shopping-specific) to avoid shopping IP ban
    SEARCH_URL = "https://search.naver.com/search.naver"

    def __init__(
        self,
        proxy: Optional[str] = None,
        headless: bool = False,
        profile_dir: Optional[str] = None,
    ):
        """
        Args:
            proxy: Proxy string "host:port" or "user:pass@host:port"
            headless: Run headless (less reliable for detection bypass)
            profile_dir: Chrome user data dir (for cookie persistence)
        """
        self.proxy = proxy
        self.headless = headless
        self.profile_dir = profile_dir
        self.driver = None
        self.human = None
        self.captcha_solver = CaptchaSolver()

    def start(self):
        """Launch Chrome with undetected-chromedriver."""
        fp = generate_fingerprint()

        options = uc.ChromeOptions()

        # Window size
        w, h = fp["viewport"]["width"], fp["viewport"]["height"]
        options.add_argument(f"--window-size={w},{h}")

        # Language
        options.add_argument("--lang=ko-KR")

        # Proxy
        if self.proxy:
            self._proxy_ext_dir = setup_proxy(options, self.proxy)

        # Profile persistence
        if self.profile_dir:
            options.add_argument(f"--user-data-dir={self.profile_dir}")

        # Headless (use new headless mode if needed)
        if self.headless:
            options.add_argument("--headless=new")

        # Disable automation indicators
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-popup-blocking")

        # Preferences to look more human
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)

        self.driver = uc.Chrome(options=options, version_main=146)
        self.human = HumanBehavior(self.driver)

        # Set page load timeout
        self.driver.set_page_load_timeout(30)

        ua = self.driver.execute_script("return navigator.userAgent")
        webdriver_flag = self.driver.execute_script("return navigator.webdriver")
        log.info("Chrome started (UA=%s..., webdriver=%s)", ua[:50], webdriver_flag)

    def stop(self):
        """Close browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        cleanup_proxy_extension(getattr(self, '_proxy_ext_dir', None))
        self._proxy_ext_dir = None
        log.info("Chrome stopped")

    def execute_visit(self, campaign: Campaign) -> ExecutionResult:
        """Execute: search → find product → click → browse → exit."""
        start_time = datetime.now()

        try:
            # 1. Navigate to Naver integrated search (shopping results included)
            search_url = f"{self.SEARCH_URL}?where=nexearch&query={quote(campaign.keyword)}"
            log.info("[%s] Searching...", campaign.keyword)
            self.driver.get(search_url)

            # Wait for page to render (SPA)
            time.sleep(random.uniform(3.0, 5.0))

            # 2. Check for captcha/block — attempt auto-solve
            if self._check_blocked():
                if self.captcha_solver.enabled:
                    log.info("[%s] Block detected, attempting captcha solve...", campaign.keyword)
                    if not self.captcha_solver.solve_if_needed(self.driver):
                        raise Exception("Blocked by Naver (captcha solve failed)")
                    log.info("[%s] Captcha solved, continuing...", campaign.keyword)
                else:
                    raise Exception("Blocked by Naver (captcha or IP ban)")

            # 3. Simulate reading search results
            self.human.simulate_reading(min_sec=2.0, max_sec=4.0)

            # 4. Find and click target product
            clicked = self._find_and_click_product(campaign)
            if not clicked:
                # Scroll down and retry
                for _ in range(3):
                    self.human.scroll_down(random.randint(300, 700))
                    time.sleep(random.uniform(1.5, 3.0))
                    clicked = self._find_and_click_product(campaign)
                    if clicked:
                        break

            if not clicked:
                raise Exception(f"Product not found: {campaign.product_name}")

            # 5. Handle new tab (product pages often open in new tab)
            self._switch_to_product_tab()
            time.sleep(random.uniform(2.0, 4.0))

            # 6. Browse product page (persona-driven)
            persona = Persona.generate()
            log.info("[%s] Persona: %s", campaign.keyword, persona.signature())
            pbrowser = PersonaBrowser(self.driver, self.human, persona)
            pbrowser.browse_product(campaign.dwell_time_min, campaign.dwell_time_max)

            # 6a. L2 options — additional shopping behaviors
            opts = campaign.options or []
            if opts:
                log.info("[%s] Executing L2 options: %s", campaign.keyword, opts)
                self._execute_shopping_l2(opts)

            # 7. Close product tab, return to search
            self._close_product_tab()

            duration = (datetime.now() - start_time).total_seconds()
            log.info("[%s] Visit complete (%.1fs)", campaign.keyword, duration)

            result = ExecutionResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=True,
                duration_sec=round(duration, 1),
                fingerprint_ua=self.driver.execute_script("return navigator.userAgent")[:60],
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            log.error("[%s] Failed: %s", campaign.keyword, str(e))
            result = ExecutionResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=False,
                duration_sec=round(duration, 1),
                error=str(e),
            )

        self._save_log(result)
        return result

    def _execute_shopping_l2(self, opts: list):
        """Execute L2 shopping behaviors based on selected options."""
        try:
            # wish_click: click 찜/좋아요
            if "wish_click" in opts:
                try:
                    selectors = [
                        "button[class*='wish']", "button[class*='like']",
                        "a[class*='wish']", "button[class*='zzim']",
                        "[class*='_productWish']", "[class*='favoriteBtn']",
                    ]
                    for sel in selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                self.human.scroll_to_element(el)
                                time.sleep(random.uniform(0.5, 1.5))
                                self.human.human_click(el)
                                log.info("[L2] Clicked wish/like button")
                                time.sleep(random.uniform(1.0, 2.0))
                                break
                        else:
                            continue
                        break
                except Exception as e:
                    log.warning("[L2] wish_click failed: %s", e)

            # review_dwell: scroll to reviews and read
            if "review_dwell" in opts:
                try:
                    review_selectors = [
                        "[class*='review']", "[id*='review']",
                        "a[href*='review']", "[class*='_review']",
                    ]
                    for sel in review_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed() and el.tag_name in ("a", "button", "li", "div"):
                                self.human.scroll_to_element(el)
                                try:
                                    self.human.human_click(el)
                                except Exception:
                                    pass
                                log.info("[L2] Scrolled to review section")
                                # Dwell on reviews
                                for _ in range(random.randint(2, 4)):
                                    self.human.scroll_down(random.randint(200, 400))
                                    time.sleep(random.uniform(2.0, 5.0))
                                break
                        else:
                            continue
                        break
                except Exception as e:
                    log.warning("[L2] review_dwell failed: %s", e)

            # cart_add: click add-to-cart button
            if "cart_add" in opts:
                try:
                    cart_selectors = [
                        "button[class*='cart']", "button[class*='basket']",
                        "[class*='addCart']", "[class*='_cart']",
                        "a[class*='cart']",
                    ]
                    for sel in cart_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                self.human.scroll_to_element(el)
                                time.sleep(random.uniform(0.5, 1.0))
                                self.human.human_click(el)
                                log.info("[L2] Clicked add-to-cart")
                                time.sleep(random.uniform(1.5, 3.0))
                                # Close cart popup if any
                                try:
                                    close_btns = self.driver.find_elements(By.CSS_SELECTOR, "[class*='close'], [class*='cancel']")
                                    for cb in close_btns:
                                        if cb.is_displayed():
                                            cb.click()
                                            break
                                except Exception:
                                    pass
                                break
                        else:
                            continue
                        break
                except Exception as e:
                    log.warning("[L2] cart_add failed: %s", e)

            # compare_behavior: scroll back up, look at other products
            if "compare_behavior" in opts:
                try:
                    log.info("[L2] Simulating compare behavior")
                    self.human.scroll_up(random.randint(500, 1000))
                    time.sleep(random.uniform(1.0, 2.0))
                    self.human.scroll_down(random.randint(300, 600))
                    time.sleep(random.uniform(2.0, 4.0))
                except Exception as e:
                    log.warning("[L2] compare_behavior failed: %s", e)

            # price_compare: click price comparison tab
            if "price_compare" in opts:
                try:
                    price_selectors = [
                        "a[href*='price']", "[class*='priceCompare']",
                        "[class*='_price']", "a[class*='compare']",
                    ]
                    for sel in price_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                self.human.scroll_to_element(el)
                                self.human.human_click(el)
                                log.info("[L2] Clicked price compare")
                                time.sleep(random.uniform(3.0, 6.0))
                                break
                        else:
                            continue
                        break
                except Exception as e:
                    log.warning("[L2] price_compare failed: %s", e)

            # inquiry_click: open Q&A section
            if "inquiry_click" in opts:
                try:
                    qa_selectors = [
                        "[class*='inquiry']", "[class*='qna']",
                        "a[href*='inquiry']", "a[href*='qna']",
                        "[class*='_qa']",
                    ]
                    for sel in qa_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                self.human.scroll_to_element(el)
                                self.human.human_click(el)
                                log.info("[L2] Opened Q&A section")
                                time.sleep(random.uniform(2.0, 4.0))
                                break
                        else:
                            continue
                        break
                except Exception as e:
                    log.warning("[L2] inquiry_click failed: %s", e)

            # store_browse: visit other products in same store
            if "store_browse" in opts:
                try:
                    store_selectors = [
                        "a[href*='smartstore']", "[class*='storeName']",
                        "[class*='_store']", "a[class*='store']",
                    ]
                    for sel in store_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                self.human.scroll_to_element(el)
                                self.human.human_click(el)
                                log.info("[L2] Browsing store page")
                                time.sleep(random.uniform(3.0, 6.0))
                                # Scroll around the store
                                for _ in range(random.randint(2, 3)):
                                    self.human.scroll_down(random.randint(300, 600))
                                    time.sleep(random.uniform(1.5, 3.0))
                                break
                        else:
                            continue
                        break
                except Exception as e:
                    log.warning("[L2] store_browse failed: %s", e)

            # sort_filter: click a sort option (review/price)
            if "sort_filter" in opts:
                try:
                    sort_selectors = [
                        "[class*='sort'] a", "[class*='filter'] button",
                        "[class*='_sortFilter']", "a[class*='sort']",
                    ]
                    for sel in sort_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if len(els) > 1:
                            el = random.choice(els[1:])  # skip first (default sort)
                            if el.is_displayed():
                                self.human.human_click(el)
                                log.info("[L2] Clicked sort/filter")
                                time.sleep(random.uniform(2.0, 4.0))
                                break
                except Exception as e:
                    log.warning("[L2] sort_filter failed: %s", e)

        except Exception as e:
            log.warning("[L2] Shopping L2 error: %s", e)

    def _check_blocked(self) -> bool:
        """Check if Naver blocked us (captcha or restriction page)."""
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            blocked_signals = [
                "확인을 완료해 주세요",
                "일시적으로 제한",
                "captcha",
                "비정상적인 접근",
            ]
            return any(s in body for s in blocked_signals)
        except Exception:
            return False

    def _find_and_click_product(self, campaign: Campaign) -> bool:
        """Find target product in search results and click it."""
        product_name_lower = campaign.product_name.lower()

        try:
            # Get all links on page
            links = self.driver.find_elements(By.TAG_NAME, "a")
            candidates = []

            for link in links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""

                    if not text or len(text) < 3:
                        continue
                    if product_name_lower not in text.lower():
                        continue

                    score = 0
                    # cr.shopping links from integrated search are the primary target
                    if "cr.shopping.naver" in href or "cr3.shopping.naver" in href:
                        score += 15
                    if any(x in href for x in ["smartstore", "brand.naver", "shopping.naver.com/product"]):
                        score += 10
                    if "search.naver.com" not in href:
                        score += 5
                    if len(text) > 10:
                        score += 2

                    candidates.append((score, link, text[:60], href[:100]))
                except StaleElementReferenceException:
                    continue

            if not candidates:
                return False

            # Pick best match
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_link, match_text, match_href = candidates[0]

            log.info("[%s] Found: %s", campaign.keyword, match_text)

            # Scroll into view and click with human behavior
            self.human.scroll_to_element(best_link)
            time.sleep(random.uniform(0.5, 1.5))
            self.human.human_click(best_link)

            return True

        except Exception as e:
            log.warning("Find product error: %s", e)
            return False

    def _switch_to_product_tab(self):
        """Switch to newly opened product tab."""
        handles = self.driver.window_handles
        if len(handles) > 1:
            self.driver.switch_to.window(handles[-1])
            log.debug("Switched to product tab")
        # If no new tab, product opened in same tab — that's fine

    def _close_product_tab(self):
        """Close product tab and return to search tab."""
        handles = self.driver.window_handles
        if len(handles) > 1:
            self.driver.close()
            self.driver.switch_to.window(handles[0])

    def _save_log(self, result: ExecutionResult):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


def run_campaign_batch(
    campaign: Campaign,
    count: int = 10,
    proxy: Optional[str] = None,
    proxy_pool=None,
    headless: bool = False,
    delay_between: tuple = (10.0, 30.0),
    profile_dir: Optional[str] = None,
):
    """Run multiple visits. With proxy_pool, rotates IP per visit."""
    results = []
    success_count = 0

    if proxy_pool:
        for i in range(count):
            log.info("=== Visit %d/%d ===", i + 1, count)
            visit_proxy = proxy_pool.get_next()
            proxy_server = visit_proxy.get("server", "").replace("http://", "") if visit_proxy else None

            engine = NaverShoppingEngine(proxy=proxy_server, headless=headless, profile_dir=profile_dir)
            engine.start()
            try:
                result = engine.execute_visit(campaign)
                result.proxy_ip = proxy_server
                results.append(result)
                if result.success:
                    success_count += 1
            finally:
                engine.stop()

            if i < count - 1:
                delay = random.uniform(*delay_between)
                log.info("Waiting %.1fs...", delay)
                time.sleep(delay)
    else:
        engine = NaverShoppingEngine(proxy=proxy, headless=headless, profile_dir=profile_dir)
        engine.start()
        try:
            for i in range(count):
                log.info("=== Visit %d/%d ===", i + 1, count)
                result = engine.execute_visit(campaign)
                results.append(result)
                if result.success:
                    success_count += 1
                if i < count - 1:
                    delay = random.uniform(*delay_between)
                    log.info("Waiting %.1fs...", delay)
                    time.sleep(delay)
        finally:
            engine.stop()

    log.info(
        "=== Batch: %d/%d success (%.0f%%) ===",
        success_count, count, (success_count / count * 100) if count > 0 else 0,
    )
    return results
