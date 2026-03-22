#!/usr/bin/env python3
"""
Auto-campaign creator for Naver blog posts.

Scrapes the RSS feed of Naver blogs, checks which posts are already
registered as campaigns in the SQLite DB, extracts search keywords via
Gemini API for new posts, and registers them through the master API.

Supports multiple blogs with per-blog configuration.

Usage:
    python auto_campaign.py            # create campaigns for all blogs
    python auto_campaign.py --dry-run  # preview only, no creation
    python auto_campaign.py --blog nestorium  # specific blog only
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MASTER_API = "http://localhost:5000/api/campaigns"
DB_PATH = Path(__file__).parent / "data" / "traffic_engine.db"
ENV_FILE = "/opt/traffic-engine/.env"

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_PROMPT = (
    "다음 블로그 글 제목에서 네이버 검색에 사용할 핵심 키워드 2~4단어를 "
    "추출해줘. 키워드만 출력해: {title}"
)

# Multi-blog configurations
BLOG_CONFIGS = [
    {
        "blog_id": "alswndboss",
        "customer_name": "민팀장의 보험스토리",
        "product_name": "민팀장의 보험스토리",
        "daily_target": 2,
        "dwell_time_min": 20,
        "dwell_time_max": 45,
        "engage_like": 1,
        "options": [],
    },
    {
        "blog_id": "nestorium",
        "customer_name": "네스토리움",
        "product_name": "네스토리움 블로그",
        "daily_target": 2,
        "dwell_time_min": 25,
        "dwell_time_max": 50,
        "engage_like": 1,
        "options": ["blog_like", "blog_comment_view", "blog_series", "regional_targeting"],
    },
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("auto_campaign")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_gemini_key() -> str:
    """Read Gemini API key from env var or .env file."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    env_path = Path(ENV_FILE)
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")

    log.error("GEMINI_API_KEY not found in environment or %s", ENV_FILE)
    sys.exit(1)


def fetch_rss_posts(blog_id: str) -> list[dict]:
    """Fetch blog posts from the Naver RSS feed."""
    rss_url = f"https://rss.blog.naver.com/{blog_id}"
    log.info("Fetching RSS feed: %s", rss_url)
    resp = requests.get(rss_url, timeout=15)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)
    posts = []
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is not None and link_el is not None:
            title = (title_el.text or "").strip()
            link = (link_el.text or "").strip()
            if title:
                posts.append({"title": title, "link": link})

    log.info("Found %d posts in RSS feed for %s", len(posts), blog_id)
    return posts


