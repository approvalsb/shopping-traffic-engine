"""
Naver Place Traffic Engine - Selenium + undetected-chromedriver.
Searches keyword → finds place → clicks → browses place detail page.
"""

import sys
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

from human_behavior_selenium import HumanBehavior
from fingerprint import generate_fingerprint
from captcha_solver import CaptchaSolver
from visit_persona import Persona, PersonaBrowser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("place_engine")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


@dataclass
class PlaceCampaign:
    keyword: str          # Search keyword (e.g. "성수동 행정사")
    place_name: str       # Place name to find (e.g. "승인행정사사무소")
    daily_target: int = 100
    dwell_time_min: float = 20.0
    dwell_time_max: float = 60.0


@dataclass
class PlaceResult:
    campaign_keyword: str
    timestamp: str
    success: bool
    duration_sec: float
    place_url: Optional[str] = None
    error: Optional[str] = None
    screenshot: Optional[str] = None


class NaverPlaceEngine:
    """Naver Place traffic engine using undetected-chromedriver."""

    SEARCH_URL = "https://search.naver.com/search.naver"

    def __init__(self, proxy=None, headless=False):
        self.proxy = proxy
        self.headless = headless
        self.driver = None
        self.human = None
        self.captcha_solver = CaptchaSolver()

    def start(self):
        fp = generate_fingerprint()
        options = uc.ChromeOptions()

        w, h = fp["viewport"]["width"], fp["viewport"]["height"]
        options.add_argument(f"--window-size={w},{h}")
        options.add_argument("--lang=ko-KR")

        if self.proxy:
            self._proxy_ext_dir = setup_proxy(options, self.proxy)
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--disable-infobars")
        options.add_argument("--disable-popup-blocking")

        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)

        self.driver = uc.Chrome(options=options, version_main=146)
        self.human = HumanBehavior(self.driver)
        self.driver.set_page_load_timeout(30)

        ua = self.driver.execute_script("return navigator.userAgent")
        log.info("Chrome started (UA=%s...)", ua[:50])

    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        cleanup_proxy_extension(getattr(self, '_proxy_ext_dir', None))
        self._proxy_ext_dir = None
        log.info("Chrome stopped")

    def execute_visit(self, campaign: PlaceCampaign) -> PlaceResult:
        start_time = datetime.now()

        try:
            # 1. Search on Naver
            search_url = f"{self.SEARCH_URL}?where=nexearch&query={quote(campaign.keyword)}"
            log.info("[%s] Searching...", campaign.keyword)
            self.driver.get(search_url)
            time.sleep(random.uniform(3.0, 5.0))

            # 2. Check for block — attempt auto-solve
            if self._check_blocked():
                if self.captcha_solver.enabled:
                    log.info("[%s] Block detected, attempting captcha solve...", campaign.keyword)
                    if not self.captcha_solver.solve_if_needed(self.driver):
                        raise Exception("Blocked by Naver (captcha solve failed)")
                    log.info("[%s] Captcha solved, continuing...", campaign.keyword)
                else:
                    raise Exception("Blocked by Naver (captcha)")

            # 3. Simulate reading search results
            self.human.simulate_reading(min_sec=2.0, max_sec=4.0)

            # 4. Screenshot search results
            ts = datetime.now().strftime("%H%M%S")
            search_shot = str(SCREENSHOT_DIR / f"search_{ts}.png")
            self.driver.save_screenshot(search_shot)
            log.info("[%s] Search screenshot saved", campaign.keyword)

            # 5. Find and click the place
            clicked, place_url = self._find_and_click_place(campaign)

            if not clicked:
                # Scroll and retry
                for _ in range(3):
                    self.human.scroll_down(random.randint(300, 700))
                    time.sleep(random.uniform(1.5, 3.0))
                    clicked, place_url = self._find_and_click_place(campaign)
                    if clicked:
                        break

            if not clicked:
                raise Exception(f"Place not found: {campaign.place_name}")

            # 6. Wait for place page
            time.sleep(random.uniform(2.0, 4.0))

            # 7. Screenshot place detail
            place_shot = str(SCREENSHOT_DIR / f"place_{ts}.png")
            self.driver.save_screenshot(place_shot)
            log.info("[%s] Place screenshot saved", campaign.keyword)

            # 8. Browse place page (persona-driven)
            persona = Persona.generate()
            log.info("[%s] Persona: %s", campaign.keyword, persona.signature())
            browser = PersonaBrowser(self.driver, self.human, persona)
            browser.browse_place(campaign.dwell_time_min, campaign.dwell_time_max)

            # 9. Close tab if new one opened
            self._close_extra_tabs()

            duration = (datetime.now() - start_time).total_seconds()
            log.info("[%s] Visit complete (%.1fs)", campaign.keyword, duration)

            return PlaceResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=True,
                duration_sec=round(duration, 1),
                place_url=place_url,
                screenshot=place_shot,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            log.error("[%s] Failed: %s", campaign.keyword, str(e))

            # Error screenshot
            try:
                err_shot = str(SCREENSHOT_DIR / f"error_{datetime.now().strftime('%H%M%S')}.png")
                self.driver.save_screenshot(err_shot)
            except Exception:
                err_shot = None

            return PlaceResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=False,
                duration_sec=round(duration, 1),
                error=str(e),
                screenshot=err_shot,
            )

    def _check_blocked(self) -> bool:
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            blocked_signals = ["확인을 완료해 주세요", "일시적으로 제한", "captcha", "비정상적인 접근"]
            return any(s in body for s in blocked_signals)
        except Exception:
            return False

    def _find_and_click_place(self, campaign) -> tuple[bool, str]:
        """Find target place in search results and click it."""
        place_name_lower = campaign.place_name.lower()

        try:
            # Strategy 1: Find place links (place.naver.com or m.place.naver.com)
            links = self.driver.find_elements(By.TAG_NAME, "a")
            candidates = []

            for link in links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""

                    if not text or len(text) < 2:
                        continue

                    if place_name_lower not in text.lower():
                        continue

                    score = 0
                    # Place links
                    if "place.naver.com" in href or "m.place.naver.com" in href:
                        score += 20
                    if "map.naver.com" in href:
                        score += 15
                    # Place section in integrated search
                    if "naver.me" in href:
                        score += 10
                    if len(text) > 3:
                        score += 2

                    if score > 0 or place_name_lower in text.lower():
                        candidates.append((score, link, text[:60], href[:120]))

                except StaleElementReferenceException:
                    continue

            # Strategy 2: Find place-specific elements
            if not candidates:
                place_selectors = [
                    "[class*='place'] a",
                    "[class*='Place'] a",
                    "[class*='local'] a",
                    "[class*='biz'] a",
                    "[data-type='place'] a",
                ]
                for sel in place_selectors:
                    try:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            text = el.text.strip()
                            href = el.get_attribute("href") or ""
                            if place_name_lower in text.lower():
                                candidates.append((10, el, text[:60], href[:120]))
                    except Exception:
                        continue

            if not candidates:
                log.warning("[%s] No candidates found for '%s'", campaign.keyword, campaign.place_name)
                return False, ""

            # Pick best match
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_link, match_text, match_href = candidates[0]

            log.info("[%s] Found: %s (href=%s)", campaign.keyword, match_text, match_href[:80])

            # Scroll into view and click
            self.human.scroll_to_element(best_link)
            time.sleep(random.uniform(0.5, 1.5))
            self.human.human_click(best_link)

            # Handle new tab
            time.sleep(2.0)
            handles = self.driver.window_handles
            if len(handles) > 1:
                self.driver.switch_to.window(handles[-1])

            current_url = self.driver.current_url
            log.info("[%s] Landed on: %s", campaign.keyword, current_url[:100])

            return True, current_url

        except Exception as e:
            log.warning("Find place error: %s", e)
            return False, ""

    def _close_extra_tabs(self):
        handles = self.driver.window_handles
        if len(handles) > 1:
            self.driver.close()
            self.driver.switch_to.window(handles[0])

    def _save_log(self, result: PlaceResult):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"place_{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


