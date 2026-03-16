"""
Master server - Flask API for job distribution and monitoring.
Workers poll this server for jobs and report results.

Usage:
    python master.py [--host 0.0.0.0] [--port 5000]
"""

import json
import sys
import logging
import threading
import time
from datetime import datetime, date, timedelta
from pathlib import Path

from flask import Flask, request, jsonify

import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("master")

app = Flask(__name__)


# --- Worker API ---

@app.route("/api/jobs/next", methods=["POST"])
def get_next_jobs():
    """Worker calls this to get pending jobs."""
    data = request.json or {}
    worker_id = data.get("worker_id", "unknown")
    batch_size = data.get("batch_size", 5)

    # Register heartbeat
    db.heartbeat_worker(worker_id)

    jobs = db.fetch_next_jobs(worker_id, batch_size=batch_size)
    return jsonify({"jobs": jobs})


@app.route("/api/jobs/<int:job_id>/complete", methods=["POST"])
def complete_job(job_id):
    """Worker reports job completion."""
    data = request.json or {}
    db.complete_job(
        job_id=job_id,
        success=data.get("success", False),
        duration_sec=data.get("duration_sec", 0),
        error=data.get("error"),
    )
    return jsonify({"ok": True})


@app.route("/api/workers/register", methods=["POST"])
def register_worker():
    """Worker registers itself on startup."""
    data = request.json or {}
    db.register_worker(
        worker_id=data["worker_id"],
        hostname=data.get("hostname", "unknown"),
        max_chrome=data.get("max_chrome", 8),
    )
    log.info("Worker registered: %s (%s)", data["worker_id"], data.get("hostname"))
    return jsonify({"ok": True})


@app.route("/api/workers/heartbeat", methods=["POST"])
def heartbeat():
    """Worker periodic heartbeat."""
    data = request.json or {}
    db.heartbeat_worker(data.get("worker_id", "unknown"))
    return jsonify({"ok": True})


# --- Management API ---

@app.route("/api/campaigns", methods=["GET"])
def list_campaigns():
    campaigns = db.list_campaigns(active_only=request.args.get("all") != "1")
    return jsonify({"campaigns": campaigns})


@app.route("/api/campaigns", methods=["POST"])
def add_campaign():
    data = request.json
    cid = db.add_campaign(
        customer_name=data["customer_name"],
        keyword=data["keyword"],
        product_name=data["product_name"],
        product_url=data.get("product_url", ""),
        daily_target=data.get("daily_target", 300),
        dwell_min=data.get("dwell_time_min", 30.0),
        dwell_max=data.get("dwell_time_max", 90.0),
        campaign_type=data.get("type", "shopping"),
    )
    log.info("Campaign added: #%d %s [%s]", cid, data["customer_name"], data["keyword"])
    return jsonify({"id": cid})


@app.route("/api/campaigns/<int:cid>", methods=["DELETE"])
def delete_campaign(cid):
    db.delete_campaign(cid)
    return jsonify({"ok": True})


@app.route("/api/campaigns/<int:cid>/toggle", methods=["POST"])
def toggle_campaign(cid):
    data = request.json or {}
    db.toggle_campaign(cid, data.get("active", True))
    return jsonify({"ok": True})


# --- Stats API ---

@app.route("/api/stats", methods=["GET"])
def get_stats():
    target_date = request.args.get("date", date.today().isoformat())
    stats = db.get_daily_stats(target_date)
    workers = db.list_workers()
    return jsonify({"stats": stats, "workers": workers})


@app.route("/api/stats/summary", methods=["GET"])
def get_summary():
    """Quick summary for monitoring."""
    stats = db.get_daily_stats()
    total = stats.get("total", 0) or 0
    completed = stats.get("completed", 0) or 0
    failed = stats.get("failed", 0) or 0
    pending = stats.get("pending", 0) or 0
    running = stats.get("running", 0) or 0
    pct = (completed / total * 100) if total > 0 else 0
    return jsonify({
        "date": date.today().isoformat(),
        "total": total,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "running": running,
        "progress_pct": round(pct, 1),
    })


