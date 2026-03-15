"""
Telegram notification module for the Shopping Traffic Engine.
Sends daily reports, anomaly alerts, and goal achievements.

Usage:
    python notifier.py report    # Send daily report now
    python notifier.py check     # Run anomaly + goal checks
    python notifier.py test      # Send test message
"""

import json
import logging
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import requests

from database import (
    get_db,
    get_daily_stats,
    get_tracking_history,
    get_latest_tracking,
    list_campaigns,
)

log = logging.getLogger("notifier")

# --- Config ---
TELEGRAM_BOT_TOKEN = "8579891351:AAGrJsEmYSv7IxqtQURNazj1kQ2gEAzctnA"
TELEGRAM_CHAT_ID = "6095945808"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

ACCOUNTS_FILE = Path(__file__).parent / "accounts.json"

# Anomaly thresholds
MIN_SUCCESS_RATE = 0.5       # alert if below 50% in last hour
LOOKBACK_MINUTES = 60        # anomaly check window


# ------------------------------------------------------------------
# Telegram transport
# ------------------------------------------------------------------

def send_telegram(message: str) -> bool:
    """Send a message to the configured Telegram chat. Returns True on success."""
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            log.info("Telegram message sent (%d chars)", len(message))
            return True
        log.error("Telegram API error: %s", resp.text)
        return False
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False


# ------------------------------------------------------------------
# Daily report
# ------------------------------------------------------------------

def send_daily_report(target_date: str | None = None) -> bool:
    """Generate and send a daily campaign performance summary."""
    if target_date is None:
        target_date = date.today().isoformat()

    stats = get_daily_stats(target_date)
    campaigns = stats.get("campaigns", [])
    total = stats.get("total", 0)
    completed = stats.get("completed", 0)
    failed = stats.get("failed", 0)

    # Overall percentage
    pct = round(completed / total * 100) if total > 0 else 0

    # Average dwell time from completed jobs
    avg_duration = _get_avg_duration(target_date)

    # Account stats
    accounts_used, accounts_total = _get_account_stats()

    # Build message
    lines = [f"<b>📊 트래픽 엔진 일간 리포트 — {target_date}</b>", ""]

    # Per-campaign breakdown
    if campaigns:
        lines.append("<b>📋 캠페인 실적:</b>")
        for c in campaigns:
            cid = c["id"]
            kw = c["keyword"]
            success = c.get("success", 0) or 0
            target = c.get("daily_target", 0) or 0
            c_pct = round(success / target * 100) if target > 0 else 0
            icon = "✅" if c_pct >= 70 else ("⚠️" if c_pct >= 40 else "❌")
            lines.append(f"  #{cid} {kw}: {success}/{target} ({c_pct}%) {icon}")
        lines.append("")

    # Summary
    lines.append(f"<b>📈 전체:</b> {completed}/{total} ({pct}%)")
    lines.append(f"<b>⏱ 평균 체류시간:</b> {avg_duration:.1f}초")
    lines.append(f"<b>❌ 실패:</b> {failed}건")
    lines.append(f"<b>👤 계정 사용:</b> {accounts_used}/{accounts_total}")

    # Rank changes
    rank_lines = _build_rank_section(campaigns, target_date)
    if rank_lines:
        lines.append("")
        lines.append("<b>🏆 순위 변동:</b>")
        lines.extend(rank_lines)

    message = "\n".join(lines)
    return send_telegram(message)


def _get_avg_duration(target_date: str) -> float:
    """Calculate average duration_sec for completed jobs on the given date."""
    conn = get_db()
    row = conn.execute(
        """SELECT AVG(duration_sec) as avg_dur
           FROM jobs
           WHERE scheduled_date = ? AND status = 'completed' AND duration_sec > 0""",
        (target_date,),
    ).fetchone()
    conn.close()
    return (row["avg_dur"] or 0.0) if row else 0.0


def _get_account_stats() -> tuple[int, int]:
    """Return (accounts_used_today, accounts_total) from accounts.json."""
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 0

    total = len(accounts)
    today = date.today().isoformat()
    used = sum(1 for a in accounts if a.get("last_used") == today)
    return used, total


