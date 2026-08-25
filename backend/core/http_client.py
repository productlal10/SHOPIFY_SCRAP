#!/usr/bin/env python3
"""
Resilient HTTP Client
=====================
Wrapper over cloudscraper and requests providing user-agent rotation, headers management,
timeout controls, and thread-safe session reuse.
"""

import threading
import requests
try:
    import cloudscraper
except ImportError:
    cloudscraper = None

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_thread_local = threading.local()

def get_http_session(use_cloudscraper: bool = True):
    """Retrieve or create a thread-safe HTTP session."""
    if not hasattr(_thread_local, "session"):
        if use_cloudscraper and cloudscraper:
            s = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
        else:
            s = requests.Session()
        s.headers.update(DEFAULT_HEADERS)
        _thread_local.session = s
    return _thread_local.session

def fetch_url(url: str, timeout: int = 15, headers: dict = None, use_cloudscraper: bool = True) -> requests.Response:
    """Fetch URL with configured session and timeout."""
    session = get_http_session(use_cloudscraper)
    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)
    return session.get(url, timeout=timeout, headers=req_headers)
