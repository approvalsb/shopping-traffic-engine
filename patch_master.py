#!/usr/bin/env python3
"""Patch master.py to add /api/jobs/supplement endpoint."""

MASTER_PATH = "/opt/traffic-engine/master.py"
MARKER = "# --- Background scheduler ---"

SUPPLEMENT_CODE = '''
@app.route("/api/jobs/supplement", methods=["POST"])
def supplement_jobs():
    """Create supplementary jobs for a campaign to compensate for failures."""
    data = request.json or {}
    campaign_id = data.get("campaign_id")
    count = data.get("count", 0)
    target_date = data.get("date", date.today().isoformat())
    start_hour = data.get("start_hour", datetime.now().hour + 1)

    if not campaign_id or count <= 0:
        return jsonify({"error": "campaign_id and count required"}), 400

    import random as _rand
    conn = db.get_db()
    created = 0

    remaining_hours = list(range(start_hour, 24))
    if not remaining_hours:
        conn.close()
        return jsonify({"created": 0, "reason": "no remaining hours"})

    for _ in range(count):
        hour = _rand.choice(remaining_hours)
        conn.execute(
            """INSERT INTO jobs (campaign_id, scheduled_date, scheduled_hour, status)
               VALUES (?, ?, ?, ?)""",
            (campaign_id, target_date, hour, "pending"),
        )
        created += 1

    conn.commit()
    conn.close()
    log.info("Supplement: created %d jobs for campaign #%d on %s", created, campaign_id, target_date)
    return jsonify({"created": created, "campaign_id": campaign_id, "date": target_date})


'''

def main():
    with open(MASTER_PATH, "r") as f:
        content = f.read()

    if "supplement_jobs" in content:
        print("ALREADY PATCHED")
        return

    if MARKER not in content:
        print("ERROR: marker not found in master.py")
        return

    content = content.replace(MARKER, SUPPLEMENT_CODE + MARKER)

    with open(MASTER_PATH, "w") as f:
        f.write(content)

    print("PATCHED OK")


if __name__ == "__main__":
    main()
