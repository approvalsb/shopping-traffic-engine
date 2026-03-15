"""
Human-like behavior simulation for browser automation.
Randomizes mouse movements, scroll patterns, timing, and interactions.
"""

import random
import math
import asyncio
from typing import Tuple


def random_delay(min_sec: float = 0.5, max_sec: float = 2.0) -> float:
    """Generate a human-like random delay (slightly skewed toward shorter)."""
    return min_sec + (max_sec - min_sec) * (random.random() ** 1.5)


def bezier_curve_points(
    start: Tuple[int, int],
    end: Tuple[int, int],
    steps: int = 20,
) -> list[Tuple[int, int]]:
    """Generate bezier curve points for natural mouse movement."""
    sx, sy = start
    ex, ey = end

    # Random control points for natural curve
    cx1 = sx + random.randint(-100, 100)
    cy1 = sy + random.randint(-100, 100)
    cx2 = ex + random.randint(-50, 50)
    cy2 = ey + random.randint(-50, 50)

    points = []
    for i in range(steps + 1):
        t = i / steps
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        x = mt3 * sx + 3 * mt2 * t * cx1 + 3 * mt * t2 * cx2 + t3 * ex
        y = mt3 * sy + 3 * mt2 * t * cy1 + 3 * mt * t2 * cy2 + t3 * ey

        # Add slight jitter
        x += random.randint(-2, 2)
        y += random.randint(-2, 2)

        points.append((int(x), int(y)))

    return points


async def human_mouse_move(page, x: int, y: int):
    """Move mouse to target with natural bezier curve motion."""
    current = await page.evaluate("() => ({x: window._mouseX || 0, y: window._mouseY || 0})")
    start = (current.get("x", random.randint(100, 500)), current.get("y", random.randint(100, 300)))
    points = bezier_curve_points(start, (x, y), steps=random.randint(15, 30))

    for px, py in points:
        await page.mouse.move(px, py)
        await asyncio.sleep(random.uniform(0.005, 0.02))

    # Track position
    await page.evaluate(f"() => {{ window._mouseX = {x}; window._mouseY = {y}; }}")


async def human_click(page, selector: str = None, x: int = None, y: int = None):
    """Click with human-like behavior: move → hover → click."""
    if selector:
        element = await page.query_selector(selector)
        if not element:
            return False
        box = await element.bounding_box()
        if not box:
            return False
        # Click at random point within element (not exact center)
        x = int(box["x"] + box["width"] * random.uniform(0.2, 0.8))
        y = int(box["y"] + box["height"] * random.uniform(0.3, 0.7))

    if x is not None and y is not None:
        await human_mouse_move(page, x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))  # Hover pause
        await page.mouse.click(x, y)
        return True
    return False


async def human_scroll(page, direction: str = "down", amount: int = None):
    """Scroll with variable speed and pauses, like a real person reading."""
    if amount is None:
        amount = random.randint(200, 600)

    delta = amount if direction == "down" else -amount

    # Break scroll into smaller chunks with varying speeds
    chunks = random.randint(3, 8)
    chunk_size = delta / chunks

    for i in range(chunks):
        variation = chunk_size * random.uniform(0.7, 1.3)
        await page.mouse.wheel(0, variation)
        await asyncio.sleep(random.uniform(0.05, 0.15))

    # Reading pause after scroll
    await asyncio.sleep(random.uniform(0.5, 2.0))


async def simulate_reading(page, min_sec: float = 3.0, max_sec: float = 8.0):
    """Simulate reading: random scrolls + pauses."""
    duration = random.uniform(min_sec, max_sec)
    elapsed = 0.0

    while elapsed < duration:
        action = random.choices(
            ["scroll_down", "scroll_up", "pause", "small_mouse_move"],
            weights=[0.4, 0.1, 0.3, 0.2],
        )[0]

        if action == "scroll_down":
            await human_scroll(page, "down", random.randint(100, 400))
            elapsed += 1.5
        elif action == "scroll_up":
            await human_scroll(page, "up", random.randint(50, 200))
            elapsed += 1.0
        elif action == "pause":
            pause = random.uniform(1.0, 3.0)
            await asyncio.sleep(pause)
            elapsed += pause
        elif action == "small_mouse_move":
            vw = await page.evaluate("() => window.innerWidth")
            vh = await page.evaluate("() => window.innerHeight")
            await human_mouse_move(
                page,
                random.randint(100, vw - 100),
                random.randint(100, vh - 100),
            )
            elapsed += 0.8


async def simulate_product_browse(page, min_sec: float = 30.0, max_sec: float = 90.0):
    """Simulate browsing a product page: scroll through images, read details, etc."""
    duration = random.uniform(min_sec, max_sec)
    elapsed = 0.0

    while elapsed < duration:
        action = random.choices(
            ["scroll_read", "check_reviews", "look_at_images", "idle_pause"],
            weights=[0.35, 0.2, 0.25, 0.2],
        )[0]

        if action == "scroll_read":
            for _ in range(random.randint(2, 5)):
                await human_scroll(page, "down", random.randint(150, 500))
                await asyncio.sleep(random.uniform(1.0, 3.0))
            elapsed += 8.0

        elif action == "check_reviews":
            # Try to click review tab if exists
            review_selectors = [
                "a[href*='review']",
                "[class*='review']",
                "text=리뷰",
                "text=상품평",
            ]
            for sel in review_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await human_click(page, sel)
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                        break
                except Exception:
                    continue
            elapsed += 5.0

        elif action == "look_at_images":
            # Scroll back to top to see product images
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(random.uniform(2.0, 4.0))
            # Try clicking image thumbnails
            try:
                thumbs = await page.query_selector_all("[class*='thumb'] img, [class*='image'] img")
                if thumbs and len(thumbs) > 1:
                    idx = random.randint(0, min(len(thumbs) - 1, 4))
                    await thumbs[idx].click()
                    await asyncio.sleep(random.uniform(1.5, 3.0))
            except Exception:
                pass
            elapsed += 6.0

        elif action == "idle_pause":
            await asyncio.sleep(random.uniform(3.0, 8.0))
            elapsed += 5.0