def get_existing_keywords(customer_name: str = None) -> set[str]:
    """Load existing blog campaign keywords from the SQLite DB."""
    import sqlite3

    if not DB_PATH.exists():
        log.warning("Database not found at %s — treating as empty", DB_PATH)
        return set()

    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row

    if customer_name:
        rows = conn.execute(
            "SELECT keyword FROM campaigns WHERE type = 'blog' AND customer_name = ?",
            (customer_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT keyword FROM campaigns WHERE type = 'blog'"
        ).fetchall()
    conn.close()

    keywords = {row["keyword"].strip().lower() for row in rows}
    log.info("Loaded %d existing blog campaign keywords", len(keywords))
    return keywords


def get_existing_product_names(customer_name: str = None) -> set[str]:
    """Load existing blog campaign product_names from the SQLite DB."""
    import sqlite3

    if not DB_PATH.exists():
        return set()

    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row

    if customer_name:
        rows = conn.execute(
            "SELECT product_name FROM campaigns WHERE type = 'blog' AND customer_name = ?",
            (customer_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT product_name FROM campaigns WHERE type = 'blog'"
        ).fetchall()
    conn.close()

    return {row["product_name"].strip().lower() for row in rows}


def extract_keyword_gemini(title: str, api_key: str) -> str:
    """Use Gemini API to extract a short search keyword from a blog title."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_PROMPT.format(title=title)}
                ]
            }
        ],
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    try:
        keyword = (
            data["candidates"][0]["content"]["parts"][0]["text"].strip()
        )
    except (KeyError, IndexError):
        log.warning("Gemini returned unexpected response for '%s': %s", title, data)
        keyword = " ".join(title.split()[:4])

    keyword = keyword.strip("\"'.,!?;: ")
    return keyword


def create_campaign(blog_config: dict, keyword: str, dry_run: bool = False) -> dict | None:
    """Register a campaign via the master API."""
    payload = {
        "type": "blog",
        "customer_name": blog_config["customer_name"],
        "product_name": blog_config["product_name"],
        "product_url": f"https://m.blog.naver.com/{blog_config['blog_id']}",
        "keyword": keyword,
        "daily_target": blog_config["daily_target"],
        "dwell_time_min": blog_config["dwell_time_min"],
        "dwell_time_max": blog_config["dwell_time_max"],
        "engage_like": blog_config.get("engage_like", 0),
        "options": blog_config.get("options", []),
    }

    if dry_run:
        log.info("[DRY-RUN] Would create campaign: %s", json.dumps(payload, ensure_ascii=False))
        return {"id": "(dry-run)", "keyword": keyword}

    try:
        resp = requests.post(MASTER_API, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        log.info("Campaign created: id=%s keyword='%s'", result.get("id"), keyword)
        return result
    except requests.RequestException as e:
        log.error("Failed to create campaign for keyword '%s': %s", keyword, e)
        return None


def process_blog(blog_config: dict, api_key: str, dry_run: bool = False) -> dict:
    """Process a single blog: fetch RSS, extract keywords, create campaigns."""
    blog_id = blog_config["blog_id"]
    customer = blog_config["customer_name"]
    log.info("=" * 50)
    log.info("Processing blog: %s (%s)", customer, blog_id)
    log.info("=" * 50)

    # 1. Fetch RSS posts
    try:
        posts = fetch_rss_posts(blog_id)
    except Exception as e:
        log.error("Failed to fetch RSS for %s: %s", blog_id, e)
        return {"blog_id": blog_id, "customer": customer, "created": [], "failed": [], "skipped": []}

    if not posts:
        log.info("No posts found for %s", blog_id)
        return {"blog_id": blog_id, "customer": customer, "created": [], "failed": [], "skipped": []}

    # 2. Load existing campaigns for this customer
    existing_keywords = get_existing_keywords(customer)
    existing_names = get_existing_product_names(customer)

    # 3. Filter new posts
    new_posts = []
    skipped = []

    for post in posts:
        title_lower = post["title"].strip().lower()
        matched = False
        for term in existing_keywords | existing_names:
            if term in title_lower or title_lower in term:
                skipped.append(post["title"])
                matched = True
                break
        if not matched:
            new_posts.append(post)

    log.info("New posts: %d, Skipped: %d", len(new_posts), len(skipped))

    if not new_posts:
        log.info("No new posts for %s", blog_id)
        return {"blog_id": blog_id, "customer": customer, "created": [], "failed": [], "skipped": skipped}

    # 4. Extract keywords and create campaigns
    created = []
    failed = []

    for post in new_posts:
        title = post["title"]
        log.info("Processing: %s", title)

        try:
            keyword = extract_keyword_gemini(title, api_key)
        except Exception as e:
            log.error("Keyword extraction failed for '%s': %s", title, e)
            failed.append(title)
            continue

        if keyword.strip().lower() in existing_keywords:
            log.info("  SKIP (keyword exists): %s -> '%s'", title, keyword)
            skipped.append(title)
            continue

        log.info("  Keyword: '%s'", keyword)

        result = create_campaign(blog_config, keyword, dry_run=dry_run)
        if result:
            created.append({"title": title, "keyword": keyword, "id": result.get("id")})
            existing_keywords.add(keyword.strip().lower())
        else:
            failed.append(title)

    return {"blog_id": blog_id, "customer": customer, "created": created, "failed": failed, "skipped": skipped}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Auto-register blog campaigns from Naver RSS")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating campaigns")
    parser.add_argument("--blog", type=str, help="Process specific blog_id only")
    args = parser.parse_args()

    api_key = load_gemini_key()

    # Filter blogs if --blog specified
    blogs = BLOG_CONFIGS
    if args.blog:
        blogs = [b for b in BLOG_CONFIGS if b["blog_id"] == args.blog]
        if not blogs:
            log.error("Blog '%s' not found in config", args.blog)
            sys.exit(1)

    # Process each blog
    all_results = []
    for blog_config in blogs:
        result = process_blog(blog_config, api_key, dry_run=args.dry_run)
        all_results.append(result)

    # Summary
    print()
    print("=" * 60)
    print("  Auto Campaign Summary")
    print("=" * 60)
    if args.dry_run:
        print("  Mode: DRY-RUN (no changes made)")
    print()

    total_created = 0
    total_failed = 0
    for r in all_results:
        created_count = len(r["created"])
        failed_count = len(r["failed"])
        total_created += created_count
        total_failed += failed_count

        print(f"  [{r['blog_id']}] {r['customer']}")
        print(f"    Skipped: {len(r['skipped'])}, Created: {created_count}, Failed: {failed_count}")
        for c in r["created"]:
            print(f"      + [{c['id']}] {c['keyword']}")
        for f in r["failed"]:
            print(f"      ! {f}")
        print()

    print(f"  Total: {total_created} created, {total_failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
