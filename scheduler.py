"""
Daily scheduler - distributes visits across hours to mimic natural traffic patterns.
Peak hours get more visits, late night gets fewer.
"""

import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from engine import Campaign, NaverShoppingEngine

log = logging.getLogger("scheduler")


# Hourly traffic weight (Korean shopping patterns)
# Higher weight = more visits during that hour
HOURLY_WEIGHTS = {
    0: 0.3,  1: 0.1,  2: 0.05, 3: 0.02,
    4: 0.02, 5: 0.05, 6: 0.2,  7: 0.5,
    8: 0.7,  9: 1.0,  10: 1.2, 11: 1.0,
    12: 0.8, 13: 1.0, 14: 1.2, 15: 1.1,
    16: 1.0, 17: 0.9, 18: 0.8, 19: 1.0,
    20: 1.3, 21: 1.5, 22: 1.2, 23: 0.8,
}


def distribute_visits(daily_target: int) -> dict[int, int]:
    """Distribute daily visits across 24 hours based on natural patterns."""
    total_weight = sum(HOURLY_WEIGHTS.values())
    distribution = {}

    remaining = daily_target
    hours = list(HOURLY_WEIGHTS.keys())
    random.shuffle(hours)  # Randomize allocation order to avoid systematic bias

    for i, hour in enumerate(hours):
        if i == len(hours) - 1:
            # Last hour gets whatever remains
            distribution[hour] = remaining
        else:
            weight = HOURLY_WEIGHTS[hour]
            base = daily_target * (weight / total_weight)
            # Add ±20% randomness
            count = max(0, int(base * random.uniform(0.8, 1.2)))
            count = min(count, remaining)
            distribution[hour] = count
            remaining -= count

    return dict(sorted(distribution.items()))


def get_current_hour_visits(daily_target: int) -> int:
    """Get how many visits to run for the current hour."""
    dist = distribute_visits(daily_target)
    current_hour = datetime.now().hour
    return dist.get(current_hour, 0)


async def run_hourly_batch(
    campaign: Campaign,
    proxy: Optional[dict] = None,
    headless: bool = True,
):
    """Run visits for the current hour based on daily target distribution."""
    count = get_current_hour_visits(campaign.daily_target)
    current_hour = datetime.now().hour

    if count == 0:
        log.info("Hour %02d: No visits scheduled", current_hour)
        return []

    log.info("Hour %02d: Running %d visits", current_hour, count)

    engine = NaverShoppingEngine(proxy=proxy, headless=headless)
    await engine.start()

    results = []
    try:
        # Spread visits across the hour (3600 seconds)
        interval = 3600 / count if count > 0 else 3600

        for i in range(count):
            log.info("Hour %02d: Visit %d/%d", current_hour, i + 1, count)
            result = await engine.execute_visit(campaign)
            results.append(result)

            if i < count - 1:
                # Wait with ±30% jitter
                delay = interval * random.uniform(0.7, 1.3)
                # Subtract time already spent on the visit
                delay = max(5.0, delay - result.duration_sec)
                log.info("Next visit in %.0fs", delay)
                await asyncio.sleep(delay)

    finally:
        await engine.stop()

    success = sum(1 for r in results if r.success)
    log.info("Hour %02d complete: %d/%d success", current_hour, success, count)
    return results


async def run_daemon(
    campaign: Campaign,
    proxy: Optional[dict] = None,
    headless: bool = True,
):
    """Run continuously, executing hourly batches. Designed for background service."""
    log.info("Daemon started for campaign: %s", campaign.keyword)
    log.info("Daily target: %d visits", campaign.daily_target)

    # Show today's distribution
    dist = distribute_visits(campaign.daily_target)
    log.info("Today's distribution:")
    for hour, count in dist.items():
        bar = "#" * count
        log.info("  %02d:00  %3d  %s", hour, count, bar)

    while True:
        now = datetime.now()
        log.info("--- %s ---", now.strftime("%Y-%m-%d %H:%M"))

        await run_hourly_batch(campaign, proxy=proxy, headless=headless)

        # Wait until next hour
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        # Add random offset (don't start exactly on the hour)
        next_hour += timedelta(minutes=random.randint(1, 10))
        wait_seconds = (next_hour - datetime.now()).total_seconds()

        if wait_seconds > 0:
            log.info("Next batch at %s (waiting %.0fm)",
                     next_hour.strftime("%H:%M"), wait_seconds / 60)
            await asyncio.sleep(wait_seconds)
