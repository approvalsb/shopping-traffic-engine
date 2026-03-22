"""
Chrome proxy authentication via extension.
Chrome --proxy-server flag does NOT support user:pass@ format (broken since Chrome 146).
This module creates a lightweight Chrome extension that handles proxy auth.
"""

import os
import json
import shutil
import tempfile
import logging
from urllib.parse import urlparse

log = logging.getLogger("proxy_auth")


def parse_proxy_url(proxy_url: str) -> dict:
    """
    Parse proxy URL into components.
    Supports: http://user:pass@host:port, http://host:port, host:port
    Returns: {"scheme": str, "host": str, "port": int, "username": str|None, "password": str|None}
    """
    if "://" not in proxy_url:
        proxy_url = f"http://{proxy_url}"

    parsed = urlparse(proxy_url)
    return {
        "scheme": parsed.scheme or "http",
        "host": parsed.hostname or "",
        "port": parsed.port or 8080,
        "username": parsed.username,
        "password": parsed.password,
    }


def create_proxy_auth_extension(proxy_url: str) -> str | None:
    """
    Create a Chrome extension for proxy authentication.
    Returns the path to the extension directory, or None if no auth needed.
    The caller is responsible for cleaning up the temp directory.
    """
    parsed = parse_proxy_url(proxy_url)

    if not parsed["username"] or not parsed["password"]:
        return None

    ext_dir = tempfile.mkdtemp(prefix="proxy_auth_")

    manifest = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Auth",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking",
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "22.0.0",
    }

    background_js = """
var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "%s",
            host: "%s",
            port: parseInt(%s)
        },
        bypassList: ["localhost"]
    }
};

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {urls: ["<all_urls>"]},
    ['blocking']
);
""" % (
        parsed["scheme"],
        parsed["host"],
        parsed["port"],
        parsed["username"],
        parsed["password"],
    )

    with open(os.path.join(ext_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    with open(os.path.join(ext_dir, "background.js"), "w") as f:
        f.write(background_js)

    log.debug("Proxy auth extension created at %s for %s:%s",
              ext_dir, parsed["host"], parsed["port"])
    return ext_dir


def get_proxy_server_url(proxy_url: str) -> str:
    """
    Return proxy URL without auth credentials (for --proxy-server flag).
    e.g. http://user:pass@host:port -> http://host:port
    """
    parsed = parse_proxy_url(proxy_url)
    return f"{parsed['scheme']}://{parsed['host']}:{parsed['port']}"


def has_auth(proxy_url: str) -> bool:
    """Check if proxy URL contains authentication credentials."""
    parsed = parse_proxy_url(proxy_url)
    return bool(parsed["username"] and parsed["password"])


def setup_proxy(options, proxy_url: str) -> str | None:
    """
    Configure Chrome options for proxy.
    If proxy has auth, creates extension and loads it.
    If proxy has no auth, uses simple --proxy-server flag.
    Returns extension dir path (for cleanup) or None.
    """
    if not proxy_url:
        return None

    if has_auth(proxy_url):
        ext_dir = create_proxy_auth_extension(proxy_url)
        if ext_dir:
            options.add_argument(f"--load-extension={ext_dir}")
            log.info("Proxy auth extension loaded for %s",
                     get_proxy_server_url(proxy_url))
            return ext_dir
    else:
        options.add_argument(f"--proxy-server={proxy_url}")
        log.info("Proxy (no auth): %s", proxy_url)
        return None


def cleanup_proxy_extension(ext_dir: str | None):
    """Remove temporary proxy auth extension directory."""
    if ext_dir and os.path.isdir(ext_dir):
        try:
            shutil.rmtree(ext_dir)
        except Exception:
            pass
