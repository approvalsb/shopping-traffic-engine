"""
Visit Persona Generator — every visit is truly unique.

Instead of picking from fixed action pools, generates a unique "persona"
per visit with continuous personality traits. All behaviors derive from
these traits, making the probability of two identical visits near zero.

With 15+ continuous parameters each in [0,1], the behavioral space is
effectively infinite. Two visits will never look the same.
"""

import random
import time
import math
import logging
from dataclasses import dataclass, field

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

log = logging.getLogger("persona")


@dataclass
class Persona:
    """A unique visitor personality. Every trait is a continuous float [0, 1]."""

    # Core personality
    patience: float = 0.0       # 0 = impatient/skimmer, 1 = thorough reader
    curiosity: float = 0.0      # 0 = focused, 1 = explores everything
    scroll_style: float = 0.0   # 0 = big jumps, 1 = slow smooth scroll
    attention_span: float = 0.0 # 0 = short bursts, 1 = long sustained focus
    tech_savvy: float = 0.0     # 0 = slow/deliberate, 1 = fast/confident

    # Interaction preferences
    image_interest: float = 0.0   # 0 = text-only reader, 1 = visual person
    comment_interest: float = 0.0 # 0 = ignores comments, 1 = reads all comments
    tab_explorer: float = 0.0     # 0 = stays on main content, 1 = clicks tabs
    re_reader: float = 0.0        # 0 = one pass, 1 = scrolls back frequently
    idle_tendency: float = 0.0    # 0 = always active, 1 = many thinking pauses

    # Physical behavior
    scroll_speed: float = 0.0    # 0 = very slow, 1 = very fast
    click_precision: float = 0.0 # 0 = sloppy clicks, 1 = precise
    mouse_restless: float = 0.0  # 0 = mouse still, 1 = mouse always moving

    # Session shape
    warmup_ratio: float = 0.0   # 0 = dives in, 1 = slow start
    fatigue_rate: float = 0.0   # 0 = consistent, 1 = loses interest fast
    exit_style: float = 0.0     # 0 = abrupt exit, 1 = gradual wind-down

    @classmethod
    def generate(cls) -> "Persona":
        """Generate a completely random persona with correlated traits."""
        # Base personality archetype (creates natural correlations)
        archetype = random.random()

        # Generate base traits with slight archetype influence
        def trait(base_mean=0.5, archetype_pull=0.0):
            """Generate trait with beta distribution for natural clustering."""
            mean = base_mean + archetype_pull * (archetype - 0.5)
            mean = max(0.05, min(0.95, mean))
            # Beta distribution parameters from mean
            alpha = mean * 5
            beta = (1 - mean) * 5
            return max(0.0, min(1.0, random.betavariate(alpha, beta)))

        # Correlated trait generation
        patience = trait(0.5)
        tech_savvy = trait(0.5)

        return cls(
            patience=patience,
            curiosity=trait(0.5, 0.3),
            scroll_style=trait(0.5, -0.2 if tech_savvy > 0.6 else 0.2),
            attention_span=trait(patience * 0.6 + 0.2),  # patient people focus longer
            tech_savvy=tech_savvy,
            image_interest=trait(0.5, 0.2),
            comment_interest=trait(0.3 + patience * 0.3),
            tab_explorer=trait(0.3 + patience * 0.2),
            re_reader=trait(0.2 + patience * 0.3),
            idle_tendency=trait(0.3 + (1 - tech_savvy) * 0.3),
            scroll_speed=trait(0.3 + tech_savvy * 0.4),
            click_precision=trait(0.4 + tech_savvy * 0.3),
            mouse_restless=trait(0.3, 0.2),
            warmup_ratio=trait(0.3 + (1 - tech_savvy) * 0.2),
            fatigue_rate=trait(0.3 + (1 - patience) * 0.3),
            exit_style=trait(0.5),
        )

    def signature(self) -> str:
        """Compact string for logging — no two should look the same."""
        return (
            f"PAT={self.patience:.2f} CUR={self.curiosity:.2f} "
            f"SCR={self.scroll_style:.2f} ATT={self.attention_span:.2f} "
            f"IMG={self.image_interest:.2f} CMT={self.comment_interest:.2f}"
        )


