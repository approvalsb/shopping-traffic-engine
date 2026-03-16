"""
CLI management tool for the traffic engine.

Usage:
    python manage.py campaign add --customer "고객A" --keyword "여성 원피스" --product "플라워 원피스"
    python manage.py campaign list
    python manage.py campaign delete 3
    python manage.py stats
    python manage.py jobs generate
    python manage.py workers
"""

import sys
import argparse
import json

import database as db

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def cmd_campaign_add(args):
    db.init_db()
    cid = db.add_campaign(
        customer_name=args.customer,
        keyword=args.keyword,
        product_name=args.product,
        product_url=args.url or "",
        daily_target=args.target,
        dwell_min=args.dwell_min,
        dwell_max=args.dwell_max,
        campaign_type=args.type,
        engage_like=args.engage_like,
    )
    like_tag = " [공감ON]" if args.engage_like else ""
    print(f"Campaign #{cid} added: [{args.type}] {args.customer} [{args.keyword}] target={args.target}/day{like_tag}")


def cmd_campaign_list(args):
    db.init_db()
    campaigns = db.list_campaigns(active_only=not args.all)
    if not campaigns:
        print("No campaigns found.")
        return

    print(f"{'ID':>4}  {'Type':<9} {'Active':>6}  {'Customer':<15} {'Keyword':<20} {'Product':<20} {'Target':>6}")
    print("-" * 90)
    for c in campaigns:
        active = "ON" if c["active"] else "OFF"
        ctype = c.get("type", "shopping")
        print(f"{c['id']:>4}  {ctype:<9} {active:>6}  {c['customer_name']:<15} "
              f"{c['keyword']:<20} {c['product_name']:<20} {c['daily_target']:>6}")
    print(f"\nTotal: {len(campaigns)} campaigns")


def cmd_campaign_delete(args):
    db.init_db()
    camp = db.get_campaign(args.id)
    if not camp:
        print(f"Campaign #{args.id} not found.")
        return
    db.delete_campaign(args.id)
    print(f"Campaign #{args.id} deleted: {camp['customer_name']} [{camp['keyword']}]")


def cmd_campaign_toggle(args):
    db.init_db()
    camp = db.get_campaign(args.id)
    if not camp:
        print(f"Campaign #{args.id} not found.")
        return
    new_state = not bool(camp["active"])
    db.toggle_campaign(args.id, new_state)
    state = "ON" if new_state else "OFF"
    print(f"Campaign #{args.id} [{camp['keyword']}] -> {state}")


def cmd_campaign_schedule(args):
    """View or edit a campaign's hourly schedule weights."""
    db.init_db()
    camp = db.get_campaign(args.id)
    if not camp:
        print(f"Campaign #{args.id} not found.")
        return

    # Set preset
    if args.preset:
        presets = {
            "shopping": db.SHOPPING_WEIGHTS,
            "blog": db.BLOG_WEIGHTS,
            "place": db.PLACE_WEIGHTS,
        }
        if args.preset not in presets:
            print(f"Unknown preset '{args.preset}'. Choose from: {', '.join(presets.keys())}")
            return
        db.update_campaign_weights(args.id, presets[args.preset])
        print(f"Campaign #{args.id} schedule set to '{args.preset}' preset.")
        camp = db.get_campaign(args.id)

    # Set custom JSON
    elif args.json:
        try:
            weights = json.loads(args.json)
            weights = {int(k): float(v) for k, v in weights.items()}
            if len(weights) != 24:
                print(f"Warning: expected 24 hours, got {len(weights)}. Missing hours will use 0.5.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Invalid JSON: {e}")
            return
        db.update_campaign_weights(args.id, weights)
        print(f"Campaign #{args.id} schedule updated with custom weights.")
        camp = db.get_campaign(args.id)

    # Display current schedule
    print(f"\n=== Campaign #{camp['id']} Schedule ===")
    print(f"  Customer: {camp['customer_name']}")
    print(f"  Keyword:  {camp['keyword']}")
    print(f"  Type:     {camp.get('type', 'shopping')}")
    print()

    raw = camp.get("hourly_weights")
    if raw:
        try:
            weights = json.loads(raw)
            weights = {int(k): float(v) for k, v in weights.items()}
        except (json.JSONDecodeError, ValueError):
            print("  (invalid weights in DB, showing default)")
            weights = db.HOURLY_WEIGHTS
    else:
        weights = db.HOURLY_WEIGHTS
        print("  (using global default weights)")

    # Bar chart display
    max_w = max(weights.values()) if weights else 1
    print(f"  {'Hour':>4}  {'Weight':>6}  Bar")
    print(f"  {'----':>4}  {'------':>6}  ---")
    for h in range(24):
        w = weights.get(h, 0)
        bar_len = int(w / max_w * 30) if max_w > 0 else 0
        bar = "█" * bar_len
        print(f"  {h:>4}  {w:>6.2f}  {bar}")


def cmd_campaign_import(args):
    """Import campaigns from JSON file."""
    db.init_db()
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    campaigns = data if isinstance(data, list) else [data]
    count = 0
    for c in campaigns:
        cid = db.add_campaign(
            customer_name=c.get("customer_name", c.get("customer", "unknown")),
            keyword=c["keyword"],
            product_name=c["product_name"],
            product_url=c.get("product_url", ""),
            daily_target=c.get("daily_target", 300),
            dwell_min=c.get("dwell_time_min", 30.0),
            dwell_max=c.get("dwell_time_max", 90.0),
            campaign_type=c.get("type", "shopping"),
        )
        print(f"  #{cid}: {c['keyword']}")
        count += 1
    print(f"\nImported {count} campaigns.")


