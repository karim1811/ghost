# GHOST — HTTP utils avec rotation User-Agent + gestion rate-limit

import httpx
from fake_useragent import UserAgent
import time
import random

ua = UserAgent()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def get_headers():
    """Return fresh headers with random UA"""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


# ── Known error/fallback pages that return 200 but don't exist ──
NOT_FOUND_PATTERNS = [
    "page not found", "404", "sorry, that page",
    "could not be found", "this page doesn",
    "doesn't exist", "does not exist", "no such",
    "user not found", "not found", "profile unavailable",
    "this account doesn", "this user doesn",
    "the page you are looking for",
    "couldn't find", "could not find",
    "content unavailable", "unavailable",
    "something went wrong", "error-page",
    "404 error", "we can't find",
    "profile not found", "account not found",
]

EXISTS_PATTERNS = [
    "profile", "channel", "timeline",
]


def head_check(url: str, timeout: int = 8) -> dict:
    """
    Fast HEAD request to check if profile exists.
    Returns dict with: url, exists (bool), status_code, redirect, error
    """
    result = {
        "url": url,
        "exists": False,
        "status_code": None,
        "final_url": url,
        "error": None,
        "method": "HEAD",
    }

    try:
        with httpx.Client(
            timeout=timeout,
            headers=get_headers(),
            follow_redirects=True,
            verify=False,
        ) as client:
            r = client.head(url)
            result["status_code"] = r.status_code
            result["final_url"] = str(r.url)

            if r.status_code == 404:
                result["exists"] = False
            elif r.status_code >= 400:
                result["error"] = f"HTTP {r.status_code}"
            else:
                result["exists"] = None  # Unknown — needs GET verification

    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def get_check(url: str, timeout: int = 10) -> dict:
    """
    GET request for deeper analysis.
    Returns dict with: url, exists, status_code, content_snippet, error
    """
    result = {
        "url": url,
        "exists": None,
        "status_code": None,
        "content_snippet": "",
        "title": "",
        "body_length": 0,
        "error": None,
    }

    try:
        with httpx.Client(
            timeout=timeout,
            headers=get_headers(),
            follow_redirects=True,
            verify=False,
        ) as client:
            r = client.get(url)
            result["status_code"] = r.status_code
            result["body_length"] = len(r.text)

            # Extract title
            import re
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", r.text, re.I)
            if title_match:
                result["title"] = title_match.group(1).strip()
            else:
                result["title"] = ""

            content_lower = (result["title"] + " " + r.text[:3000]).lower()

            # Detect false positives (200 but profile doesn't exist)
            if r.status_code < 400:
                not_found_hit = any(p in content_lower for p in NOT_FOUND_PATTERNS)
                if not_found_hit:
                    result["exists"] = False
                else:
                    result["exists"] = True
            else:
                result["exists"] = False

            result["content_snippet"] = r.text[:2000]
    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def api_get(url: str, timeout: int = 8) -> dict:
    """GET for JSON APIs"""
    result = {"url": url, "exists": False, "data": None, "error": None, "status_code": None}
    try:
        headers = get_headers()
        headers["Accept"] = "application/json"
        with httpx.Client(timeout=timeout, headers=headers, verify=False) as client:
            r = client.get(url)
            result["status_code"] = r.status_code
            if r.status_code == 200:
                result["exists"] = True
                result["data"] = r.json()
    except Exception as e:
        result["error"] = str(e)
    return result


def polite_request(url: str, method: str = "head", delay: float = 0.3) -> dict:
    """Respectful request with jitter"""
    time.sleep(delay + random.uniform(0, 0.2))
    if method == "get":
        return get_check(url)
    elif method == "api":
        return api_get(url)
    return head_check(url)
