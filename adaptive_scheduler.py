#!/usr/bin/env python3
"""
Adaptive scheduler — monitors daily progress and creates supplementary jobs
to ensure daily success targets are met despite failures.

Also runs anomaly detection and sends Telegram alerts.

Designed to run via cron every 2 hours (e.g., 10, 12, 14, 16, 18, 20).

Flow:
  1. Check each campaign's success count vs daily_target
  2. Calculate how many more successes are needed
  3. Estimate failure rate from recent history
  4. Create supplementary jobs with buffer (needed / expected_success_rate)
  5. Run anomaly checks and alert via Telegram
  6. Send progress summary if significantly behind

Usage:
    python adaptive_scheduler.py           # run adaptive check
    python adaptive_scheduler.py --dry-run # preview without creating jobs
    python adaptive_scheduler.py --force   # force refill even if already ran this hour
"""

import argparse
import json
import logging
import random
import sys
from datetime import date, datetime, timedelta

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("adaptive")

# --- Config ---
MASTER_API = "http://localhost:5000"
MIN_SUCCESS_RATE = 0.3          # alert if campaign success rate drops below 30%
CONSECUTIVE_FAIL_THRESHOLD = 5  # alert after N consecutive failures
MAX_SUPPLEMENT_RATIO = 3.0      # never create more than 3x daily_target total jobs
DEFAULT_BUFFER = 1.5            # create 50% extra jobs to account for failures

# Telegram (same as notifier.py)
TELEGRAM_BOT_TOKEN = "8579891351:AAGrJsEmYSv7IxqtQURNazj1kQ2gEAzctnA"
TELEGRAM_CHAT_ID = "6095945808"


def send_telegram(message: str) -> bool:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        return resp.status_code == 200 and resp.json().get("ok")
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False