def cmd_stats(args):
    db.init_db()
    stats = db.get_daily_stats(args.date)
    total = stats.get("total", 0)
    completed = stats.get("completed", 0)
    failed = stats.get("failed", 0)
    pending = stats.get("pending", 0)
    running = stats.get("running", 0)
    pct = (completed / total * 100) if total > 0 else 0

    print(f"\n=== {stats['date']} Traffic Stats ===")
    print(f"  Total:     {total}")
    print(f"  Completed: {completed} ({pct:.0f}%)")
    print(f"  Failed:    {failed}")
    print(f"  Running:   {running}")
    print(f"  Pending:   {pending}")

    campaigns = stats.get("campaigns", [])
    if campaigns:
        print(f"\n{'ID':>4}  {'Type':<9} {'Customer':<15} {'Keyword':<20} {'Target':>6} {'Done':>6} {'Fail':>6} {'Wait':>6}")
        print("-" * 90)
        for c in campaigns:
            ctype = c.get("type", "shopping")
            print(f"{c['id']:>4}  {ctype:<9} {c['customer_name']:<15} {c['keyword']:<20} "
                  f"{c['daily_target']:>6} {c.get('success', 0):>6} "
                  f"{c.get('failed', 0):>6} {c.get('pending', 0):>6}")


def cmd_jobs_generate(args):
    db.init_db()
    count = db.generate_daily_jobs(args.date)
    print(f"Generated {count} jobs for {args.date or 'today'}")


def cmd_jobs_reset(args):
    db.init_db()
    count = db.reset_stale_jobs(timeout_minutes=args.timeout)
    print(f"Reset {count} stale jobs (timeout={args.timeout}min)")


def cmd_workers(args):
    db.init_db()
    workers = db.list_workers()
    if not workers:
        print("No workers registered.")
        return

    print(f"{'ID':<25} {'Host':<15} {'Status':<8} {'Done':>6} {'Fail':>6} {'Last Seen':<20}")
    print("-" * 90)
    for w in workers:
        print(f"{w['id']:<25} {w['hostname']:<15} {w['status']:<8} "
              f"{w['jobs_completed']:>6} {w['jobs_failed']:>6} {w['last_heartbeat'] or '-':<20}")


def main():
    parser = argparse.ArgumentParser(description="Traffic Engine Management CLI")
    sub = parser.add_subparsers(dest="command")

    # --- campaign ---
    camp_parser = sub.add_parser("campaign", help="Manage campaigns")
    camp_sub = camp_parser.add_subparsers(dest="action")

    # campaign add
    add_p = camp_sub.add_parser("add", help="Add a campaign")
    add_p.add_argument("--type", default="shopping", choices=["shopping", "place", "blog"], help="Campaign type")
    add_p.add_argument("--customer", required=True, help="Customer name")
    add_p.add_argument("--keyword", required=True, help="Search keyword")
    add_p.add_argument("--product", required=True, help="Product/Place name to find")
    add_p.add_argument("--url", default="", help="Product URL")
    add_p.add_argument("--target", type=int, default=300, help="Daily target (default: 300)")
    add_p.add_argument("--dwell-min", type=float, default=30.0, help="Min dwell time sec")
    add_p.add_argument("--dwell-max", type=float, default=90.0, help="Max dwell time sec")
    add_p.add_argument("--engage-like", action="store_true", help="Enable 공감 (blog only, requires accounts)")
    add_p.set_defaults(func=cmd_campaign_add)

    # campaign list
    list_p = camp_sub.add_parser("list", help="List campaigns")
    list_p.add_argument("--all", action="store_true", help="Include inactive")
    list_p.set_defaults(func=cmd_campaign_list)

    # campaign delete
    del_p = camp_sub.add_parser("delete", help="Delete a campaign")
    del_p.add_argument("id", type=int, help="Campaign ID")
    del_p.set_defaults(func=cmd_campaign_delete)

    # campaign toggle
    tog_p = camp_sub.add_parser("toggle", help="Toggle campaign on/off")
    tog_p.add_argument("id", type=int, help="Campaign ID")
    tog_p.set_defaults(func=cmd_campaign_toggle)

    # campaign schedule
    sched_p = camp_sub.add_parser("schedule", help="View/edit campaign hourly weights")
    sched_p.add_argument("id", type=int, help="Campaign ID")
    sched_p.add_argument("--preset", choices=["shopping", "blog", "place"], help="Apply a preset schedule")
    sched_p.add_argument("--json", help="Custom weights as JSON string")
    sched_p.set_defaults(func=cmd_campaign_schedule)

    # campaign import
    imp_p = camp_sub.add_parser("import", help="Import campaigns from JSON")
    imp_p.add_argument("file", help="JSON file path")
    imp_p.set_defaults(func=cmd_campaign_import)

    # --- stats ---
    stats_p = sub.add_parser("stats", help="Show daily stats")
    stats_p.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")
    stats_p.set_defaults(func=cmd_stats)

    # --- jobs ---
    jobs_p = sub.add_parser("jobs", help="Job management")
    jobs_sub = jobs_p.add_subparsers(dest="action")

    gen_p = jobs_sub.add_parser("generate", help="Generate daily jobs")
    gen_p.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")
    gen_p.set_defaults(func=cmd_jobs_generate)

    reset_p = jobs_sub.add_parser("reset", help="Reset stale running jobs")
    reset_p.add_argument("--timeout", type=int, default=10, help="Timeout minutes")
    reset_p.set_defaults(func=cmd_jobs_reset)

    # --- workers ---
    workers_p = sub.add_parser("workers", help="Show workers")
    workers_p.set_defaults(func=cmd_workers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
