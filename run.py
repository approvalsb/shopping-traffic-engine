"""
Campaign runner - CLI interface for the traffic engine.

Usage:
    # Single test run (visible browser)
    python run.py --keyword "여성 원피스" --product "봄 플라워 원피스" --count 3 --visible

    # Batch run (headless)
    python run.py --keyword "남성 운동화" --product "나이키 에어맥스" --count 50

    # With proxy
    python run.py --keyword "여성 원피스" --product "봄 플라워 원피스" --count 10 \
        --proxy "http://user:pass@proxy.example.com:8080"

    # Config file
    python run.py --config campaign.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from engine import Campaign, run_campaign_batch


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_sample_config():
    """Create a sample campaign.json for reference."""
    sample = {
        "keyword": "여성 원피스 봄",
        "product_name": "플라워 원피스",
        "product_url": "https://smartstore.naver.com/example/products/12345",
        "daily_target": 100,
        "dwell_time_min": 30,
        "dwell_time_max": 90,
        "proxy": None,
        "headless": True,
        "delay_between_min": 10,
        "delay_between_max": 30,
    }
    path = Path("campaign.sample.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
    print(f"Sample config created: {path}")


async def main():
    parser = argparse.ArgumentParser(description="Naver Shopping Traffic Engine")
    parser.add_argument("--keyword", "-k", help="Search keyword")
    parser.add_argument("--product", "-p", help="Product name to find in results")
    parser.add_argument("--url", "-u", help="Product URL (for logging)", default="")
    parser.add_argument("--count", "-n", type=int, default=10, help="Number of visits")
    parser.add_argument("--dwell-min", type=float, default=30.0, help="Min dwell time (seconds)")
    parser.add_argument("--dwell-max", type=float, default=90.0, help="Max dwell time (seconds)")
    parser.add_argument("--delay-min", type=float, default=10.0, help="Min delay between visits")
    parser.add_argument("--delay-max", type=float, default=30.0, help="Max delay between visits")
    parser.add_argument("--proxy", help="Proxy URL (http://user:pass@host:port)")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--config", "-c", help="Load campaign from JSON config file")
    parser.add_argument("--sample-config", action="store_true", help="Create sample config file")

    args = parser.parse_args()

    if args.sample_config:
        create_sample_config()
        return

    # Load from config or CLI args
    if args.config:
        cfg = load_config(args.config)
        campaign = Campaign(
            product_url=cfg.get("product_url", ""),
            keyword=cfg["keyword"],
            product_name=cfg["product_name"],
            daily_target=cfg.get("daily_target", 100),
            dwell_time_min=cfg.get("dwell_time_min", 30.0),
            dwell_time_max=cfg.get("dwell_time_max", 90.0),
        )
        proxy_url = cfg.get("proxy")
        headless = cfg.get("headless", True)
        count = cfg.get("daily_target", 100)
        delay_between = (cfg.get("delay_between_min", 10.0), cfg.get("delay_between_max", 30.0))
    else:
        if not args.keyword or not args.product:
            parser.error("--keyword and --product are required (or use --config)")
            sys.exit(1)

        campaign = Campaign(
            product_url=args.url,
            keyword=args.keyword,
            product_name=args.product,
            daily_target=args.count,
            dwell_time_min=args.dwell_min,
            dwell_time_max=args.dwell_max,
        )
        proxy_url = args.proxy
        headless = not args.visible
        count = args.count
        delay_between = (args.delay_min, args.delay_max)

    # Build proxy dict
    proxy = None
    if proxy_url:
        proxy = {"server": proxy_url}

    print(f"""
╔══════════════════════════════════════════╗
║   Naver Shopping Traffic Engine          ║
╠══════════════════════════════════════════╣
║  Keyword:  {campaign.keyword:<29}║
║  Product:  {campaign.product_name:<29}║
║  Count:    {count:<29}║
║  Dwell:    {campaign.dwell_time_min:.0f}~{campaign.dwell_time_max:.0f}s{'':<23}║
║  Headless: {str(headless):<29}║
║  Proxy:    {str(bool(proxy)):<29}║
╚══════════════════════════════════════════╝
""")

    results = await run_campaign_batch(
        campaign=campaign,
        count=count,
        proxy=proxy,
        headless=headless,
        delay_between=delay_between,
    )

    # Summary
    success = sum(1 for r in results if r.success)
    failed = len(results) - success
    avg_duration = sum(r.duration_sec for r in results) / len(results) if results else 0

    print(f"""
╔══════════════════════════════════════════╗
║   Results Summary                        ║
╠══════════════════════════════════════════╣
║  Total:     {len(results):<28}║
║  Success:   {success:<28}║
║  Failed:    {failed:<28}║
║  Avg Time:  {avg_duration:.1f}s{'':<24}║
╚══════════════════════════════════════════╝
""")


if __name__ == "__main__":
    asyncio.run(main())