def api_get(path: str) -> dict:
    resp = requests.get(f"{MASTER_API}{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, data: dict) -> dict:
    resp = requests.post(f"{MASTER_API}{path}", json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_daily_progress(target_date: str) -> dict:
    """Get today's schedule data from master API."""
    return api_get(f"/api/schedule?date={target_date}")


def get_campaigns() -> list[dict]:
    """Get all active campaigns."""
    data = api_get("/api/campaigns")
    camps = data if isinstance(data, list) else data.get("campaigns", [])
    return [c for c in camps if c.get("active")]


def get_campaign_stats(schedule_data: dict) -> dict:
    """Aggregate job stats per campaign from schedule timeline."""
    stats = {}  # campaign_id -> {completed, failed, pending, running, total}

    for block in schedule_data.get("timeline", []):
        for job in block.get("jobs", []):
            cid = job.get("campaign_id")
            if cid not in stats:
                stats[cid] = {"completed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0}
            stats[cid]["total"] += 1
            status = job.get("status", "pending")
            if status in stats[cid]:
                stats[cid][status] += 1

    return stats


def get_recent_success_rate(schedule_data: dict, last_n_hours: int = 4) -> float:
    """Calculate overall success rate from recent hours."""
    now_hour = datetime.now().hour
    completed = 0
    total_done = 0

    for block in schedule_data.get("timeline", []):
        hour = block.get("hour", 0)
        if hour > now_hour - last_n_hours and hour <= now_hour:
            for job in block.get("jobs", []):
                status = job.get("status")
                if status == "completed":
                    completed += 1
                    total_done += 1
                elif status == "failed":
                    total_done += 1

    if total_done == 0:
        return 0.7  # assume 70% if no data yet
    return completed / total_done


def check_consecutive_failures(schedule_data: dict) -> list[str]:
    """Check for consecutive failures across all jobs (most recent first)."""
    all_jobs = []
    for block in schedule_data.get("timeline", []):
        for job in block.get("jobs", []):
            if job.get("status") in ("completed", "failed"):
                all_jobs.append(job)

    # Sort by completion time (most recent first)
    all_jobs.sort(key=lambda j: j.get("completed_at") or "", reverse=True)

    consecutive_fails = 0
    last_error = ""
    for job in all_jobs:
        if job["status"] == "failed":
            consecutive_fails += 1
            if not last_error:
                last_error = job.get("error", "unknown")
        else:
            break

    return consecutive_fails, last_error


def calculate_supplement_jobs(
    campaign: dict,
    camp_stats: dict,
    success_rate: float,
) -> int:
    """Calculate how many supplementary jobs to create for a campaign."""
    daily_target = campaign.get("daily_target", 2)
    completed = camp_stats.get("completed", 0)
    pending = camp_stats.get("pending", 0)
    running = camp_stats.get("running", 0)
    total_created = camp_stats.get("total", 0)

    # How many more successes do we need?
    needed = daily_target - completed

    if needed <= 0:
        return 0  # already at target

    # Subtract pending/running jobs (they might still succeed)
    expected_from_pending = int((pending + running) * success_rate)
    still_needed = needed - expected_from_pending

    if still_needed <= 0:
        return 0  # pending jobs should cover it

    # Add buffer based on success rate
    if success_rate > 0.1:
        jobs_to_create = int(still_needed / success_rate)
    else:
        # Very low success rate — create minimal, something is very wrong
        jobs_to_create = still_needed

    # Cap at MAX_SUPPLEMENT_RATIO * daily_target total jobs
    max_total = int(daily_target * MAX_SUPPLEMENT_RATIO)
    max_new = max(0, max_total - total_created)
    jobs_to_create = min(jobs_to_create, max_new)

    return max(0, jobs_to_create)


def create_supplement_jobs(
    campaign_id: int,
    count: int,
    target_date: str,
    dry_run: bool = False,
) -> int:
    """Create supplementary jobs via master API for remaining hours today."""
    if count <= 0:
        return 0

    now_hour = datetime.now().hour
    remaining_hours = list(range(now_hour + 1, 24))

    if not remaining_hours:
        log.info("No remaining hours today, skipping supplement for campaign #%d", campaign_id)
        return 0

    if dry_run:
        log.info("[DRY-RUN] Would create %d supplement jobs for campaign #%d", count, campaign_id)
        return count

    # Use master API to generate jobs
    try:
        resp = requests.post(
            f"{MASTER_API}/api/jobs/supplement",
            json={
                "campaign_id": campaign_id,
                "count": count,
                "date": target_date,
                "start_hour": now_hour + 1,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            result = resp.json()
            created = result.get("created", 0)
            log.info("Created %d supplement jobs for campaign #%d", created, campaign_id)
            return created
        else:
            log.error("Supplement API error: %s %s", resp.status_code, resp.text)
            return 0
    except Exception as e:
        log.error("Failed to create supplement jobs: %s", e)
        return 0


def run_adaptive_check(dry_run: bool = False) -> dict:
    """Main adaptive scheduling logic."""
    today = date.today().isoformat()
    now = datetime.now()
    log.info("=== Adaptive check: %s %s ===", today, now.strftime("%H:%M"))

    # 1. Get current progress
    schedule = get_daily_progress(today)
    campaigns = get_campaigns()
    camp_stats = get_campaign_stats(schedule)
    success_rate = get_recent_success_rate(schedule)

    log.info("Recent success rate: %.0f%%", success_rate * 100)

    # 2. Check consecutive failures -> alert
    consec_fails, last_error = check_consecutive_failures(schedule)
    alerts_sent = []

    if consec_fails >= CONSECUTIVE_FAIL_THRESHOLD:
        alert_msg = (
            f"🚨 <b>연속 실패 경고</b>\n\n"
            f"연속 {consec_fails}회 실패 감지\n"
            f"최근 에러: {last_error[:100]}\n"
            f"시각: {now.strftime('%H:%M')}\n\n"
            f"확인이 필요합니다."
        )
        send_telegram(alert_msg)
        alerts_sent.append(f"consecutive_failures: {consec_fails}")
        log.warning("ALERT: %d consecutive failures", consec_fails)

    # 3. Check per-campaign progress and create supplements
    total_supplemented = 0
    campaign_summary = []

    for camp in campaigns:
        cid = camp["id"]
        stats = camp_stats.get(cid, {"completed": 0, "failed": 0, "pending": 0, "running": 0, "total": 0})
        daily_target = camp.get("daily_target", 2)
        completed = stats["completed"]
        failed = stats["failed"]
        total = stats["total"]

        # Campaign-level success rate
        camp_done = completed + failed
        camp_success_rate = (completed / camp_done) if camp_done > 0 else success_rate

        # Alert if campaign success rate is very low
        if camp_done >= 3 and camp_success_rate < MIN_SUCCESS_RATE:
            alert_msg = (
                f"⚠️ <b>캠페인 성공률 저조</b>\n\n"
                f"캠페인 #{cid}: {camp['keyword']}\n"
                f"성공률: {camp_success_rate:.0%} ({completed}/{camp_done})\n"
                f"목표: {daily_target}건\n"
                f"시각: {now.strftime('%H:%M')}"
            )
            if f"camp_{cid}" not in [a.split(":")[0] for a in alerts_sent]:
                send_telegram(alert_msg)
                alerts_sent.append(f"camp_{cid}: low_rate")

        # Calculate supplement
        supplement = calculate_supplement_jobs(camp, stats, max(camp_success_rate, success_rate))

        if supplement > 0:
            created = create_supplement_jobs(cid, supplement, today, dry_run=dry_run)
            total_supplemented += created
            log.info("Campaign #%d (%s): %d/%d done, +%d supplement jobs",
                     cid, camp["keyword"], completed, daily_target, created)

        campaign_summary.append({
            "id": cid,
            "keyword": camp["keyword"],
            "target": daily_target,
            "completed": completed,
            "failed": failed,
            "pending": stats["pending"],
            "supplemented": supplement,
        })

    # 4. Send progress summary if behind schedule
    expected_progress = now.hour / 24.0  # rough expected % of day completed
    overall_completed = schedule.get("completed", 0)
    overall_total = schedule.get("total", 0)
    overall_target = sum(c.get("daily_target", 0) for c in campaigns)

    if overall_target > 0:
        actual_progress = overall_completed / overall_target
        if actual_progress < expected_progress * 0.5 and now.hour >= 12:
            # Significantly behind (less than half expected progress, after noon)
            summary_lines = [
                f"📊 <b>일일 진행 상황 (적응형 스케줄러)</b>",
                f"시각: {now.strftime('%H:%M')} | 목표: {overall_target}건",
                f"완료: {overall_completed} | 실패: {schedule.get('failed', 0)}",
                f"성공률: {success_rate:.0%}",
                "",
            ]
            for cs in campaign_summary:
                icon = "✅" if cs["completed"] >= cs["target"] else "⏳"
                supplement_note = f" (+{cs['supplemented']}보충)" if cs["supplemented"] > 0 else ""
                summary_lines.append(
                    f"  {icon} #{cs['id']} {cs['keyword']}: "
                    f"{cs['completed']}/{cs['target']}{supplement_note}"
                )

            if total_supplemented > 0:
                summary_lines.append(f"\n📌 보충 잡 {total_supplemented}건 생성")

            send_telegram("\n".join(summary_lines))

    log.info("Adaptive check complete: %d supplement jobs created, %d alerts sent",
             total_supplemented, len(alerts_sent))

    return {
        "date": today,
        "success_rate": success_rate,
        "consecutive_failures": consec_fails,
        "supplements_created": total_supplemented,
        "alerts": alerts_sent,
        "campaigns": campaign_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Adaptive scheduler for traffic engine")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating jobs")
    parser.add_argument("--force", action="store_true", help="Force run even if recently ran")
    args = parser.parse_args()

    result = run_adaptive_check(dry_run=args.dry_run)

    print()
    print("=" * 50)
    print("  Adaptive Scheduler Result")
    print("=" * 50)
    print(f"  Date: {result['date']}")
    print(f"  Success rate: {result['success_rate']:.0%}")
    print(f"  Consecutive failures: {result['consecutive_failures']}")
    print(f"  Supplements created: {result['supplements_created']}")
    print(f"  Alerts sent: {len(result['alerts'])}")
    for cs in result["campaigns"]:
        print(f"  #{cs['id']} {cs['keyword']}: {cs['completed']}/{cs['target']} "
              f"(+{cs['supplemented']} supplement)")
    print("=" * 50)


if __name__ == "__main__":
    main()
