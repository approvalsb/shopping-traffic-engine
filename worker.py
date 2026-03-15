"""
Worker process - polls master for jobs and executes Chrome visits.
Run on each VPS/PC that should process traffic.

Usage:
    python worker.py --master http://MASTER_IP:5000 [--id worker-01] [--chrome 8] [--headless]
"""

import os
import sys
import time
import signal
import random
import socket
import logging
import argparse
import threading
from datetime import datetime

import requests

from engine_selenium import NaverShoppingEngine, Campaign
from engine_place import NaverPlaceEngine, PlaceCampaign
from engine_blog import NaverBlogEngine, BlogCampaign

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("worker")


class TrafficWorker:
    """Polls master server for jobs and executes them with Chrome."""

    def __init__(self, master_url: str, worker_id: str,
                 max_chrome: int = 8, headless: bool = True,
                 proxy: str = None, poll_interval: float = 10.0):
        self.master_url = master_url.rstrip("/")
        self.worker_id = worker_id
        self.max_chrome = max_chrome
        self.headless = headless
        self.proxy = proxy
        self.poll_interval = poll_interval
        self.hostname = socket.gethostname()
        self._running = False

    def register(self):
        """Register this worker with master."""
        try:
            resp = requests.post(f"{self.master_url}/api/workers/register", json={
                "worker_id": self.worker_id,
                "hostname": self.hostname,
                "max_chrome": self.max_chrome,
            }, timeout=10)
            resp.raise_for_status()
            log.info("Registered with master: %s (id=%s)", self.master_url, self.worker_id)
        except Exception as e:
            log.error("Failed to register: %s", e)
            raise

    def heartbeat(self):
        """Send periodic heartbeat to master."""
        try:
            requests.post(f"{self.master_url}/api/workers/heartbeat", json={
                "worker_id": self.worker_id,
            }, timeout=5)
        except Exception:
            pass

    def _heartbeat_loop(self):
        """Background heartbeat thread."""
        while self._running:
            self.heartbeat()
            time.sleep(30)

    def fetch_jobs(self, batch_size: int = 1) -> list[dict]:
        """Get next pending jobs from master."""
        try:
            resp = requests.post(f"{self.master_url}/api/jobs/next", json={
                "worker_id": self.worker_id,
                "batch_size": batch_size,
            }, timeout=10)
            resp.raise_for_status()
            return resp.json().get("jobs", [])
        except Exception as e:
            log.warning("Failed to fetch jobs: %s", e)
            return []

    def report_result(self, job_id: int, success: bool,
                      duration_sec: float = 0, error: str = None):
        """Report job result to master."""
        try:
            requests.post(f"{self.master_url}/api/jobs/{job_id}/complete", json={
                "success": success,
                "duration_sec": duration_sec,
                "error": error,
            }, timeout=10)
        except Exception as e:
            log.warning("Failed to report result for job %d: %s", job_id, e)

    def execute_job(self, job: dict) -> bool:
        """Execute a single traffic visit job (shopping or place)."""
        job_type = job.get("type", "shopping")
        start = datetime.now()

        if job_type == "blog":
            engine = NaverBlogEngine(proxy=self.proxy, headless=self.headless)
            campaign = BlogCampaign(
                keyword=job["keyword"],
                blog_title=job["product_name"],
                blog_name=job.get("product_url", ""),
                daily_target=1,
                dwell_time_min=job.get("dwell_time_min", 20.0),
                dwell_time_max=job.get("dwell_time_max", 45.0),
            )
        elif job_type == "place":
            engine = NaverPlaceEngine(proxy=self.proxy, headless=self.headless)
            campaign = PlaceCampaign(
                keyword=job["keyword"],
                place_name=job["product_name"],
                daily_target=1,
                dwell_time_min=job.get("dwell_time_min", 20.0),
                dwell_time_max=job.get("dwell_time_max", 45.0),
            )
        else:
            engine = NaverShoppingEngine(proxy=self.proxy, headless=self.headless)
            campaign = Campaign(
                product_url=job.get("product_url", ""),
                keyword=job["keyword"],
                product_name=job["product_name"],
                daily_target=1,
                dwell_time_min=job.get("dwell_time_min", 30.0),
                dwell_time_max=job.get("dwell_time_max", 90.0),
            )

        try:
            engine.start()
            result = engine.execute_visit(campaign)
            duration = (datetime.now() - start).total_seconds()

            self.report_result(
                job_id=job["id"],
                success=result.success,
                duration_sec=round(duration, 1),
                error=result.error if hasattr(result, 'error') else None,
            )

            if result.success:
                log.info("[Job %d] OK (%.1fs) [%s] %s", job["id"], duration, job_type, job["keyword"])
            else:
                err = result.error if hasattr(result, 'error') else 'unknown'
                log.warning("[Job %d] FAIL [%s] %s: %s", job["id"], job_type, job["keyword"], err)

            return result.success

        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            log.error("[Job %d] ERROR [%s] %s: %s", job["id"], job_type, job["keyword"], e)
            self.report_result(
                job_id=job["id"],
                success=False,
                duration_sec=round(duration, 1),
                error=str(e),
            )
            return False

        finally:
            engine.stop()

    def _setup_signals(self):
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        def _handler(signum, frame):
            signame = signal.Signals(signum).name
            log.info("Received %s, shutting down gracefully...", signame)
            self._running = False

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def run(self):
        """Main loop: poll master → execute jobs → report → repeat."""
        self._running = True
        self._setup_signals()
        self.register()

        # Start heartbeat thread
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()

        log.info("Worker started: %s (max_chrome=%d, headless=%s)",
                 self.worker_id, self.max_chrome, self.headless)

        consecutive_empty = 0

        while self._running:
            try:
                # Fetch one job at a time (sequential execution)
                jobs = self.fetch_jobs(batch_size=1)

                if not jobs:
                    consecutive_empty += 1
                    # Backoff: wait longer when no jobs available
                    wait = min(self.poll_interval * min(consecutive_empty, 6), 60)
                    if consecutive_empty % 6 == 1:
                        log.info("No pending jobs, waiting %.0fs...", wait)
                    time.sleep(wait)
                    continue

                consecutive_empty = 0

                for job in jobs:
                    log.info("=== Job %d: [%s] %s ===",
                             job["id"], job["keyword"], job["product_name"][:30])
                    self.execute_job(job)

                    # Random delay between jobs (human-like spacing)
                    delay = random.uniform(5.0, 20.0)
                    time.sleep(delay)

            except Exception as e:
                log.error("Worker loop error: %s", e)
                time.sleep(30)

        log.info("Worker stopped: %s", self.worker_id)

    def stop(self):
        self._running = False


