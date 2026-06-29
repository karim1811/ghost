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

                # Determine if profile exists
                exists = False
                e_string = site.get("e_string", "")
                m_string = site.get("m_string", "")

                if e_string and e_string in r.text:
                    exists = True
                elif m_string and m_string not in r.text:
                    exists = True

                results.append({
                    "name": site.get("name"),
                    "category": site.get("cat"),
                    "url": uri,
                    "exists": exists,
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
