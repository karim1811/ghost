# GHOST — Data Breach and Leak Search Module
# DeHashed, LeakCheck, HaveIBeenPwned

import os
import json
import hashlib
import httpx
from pathlib import Path
from typing import Optional

# Config
DEHASHED_API_KEY = os.getenv("DEHASHED_API_KEY", "")
DEHASHED_EMAIL = os.getenv("DEHASHED_EMAIL", "")
LEAKCHECK_API_KEY = os.getenv("LEAKCHECK_API_KEY", "")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")


# DeHashed

def dehashed_search(query: str, field: str = "email") -> dict:
    """DeHashed API — search data breaches."""
    result = {
        "source": "DeHashed",
        "query": query,
        "field": field,
        "found": False,
        "entries": [],
        "total": 0,
        "error": None,
    }

    if not DEHASHED_API_KEY:
        result["error"] = "API key required"
        return result

    try:
        url = "https://api.dehashed.com/search"
        auth = (DEHASHED_EMAIL, DEHASHED_API_KEY)
        params = {"query": f'{field}:"{query}"', "size": 100}
        r = httpx.get(url, auth=auth, params=params, timeout=30)

        if r.status_code == 200:
            data = r.json()
            entries = data.get("entries", [])
            result["found"] = len(entries) > 0
            result["entries"] = entries[:20]
            result["total"] = data.get("total", len(entries))
        else:
            result["error"] = f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        result["error"] = str(e)

    return result


# LeakCheck

def leakcheck_search(query: str, field: str = "email") -> dict:
    """LeakCheck API — search data breaches."""
    result = {
        "source": "LeakCheck",
        "query": query,
        "field": field,
        "found": False,
        "entries": [],
        "error": None,
    }

    if not LEAKCHECK_API_KEY:
        result["error"] = "API key required"
        return result

    try:
        url = "https://leakcheck.io/api"
        params = {"key": LEAKCHECK_API_KEY, "type": field, "check": query}
        r = httpx.get(url, params=params, timeout=30)

        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                result["found"] = data.get("found", 0) > 0
                result["entries"] = data.get("result", [])[:20]
                result["total"] = data.get("found", 0)
            else:
                result["error"] = data.get("error", "Unknown")
        else:
            result["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        result["error"] = str(e)

    return result


# HaveIBeenPwned

def hibp_check_email(email: str) -> dict:
    """HaveIBeenPwned — check if email is in data breaches."""
    result = {
        "source": "HaveIBeenPwned",
        "email": email,
        "found": False,
        "breaches": [],
        "total": 0,
        "error": None,
    }

    if not HIBP_API_KEY:
        result["error"] = "API key required (free at haveibeenpwned.com/API/Key)"
        return result

    try:
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        headers = {"hibp-api-key": HIBP_API_KEY, "User-Agent": "GHOST-OSINT"}
        r = httpx.get(url, headers=headers, timeout=15)

        if r.status_code == 200:
            breaches = r.json()
            result["found"] = True
            result["breaches"] = [
                {
                    "name": b.get("Name"),
                    "title": b.get("Title"),
                    "date": b.get("BreachDate"),
                    "data_classes": b.get("DataClasses", []),
                }
                for b in breaches
            ]
            result["total"] = len(breaches)
        elif r.status_code == 404:
            result["found"] = False
        else:
            result["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        result["error"] = str(e)

    return result


def hibp_check_password(password: str) -> dict:
    """HIBP — check if password exposed (k-anonymity, no API key needed)."""
    result = {"source": "HIBP-Password", "found": False, "exposure_count": 0, "error": None}

    try:
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        r = httpx.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=10)
        if r.status_code == 200:
            for line in r.text.splitlines():
                h, count = line.split(":")
                if h.strip() == suffix:
                    result["found"] = True
                    result["exposure_count"] = int(count.strip())
                    break
    except Exception as e:
        result["error"] = str(e)

    return result


# Combined

def full_breach_search(email=None, username=None, password=None) -> dict:
    """Complete breach search across all services."""
    result = {
        "email": email, "username": username,
        "breaches": [], "passwords_exposed": False,
        "sources_checked": [], "total_breaches": 0, "summary": {},
    }

    if email and HIBP_API_KEY:
        h = hibp_check_email(email)
        result["sources_checked"].append("HIBP")
        if h.get("found"):
            result["breaches"].extend(h["breaches"])
            result["total_breaches"] += h["total"]

    if email and DEHASHED_API_KEY:
        d = dehashed_search(email, "email")
        result["sources_checked"].append("DeHashed")
        if d.get("found"):
            result["total_breaches"] += d.get("total", 0)

    if username and DEHASHED_API_KEY:
        d = dehashed_search(username, "username")
        if d.get("found"):
            result["total_breaches"] += d.get("total", 0)

    if email and LEAKCHECK_API_KEY:
        lc = leakcheck_search(email, "email")
        result["sources_checked"].append("LeakCheck")
        if lc.get("found"):
            result["total_breaches"] += lc.get("total", 0)

    if password:
        pw = hibp_check_password(password)
        result["sources_checked"].append("HIBP-Password")
        if pw.get("found"):
            result["passwords_exposed"] = True

    result["summary"] = {
        "total_breaches": result["total_breaches"],
        "email_compromised": result["total_breaches"] > 0,
        "risk_level": "HIGH" if result["total_breaches"] > 5 else "MEDIUM" if result["total_breaches"] > 0 else "LOW",
    }

    return result
