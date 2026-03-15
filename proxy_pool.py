"""
Proxy pool management with rotation.
Supports residential proxy services (Bright Data, Oxylabs, etc.)
and manual proxy lists.

Residential proxies are REQUIRED for this service.
Regular datacenter proxies will be detected and blocked by Naver.
"""

import random
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("proxy")


@dataclass
class ProxyConfig:
    """Proxy connection config for Playwright."""
    server: str
    username: Optional[str] = None
    password: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"server": self.server}
        if self.username:
            d["username"] = self.username
        if self.password:
            d["password"] = self.password
        return d


class ProxyPool:
    """Manages proxy rotation across visits."""

    def __init__(self):
        self._proxies: list[ProxyConfig] = []
        self._used_index = 0

    def add(self, server: str, username: str = None, password: str = None):
        self._proxies.append(ProxyConfig(server, username, password))

    def add_list(self, proxies: list[dict]):
        """Add multiple proxies from list of dicts."""
        for p in proxies:
            self.add(p["server"], p.get("username"), p.get("password"))

    @property
    def count(self) -> int:
        return len(self._proxies)

    def get_next(self) -> Optional[dict]:
        """Get next proxy (round-robin)."""
        if not self._proxies:
            return None
        proxy = self._proxies[self._used_index % len(self._proxies)]
        self._used_index += 1
        log.debug("Using proxy %d/%d: %s", self._used_index, len(self._proxies), proxy.server)
        return proxy.to_dict()

    def get_random(self) -> Optional[dict]:
        """Get random proxy."""
        if not self._proxies:
            return None
        proxy = random.choice(self._proxies)
        return proxy.to_dict()

    @classmethod
    def from_file(cls, path: str) -> "ProxyPool":
        """
        Load proxies from a text file.
        Format per line: server or server|username|password
        Example:
            http://1.2.3.4:8080
            http://proxy.example.com:9090|user123|pass456
        """
        pool = cls()
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                if len(parts) == 3:
                    pool.add(parts[0], parts[1], parts[2])
                elif len(parts) == 1:
                    pool.add(parts[0])
                else:
                    log.warning("Invalid proxy format: %s", line)
        log.info("Loaded %d proxies from %s", pool.count, path)
        return pool

    @classmethod
    def from_rotating_service(
        cls,
        provider: str,
        host: str,
        port: int,
        username: str,
        password: str,
        country: str = "kr",
        sessions: int = 10,
    ) -> "ProxyPool":
        """
        Create pool using a rotating residential proxy service.
        Each "session" gets a different sticky IP.

        Supported providers:
        - brightdata: Bright Data (formerly Luminati)
        - oxylabs: Oxylabs
        - smartproxy: Smartproxy
        - generic: Generic rotating proxy
        """
        pool = cls()

        for i in range(sessions):
            if provider == "brightdata":
                # Bright Data session format
                session_user = f"{username}-country-{country}-session-rand{i}"
                pool.add(f"http://{host}:{port}", session_user, password)

            elif provider == "oxylabs":
                # Oxylabs session format
                session_user = f"customer-{username}-cc-{country}-sessid-{i}"
                pool.add(f"http://{host}:{port}", session_user, password)

            elif provider == "smartproxy":
                # Smartproxy session format
                session_user = f"{username}-country-{country}-session-{i}"
                pool.add(f"http://{host}:{port}", session_user, password)

            else:  # generic
                pool.add(f"http://{host}:{port}", username, password)

        log.info("Created %d sessions via %s (%s)", sessions, provider, country)
        return pool


# === Example configurations ===

def example_brightdata():
    """Example: Bright Data residential proxy setup."""
    return ProxyPool.from_rotating_service(
        provider="brightdata",
        host="brd.superproxy.io",
        port=22225,
        username="brd-customer-XXXXX-zone-residential",
        password="YOUR_PASSWORD",
        country="kr",
        sessions=20,
    )


def example_oxylabs():
    """Example: Oxylabs residential proxy setup."""
    return ProxyPool.from_rotating_service(
        provider="oxylabs",
        host="pr.oxylabs.io",
        port=7777,
        username="YOUR_USERNAME",
        password="YOUR_PASSWORD",
        country="kr",
        sessions=20,
    )


def example_manual_list():
    """Example: Manual proxy list."""
    pool = ProxyPool()
    pool.add_list([
        {"server": "http://kr-proxy1.example.com:8080", "username": "user", "password": "pass"},
        {"server": "http://kr-proxy2.example.com:8080", "username": "user", "password": "pass"},
        {"server": "socks5://kr-proxy3.example.com:1080"},
    ])
    return pool
