"""
SQLite database for campaign and job management.
Handles campaign CRUD, job scheduling, and worker tracking.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, date

log = logging.getLogger("database")

DB_PATH = Path("data/traffic_engine.db")

# Hourly traffic weight presets by campaign type
SHOPPING_WEIGHTS = {
    0: 0.3,  1: 0.1,  2: 0.05, 3: 0.02,
    4: 0.02, 5: 0.05, 6: 0.2,  7: 0.5,
    8: 0.7,  9: 1.0,  10: 1.2, 11: 1.0,
    12: 0.8, 13: 1.0, 14: 1.2, 15: 1.1,
    16: 1.0, 17: 0.9, 18: 0.8, 19: 1.0,
    20: 1.3, 21: 1.5, 22: 1.2, 23: 0.8,
}

BLOG_WEIGHTS = {
    0: 0.1,  1: 0.05, 2: 0.02, 3: 0.02,
    4: 0.02, 5: 0.05, 6: 0.1,  7: 0.3,
    8: 0.6,  9: 1.0,  10: 1.4, 11: 1.5,
    12: 1.3, 13: 1.4, 14: 1.3, 15: 1.1,
    16: 1.0, 17: 0.8, 18: 0.5, 19: 0.4,
    20: 0.3, 21: 0.3, 22: 0.2, 23: 0.1,
}

PLACE_WEIGHTS = {
    0: 0.1,  1: 0.05, 2: 0.02, 3: 0.02,
    4: 0.02, 5: 0.05, 6: 0.1,  7: 0.3,
    8: 0.5,  9: 0.7,  10: 0.8, 11: 1.0,
    12: 1.5, 13: 1.4, 14: 1.0, 15: 0.7,
    16: 0.6, 17: 0.8, 18: 1.3, 19: 1.5,
    20: 1.4, 21: 1.0, 22: 0.5, 23: 0.2,
}

# Global default (backward compat alias)
HOURLY_WEIGHTS = SHOPPING_WEIGHTS

DEFAULT_WEIGHTS_BY_TYPE = {
    "shopping": SHOPPING_WEIGHTS,
    "blog": BLOG_WEIGHTS,
    "place": PLACE_WEIGHTS,
}


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT DEFAULT 'shopping',
            customer_name TEXT NOT NULL,
            keyword TEXT NOT NULL,
            product_name TEXT NOT NULL,
            product_url TEXT DEFAULT '',
            daily_target INTEGER DEFAULT 300,
            dwell_time_min REAL DEFAULT 30.0,
            dwell_time_max REAL DEFAULT 90.0,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            scheduled_date TEXT NOT NULL,
            scheduled_hour INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            worker_id TEXT,
            started_at TEXT,
            completed_at TEXT,
            success INTEGER,
            error TEXT,
            duration_sec REAL,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );

        CREATE TABLE IF NOT EXISTS workers (
            id TEXT PRIMARY KEY,
            hostname TEXT,
            max_chrome INTEGER DEFAULT 8,
            status TEXT DEFAULT 'offline',
            last_heartbeat TEXT,
            jobs_completed INTEGER DEFAULT 0,
            jobs_failed INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status
            ON jobs(status, scheduled_date, scheduled_hour);
        CREATE INDEX IF NOT EXISTS idx_jobs_campaign
            ON jobs(campaign_id, scheduled_date);
    """)
    conn.commit()

    # Migration: add hourly_weights column
    try:
        conn.execute("ALTER TABLE campaigns ADD COLUMN hourly_weights TEXT")
        conn.commit()
        log.info("Added hourly_weights column to campaigns")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add engage_like column
    try:
        conn.execute("ALTER TABLE campaigns ADD COLUMN engage_like INTEGER DEFAULT 0")
        conn.commit()
        log.info("Added engage_like column to campaigns")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add options column (JSON array of paid option keys)
    try:
        conn.execute("ALTER TABLE campaigns ADD COLUMN options TEXT DEFAULT '[]'")
        conn.commit()
        log.info("Added options column to campaigns")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Tracking table for rank monitoring
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            check_date TEXT NOT NULL,
            check_type TEXT NOT NULL,
            keyword TEXT NOT NULL,
            rank_position INTEGER,
            page_number INTEGER DEFAULT 1,
            snapshot TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );
        CREATE INDEX IF NOT EXISTS idx_tracking_campaign_date
            ON tracking(campaign_id, check_date);
    """)
    conn.commit()

    conn.close()
    log.info("Database initialized: %s", DB_PATH)


# --- Campaign CRUD ---

def add_campaign(customer_name, keyword, product_name, product_url="",
                 daily_target=300, dwell_min=30.0, dwell_max=90.0,
                 campaign_type="shopping", hourly_weights=None,
                 engage_like=False, options=None) -> int:
    conn = get_db()
    # Auto-assign default weights based on campaign type if not provided
    if hourly_weights is None:
        weights_dict = DEFAULT_WEIGHTS_BY_TYPE.get(campaign_type, SHOPPING_WEIGHTS)
        weights_json = json.dumps(weights_dict)
    elif isinstance(hourly_weights, dict):
        weights_json = json.dumps(hourly_weights)
    else:
        weights_json = hourly_weights  # already a JSON string
    options_json = json.dumps(options or [])
    cur = conn.execute(
        """INSERT INTO campaigns
           (type, customer_name, keyword, product_name, product_url,
            daily_target, dwell_time_min, dwell_time_max, hourly_weights, engage_like, options)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (campaign_type, customer_name, keyword, product_name, product_url,
         daily_target, dwell_min, dwell_max, weights_json, int(engage_like), options_json),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def list_campaigns(active_only=True) -> list[dict]:
    conn = get_db()
    sql = "SELECT * FROM campaigns"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_campaign(campaign_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def toggle_campaign(campaign_id: int, active: bool):
    conn = get_db()
    conn.execute("UPDATE campaigns SET active = ? WHERE id = ?", (int(active), campaign_id))
    conn.commit()
    conn.close()


def delete_campaign(campaign_id: int):
    conn = get_db()
    conn.execute("DELETE FROM jobs WHERE campaign_id = ? AND status = 'pending'", (campaign_id,))
    conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()


def update_campaign(campaign_id: int, **fields):
    """Update arbitrary campaign fields. Only provided keys are updated."""
    allowed = {
        "type", "customer_name", "keyword", "product_name", "product_url",
        "daily_target", "dwell_time_min", "dwell_time_max", "options",
        "hourly_weights", "engage_like",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    # Serialize list/dict fields to JSON
    for k in ("options", "hourly_weights"):
        if k in updates and not isinstance(updates[k], str):
            updates[k] = json.dumps(updates[k])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [campaign_id]
    conn = get_db()
    conn.execute(f"UPDATE campaigns SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def update_campaign_weights(campaign_id: int, weights: dict | str):
    """Update hourly_weights for a campaign. Accepts dict or JSON string."""
    if isinstance(weights, dict):
        weights = json.dumps(weights)
    conn = get_db()
    conn.execute("UPDATE campaigns SET hourly_weights = ? WHERE id = ?", (weights, campaign_id))
    conn.commit()
    conn.close()


# --- Job scheduling ---

def _distribute_visits(daily_target: int, weights: dict[int, float] | None = None) -> dict[int, int]:
    """Distribute daily visits across 24 hours based on traffic patterns.
    For small targets (<=24), uses weighted random selection of hours.
    For larger targets, uses proportional distribution with ±20% jitter.
    """
    import random
    if weights is None:
        weights = HOURLY_WEIGHTS
    total_weight = sum(weights.values())
    distribution = {h: 0 for h in range(24)}

    if daily_target <= 24:
        # Small target: weighted random pick of hours (natural spread)
        hour_pool = [(h, weights.get(h, 0.5)) for h in range(24)]
        for _ in range(daily_target):
            total_w = sum(w for _, w in hour_pool)
            r = random.uniform(0, total_w)
            cumulative = 0
            for idx, (h, w) in enumerate(hour_pool):
                cumulative += w
                if cumulative >= r:
                    distribution[h] += 1
                    hour_pool.pop(idx)  # avoid same hour twice (until exhausted)
                    break
            if not hour_pool:
                hour_pool = [(h, weights.get(h, 0.5)) for h in range(24)]
    else:
        # Large target: proportional distribution with jitter
        remaining = daily_target
        hours = list(range(24))
        random.shuffle(hours)
        for i, hour in enumerate(hours):
            if i == len(hours) - 1:
                distribution[hour] = remaining
            else:
                weight = weights.get(hour, 0.5)
                base = daily_target * (weight / total_weight)
                count = max(0, int(base * random.uniform(0.8, 1.2)))
                count = min(count, remaining)
                distribution[hour] = count
                remaining -= count

    return distribution


def generate_daily_jobs(target_date: str = None):
    """Generate jobs for all active campaigns for a given date."""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_db()

    # Check if jobs already exist for this date
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM jobs WHERE scheduled_date = ?",
        (target_date,),
    ).fetchone()["cnt"]

    if existing > 0:
        log.info("Jobs already exist for %s (%d jobs), skipping", target_date, existing)
        conn.close()
        return 0

    campaigns = list_campaigns(active_only=True)
    total_jobs = 0

    # Collect all individual jobs first (campaign_id, weights)
    import random
    all_jobs = []  # list of (campaign_id, weights_dict)
    for camp in campaigns:
        camp_weights = None
        raw_weights = camp.get("hourly_weights")
        if raw_weights:
            try:
                parsed = json.loads(raw_weights)
                camp_weights = {int(k): float(v) for k, v in parsed.items()}
            except (json.JSONDecodeError, ValueError):
                log.warning("Invalid hourly_weights for campaign #%d, using default", camp["id"])
        camp_type = camp.get("type", "shopping")
        weights = camp_weights or DEFAULT_WEIGHTS_BY_TYPE.get(camp_type, HOURLY_WEIGHTS)
        for _ in range(camp["daily_target"]):
            all_jobs.append((camp["id"], weights))

    # Shuffle all jobs, then assign each to a weighted-random hour
    # Track how many jobs per hour to avoid overloading single hours
    random.shuffle(all_jobs)
    hour_counts = {h: 0 for h in range(24)}
    max_per_hour = max(2, len(all_jobs) // 8)  # soft cap per hour

    for campaign_id, weights in all_jobs:
        # Build weighted pool, penalizing hours that already have many jobs
        pool = []
        for h in range(24):
            w = weights.get(h, 0.5)
            # Reduce weight for hours already loaded
            if hour_counts[h] >= max_per_hour:
                w *= 0.1
            pool.append((h, w))

        total_w = sum(w for _, w in pool)
        r = random.uniform(0, total_w)
        cumulative = 0
        chosen_hour = 12  # fallback
        for h, w in pool:
            cumulative += w
            if cumulative >= r:
                chosen_hour = h
                break

        conn.execute(
            """INSERT INTO jobs (campaign_id, scheduled_date, scheduled_hour, status)
               VALUES (?, ?, ?, 'pending')""",
            (campaign_id, target_date, chosen_hour),
        )
        hour_counts[chosen_hour] += 1
        total_jobs += 1

    conn.commit()
    conn.close()
    log.info("Generated %d jobs for %s (%d campaigns)", total_jobs, target_date, len(campaigns))
    return total_jobs


# --- Job dispatch (called by master API) ---

def fetch_next_jobs(worker_id: str, batch_size: int = 5) -> list[dict]:
    """Fetch next pending jobs for a worker. Assigns them atomically."""
    now = datetime.now()
    current_hour = now.hour
    today = date.today().isoformat()

    conn = get_db()
    # Get pending jobs for current or past hours today
    rows = conn.execute(
        """SELECT j.id, j.campaign_id, j.scheduled_date, j.scheduled_hour,
                  c.type, c.keyword, c.product_name, c.product_url,
                  c.dwell_time_min, c.dwell_time_max, c.engage_like
           FROM jobs j
           JOIN campaigns c ON j.campaign_id = c.id
           WHERE j.status = 'pending'
             AND j.scheduled_date = ?
             AND j.scheduled_hour <= ?
             AND c.active = 1
           ORDER BY j.scheduled_hour, j.id
           LIMIT ?""",
        (today, current_hour, batch_size),
    ).fetchall()

    jobs = []
    for row in rows:
        conn.execute(
            "UPDATE jobs SET status = 'running', worker_id = ?, started_at = ? WHERE id = ?",
            (worker_id, now.isoformat(), row["id"]),
        )
        jobs.append(dict(row))

    conn.commit()
    conn.close()
    return jobs


def complete_job(job_id: int, success: bool, duration_sec: float = 0, error: str = None):
    """Mark a job as completed or failed."""
    now = datetime.now().isoformat()
    status = "completed" if success else "failed"

    conn = get_db()
    conn.execute(
        """UPDATE jobs SET status = ?, completed_at = ?, success = ?, duration_sec = ?, error = ?
           WHERE id = ?""",
        (status, now, int(success), duration_sec, error, job_id),
    )

    # Update worker stats
    row = conn.execute("SELECT worker_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row and row["worker_id"]:
        if success:
            conn.execute(
                "UPDATE workers SET jobs_completed = jobs_completed + 1 WHERE id = ?",
                (row["worker_id"],),
            )
        else:
            conn.execute(
                "UPDATE workers SET jobs_failed = jobs_failed + 1 WHERE id = ?",
                (row["worker_id"],),
            )

    conn.commit()
    conn.close()


def reset_stale_jobs(timeout_minutes: int = 10):
    """Reset jobs stuck in 'running' for too long (worker crashed)."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()

    conn = get_db()
    updated = conn.execute(
        "UPDATE jobs SET status = 'pending', worker_id = NULL, started_at = NULL "
        "WHERE status = 'running' AND started_at < ?",
        (cutoff,),
    ).rowcount
    conn.commit()
    conn.close()

    if updated > 0:
        log.info("Reset %d stale jobs", updated)
    return updated


# --- Worker management ---

def register_worker(worker_id: str, hostname: str, max_chrome: int = 8):
    conn = get_db()
    conn.execute(
        """INSERT INTO workers (id, hostname, max_chrome, status, last_heartbeat)
           VALUES (?, ?, ?, 'online', ?)
           ON CONFLICT(id) DO UPDATE SET
             hostname = excluded.hostname,
             max_chrome = excluded.max_chrome,
             status = 'online',
             last_heartbeat = excluded.last_heartbeat""",
        (worker_id, hostname, max_chrome, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def heartbeat_worker(worker_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE workers SET last_heartbeat = ?, status = 'online' WHERE id = ?",
        (datetime.now().isoformat(), worker_id),
    )
    conn.commit()
    conn.close()


def cleanup_stale_workers(timeout_minutes: int = 5):
    """Delete workers that haven't sent a heartbeat recently."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()
    conn = get_db()
    deleted = conn.execute(
        "DELETE FROM workers WHERE last_heartbeat < ?",
        (cutoff,),
    ).rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        log.info("Cleaned up %d stale workers", deleted)


def list_workers() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM workers ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Stats ---

def get_daily_stats(target_date: str = None) -> dict:
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_db()
    row = conn.execute(
        """SELECT
             COUNT(*) as total,
             SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
             SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
             SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
             SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
           FROM jobs WHERE scheduled_date = ?""",
        (target_date,),
    ).fetchone()

    stats = dict(row) if row else {}
    stats["date"] = target_date

    # Per-campaign breakdown
    campaigns = conn.execute(
        """SELECT c.id, c.type, c.customer_name, c.keyword, c.daily_target,
             SUM(CASE WHEN j.status = 'completed' AND j.success = 1 THEN 1 ELSE 0 END) as success,
             SUM(CASE WHEN j.status = 'completed' AND j.success = 0 THEN 1 ELSE 0 END) as fail_complete,
             SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) as failed,
             SUM(CASE WHEN j.status = 'pending' THEN 1 ELSE 0 END) as pending,
             COUNT(*) as total
           FROM campaigns c
           LEFT JOIN jobs j ON c.id = j.campaign_id AND j.scheduled_date = ?
           WHERE c.active = 1
           GROUP BY c.id
           ORDER BY c.id""",
        (target_date,),
    ).fetchall()

    stats["campaigns"] = [dict(r) for r in campaigns]
    conn.close()
    return stats


# --- Tracking ---

def save_tracking(campaign_id: int, check_type: str, keyword: str,
                  rank_position: int | None, page_number: int = 1,
                  snapshot_json: str | None = None):
    """Save a rank tracking result to the database."""
    conn = get_db()
    check_date = date.today().isoformat()
    conn.execute(
        """INSERT INTO tracking
           (campaign_id, check_date, check_type, keyword, rank_position, page_number, snapshot)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (campaign_id, check_date, check_type, keyword, rank_position, page_number, snapshot_json),
    )
    conn.commit()
    conn.close()


def get_tracking_history(campaign_id: int, days: int = 30) -> list[dict]:
    """Get tracking history for a campaign over the last N days."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM tracking
           WHERE campaign_id = ?
             AND check_date >= date('now', 'localtime', ?)
           ORDER BY created_at DESC""",
        (campaign_id, f"-{days} days"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_tracking(campaign_id: int) -> dict | None:
    """Get the most recent tracking result for a campaign."""
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM tracking
           WHERE campaign_id = ?
           ORDER BY created_at DESC
           LIMIT 1""",
        (campaign_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