class PersonaBrowser:
    """Executes browsing behavior driven by a persona's unique traits."""

    def __init__(self, driver, human_behavior, persona: Persona = None):
        self.driver = driver
        self.human = human_behavior
        self.persona = persona or Persona.generate()
        self._elapsed = 0.0
        self._total_duration = 0.0
        self._action_count = 0

    def browse_blog(self, dwell_min: float, dwell_max: float):
        """Browse a blog post with persona-driven behavior."""
        p = self.persona
        # Duration influenced by patience (patient people stay longer)
        base = random.uniform(dwell_min, dwell_max)
        patience_factor = 0.7 + p.patience * 0.6  # 0.7x ~ 1.3x
        self._total_duration = base * patience_factor
        self._elapsed = 0.0

        log.debug("Persona: %s | Duration: %.0fs", p.signature(), self._total_duration)

        # Phase 1: Warmup (initial scan)
        warmup_end = self._total_duration * (0.05 + p.warmup_ratio * 0.2)
        self._phase_warmup(warmup_end)

        # Phase 2: Main reading (bulk of time)
        main_end = self._total_duration * (0.7 + (1 - p.fatigue_rate) * 0.15)
        self._phase_main_read(main_end)

        # Phase 3: Wind down
        self._phase_wind_down()

    def browse_place(self, dwell_min: float, dwell_max: float):
        """Browse a place detail page with persona-driven behavior."""
        p = self.persona
        base = random.uniform(dwell_min, dwell_max)
        self._total_duration = base * (0.7 + p.patience * 0.6)
        self._elapsed = 0.0

        log.debug("Persona: %s | Duration: %.0fs", p.signature(), self._total_duration)

        warmup_end = self._total_duration * (0.05 + p.warmup_ratio * 0.15)
        self._phase_warmup(warmup_end)

        main_end = self._total_duration * (0.7 + (1 - p.fatigue_rate) * 0.15)
        self._phase_place_explore(main_end)

        self._phase_wind_down()

    def browse_product(self, dwell_min: float, dwell_max: float):
        """Browse a shopping product page with persona-driven behavior."""
        p = self.persona
        base = random.uniform(dwell_min, dwell_max)
        self._total_duration = base * (0.7 + p.patience * 0.6)
        self._elapsed = 0.0

        log.debug("Persona: %s | Duration: %.0fs", p.signature(), self._total_duration)

        warmup_end = self._total_duration * (0.05 + p.warmup_ratio * 0.15)
        self._phase_warmup(warmup_end)

        main_end = self._total_duration * (0.7 + (1 - p.fatigue_rate) * 0.15)
        self._phase_product_explore(main_end)

        self._phase_wind_down()

    # ── Phase implementations ──

    def _phase_warmup(self, until: float):
        """Initial page scan — quick scroll overview."""
        p = self.persona

        # Maybe move mouse first (restless people)
        if p.mouse_restless > 0.4:
            self._do_mouse_wander()

        # Initial pause (looking at the page)
        pause = 1.0 + (1 - p.tech_savvy) * 3.0 + random.uniform(0, 1.5)
        self._wait(pause)

        # Quick scroll to get page overview
        scroll_count = 1 + int(p.curiosity * 3)
        for _ in range(scroll_count):
            if self._elapsed >= until:
                break
            px = self._scroll_pixels(small=True)
            self._do_scroll(px)
            self._wait(self._reading_pause(short=True))

    def _phase_main_read(self, until: float):
        """Main reading phase for blog posts."""
        p = self.persona

        while self._elapsed < until:
            # Generate next action based on persona weights
            # Each weight is a continuous function of persona traits
            weights = self._blog_action_weights()
            action = self._weighted_pick(weights)

            if action == "scroll_read":
                self._action_scroll_read()
            elif action == "image_look":
                self._action_look_images()
            elif action == "scroll_back":
                self._action_scroll_back()
            elif action == "comment_area":
                self._action_read_comments()
            elif action == "idle_think":
                self._action_idle()
            elif action == "mouse_wander":
                self._do_mouse_wander()
                self._wait(random.uniform(0.3, 1.0))

            # Fatigue: actions slow down over time
            fatigue = self._elapsed / self._total_duration
            if fatigue > 0.6 and p.fatigue_rate > 0.5:
                extra_pause = (fatigue - 0.6) * p.fatigue_rate * 3
                self._wait(extra_pause)

    def _phase_place_explore(self, until: float):
        """Main exploration phase for place pages."""
        p = self.persona

        while self._elapsed < until:
            weights = self._place_action_weights()
            action = self._weighted_pick(weights)

            if action == "scroll_read":
                self._action_scroll_read()
            elif action == "click_tab":
                self._action_click_place_tab()
            elif action == "image_look":
                self._action_look_images()
            elif action == "scroll_back":
                self._action_scroll_back()
            elif action == "idle_think":
                self._action_idle()
            elif action == "mouse_wander":
                self._do_mouse_wander()
                self._wait(random.uniform(0.3, 1.0))

            fatigue = self._elapsed / self._total_duration
            if fatigue > 0.6 and p.fatigue_rate > 0.5:
                self._wait((fatigue - 0.6) * p.fatigue_rate * 3)

    def _phase_product_explore(self, until: float):
        """Main exploration phase for product pages."""
        p = self.persona

        while self._elapsed < until:
            weights = self._product_action_weights()
            action = self._weighted_pick(weights)

            if action == "scroll_read":
                self._action_scroll_read()
            elif action == "check_reviews":
                self._action_check_reviews()
            elif action == "image_look":
                self._action_look_product_images()
            elif action == "scroll_back":
                self._action_scroll_back()
            elif action == "idle_think":
                self._action_idle()
            elif action == "mouse_wander":
                self._do_mouse_wander()
                self._wait(random.uniform(0.3, 1.0))

            fatigue = self._elapsed / self._total_duration
            if fatigue > 0.6 and p.fatigue_rate > 0.5:
                self._wait((fatigue - 0.6) * p.fatigue_rate * 3)

    def _phase_wind_down(self):
        """Exit phase — behavior depends on exit_style."""
        p = self.persona
        remaining = max(0, self._total_duration - self._elapsed)
        if remaining <= 0:
            return

        if p.exit_style > 0.6:
            # Gradual: slow scroll, maybe re-read top
            if random.random() < p.re_reader:
                self.human.scroll_to_top()
                self._wait(random.uniform(1.5, 4.0))
            else:
                self._do_scroll(random.randint(-200, 200))
                self._wait(random.uniform(1.0, 3.0))
        elif p.exit_style > 0.3:
            # Normal: small pause then done
            self._wait(random.uniform(1.0, 2.5))
        # else: abrupt — just stop

    # ── Action implementations ──

    def _action_scroll_read(self):
        """Scroll down and read — the most common action."""
        p = self.persona
        # Number of scroll segments: patient = more, impatient = fewer
        segments = max(1, int(2 + p.patience * 4 + random.uniform(-1, 1)))

        for _ in range(segments):
            px = self._scroll_pixels()
            self._do_scroll(px)
            pause = self._reading_pause()
            self._wait(pause)

            # Sometimes move mouse while reading
            if random.random() < p.mouse_restless * 0.4:
                self._do_mouse_wander()

    def _action_look_images(self):
        """Look at images in the content."""
        p = self.persona
        if random.random() > p.image_interest * 0.8 + 0.1:
            # Not interested enough this time
            self._wait(random.uniform(0.5, 1.5))
            return

        try:
            images = self.driver.find_elements(
                By.CSS_SELECTOR,
                "img[src*='pstatic'], img[src*='blogfiles'], "
                "img[src*='postfiles'], img[src*='naver'], "
                "img[src*='shop'], img[src*='thumb']"
            )
            visible = [img for img in images if img.is_displayed()]
            if not visible:
                return

            # Pick 1~3 images based on curiosity
            count = max(1, int(p.curiosity * 3 * random.uniform(0.5, 1.5)))
            targets = random.sample(visible[:10], min(count, len(visible)))

            for img in targets:
                self.human.scroll_to_element(img)
                # Gaze time depends on image interest
                gaze = 0.5 + p.image_interest * 3.0 + random.uniform(0, 1.5)
                self._wait(gaze)

                # Maybe click to enlarge
                if random.random() < p.curiosity * 0.25:
                    try:
                        self.human.human_click(img)
                        self._wait(random.uniform(1.0, 3.0))
                        self.driver.back()
                        self._wait(0.5)
                    except Exception:
                        pass
        except Exception:
            pass

    def _action_look_product_images(self):
        """Look at product images specifically."""
        p = self.persona
        if random.random() > p.image_interest * 0.7 + 0.2:
            self._wait(random.uniform(0.5, 1.0))
            return

        try:
            self.human.scroll_to_top()
            self._wait(random.uniform(1.0, 3.0))

            images = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[class*='thumb'] img, [class*='image'] img, [class*='Image'] img, "
                "[class*='photo'] img, [class*='gallery'] img"
            )
            visible = [img for img in images if img.is_displayed()]
            if visible and len(visible) > 1:
                count = max(1, int(p.curiosity * 2 + random.uniform(0, 1)))
                for img in random.sample(visible[:6], min(count, len(visible))):
                    self.human.human_click(img)
                    self._wait(1.0 + p.image_interest * 2.5 + random.uniform(0, 1))
        except Exception:
            pass

    def _action_scroll_back(self):
        """Scroll back up to re-read something."""
        p = self.persona
        if random.random() > p.re_reader * 0.7 + 0.1:
            return

        # Scroll up partially or to top
        if random.random() < 0.3:
            self.human.scroll_to_top()
        else:
            up_px = int(200 + random.uniform(100, 600))
            self._do_scroll(-up_px)

        self._wait(self._reading_pause())

        # Read again going down
        segments = random.randint(1, 3)
        for _ in range(segments):
            self._do_scroll(self._scroll_pixels())
            self._wait(self._reading_pause(short=True))

    def _action_read_comments(self):
        """Navigate to and read comments."""
        p = self.persona
        if random.random() > p.comment_interest * 0.6 + 0.1:
            return

        try:
            keywords = ["댓글", "공감", "이웃", "좋아요"]
            elements = self.driver.find_elements(
                By.XPATH,
                "//*[" + " or ".join(f"contains(text(),'{kw}')" for kw in keywords) + "]"
            )
            clickable = [
                el for el in elements
                if el.is_displayed() and len(el.text.strip()) < 15
            ]
            if clickable:
                target = random.choice(clickable[:3])
                self.human.scroll_to_element(target)
                self._wait(1.0 + p.comment_interest * 3.0 + random.uniform(0, 2))
        except Exception:
            pass

    def _action_check_reviews(self):
        """Click on review/rating tabs (for product pages)."""
        p = self.persona
        if random.random() > p.comment_interest * 0.5 + 0.2:
            return

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
                self.human.scroll_to_element(target)
                self.human.human_click(target)
                self._wait(2.0 + p.patience * 4.0 + random.uniform(0, 2))
        except Exception:
            pass

    def _action_click_place_tab(self):
        """Click tabs on place page (reviews, photos, menu, etc)."""
        p = self.persona
        if random.random() > p.tab_explorer * 0.6 + 0.15:
            return

        try:
            tab_keywords = ["리뷰", "사진", "메뉴", "정보", "소식", "홈"]
            tabs = self.driver.find_elements(
                By.XPATH,
                "//*[" + " or ".join(f"contains(text(),'{kw}')" for kw in tab_keywords) + "]"
            )
            clickable = [
                el for el in tabs
                if el.tag_name in ("a", "button", "span", "div", "li", "label")
                and el.is_displayed()
                and len(el.text.strip()) < 10
            ]
            if clickable:
                target = random.choice(clickable[:5])
                self.human.scroll_to_element(target)
                self.human.human_click(target)
                self._wait(2.0 + p.curiosity * 3.0 + random.uniform(0, 2))
        except Exception:
            pass

    def _action_idle(self):
        """Thinking pause — varies hugely by persona."""
        p = self.persona
        base = 1.0 + p.idle_tendency * 5.0
        jitter = random.uniform(-base * 0.3, base * 0.5)
        self._wait(max(0.5, base + jitter))

    # ── Helpers ──

    def _blog_action_weights(self) -> dict:
        p = self.persona
        progress = min(1.0, self._elapsed / max(1, self._total_duration))
        return {
            "scroll_read":   0.30 + p.patience * 0.15 - progress * 0.1,
            "image_look":    0.10 + p.image_interest * 0.20,
            "scroll_back":   0.05 + p.re_reader * 0.15 + progress * 0.05,
            "comment_area":  0.05 + p.comment_interest * 0.15,
            "idle_think":    0.10 + p.idle_tendency * 0.15,
            "mouse_wander":  0.05 + p.mouse_restless * 0.10,
        }

    def _place_action_weights(self) -> dict:
        p = self.persona
        progress = min(1.0, self._elapsed / max(1, self._total_duration))
        return {
            "scroll_read":   0.25 + p.patience * 0.10,
            "click_tab":     0.15 + p.tab_explorer * 0.20,
            "image_look":    0.15 + p.image_interest * 0.15,
            "scroll_back":   0.05 + p.re_reader * 0.10,
            "idle_think":    0.10 + p.idle_tendency * 0.10,
            "mouse_wander":  0.05 + p.mouse_restless * 0.08,
        }

    def _product_action_weights(self) -> dict:
        p = self.persona
        progress = min(1.0, self._elapsed / max(1, self._total_duration))
        return {
            "scroll_read":   0.30 + p.patience * 0.10,
            "check_reviews": 0.10 + p.comment_interest * 0.20,
            "image_look":    0.15 + p.image_interest * 0.15,
            "scroll_back":   0.05 + p.re_reader * 0.10,
            "idle_think":    0.10 + p.idle_tendency * 0.10,
            "mouse_wander":  0.05 + p.mouse_restless * 0.08,
        }

    def _weighted_pick(self, weights: dict) -> str:
        """Pick action from continuous weights with noise."""
        # Add per-pick noise so even same persona varies
        noisy = {}
        for k, w in weights.items():
            noise = random.gauss(0, 0.05)
            noisy[k] = max(0.01, w + noise)

        actions = list(noisy.keys())
        values = [noisy[a] for a in actions]
        return random.choices(actions, weights=values, k=1)[0]

    def _scroll_pixels(self, small=False) -> int:
        """Generate scroll distance based on persona."""
        p = self.persona
        if small:
            base = 80 + (1 - p.scroll_style) * 200
        else:
            base = 120 + (1 - p.scroll_style) * 400

        # Add continuous noise
        noise = random.gauss(0, base * 0.3)
        return max(50, int(base + noise))

    def _reading_pause(self, short=False) -> float:
        """Generate reading pause duration based on persona."""
        p = self.persona
        if short:
            base = 0.5 + p.patience * 1.5
        else:
            base = 1.0 + p.patience * 3.5 + p.attention_span * 2.0

        # Gamma distribution for natural reading pauses
        # (most pauses short, occasional long ones)
        shape = 2.0 + p.attention_span * 3.0
        scale = base / shape
        pause = random.gammavariate(shape, scale)
        return max(0.3, min(pause, 12.0))

    def _do_scroll(self, pixels: int):
        """Execute scroll with persona-influenced style."""
        p = self.persona
        # Chunk count: smooth scrollers use more chunks
        chunks = max(2, int(3 + p.scroll_style * 5 + random.uniform(-1, 1)))
        chunk_size = pixels / chunks

        for i in range(chunks):
            # Each chunk slightly different
            amount = int(chunk_size * random.uniform(0.6, 1.4))
            self.driver.execute_script(f"window.scrollBy(0, {amount})")
            # Inter-chunk delay: smooth scrollers have tiny gaps
            gap = 0.02 + (1 - p.scroll_speed) * 0.12 + random.uniform(0, 0.05)
            time.sleep(gap)

        # Post-scroll settle
        settle = 0.1 + (1 - p.scroll_speed) * 0.5 + random.uniform(0, 0.3)
        time.sleep(settle)
        self._action_count += 1

    def _do_mouse_wander(self):
        """Move mouse to random position."""
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            vw = self.driver.execute_script("return window.innerWidth")
            vh = self.driver.execute_script("return window.innerHeight")

            action = ActionChains(self.driver)
            x = random.randint(50, max(51, vw - 50))
            y = random.randint(50, max(51, vh - 50))
            action.move_to_element_with_offset(body, x, y)
            action.perform()
        except Exception:
            pass

    def _wait(self, seconds: float):
        """Wait and track elapsed time."""
        seconds = max(0, seconds)
        time.sleep(seconds)
        self._elapsed += seconds
