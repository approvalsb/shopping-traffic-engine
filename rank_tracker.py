"""
Naver rank tracking for blog, place, and shopping campaigns.
Uses requests + BeautifulSoup for lightweight scraping (no Selenium).
"""

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

# Load .env file manually (no external dependency)
def _load_dotenv():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val

_load_dotenv()

import requests
from bs4 import BeautifulSoup

from database import get_db, get_campaign, list_campaigns, save_tracking, DB_PATH

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


def check_blog_rank(keyword: str, blog_id: str, max_pages: int = 5) -> dict:
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


def check_place_rank(keyword: str, place_name: str, max_pages: int = 5) -> dict:
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


def check_shopping_rank(keyword: str, product_name: str, max_pages: int = 5) -> dict:
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


def find_related_rankings(keyword: str, blog_id: str, api_key: str) -> list[dict]:
    """Generate related keywords via Gemini and check blog rank for each.

    Args:
        keyword: Original search keyword
        blog_id: Naver blog ID
        api_key: Gemini API key

    Returns:
        list of dicts with keyword, rank, page
    """
    prompt = (
        "다음 네이버 블로그 검색 키워드의 짧은 연관 키워드 3개를 JSON 배열로만 응답해줘. "
        "원래 키워드의 핵심 단어를 포함한 2-3단어 조합으로. "
        f"키워드: {keyword}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
    }

    related_keywords = []
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # Extract JSON array from response (may be wrapped in markdown code block)
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        related_keywords = json.loads(text.strip())
        log.info("Related keywords for '%s': %s", keyword, related_keywords)
    except Exception as e:
        log.error("Gemini related keyword generation failed: %s", e)
        return []

    results = []
    for rk in related_keywords[:3]:
        time.sleep(3)
        try:
            rank_result = check_blog_rank(rk, blog_id, max_pages=3)
            results.append({
                "keyword": rk,
                "rank": rank_result.get("rank"),
                "page": rank_result.get("page", 0),
            })
        except Exception as e:
            log.error("Related rank check failed for '%s': %s", rk, e)
            results.append({"keyword": rk, "rank": None, "page": 0})

    return results


def generate_strategy(results: list[dict], customer_name: str) -> dict:
    """Generate AI strategy based on tracking results using Gemini 2.5 Flash.

    Returns dict with:
      - keyword_strategies: list of {keyword, rank, strategy}
      - overall_strategy: str (overall blog strategy, 3-5 sentences)
      - generated_at: str (datetime)
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        log.warning("GEMINI_API_KEY not set, skipping strategy generation")
        return {}

    # Build keyword data text
    keyword_lines = []
    for r in results:
        keyword = r.get("keyword", "")
        rank = r.get("rank")
        rank_str = f"#{rank}" if rank else "미발견"
        related = r.get("related_rankings", [])
        related_str = ""
        if related:
            parts = [f"{rr['keyword']}(#{rr['rank']})" if rr.get("rank") else f"{rr['keyword']}(미발견)" for rr in related]
            related_str = f" | 연관키워드: {', '.join(parts)}"
        keyword_lines.append(f"- {keyword}: {rank_str}{related_str}")

    keyword_data = "\n".join(keyword_lines)

    prompt = f"""당신은 네이버 블로그 SEO 전문 컨설턴트입니다.

고객: {customer_name}
현재 키워드별 네이버 블로그 검색 순위:
{keyword_data}

위 데이터를 분석하여 다음을 JSON으로 응답해주세요:
{{
  "keyword_strategies": [
    {{"keyword": "키워드명", "current_status": "현재상태 요약", "action": "구체적 액션 1-2문장"}}
  ],
  "overall_strategy": "블로그 전체 운영 방향 3-5문장. 현재 상황 진단과 향후 1개월 전략을 포함."
}}