def main():
    parser = argparse.ArgumentParser(description="Traffic Engine Worker")
    parser.add_argument("--master", "--master-url",
                        default=os.environ.get("MASTER_URL", "http://localhost:5000"),
                        help="Master server URL (default: $MASTER_URL or http://localhost:5000)")
    parser.add_argument("--id", "--worker-id",
                        default=os.environ.get("WORKER_ID"),
                        help="Worker ID (default: $WORKER_ID or auto-generate)")
    parser.add_argument("--chrome", "--max-chrome", type=int,
                        default=int(os.environ.get("MAX_CHROME", "3")),
                        help="Max Chrome instances (default: $MAX_CHROME or 3)")
    parser.add_argument("--headless", action="store_true",
                        default=os.environ.get("HEADLESS", "1") == "1",
                        help="Run Chrome headless (default: true, set HEADLESS=0 to disable)")
    parser.add_argument("--no-headless", action="store_true",
                        help="Disable headless mode (for local debugging)")
    parser.add_argument("--proxy", default=os.environ.get("PROXY"),
                        help="Proxy server (host:port)")
    parser.add_argument("--poll", type=float,
                        default=float(os.environ.get("POLL_INTERVAL", "10.0")),
                        help="Poll interval seconds (default: 10)")
    args = parser.parse_args()

    if args.no_headless:
        args.headless = False

    worker_id = args.id or f"worker-{socket.gethostname()}-{random.randint(1000, 9999)}"

    worker = TrafficWorker(
        master_url=args.master,
        worker_id=worker_id,
        max_chrome=args.chrome,
        headless=args.headless,
        proxy=args.proxy,
        poll_interval=args.poll,
    )

    worker.run()


if __name__ == "__main__":
    main()