def _build_rank_section(campaigns: list[dict], target_date: str) -> list[str]:
    """Build rank-change lines from tracking data."""
    lines = []
    yesterday = (date.fromisoformat(target_date) - timedelta(days=1)).isoformat()

    for c in campaigns:
        cid = c["id"]
        kw = c["keyword"]

        # Latest tracking for today
        today_track = get_latest_tracking(cid)
        if not today_track or not today_track.get("rank_position"):
            continue

        today_rank = today_track["rank_position"]

        # Yesterday's tracking
        history = get_tracking_history(cid, days=7)
        yesterday_rank = None
        for h in history:
            if h.get("check_date") == yesterday and h.get("rank_position"):
                yesterday_rank = h["rank_position"]
                break

        if yesterday_rank is not None:
            diff = yesterday_rank - today_rank
            if diff > 0:
                arrow = f"▲{diff}"
            elif diff < 0:
                arrow = f"▼{abs(diff)}"
            else:
                arrow = "→"
            lines.append(f"  {kw}: {yesterday_rank}위 → {today_rank}위 ({arrow})")
        else:
            lines.append(f"  {kw}: {today_rank}위")

    return lines


# ------------------------------------------------------------------
# Anomaly detection
# ------------------------------------------------------------------

def check_anomalies() -> list[str]:
    """Check for anomalies and send alerts. Returns list of issues found."""
    issues = []

    conn = get_db()
    cutoff = (datetime.now() - timedelta(minutes=LOOKBACK_MINUTES)).isoformat()
    today = date.today().isoformat()

    # 1. Low success rate in last hour (per campaign)
    rows = conn.execute(
        """SELECT c.id, c.keyword,
                  COUNT(*) as total,
                  SUM(CASE WHEN j.success = 1 THEN 1 ELSE 0 END) as success
           FROM jobs j
           JOIN campaigns c ON j.campaign_id = c.id
           WHERE j.scheduled_date = ?
             AND j.status IN ('completed', 'failed')
             AND j.completed_at >= ?
           GROUP BY c.id""",
        (today, cutoff),
    ).fetchall()

    for row in rows:
        total = row["total"]
        success = row["success"] or 0
        if total >= 3 and (success / total) < MIN_SUCCESS_RATE:
            rate = round(success / total * 100)
            issue = f"캠페인 #{row['id']} ({row['keyword']}): 최근 1시간 성공률 {rate}% ({success}/{total})"
            issues.append(issue)
            send_anomaly_alert(row["id"], "low_success_rate", issue)

    # 2. All jobs failing for a campaign today
    rows = conn.execute(
        """SELECT c.id, c.keyword,
                  COUNT(*) as total,
                  SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) as failed
           FROM jobs j
           JOIN campaigns c ON j.campaign_id = c.id
           WHERE j.scheduled_date = ?
             AND j.status IN ('completed', 'failed')
           GROUP BY c.id
           HAVING total >= 5 AND failed = total""",
        (today,),
    ).fetchall()

    for row in rows:
        issue = f"캠페인 #{row['id']} ({row['keyword']}): 오늘 전체 {row['total']}건 실패"
        issues.append(issue)
        send_anomaly_alert(row["id"], "all_failed", issue)

    # 3. Captcha / block detection (error messages containing captcha keywords)
    rows = conn.execute(
        """SELECT c.id, c.keyword, COUNT(*) as cnt
           FROM jobs j
           JOIN campaigns c ON j.campaign_id = c.id
           WHERE j.scheduled_date = ?
             AND j.status = 'failed'
             AND j.completed_at >= ?
             AND (j.error LIKE '%captcha%' OR j.error LIKE '%차단%' OR j.error LIKE '%block%')
           GROUP BY c.id
           HAVING cnt >= 3""",
        (today, cutoff),
    ).fetchall()

    for row in rows:
        issue = f"캠페인 #{row['id']} ({row['keyword']}): 네이버 차단 감지 ({row['cnt']}건 캡차/차단)"
        issues.append(issue)
        send_anomaly_alert(row["id"], "naver_block", issue)

    # 4. Account suspension check
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        suspended = [a for a in accounts if a.get("status") == "suspended"]
        for a in suspended:
            issue = f"계정 {a['id']}: 정지 상태"
            issues.append(issue)
            send_anomaly_alert(0, "account_suspended", issue)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    conn.close()

    if issues:
        log.warning("Anomaly check found %d issues", len(issues))
    else:
        log.info("Anomaly check: no issues found")

    return issues


