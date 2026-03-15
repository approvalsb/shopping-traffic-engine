"""
Naver Shopping Traffic Engine.
Core automation: search keyword → find product → click → browse → exit.
"""

import asyncio
import random
import logging
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext
from fingerprint import generate_fingerprint, get_stealth_script
from human_behavior import (
    human_click,
    human_scroll,
    simulate_reading,
    simulate_product_browse,
    random_delay,
)

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
    product_url: str          # Target product URL (for identification)
    keyword: str              # Search keyword
    product_name: str         # Product name fragment to find in results
    daily_target: int = 100   # Daily visit count
    dwell_time_min: float = 30.0   # Min seconds on product page
    dwell_time_max: float = 90.0   # Max seconds on product page


@dataclass
class ExecutionResult:
    campaign_keyword: str
    timestamp: str
    success: bool
    duration_sec: float
    proxy_ip: Optional[str] = None
    error: Optional[str] = None
    fingerprint_ua: Optional[str] = None


CHROME_USER_DATA_DIR = Path("chrome_profiles")
CHROME_USER_DATA_DIR.mkdir(exist_ok=True)


class NaverShoppingEngine:
    """Automates Naver Shopping search → product click → browse flow."""

    NAVER_SHOPPING_URL = "https://search.shopping.naver.com/search/all"

    def __init__(
        self,
        proxy: Optional[dict] = None,
        headless: bool = True,
        mode: str = "persistent",  # "persistent" | "launch" | "cdp"
        cdp_url: str = None,       # For "cdp" mode: ws://localhost:9222
    ):
        """
        Args:
            proxy: {"server": "http://host:port", "username": "...", "password": "..."}
            headless: Run browser in headless mode
            mode: Browser mode
                - "persistent": Uses Chrome user data dir (best for captcha bypass)
                - "launch": Fresh browser each time (original mode)
                - "cdp": Connect to already-running Chrome via CDP
            cdp_url: Chrome DevTools Protocol URL for "cdp" mode
        """
        self.proxy = proxy
        self.headless = headless
        self.mode = mode
        self.cdp_url = cdp_url
        self._playwright = None
        self._browser = None
        self._persistent_context = None

    async def start(self):
        self._playwright = await async_playwright().start()

        common_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        if self.mode == "cdp":
            # Connect to an already-running Chrome instance
            # Start Chrome manually with: chrome.exe --remote-debugging-port=9222
            url = self.cdp_url or "http://localhost:9222"
            self._browser = await self._playwright.chromium.connect_over_cdp(url)
            log.info("Connected to Chrome via CDP: %s", url)

        elif self.mode == "persistent":
            # Use persistent context with user data dir (cookies/sessions persist)
            fp = generate_fingerprint()
            profile_dir = str(CHROME_USER_DATA_DIR / f"profile_{random.randint(1, 20)}")

            self._persistent_context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=self.headless,
                args=common_args,
                viewport=fp["viewport"],
                user_agent=fp["user_agent"],
                locale=fp["locale"],
                timezone_id=fp["timezone"],
                color_scheme="light",
                permissions=["geolocation"],
                geolocation={"latitude": 37.5665, "longitude": 126.9780},
                proxy=self.proxy,
            )
            stealth_js = get_stealth_script(fp)
            await self._persistent_context.add_init_script(stealth_js)
            self._persistent_context._fingerprint = fp
            log.info("Persistent browser started (profile=%s, headless=%s)", profile_dir, self.headless)

        else:  # "launch"
            launch_opts = {
                "headless": self.headless,
                "args": common_args,
            }
            if self.proxy:
                launch_opts["proxy"] = self.proxy
            self._browser = await self._playwright.chromium.launch(**launch_opts)
            log.info("Browser started (headless=%s)", self.headless)

    async def stop(self):
        if self._persistent_context:
            await self._persistent_context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        log.info("Browser stopped")

    async def _create_context(self) -> BrowserContext:
        """Create a new browser context with randomized fingerprint."""
        # Persistent mode: reuse the persistent context directly
        if self._persistent_context:
            return self._persistent_context

        # Launch/CDP mode: create a new isolated context
        fp = generate_fingerprint()
        stealth_js = get_stealth_script(fp)

        context = await self._browser.new_context(
            viewport=fp["viewport"],
            user_agent=fp["user_agent"],
            locale=fp["locale"],
            timezone_id=fp["timezone"],
            color_scheme=random.choice(["light", "dark", "no-preference"]),
            permissions=["geolocation"],
            geolocation={"latitude": 37.5665, "longitude": 126.9780},
        )

        await context.add_init_script(stealth_js)
        context._fingerprint = fp
        return context

    async def execute_visit(self, campaign: Campaign) -> ExecutionResult:
        """Execute a single visit: search → find → click → browse."""
        start_time = datetime.now()
        context = None

        try:
            context = await self._create_context()
            page = await context.new_page()

            # 1. Navigate to Naver Shopping search
            log.info("[%s] Searching keyword: %s", campaign.keyword, campaign.keyword)
            search_url = f"{self.NAVER_SHOPPING_URL}?query={campaign.keyword}"
            await page.goto(search_url, wait_until="domcontentloaded")
            await asyncio.sleep(random_delay(2.0, 4.0))

            # 2. Simulate reading search results
            await simulate_reading(page, min_sec=2.0, max_sec=5.0)

            # 3. Find target product in results
            found = await self._find_and_click_product(page, campaign)
            if not found:
                # Scroll down and try again (product might be below fold)
                for _ in range(3):
                    await human_scroll(page, "down", random.randint(400, 800))
                    await asyncio.sleep(random_delay(1.0, 2.0))
                    found = await self._find_and_click_product(page, campaign)
                    if found:
                        break

            if not found:
                raise Exception(f"Product not found: {campaign.product_name}")

            # 4. Wait for product page to load
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(random_delay(2.0, 4.0))

            # 5. Simulate browsing the product
            log.info("[%s] Browsing product page...", campaign.keyword)
            await simulate_product_browse(
                page,
                min_sec=campaign.dwell_time_min,
                max_sec=campaign.dwell_time_max,
            )

            duration = (datetime.now() - start_time).total_seconds()
            log.info("[%s] Visit complete (%.1fs)", campaign.keyword, duration)

            result = ExecutionResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=True,
                duration_sec=round(duration, 1),
                fingerprint_ua=context._fingerprint["user_agent"][:60],
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            log.error("[%s] Visit failed: %s", campaign.keyword, str(e))
            result = ExecutionResult(
                campaign_keyword=campaign.keyword,
                timestamp=start_time.isoformat(),
                success=False,
                duration_sec=round(duration, 1),
                error=str(e),
            )

        finally:
            # Don't close persistent context (it's reused across visits)
            if context and context != self._persistent_context:
                await context.close()

        # Save log
        self._save_log(result)
        return result

    async def _find_and_click_product(self, page: Page, campaign: Campaign) -> bool:
        """Find the target product in search results and click it."""
        # Use a broad approach: find all links, check text content
        product_name_lower = campaign.product_name.lower()

        # Strategy 1: Find by link text matching
        all_links = await page.query_selector_all("a")
        candidates = []
        for link in all_links:
            try:
                text = (await link.inner_text()).strip()
                href = await link.get_attribute("href") or ""
                if not text or len(text) < 3:
                    continue
                if product_name_lower in text.lower():
                    # Prefer links that go to shopping/smartstore
                    score = 0
                    if "smartstore" in href or "shopping" in href or "brand.naver" in href:
                        score += 10
                    if "search" not in href:
                        score += 5
                    candidates.append((score, link, text[:60]))
            except Exception:
                continue

        if not candidates:
            # Strategy 2: Find any clickable product-like element
            selectors = [
                "[class*='product'] a",
                "[class*='item'] a[href*='smartstore']",
                "[class*='item'] a[href*='brand.naver']",
                "[class*='Product'] a",
                "[class*='Item'] a",
            ]
            for sel in selectors:
                links = await page.query_selector_all(sel)
                for link in links:
                    try:
                        text = (await link.inner_text()).strip()
                        if product_name_lower in text.lower():
                            candidates.append((5, link, text[:60]))
                    except Exception:
                        continue

        if not candidates:
            return False

        # Sort by score (highest first) and pick the best match
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, best_link, match_text = candidates[0]
        log.info("[%s] Found product: %s", campaign.keyword, match_text)

        await best_link.scroll_into_view_if_needed()
        await asyncio.sleep(random_delay(0.5, 1.5))

        # Handle potential new tab
        try:
            async with page.context.expect_page(timeout=5000) as new_page_info:
                await best_link.click()
            new_page = await new_page_info.value
            await new_page.wait_for_load_state("domcontentloaded")
            # In persistent mode, close the search tab, keep product tab
            if len(page.context.pages) > 1:
                await page.close()
            return True
        except Exception:
            # Opened in same tab
            return True

    def _save_log(self, result: ExecutionResult):
        """Append execution result to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


async def run_campaign_batch(
    campaign: Campaign,
    count: int = 10,
    proxy: Optional[dict] = None,
    proxy_pool = None,
    headless: bool = True,
    delay_between: tuple = (10.0, 30.0),
    mode: str = "persistent",
):
    """
    Run multiple visits for a campaign with delays between each.

    With proxy_pool: creates a new engine per visit (different IP each time).
    Without: reuses one engine for all visits.
    """
    results = []
    success_count = 0

    if proxy_pool:
        # Each visit gets a fresh browser with different proxy IP
        for i in range(count):
            log.info("=== Visit %d/%d ===", i + 1, count)
            visit_proxy = proxy_pool.get_next()
            log.info("Proxy: %s", visit_proxy.get("server", "none") if visit_proxy else "none")

            engine = NaverShoppingEngine(proxy=visit_proxy, headless=headless, mode=mode)
            await engine.start()
            try:
                result = await engine.execute_visit(campaign)
                result.proxy_ip = visit_proxy.get("server", "") if visit_proxy else None
                results.append(result)
                if result.success:
                    success_count += 1
            finally:
                await engine.stop()

            if i < count - 1:
                delay = random.uniform(*delay_between)
                log.info("Waiting %.1fs before next visit...", delay)
                await asyncio.sleep(delay)
    else:
        # Single engine, reuse across visits
        engine = NaverShoppingEngine(proxy=proxy, headless=headless, mode=mode)
        await engine.start()
        try:
            for i in range(count):
                log.info("=== Visit %d/%d ===", i + 1, count)
                result = await engine.execute_visit(campaign)
                results.append(result)
                if result.success:
                    success_count += 1
                if i < count - 1:
                    delay = random.uniform(*delay_between)
                    log.info("Waiting %.1fs before next visit...", delay)
                    await asyncio.sleep(delay)
        finally:
            await engine.stop()

    log.info(
        "=== Batch complete: %d/%d successful (%.0f%%) ===",
        success_count, count, (success_count / count * 100) if count > 0 else 0,
    )
    return results
