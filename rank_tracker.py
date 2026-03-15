"""
Naver rank tracking for blog, place, and shopping campaigns.
Uses requests + BeautifulSoup for lightweight scraping (no Selenium).
"""

import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from database import get_db, get_campaign, save_tracking, DB_PATH

log = logging.getLogger("rank_tracker")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.naver.com/",
}

CACHE_PATH = Path("data/tracking_cache.json")


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def check_blog_rank(keyword: str, blog_id: str, max_pages: int = 3) -> dict:
    """Search Naver blog tab and find the target blog's rank position.

    Args:
        keyword: Search keyword
        blog_id: Naver blog ID (e.g. 'alswndboss')
        max_pages: Maximum pages to scan (default 3, 10 results per page)

    Returns:
        dict with rank, page, total_results, checked_at
    """
    result = {
        "rank": None,
        "page": 0,
        "total_results": "0",
        "checked_at": _now_str(),
        "keyword": keyword,
        "target": blog_id,
        "type": "blog_rank",
    }

    for page in range(1, max_pages + 1):
        start = (page - 1) * 10 + 1
        url = "https://search.naver.com/search.naver"
        params = {
            "where": "blog",
            "query": keyword,
            "start": start,
        }

        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error("Blog search request failed: %s", e)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract total results count (first page only)
        if page == 1:
            count_el = soup.select_one(".title_num") or soup.select_one(".result_num")
            if count_el:
                nums = re.findall(r"[\d,]+", count_el.get_text())
                if nums:
                    result["total_results"] = nums[0]

        # Find blog posts - look for links containing the blog_id
        items = soup.select(".api_txt_lines.total_tit") or soup.select("a.api_txt_lines")
        if not items:
            # Fallback: scan all links
            items = soup.select("a[href*='blog.naver.com']")

        for idx, item in enumerate(items):
            href = item.get("href", "")
            if blog_id in href:
                rank = (page - 1) * 10 + idx + 1
                result["rank"] = rank
                result["page"] = page
                log.info("Blog rank found: %s at position %d (page %d)", blog_id, rank, page)
                return result

        # Also check via the list container area links
        all_links = soup.find_all("a", href=True)
        for idx_offset, link in enumerate(all_links):
            href = link["href"]
            if f"blog.naver.com/{blog_id}" in href:
                rank = (page - 1) * 10 + 1  # approximate
                result["rank"] = rank
                result["page"] = page
                return result

    log.info("Blog %s not found in top %d pages for '%s'", blog_id, max_pages, keyword)
    return result


def check_place_rank(keyword: str, place_name: str, max_pages: int = 3) -> dict:
    """Search Naver place and find the target place's rank position.

    Args:
        keyword: Search keyword
        place_name: Business/place name to find
        max_pages: Maximum pages to scan

    Returns:
        dict with rank, page, total_results, checked_at
    """
    result = {
        "rank": None,
        "page": 0,
        "total_results": "0",
        "checked_at": _now_str(),
        "keyword": keyword,
        "target": place_name,
        "type": "place_rank",
    }

    for page in range(1, max_pages + 1):
        start = (page - 1) * 15 + 1
        url = "https://search.naver.com/search.naver"
        params = {
            "where": "nexearch",
            "query": keyword,
            "sm": "tab_jum",
        }
        if page > 1:
            params["start"] = start

        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error("Place search request failed: %s", e)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for place results in the integrated search
        place_items = soup.select(".CHC5F a.place_bluelink") or soup.select(".api_txt_lines.total_tit")
        if not place_items:
            place_items = soup.select("a.place_bluelink") or soup.select(".place_bluelink")

        for idx, item in enumerate(place_items):
            name_text = item.get_text(strip=True)
            if place_name.lower() in name_text.lower():
                rank = (page - 1) * 15 + idx + 1
                result["rank"] = rank
                result["page"] = page
                log.info("Place rank found: %s at position %d", place_name, rank)
                return result

        # Fallback: scan entire page text for place name
        all_text_els = soup.find_all(string=re.compile(re.escape(place_name), re.IGNORECASE))
        if all_text_els:
            result["rank"] = (page - 1) * 15 + 1  # approximate
            result["page"] = page
            return result

    log.info("Place %s not found in top %d pages for '%s'", place_name, max_pages, keyword)
    return result