전략 작성 시 규칙:
- 구체적이고 실행 가능한 액션 위주로
- 순위가 없는 키워드는 노출 가능성을 높이는 방법 제안
- 순위가 있는 키워드는 순위 상승/유지 전략 제안
- 고객이 읽어도 이해할 수 있는 쉬운 한국어로
- 연관 키워드 데이터가 있으면 활용하여 전략 제안"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # Extract JSON from response (may be wrapped in markdown code block)
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        strategy = json.loads(text.strip())
        strategy["generated_at"] = _now_str()
        log.info("Strategy generated for '%s': %d keyword strategies", customer_name, len(strategy.get("keyword_strategies", [])))
        return strategy
    except Exception as e:
        log.error("Strategy generation failed for '%s': %s", customer_name, e)
        return {}


def _update_strategy_cache(strategy_by_customer: dict):
    """Save strategy per customer_name to tracking_cache.json."""
    CACHE_PATH.parent.mkdir(exist_ok=True)

    cache = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}

    cache["strategy"] = strategy_by_customer
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Strategy cache updated for %d customers", len(strategy_by_customer))


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

    # Preserve related_rankings in latest if present
    if "related_rankings" in tracking_result:
        cache[key]["latest"]["related_rankings"] = tracking_result["related_rankings"]

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
        # If not found, try related keywords via Gemini
        if result.get("rank") is None:
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                related = find_related_rankings(keyword, blog_id, api_key)
                if related:
                    result["related_rankings"] = related
                    log.info("Related rankings for '%s': %s", keyword, related)
            else:
                log.warning("GEMINI_API_KEY not set, skipping related keyword search")
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


def run_all_tracking() -> list[dict]:
    """Run rank tracking for ALL active campaigns.

    Returns list of tracking results.
    """

    campaigns = list_campaigns(active_only=True)
    if not campaigns:
        log.info("No active campaigns found.")
        return []

    results = []
    for camp in campaigns:
        cid = camp["id"]
        log.info("Tracking campaign #%d [%s] keyword='%s'", cid, camp.get("type", "?"), camp["keyword"])
        try:
            result = run_tracking(cid)
            if result:
                rank_str = f"#{result['rank']}" if result.get("rank") else "not found"
                log.info("  -> %s", rank_str)
                results.append(result)
            else:
                log.warning("  -> tracking failed")
        except Exception as e:
            log.error("  -> error: %s", e)

        # Polite delay between requests to avoid rate limiting
        time.sleep(4)

    # Summary
    found = sum(1 for r in results if r.get("rank") is not None)
    log.info("Tracking complete: %d/%d campaigns tracked, %d ranked", len(results), len(campaigns), found)

    # Generate AI strategy per customer
    if results:
        # Group results by customer_name
        by_customer: dict[str, list[dict]] = {}
        for r in results:
            cname = r.get("customer_name", "Unknown")
            by_customer.setdefault(cname, []).append(r)

        strategy_by_customer = {}
        for cname, cresults in by_customer.items():
            try:
                strategy = generate_strategy(cresults, cname)
                if strategy:
                    strategy_by_customer[cname] = strategy
            except Exception as e:
                log.error("Strategy generation error for '%s': %s", cname, e)

        if strategy_by_customer:
            _update_strategy_cache(strategy_by_customer)

    return results


def main():
    parser = argparse.ArgumentParser(description="Naver Rank Tracker")
    parser.add_argument("--campaign-id", type=int, help="Campaign ID to track")
    parser.add_argument("--all", action="store_true", help="Track ALL active campaigns")
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

    if args.all:
        results = run_all_tracking()
        print(f"\n{'='*50}")
        print(f"  Rank Tracking Summary")
        print(f"{'='*50}")
        for r in results:
            rank = f"#{r['rank']}" if r.get("rank") else "N/A"
            print(f"  [{r.get('type','?')}] {r.get('keyword','')} -> {rank}")
        print(f"{'='*50}")

    elif args.campaign_id:
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
        parser.error("Specify --all, --campaign-id, or --keyword with a target option")


if __name__ == "__main__":
    main()
