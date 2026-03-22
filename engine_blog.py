"""
Naver Blog Traffic Engine - Selenium + undetected-chromedriver.
Searches keyword → clicks Blog tab → finds target post → clicks → browses with dwell time.

Flow:
  1. Naver integrated search (keyword)
  2. Click "블로그" tab (VIEW tab switch)
  3. Find target blog post by title/blog name
  4. Click → enter blog post
  5. Scroll + read + dwell (20~60s)
  6. Exit

This simulates "search → blog click → stay" which improves CTR + dwell time signals.
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
from naver_login import AccountManager, naver_login

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("blog_engine")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


@dataclass
class BlogCampaign:
    keyword: str            # Search keyword (e.g. "성수동 맛집 추천")
    blog_title: str         # Blog post title or partial match (e.g. "성수동 파스타 맛집")
    blog_name: str = ""     # Blog name / author (optional, for disambiguation)
    daily_target: int = 100
    dwell_time_min: float = 20.0
    dwell_time_max: float = 60.0
    logged_in: bool = False       # Use logged-in account for this visit
    engage_like: bool = False     # Click 공감 after browsing
    engage_comment: str = ""      # Post comment text (empty = skip)
    options: list = None          # L2/L3 paid option keys


@dataclass
class BlogResult:
    campaign_keyword: str
    timestamp: str
    success: bool
    duration_sec: float
    blog_url: Optional[str] = None
    error: Optional[str] = None
    screenshot: Optional[str] = None
    account_id: Optional[str] = None
    liked: bool = False
    commented: bool = False


class NaverBlogEngine:
    """Naver Blog traffic engine using undetected-chromedriver."""

    SEARCH_URL = "https://search.naver.com/search.naver"

    def __init__(self, proxy=None, headless=False):
        self.proxy = proxy
        self.headless = headless
        self.driver = None
        self.human = None
        self.captcha_solver = CaptchaSolver()
        self.account_mgr = AccountManager()
        self._logged_in_account = None
        self._proxy_ext_dir = None

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
        cleanup_proxy_extension(self._proxy_ext_dir)
        self._proxy_ext_dir = None
        log.info("Chrome stopped")

    def _do_login(self, campaign: BlogCampaign) -> Optional[str]:
        """Attempt Naver login if campaign requires it. Returns account_id or None."""
        if not campaign.logged_in:
            return None

        account = self.account_mgr.get_available_account()
        if not account:
            log.warning("No available accounts, proceeding without login")
            return None

        success = naver_login(self.driver, account)
        if success:
            self._logged_in_account = account
            self.account_mgr.mark_used(account["id"], success=True)
            log.info("Logged in as [%s]", account["id"])
            time.sleep(random.uniform(1.5, 3.0))
            return account["id"]
        else:
            self.account_mgr.mark_used(account["id"], success=False)
            log.warning("Login failed for [%s], proceeding without login", account["id"])
            return None

    def _execute_blog_l2(self, opts: list):
        """Execute L2 blog behaviors based on selected options."""
        try:
            # blog_like: click 공감 (works without login too, just may not persist)
            if "blog_like" in opts:
                try:
                    self._do_engage_like()
                except Exception as e:
                    log.warning("[L2] blog_like failed: %s", e)

            # blog_comment_view: scroll to comment section and read
            if "blog_comment_view" in opts:
                try:
                    comment_selectors = [
                        "[class*='comment']", "[id*='comment']",
                        "[class*='Comment']", "[class*='reply']",
                    ]
                    found = False
                    for sel in comment_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                self.human.scroll_to_element(el)
                                log.info("[L2] Scrolled to comment section")
                                found = True
                                break
                        if found:
                            break

                    # Also try inside iframe
                    if not found:
                        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                        for iframe in iframes:
                            try:
                                self.driver.switch_to.frame(iframe)
                                for sel in comment_selectors:
                                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                    for el in els:
                                        if el.is_displayed():
                                            self.human.scroll_to_element(el)
                                            log.info("[L2] Scrolled to comment in iframe")
                                            found = True
                                            break
                                    if found:
                                        break
                                self.driver.switch_to.default_content()
                                if found:
                                    break
                            except Exception:
                                self.driver.switch_to.default_content()

                    # Dwell on comments
                    for _ in range(random.randint(2, 4)):
                        self.human.scroll_down(random.randint(100, 300))
                        time.sleep(random.uniform(2.0, 5.0))

                except Exception as e:
                    log.warning("[L2] blog_comment_view failed: %s", e)

            # blog_series: visit another post from same blog
            if "blog_series" in opts:
                try:
                    # Look for other post links in the blog
                    series_selectors = [
                        "[class*='series'] a", "[class*='relate'] a",
                        "[class*='post-list'] a", "[class*='otherPost'] a",
                        "[class*='another'] a", "[class*='prev'] a",
                    ]
                    clicked = False

                    # Try in main page first
                    for sel in series_selectors:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            href = el.get_attribute("href") or ""
                            if el.is_displayed() and "blog" in href:
                                self.human.scroll_to_element(el)
                                time.sleep(random.uniform(0.5, 1.5))
                                self.human.human_click(el)
                                log.info("[L2] Clicked related blog post")
                                clicked = True
                                time.sleep(random.uniform(3.0, 6.0))
                                # Browse the other post briefly
                                for _ in range(random.randint(2, 3)):
                                    self.human.scroll_down(random.randint(200, 500))
                                    time.sleep(random.uniform(1.5, 3.0))
                                # Go back
                                self.driver.back()
                                time.sleep(random.uniform(1.5, 3.0))
                                break
                        if clicked:
                            break

                    # Try inside iframe
                    if not clicked:
                        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                        for iframe in iframes:
                            try:
                                self.driver.switch_to.frame(iframe)
                                for sel in series_selectors:
                                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                    for el in els:
                                        href = el.get_attribute("href") or ""
                                        if el.is_displayed() and href:
                                            self.human.human_click(el)
                                            log.info("[L2] Clicked related post in iframe")
                                            clicked = True
                                            break
                                    if clicked:
                                        break
                                self.driver.switch_to.default_content()
                                if clicked:
                                    time.sleep(random.uniform(3.0, 6.0))
                                    for _ in range(random.randint(2, 3)):
                                        self.human.scroll_down(random.randint(200, 400))
                                        time.sleep(random.uniform(1.5, 3.0))
                                    self.driver.back()
                                    time.sleep(random.uniform(1.5, 3.0))
                                    break
                            except Exception:
                                self.driver.switch_to.default_content()

                except Exception as e:
                    log.warning("[L2] blog_series failed: %s", e)

        except Exception as e:
            log.warning("[L2] Blog L2 error: %s", e)

    def _do_engage_like(self) -> bool:
        """Click 공감/좋아요 button on current blog post."""
        try:
            like_selectors = [
                "//button[contains(@class, 'like')]",
                "//a[contains(@class, 'like')]",
                "//*[contains(@class, 'sympathy')]//button",
                "//*[contains(@class, 'btn_like')]",
                "//span[contains(text(), '공감')]/..",
                "//button[contains(text(), '공감')]",
                "//*[@data-type='like']",
                "//*[contains(@class, 'u_likeit')]//button",
            ]

            for xpath in like_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            self.human.scroll_to_element(el)
                            time.sleep(random.uniform(0.5, 1.5))
                            self.human.human_click(el)
                            log.info("Clicked like/공감 button")
                            time.sleep(random.uniform(1.0, 2.0))
                            return True
                except Exception:
                    continue

            # Fallback: try iframe (Naver blog posts often use iframes)
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    for xpath in like_selectors[:4]:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for el in elements:
                            if el.is_displayed():
                                self.human.human_click(el)
                                log.info("Clicked like inside iframe")
                                self.driver.switch_to.default_content()
                                time.sleep(random.uniform(1.0, 2.0))
                                return True
                    self.driver.switch_to.default_content()
                except Exception:
                    self.driver.switch_to.default_content()
                    continue

            log.warning("Like button not found")
            return False

        except Exception as e:
            log.warning("Like action error: %s", e)
            return False

    def _do_engage_comment(self, text: str) -> bool:
        """Post a comment on current blog post."""
        if not text:
            return False

        try:
            comment_selectors = [
                "//textarea[contains(@placeholder, '댓글')]",
                "//textarea[contains(@class, 'comment')]",
                "//*[contains(@class, 'comment')]//textarea",
                "//textarea[contains(@placeholder, '의견')]",
                "//*[contains(@class, '_commentArea')]//textarea",
            ]

            textarea = None
            for xpath in comment_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            textarea = el
                            break
                    if textarea:
                        break
                except Exception:
                    continue

            # Try inside iframe
            if not textarea:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        self.driver.switch_to.frame(iframe)
                        for xpath in comment_selectors:
                            elements = self.driver.find_elements(By.XPATH, xpath)
                            for el in elements:
                                if el.is_displayed():
                                    textarea = el
                                    break
                            if textarea:
                                break
                        if textarea:
                            break
                        self.driver.switch_to.default_content()
                    except Exception:
                        self.driver.switch_to.default_content()

            if not textarea:
                log.warning("Comment textarea not found")
                return False

            # Click textarea to focus
            self.human.scroll_to_element(textarea)
            time.sleep(random.uniform(0.5, 1.0))
            self.human.human_click(textarea)
            time.sleep(random.uniform(0.5, 1.0))

            # Type comment character by character (human-like)
            for char in text:
                textarea.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            time.sleep(random.uniform(1.0, 2.0))

            # Click submit button
            submit_selectors = [
                "//button[contains(text(), '등록')]",
                "//a[contains(text(), '등록')]",
                "//*[contains(@class, 'comment')]//button[contains(text(), '등록')]",
                "//button[contains(@class, 'btn_register')]",
            ]

            for xpath in submit_selectors:
                try:
                    btns = self.driver.find_elements(By.XPATH, xpath)
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            self.human.human_click(btn)
                            log.info("Comment posted: %s", text[:30])
                            time.sleep(random.uniform(1.5, 3.0))
                            return True
                except Exception:
                    continue

            log.warning("Comment submit button not found")
            return False

        except Exception as e:
            log.warning("Comment action error: %s", e)
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def execute_visit(self, campaign: BlogCampaign) -> BlogResult:
        start_time = datetime.now()
        account_id = None
        liked = False
        commented = False

        try:
            # 0. Login if needed
            account_id = self._do_login(campaign)

            # 1. Search on Naver (integrated search)
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

            # 3. Simulate reading search results briefly
            self.human.simulate_reading(min_sec=1.5, max_sec=3.0)

            # 4. Click "블로그" tab
            blog_tab_clicked = self._click_blog_tab()
            if not blog_tab_clicked:
                # Fallback: search directly in blog tab
                blog_url = f"{self.SEARCH_URL}?where=blog&query={quote(campaign.keyword)}"
                log.info("[%s] Blog tab not found, navigating directly", campaign.keyword)
                self.driver.get(blog_url)
                time.sleep(random.uniform(2.0, 4.0))

            time.sleep(random.uniform(2.0, 4.0))

            # 5. Screenshot blog search results
            ts = datetime.now().strftime("%H%M%S")
            search_shot = str(SCREENSHOT_DIR / f"blog_search_{ts}.png")
            self.driver.save_screenshot(search_shot)
            log.info("[%s] Blog search screenshot saved", campaign.keyword)

            # 6. Simulate reading blog search results
            self.human.simulate_reading(min_sec=1.5, max_sec=3.0)

            # 7. Find and click target blog post
            clicked, blog_url = self._find_and_click_blog(campaign)

            if not clicked:
                # Scroll and retry
                for _ in range(3):
                    self.human.scroll_down(random.randint(300, 700))
                    time.sleep(random.uniform(1.5, 3.0))
                    clicked, blog_url = self._find_and_click_blog(campaign)
                    if clicked:
                        break

            if not clicked:
                raise Exception(f"Blog post not found: {campaign.blog_title}")

            # 8. Wait for blog page to load
            time.sleep(random.uniform(2.0, 4.0))

            # 9. Screenshot blog post
            blog_shot = str(SCREENSHOT_DIR / f"blog_post_{ts}.png")
            self.driver.save_screenshot(blog_shot)
            log.info("[%s] Blog post screenshot saved", campaign.keyword)

            # 10. Browse blog post (persona-driven dwell)
            persona = Persona.generate()
            log.info("[%s] Persona: %s", campaign.keyword, persona.signature())
            browser = PersonaBrowser(self.driver, self.human, persona)
            browser.browse_blog(campaign.dwell_time_min, campaign.dwell_time_max)

            # 11. Engagement actions (logged-in only)
            if account_id:
                if campaign.engage_like:
                    time.sleep(random.uniform(1.0, 3.0))
                    liked = self._do_engage_like()

                if campaign.engage_comment:
                    time.sleep(random.uniform(2.0, 5.0))
                    commented = self._do_engage_comment(campaign.engage_comment)

            # 11a. L2 options — additional blog behaviors
            opts = campaign.options or []
            if opts:
                log.info("[%s] Executing L2 options: %s", campaign.keyword, opts)
                self._execute_blog_l2(opts)

            # 12. Close extra tabs
            self._close_extra_tabs()

            duration = (datetime.now() - start_time).total_seconds()
            log.info("[%s] Visit complete (%.1fs, login=%s, like=%s, comment=%s)",
                     campaign.keyword, duration, account_id or "N", liked, commented)

            return BlogResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=True,
                duration_sec=round(duration, 1),
                blog_url=blog_url,
                screenshot=blog_shot,
                account_id=account_id,
                liked=liked,
                commented=commented,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            log.error("[%s] Failed: %s", campaign.keyword, str(e))

            try:
                err_shot = str(SCREENSHOT_DIR / f"error_{datetime.now().strftime('%H%M%S')}.png")
                self.driver.save_screenshot(err_shot)
            except Exception:
                err_shot = None

            return BlogResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=False,
                duration_sec=round(duration, 1),
                error=str(e),
                screenshot=err_shot,
                account_id=account_id,
            )

    def _check_blocked(self) -> bool:
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            blocked_signals = ["확인을 완료해 주세요", "일시적으로 제한", "captcha", "비정상적인 접근"]
            return any(s in body for s in blocked_signals)
        except Exception:
            return False

    def _click_blog_tab(self) -> bool:
        """Click the Blog tab in Naver search results."""
        try:
            # Strategy 1: Find tab by text "블로그"
            tab_selectors = [
                "//a[contains(text(), '블로그')]",
                "//div[contains(@class, 'tab')]//a[contains(text(), '블로그')]",
                "//ul[contains(@class, 'tab')]//a[contains(text(), '블로그')]",
            ]

            for xpath in tab_selectors:
                try:
                    tabs = self.driver.find_elements(By.XPATH, xpath)
                    for tab in tabs:
                        if tab.is_displayed() and len(tab.text.strip()) < 10:
                            self.human.scroll_to_element(tab)
                            time.sleep(random.uniform(0.3, 0.8))
                            self.human.human_click(tab)
                            log.info("Clicked blog tab via XPATH")
                            return True
                except Exception:
                    continue

            # Strategy 2: Find by href containing where=blog
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    if "where=blog" in href and "블로그" in text:
                        self.human.human_click(link)
                        log.info("Clicked blog tab via href")
                        return True
                except StaleElementReferenceException:
                    continue

            # Strategy 3: CSS selector for Naver's tab structure
            css_selectors = [
                ".api_flicking_wrap a",
                ".sc_new_tab a",
                "[role='tablist'] a",
            ]
            for css in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, css)
                    for el in elements:
                        if "블로그" in el.text:
                            self.human.human_click(el)
                            log.info("Clicked blog tab via CSS: %s", css)
                            return True
                except Exception:
                    continue

            log.warning("Blog tab not found")
            return False

        except Exception as e:
            log.warning("Error clicking blog tab: %s", e)
            return False

    def _find_and_click_blog(self, campaign: BlogCampaign) -> tuple[bool, str]:
        """Find target blog post in blog search results and click it."""
        title_lower = campaign.blog_title.lower()
        blog_name_lower = campaign.blog_name.lower() if campaign.blog_name else ""

        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            candidates = []

            for link in links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""

                    if not text or len(text) < 3:
                        continue

                    text_lower = text.lower()

                    # Check title match
                    title_match = title_lower in text_lower
                    # Check if any significant portion of title words match
                    if not title_match:
                        title_words = [w for w in title_lower.split() if len(w) >= 2]
                        if title_words:
                            matched_words = sum(1 for w in title_words if w in text_lower)
                            title_match = matched_words >= len(title_words) * 0.5

                    if not title_match:
                        continue

                    score = 0

                    # Blog-specific URLs
                    if "blog.naver.com" in href:
                        score += 25
                    if "m.blog.naver.com" in href:
                        score += 20
                    if "post.naver.com" in href:
                        score += 15
                    # Blog section links in search results
                    if "blog.me" in href:
                        score += 15

                    # Blog name match (if provided)
                    if blog_name_lower and blog_name_lower in text_lower:
                        score += 10

                    # Longer text = more likely the actual title (not nav)
                    if len(text) > 15:
                        score += 3
                    if len(text) > 30:
                        score += 2

                    # Penalize non-blog links
                    if "search.naver.com" in href and "where=blog" not in href:
                        score -= 5

                    if score > 0 or title_match:
                        candidates.append((score, link, text[:80], href[:120]))

                except StaleElementReferenceException:
                    continue

            # Strategy 2: Blog-specific containers
            if not candidates:
                blog_selectors = [
                    "[class*='blog'] a",
                    "[class*='Blog'] a",
                    "[class*='total_area'] a",
                    "[class*='api_txt_lines'] a",
                    ".sp_blog a",
                ]
                for sel in blog_selectors:
                    try:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            text = el.text.strip()
                            href = el.get_attribute("href") or ""
                            if title_lower in text.lower():
                                candidates.append((10, el, text[:80], href[:120]))
                    except Exception:
                        continue

            if not candidates:
                log.warning("[%s] No blog candidates found for '%s'",
                          campaign.keyword, campaign.blog_title)
                return False, ""

            # Pick best match
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_link, match_text, match_href = candidates[0]

            log.info("[%s] Found blog: %s (href=%s)",
                    campaign.keyword, match_text[:60], match_href[:80])

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
            log.warning("Find blog error: %s", e)
            return False, ""

    def _close_extra_tabs(self):
        handles = self.driver.window_handles
        if len(handles) > 1:
            self.driver.close()
            self.driver.switch_to.window(handles[0])

    def _save_log(self, result: BlogResult):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"blog_{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


def run_blog_test(keyword: str, blog_title: str, blog_name: str = "",
                  count: int = 10, headless: bool = False,
                  delay: tuple = (10.0, 25.0),
                  logged_in: bool = False, engage_like: bool = False,
                  engage_comment: str = ""):
    """Quick test: run N visits to a Naver Blog post."""
    campaign = BlogCampaign(
        keyword=keyword,
        blog_title=blog_title,
        blog_name=blog_name,
        daily_target=count,
        dwell_time_min=20.0,
        dwell_time_max=45.0,
        logged_in=logged_in,
        engage_like=engage_like,
        engage_comment=engage_comment,
    )

    results = []
    success_count = 0

    for i in range(count):
        log.info("=== Blog Visit %d/%d ===", i + 1, count)

        engine = NaverBlogEngine(headless=headless)
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

    log.info("=== Blog Test: %d/%d success (%.0f%%) ===",
             success_count, count, (success_count / count * 100) if count > 0 else 0)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Naver Blog Traffic Test")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--title", required=True, help="Blog post title to find")
    parser.add_argument("--blog-name", default="", help="Blog name (optional)")
    parser.add_argument("--count", type=int, default=10, help="Number of visits")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--login", action="store_true", help="Use logged-in account")
    parser.add_argument("--like", action="store_true", help="Click 공감 (requires --login)")
    parser.add_argument("--comment", default="", help="Post comment text (requires --login)")
    parser.add_argument("--accounts", action="store_true", help="Show account pool stats")
    args = parser.parse_args()

    if args.accounts:
        mgr = AccountManager()
        stats = mgr.get_stats()
        print(f"\n=== Account Pool ===")
        print(f"  Total:     {stats['total']}")
        print(f"  Active:    {stats['active']}")
        print(f"  Used today: {stats['used_today']}")
        print(f"  Remaining:  {stats['remaining_actions']} actions")
        for acc in mgr.accounts:
            status = acc.get('status', '?')
            used = acc.get('daily_count', 0)
            limit = acc.get('daily_limit', 2)
            print(f"  [{status:>9}] {acc['id']:<20} {used}/{limit} today")
    else:
        run_blog_test(
            keyword=args.keyword,
            blog_title=args.title,
            blog_name=args.blog_name,
            count=args.count,
            headless=args.headless,
            logged_in=args.login,
            engage_like=args.like,
            engage_comment=args.comment,
        )