def send_anomaly_alert(campaign_id: int, issue_type: str, details: str) -> bool:
    """Send an anomaly warning to Telegram."""
    type_labels = {
        "low_success_rate": "⚠️ 낮은 성공률",
        "all_failed": "🚨 전체 실패",
        "naver_block": "🛑 네이버 차단 감지",
        "account_suspended": "🔒 계정 정지",
    }
    label = type_labels.get(issue_type, f"⚠️ {issue_type}")
    now = datetime.now().strftime("%H:%M:%S")

    message = (
        f"<b>{label}</b>\n"
        f"시각: {now}\n"
        f"캠페인: #{campaign_id}\n"
        f"상세: {details}"
    )
    return send_telegram(message)


# ------------------------------------------------------------------
# Goal check
# ------------------------------------------------------------------

def check_goals() -> list[str]:
    """Check if any campaign hit its daily target. Returns list of achieved goals."""
    achieved = []
    today = date.today().isoformat()
    stats = get_daily_stats(today)

    for c in stats.get("campaigns", []):
        success = c.get("success", 0) or 0
        target = c.get("daily_target", 0) or 0
        if target > 0 and success >= target:
            msg = f"캠페인 #{c['id']} ({c['keyword']}): {success}/{target} 달성"
            achieved.append(msg)
            send_goal_achieved(c["id"], c["keyword"], target, success)

    if achieved:
        log.info("Goal check: %d campaigns achieved target", len(achieved))
    else:
        log.info("Goal check: no campaigns at target yet")

    return achieved


def send_goal_achieved(campaign_id: int, keyword: str, target: int, completed: int) -> bool:
    """Send a goal-achieved celebration message to Telegram."""
    pct = round(completed / target * 100) if target > 0 else 0
    message = (
        f"<b>🎯 일일 목표 달성!</b>\n\n"
        f"캠페인: #{campaign_id}\n"
        f"키워드: {keyword}\n"
        f"실적: {completed}/{target} ({pct}%)\n\n"
        f"🎉 오늘 목표를 달성했습니다!"
    )
    return send_telegram(message)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("사용법: python notifier.py [report|check|test]")
        print("  report  - 일간 리포트 전송")
        print("  check   - 이상 감지 + 목표 달성 체크")
        print("  test    - 테스트 메시지 전송")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "report":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        ok = send_daily_report(target)
        print("일간 리포트 전송 완료" if ok else "일간 리포트 전송 실패")

    elif cmd == "check":
        print("이상 감지 실행 중...")
        issues = check_anomalies()
        if issues:
            print(f"발견된 이상: {len(issues)}건")
            for i in issues:
                print(f"  - {i}")
        else:
            print("이상 없음")

        print("\n목표 달성 체크 중...")
        achieved = check_goals()
        if achieved:
            print(f"목표 달성: {len(achieved)}건")
            for a in achieved:
                print(f"  - {a}")
        else:
            print("아직 목표 달성 캠페인 없음")

    elif cmd == "test":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ok = send_telegram(f"🔔 <b>트래픽 엔진 테스트</b>\n\n연결 확인: {now}\n상태: 정상")
        print("테스트 메시지 전송 완료" if ok else "테스트 메시지 전송 실패")

    else:
        print(f"알 수 없는 명령: {cmd}")
        print("사용법: python notifier.py [report|check|test]")
        sys.exit(1)


if __name__ == "__main__":
    main()