def run_place_test(keyword: str, place_name: str, count: int = 10,
                   headless: bool = False, delay: tuple = (10.0, 25.0)):
    """Quick test: run N visits to a Naver Place."""
    campaign = PlaceCampaign(
        keyword=keyword,
        place_name=place_name,
        daily_target=count,
        dwell_time_min=20.0,
        dwell_time_max=45.0,
    )

    results = []
    success_count = 0

    for i in range(count):
        log.info("=== Place Visit %d/%d ===", i + 1, count)

        engine = NaverPlaceEngine(headless=headless)
        engine.start()
        try:
            result = engine.execute_visit(campaign)
            engine._save_log(result)
            results.append(result)
            if result.success:
                success_count += 1
        finally:
            engine.stop()

        if i < count - 1:
            d = random.uniform(*delay)
            log.info("Waiting %.1fs...", d)
            time.sleep(d)

    log.info("=== Place Test: %d/%d success (%.0f%%) ===",
             success_count, count, (success_count / count * 100) if count > 0 else 0)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Naver Place Traffic Test")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--place", required=True, help="Place name to find")
    parser.add_argument("--count", type=int, default=10, help="Number of visits")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    args = parser.parse_args()

    run_place_test(
        keyword=args.keyword,
        place_name=args.place,
        count=args.count,
        headless=args.headless,
    )
