"""
Human-like behavior simulation for Selenium.
Mouse movements, scrolling, reading pauses, product browsing.
"""

import random
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


class HumanBehavior:
    """Simulates human browsing behavior with Selenium WebDriver."""

    def __init__(self, driver):
        self.driver = driver

    def random_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        time.sleep(min_sec + (max_sec - min_sec) * (random.random() ** 1.5))

    def scroll_down(self, pixels: int = None):
        """Scroll down with variable speed."""
        if pixels is None:
            pixels = random.randint(200, 600)

        # Break into smaller chunks
        chunks = random.randint(3, 6)
        chunk_size = pixels / chunks

        for _ in range(chunks):
            amount = int(chunk_size * random.uniform(0.7, 1.3))
            self.driver.execute_script(f"window.scrollBy(0, {amount})")
            time.sleep(random.uniform(0.05, 0.15))

        time.sleep(random.uniform(0.3, 1.0))

    def scroll_up(self, pixels: int = None):
        if pixels is None:
            pixels = random.randint(100, 300)
        self.scroll_down(-pixels)

    def scroll_to_element(self, element):
        """Scroll element into view with human-like behavior."""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'})",
            element,
        )
        time.sleep(random.uniform(0.5, 1.0))

    def scroll_to_top(self):
        self.driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'})")
        time.sleep(random.uniform(1.0, 2.0))

    def human_click(self, element):
        """Click with slight offset from center (humans don't click exact center)."""
        try:
            action = ActionChains(self.driver)
            # Move with small random offset
            x_offset = random.randint(-5, 5)
            y_offset = random.randint(-3, 3)
            action.move_to_element_with_offset(element, x_offset, y_offset)
            action.pause(random.uniform(0.1, 0.3))
            action.click()
            action.perform()
        except Exception:
            # Fallback to regular click
            element.click()

    def move_mouse_random(self):
        """Move mouse to a random visible area."""
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            vw = self.driver.execute_script("return window.innerWidth")
            vh = self.driver.execute_script("return window.innerHeight")

            action = ActionChains(self.driver)
            action.move_to_element_with_offset(
                body,
                random.randint(100, max(101, vw - 100)),
                random.randint(100, max(101, vh - 100)),
            )
            action.perform()
        except Exception:
            pass

    def simulate_reading(self, min_sec: float = 3.0, max_sec: float = 8.0):
        """Simulate reading: scroll, pause, move mouse."""
        duration = random.uniform(min_sec, max_sec)
        elapsed = 0.0

        while elapsed < duration:
            action = random.choices(
                ["scroll_down", "scroll_up", "pause", "mouse_move"],
                weights=[0.4, 0.1, 0.3, 0.2],
            )[0]

            if action == "scroll_down":
                self.scroll_down(random.randint(100, 400))
                elapsed += 1.5
            elif action == "scroll_up":
                self.scroll_up(random.randint(50, 200))
                elapsed += 1.0
            elif action == "pause":
                pause = random.uniform(1.0, 3.0)
                time.sleep(pause)
                elapsed += pause
            elif action == "mouse_move":
                self.move_mouse_random()
                elapsed += 0.5

    def simulate_product_browse(self, min_sec: float = 30.0, max_sec: float = 90.0):
        """Simulate browsing a product page thoroughly."""
        duration = random.uniform(min_sec, max_sec)
        elapsed = 0.0

        while elapsed < duration:
            action = random.choices(
                ["scroll_read", "check_reviews", "look_at_images", "idle"],
                weights=[0.35, 0.2, 0.25, 0.2],
            )[0]

            if action == "scroll_read":
                for _ in range(random.randint(2, 5)):
                    self.scroll_down(random.randint(150, 500))
                    time.sleep(random.uniform(1.0, 3.0))
                elapsed += 8.0

            elif action == "check_reviews":
                try:
                    review_tabs = self.driver.find_elements(
                        By.XPATH,
                        "//*[contains(text(),'리뷰') or contains(text(),'상품평') or contains(text(),'후기')]"
                    )
                    clickable = [
                        el for el in review_tabs
                        if el.tag_name in ("a", "button", "span", "div", "li")
                        and el.is_displayed()
                    ]
                    if clickable:
                        target = random.choice(clickable[:3])
                        self.scroll_to_element(target)
                        self.human_click(target)
                        time.sleep(random.uniform(2.0, 4.0))
                except Exception:
                    pass
                elapsed += 5.0

            elif action == "look_at_images":
                self.scroll_to_top()
                time.sleep(random.uniform(2.0, 4.0))
                try:
                    images = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "[class*='thumb'] img, [class*='image'] img, [class*='Image'] img"
                    )
                    visible = [img for img in images if img.is_displayed()]
                    if visible and len(visible) > 1:
                        target = random.choice(visible[:5])
                        self.human_click(target)
                        time.sleep(random.uniform(1.5, 3.0))
                except Exception:
                    pass
                elapsed += 6.0

            elif action == "idle":
                time.sleep(random.uniform(3.0, 8.0))
                elapsed += 5.0
