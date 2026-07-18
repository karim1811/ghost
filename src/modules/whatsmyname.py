# GHOST — WhatsMyName Integration
# 700+ websites for username enumeration
# Based on WebBreacher/WhatsMyName (CC BY-SA 4.0)

import json
import os
import time
from pathlib import Path
from .http_utils import get_headers

WMN_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "wmn-data.json"


def load_wmn_data():
    """Load WhatsMyName JSON dataset"""
    if not WMN_DATA_PATH.exists():
        import urllib.request
        url = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
        WMN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "GHOST-OSINT/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(WMN_DATA_PATH, "wb") as f:
            f.write(data)

    with open(WMN_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def check_whatsmyname(username: str, categories: list = None, max_sites: int = None) -> list:
    """
    Check username across WhatsMyName 700+ sites.
    Returns list of dicts: [{category, name, url, exists}]
    """
    import httpx

    data = load_wmn_data()
    sites = data.get("sites", [])

    if max_sites:
        sites = sites[:max_sites]

    results = []
    headers = get_headers()
    headers["Accept"] = "text/html"

    with httpx.Client(
        timeout=10,
        headers=headers,
        follow_redirects=True,
        verify=False,
    ) as client:
        for site in sites:
            if categories and site.get("cat") not in categories:
                continue

            if "cloudflare" in site.get("protection", []):
                continue

            uri = site.get("uri_check", "").replace("{account}", username)
            if not uri:
                continue

            try:
                r = client.get(uri)
                exists, reason = determine_existence(r, site)

                results.append({
                    "name": site.get("name"),
                    "category": site.get("cat"),
                    "url": uri,
                    "exists": exists,
                    "reason": reason,
                    "status_code": r.status_code,
                })

            except Exception as e:
                results.append({
                    "name": site.get("name"),
                    "category": site.get("cat"),
                    "url": uri,
                    "exists": False,
                    "error": str(e),
                })

            time.sleep(0.15)

    return results


def determine_existence(resp, site: dict) -> tuple[bool, str]:
    """
    WhatsMyName canonical existence test (fixes false positives).

    Each WMN site defines:
      e_code / e_string  -> when BOTH match, the profile EXISTS
      m_code / m_string  -> when BOTH match, the profile DOES NOT exist
    We require the status_code to match before trusting the string. A 200
    response that is really a Cloudflare/JS challenge or generic error page
    will NOT contain the e_string -> correctly reported as not found.

    Returns (exists: bool, reason: str).
    """
    e_code = site.get("e_code")
    e_string = (site.get("e_string") or "").strip()
    m_code = site.get("m_code")
    m_string = (site.get("m_string") or "").strip()

    text = resp.text or ""

    # 1) Missing-profile signal (m_code + m_string) wins -> not found.
    if m_string:
        code_ok = (m_code is None) or (resp.status_code == m_code)
        if code_ok and m_string in text:
            return False, f"m_string match (status {resp.status_code})"

    # 2) Existence signal (e_code + e_string): the e_string is the strong,
    #    profile-specific signal. A hard "not found" HTTP code (4xx except 415)
    #    overrides it; but a 415/4xx caused by request headers must not mask a
    #    real profile, so when e_string is present we trust it.
    HARD_NOTFOUND = {404, 403, 410, 400, 401, 429}
    if e_string:
        if resp.status_code in HARD_NOTFOUND:
            return False, f"hard {resp.status_code} + no safe override"
        if e_string in text:
            return True, f"e_string match (status {resp.status_code})"

    # 3) Status-only heuristics (sites without strings, or partial defs).
    if e_code is not None and m_code is not None:
        # Both codes defined: presence needs explicit signal above.
        if resp.status_code == m_code and not e_string:
            return False, f"m_code match (status {resp.status_code})"
        if resp.status_code == e_code and not m_string:
            return True, f"e_code match (status {resp.status_code})"
    elif e_code is not None:
        if resp.status_code == e_code:
            return True, f"e_code match (status {resp.status_code})"
    elif m_code is not None:
        if resp.status_code == m_code:
            return False, f"m_code match (status {resp.status_code})"

    # 4) Hard-block responses => not found (anti-bot / challenge pages).
    lower = text.lower()[:4000]
    block_hits = ("just a moment", "checking your browser", "enable javascript",
                  "cloudflare", "captcha", "are you a human",
                  "access denied", "request blocked", "rate limited",
                  "you are being rate limited")
    if any(b in lower for b in block_hits):
        return False, f"anti-bot/block page (status {resp.status_code})"

    # 5) Fallback: nothing conclusive -> treat as not found (safe side).
    return False, f"no signal (status {resp.status_code})"