@app.route("/api/tracking", methods=["GET"])
def get_tracking():
    """Return tracking cache data for dashboard."""
    cache_path = Path("data/tracking_cache.json")
    if not cache_path.exists():
        return jsonify({"campaigns": [], "history": [], "latest": None, "trend": "stable"})

    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return jsonify({"campaigns": [], "history": [], "latest": None, "trend": "stable"})

    campaign_id = request.args.get("campaignId")
    days = int(request.args.get("days", "30"))

    if not campaign_id:
        campaigns = []
        for cid, data in cache.items():
            campaigns.append({
                "id": int(cid),
                "customer_name": (data.get("latest") or {}).get("customer_name", f"Campaign {cid}"),
                "keyword": (data.get("latest") or {}).get("keyword", ""),
                "type": (data.get("latest") or {}).get("type", ""),
                "latest_rank": (data.get("latest") or {}).get("rank"),
                "trend": data.get("trend", "stable"),
            })
        return jsonify({"campaigns": campaigns, "history": [], "latest": None, "trend": "stable"})

    entry = cache.get(campaign_id)
    if not entry:
        return jsonify({"history": [], "latest": None, "trend": "stable"})

    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for h in entry.get("history", []):
        checked = h.get("checked_at", "")
        try:
            if datetime.strptime(checked, "%Y-%m-%d %H:%M:%S") >= cutoff:
                filtered.append(h)
        except ValueError:
            filtered.append(h)

    return jsonify({
        "history": filtered,
        "latest": entry.get("latest"),
        "trend": entry.get("trend", "stable"),
    })


@app.route("/api/jobs/generate", methods=["POST"])
def generate_jobs():
    """Manually trigger job generation for today."""
    data = request.json or {}
    target_date = data.get("date", date.today().isoformat())
    count = db.generate_daily_jobs(target_date)
    return jsonify({"generated": count, "date": target_date})


# --- Background scheduler ---

def _scheduler_loop():
    """Background thread: generate daily jobs + reset stale jobs."""
    last_generated_date = None

    while True:
        try:
            today = date.today().isoformat()

            # Generate today's jobs if not yet done
            if last_generated_date != today:
                count = db.generate_daily_jobs(today)
                if count > 0:
                    log.info("Scheduler: generated %d jobs for %s", count, today)
                last_generated_date = today

            # Reset stale running jobs (worker crashed)
            db.reset_stale_jobs(timeout_minutes=10)

        except Exception as e:
            log.error("Scheduler error: %s", e)

        time.sleep(60)  # Check every minute


@app.route("/")
def index():
    """Simple status page."""
    stats = db.get_daily_stats()
    workers = db.list_workers()
    total = stats.get("total", 0) or 0
    completed = stats.get("completed", 0) or 0
    failed = stats.get("failed", 0) or 0
    pending = stats.get("pending", 0) or 0
    running = stats.get("running", 0) or 0
    pct = (completed / total * 100) if total > 0 else 0

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Traffic Engine Master</title>
<meta http-equiv="refresh" content="30">
<style>
body {{ font-family: monospace; padding: 20px; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #00e676; }}
table {{ border-collapse: collapse; margin: 10px 0; }}
th, td {{ border: 1px solid #333; padding: 6px 12px; text-align: left; }}
th {{ background: #16213e; }}
.ok {{ color: #00e676; }} .fail {{ color: #ff5252; }} .pending {{ color: #ffd740; }}
</style></head><body>
<h1>Traffic Engine - {date.today().isoformat()}</h1>
<h2>Progress: <span class="ok">{completed}</span> / {total} ({pct:.0f}%)</h2>
<p>Pending: <span class="pending">{pending}</span> |
   Running: {running} |
   Failed: <span class="fail">{failed}</span></p>

<h3>Workers</h3>
<table><tr><th>ID</th><th>Host</th><th>Status</th><th>Done</th><th>Failed</th><th>Last Seen</th></tr>"""

    for w in workers:
        html += f"""<tr>
<td>{w['id']}</td><td>{w['hostname']}</td>
<td class="{'ok' if w['status']=='online' else 'fail'}">{w['status']}</td>
<td>{w['jobs_completed']}</td><td>{w['jobs_failed']}</td>
<td>{w['last_heartbeat'] or '-'}</td></tr>"""

    html += "</table><h3>Campaigns</h3><table>"
    html += "<tr><th>ID</th><th>Type</th><th>Customer</th><th>Keyword</th><th>Target</th><th>Done</th><th>Pending</th></tr>"

    for c in stats.get("campaigns", []):
        ctype = c.get('type', 'shopping')
        badge = '🛒' if ctype == 'shopping' else '📍'
        html += f"""<tr><td>{c['id']}</td><td>{badge} {ctype}</td><td>{c['customer_name']}</td>
<td>{c['keyword']}</td><td>{c['daily_target']}</td>
<td class="ok">{c.get('success', 0) or 0}</td>
<td class="pending">{c.get('pending', 0) or 0}</td></tr>"""

    html += "</table></body></html>"
    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Traffic Engine Master Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    # Initialize DB
    db.init_db()

    # Start background scheduler
    scheduler = threading.Thread(target=_scheduler_loop, daemon=True)
    scheduler.start()
    log.info("Background scheduler started")

    log.info("Master server starting on %s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