def check_shopping_rank(keyword: str, product_name: str, max_pages: int = 3) -> dict:
    """Search Naver shopping and find the target product's rank position.

    Args:
        keyword: Search keyword
        product_name: Product name (partial match)
        max_pages: Maximum pages to scan

    Returns:
        dict with rank, page, total_results, checked_at
    """
    result = {
        "rank": None,
        "page": 0,
        "total_results": "0",
        "checked_at": _now_str(),
        "keyword": keyword,
        "target": product_name,
        "type": "shopping_rank",
    }

    for page in range(1, max_pages + 1):
        pagingIndex = (page - 1) * 40 + 1
        url = "https://search.shopping.naver.com/search/all"
        params = {
            "query": keyword,
            "pagingIndex": pagingIndex,
            "pagingSize": 40,
        }

        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error("Shopping search request failed: %s", e)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract total results (first page only)
        if page == 1:
            count_el = soup.select_one(".subFilter_num__2x0jq") or soup.select_one("[class*='_num']")
            if count_el:
                nums = re.findall(r"[\d,]+", count_el.get_text())
                if nums:
                    result["total_results"] = nums[0]

        # Find product items
        items = soup.select(".product_link__TrAac") or soup.select("a[class*='product_link']")
        if not items:
            items = soup.select(".basicList_link__JLQJa") or soup.select("a[class*='basicList_link']")

        for idx, item in enumerate(items):
            title = item.get_text(strip=True)
            if product_name.lower() in title.lower():
                rank = (page - 1) * 40 + idx + 1
                result["rank"] = rank
                result["page"] = page
                log.info("Shopping rank found: %s at position %d", product_name, rank)
                return result

    log.info("Product %s not found in top %d pages for '%s'", product_name, max_pages, keyword)
    return result


def _update_cache(campaign_id: int, tracking_result: dict):
    """Write tracking result to JSON cache for the dashboard to read."""
    CACHE_PATH.parent.mkdir(exist_ok=True)

    cache = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}

    key = str(campaign_id)

    # Initialize campaign entry
    if key not in cache:
        cache[key] = {"latest": None, "history": []}

    cache[key]["latest"] = tracking_result

    # Append to history (keep last 90 entries)
    cache[key]["history"].append(tracking_result)
    cache[key]["history"] = cache[key]["history"][-90:]

    # Compute trend from last 3 entries
    history = cache[key]["history"]
    if len(history) >= 2:
        recent_ranks = [
            h["rank"] for h in history[-3:] if h.get("rank") is not None
        ]
        if len(recent_ranks) >= 2:
            if recent_ranks[-1] < recent_ranks[0]:
                cache[key]["trend"] = "up"
            elif recent_ranks[-1] > recent_ranks[0]:
                cache[key]["trend"] = "down"
            else:
                cache[key]["trend"] = "stable"
        else:
            cache[key]["trend"] = "stable"
    else:
        cache[key]["trend"] = "stable"

    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Cache updated for campaign %d", campaign_id)


def run_tracking(campaign_id: int) -> dict | None:
    """Run rank tracking for a campaign based on its type.

    Reads campaign from DB, performs the appropriate rank check,
    saves result to DB and updates the JSON cache.
    """
    campaign = get_campaign(campaign_id)
    if not campaign:
        log.error("Campaign %d not found", campaign_id)
        return None

    ctype = campaign["type"]
    keyword = campaign["keyword"]
    target = campaign["product_name"]

    if ctype == "blog":
        # Use product_url as blog_id if available, otherwise product_name
        blog_id = campaign.get("product_url") or target
        # Clean up blog_id (extract just the ID part)
        if "blog.naver.com/" in blog_id:
            blog_id = blog_id.split("blog.naver.com/")[-1].strip("/")
        result = check_blog_rank(keyword, blog_id)
    elif ctype == "place":
        result = check_place_rank(keyword, target)
    elif ctype == "shopping":
        result = check_shopping_rank(keyword, target)
    else:
        log.error("Unknown campaign type: %s", ctype)
        return None

    # Save to DB
    check_type = f"{ctype}_rank"
    snapshot = json.dumps(result, ensure_ascii=False)
    save_tracking(
        campaign_id=campaign_id,
        check_type=check_type,
        keyword=keyword,
        rank_position=result.get("rank"),
        page_number=result.get("page", 1),
        snapshot_json=snapshot,
    )

    # Update cache
    result["campaign_id"] = campaign_id
    result["customer_name"] = campaign["customer_name"]
    _update_cache(campaign_id, result)

    return result


def main():
    parser = argparse.ArgumentParser(description="Naver Rank Tracker")
    parser.add_argument("--campaign-id", type=int, help="Campaign ID to track")
    parser.add_argument("--keyword", type=str, help="Search keyword (manual mode)")
    parser.add_argument("--blog-id", type=str, help="Blog ID for blog rank check")
    parser.add_argument("--place-name", type=str, help="Place name for place rank check")
    parser.add_argument("--product-name", type=str, help="Product name for shopping rank check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.campaign_id:
        result = run_tracking(args.campaign_id)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("Tracking failed. Check logs.")
            exit(1)

    elif args.keyword:
        if args.blog_id:
            result = check_blog_rank(args.keyword, args.blog_id)
        elif args.place_name:
            result = check_place_rank(args.keyword, args.place_name)
        elif args.product_name:
            result = check_shopping_rank(args.keyword, args.product_name)
        else:
            parser.error("Specify --blog-id, --place-name, or --product-name with --keyword")
            return

        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.error("Specify --campaign-id or --keyword with a target option")


if __name__ == "__main__":
    main()
