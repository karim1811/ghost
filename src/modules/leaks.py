# GHOST — Module leaks (HaveIBeenPwned, etc.)

from .http_utils import api_get, get_check, polite_request
import hashlib
import base64
import time


def check_hibp_email(email: str) -> dict:
    """
    Check HaveIBeenPwned for email breaches.
    NOTE: Free tier requires API key for v3.
    """
    result = {
        "source": "HaveIBeenPwned",
        "email": email,
        "found": False,
        "breaches": [],
        "error": "API key required (free tier needs auth)",
    }

    # Without API key, we can try the paste account check
    # But HIBP requires API key for all v3 endpoints
    # Alternative: check via DeHashed (needs key) or manual search

    return result


def check_hunter_io(email: str) -> dict:
    """
    Check Hunter.io for email verification.
    Free tier: 25 searches/month, needs API key.
    """
    result = {
        "source": "Hunter.io",
        "email": email,
        "score": None,
        "found": False,
        "error": "API key required",
    }
    return result


def check_epieos(email: str) -> dict:
    """
    Check Epieos (free, no API key).
    https://epieos.com returns Google account info, Skype, etc.
    """
    result = {
        "source": "Epieos",
        "email": email,
        "found": False,
        "data": {},
    }

    try:
        from .http_utils import get_headers
        import httpx

        headers = get_headers()
        headers["Accept"] = "application/html"
        url = f"https://epieos.com/{email}"

        with httpx.Client(timeout=10, headers=headers, follow_redirects=True, verify=False) as client:
            r = client.get(url)
            if r.status_code == 200:
                content = r.text[:3000]
                result["found"] = True
                result["raw"] = content

                # Extract key info
                import re
                # Look for Google info
                google_match = re.search(r"Google.*?https://lh3\.googleusercontent\.com/\S+", content)
                if google_match:
                    result["data"]["google"] = "Google account found"

    except Exception as e:
        result["error"] = str(e)

    return result


def check_gravatar(email: str) -> dict:
    """
    Check Gravatar by MD5-hashing the email.
    Returns profile JSON if exists.
    """
    result = {
        "source": "Gravatar",
        "email": email,
        "found": False,
        "profile_url": None,
        "avatar": None,
    }

    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
    api_url = f"https://en.gravatar.com/{email_hash}.json"

    try:
        import httpx
        with httpx.Client(timeout=8, verify=False) as client:
            r = client.get(api_url)
            if r.status_code == 200:
                data = r.json()
                entry = data.get("entry", [{}])[0]
                result["found"] = True
                result["data"] = {
                    "display_name": entry.get("displayName"),
                    "about_me": entry.get("aboutMe"),
                    "location": entry.get("currentLocation"),
                    "urls": entry.get("urls", []),
                    "photos": entry.get("photos", []),
                }
                result["avatar"] = f"https://www.gravatar.com/avatar/{email_hash}"
                result["profile_url"] = f"https://en.gravatar.com/{email_hash}"
    except Exception as e:
        result["error"] = str(e)

    return result


def check_haveibeenpwned_domain(email: str) -> dict:
    """Check via HIBP domain search (if email domain is known)"""
    domain = email.split("@")[-1] if "@" in email else None
    if not domain:
        return {"error": "Invalid email"}

    # Pastebin-paste style check
    return {"domain": domain, "note": "Full HIBP requires API key"}


def check_intelx(email: str = None, username: str = None) -> dict:
    """
    Check IntelX (free tier available, needs API key).
    """
    return {"source": "IntelX", "error": "API key required"}


def check_keybase(username: str) -> dict:
    """
    Check Keybase — often reveals identities, crypto wallets, etc.
    """
    result = {
        "source": "Keybase",
        "username": username,
        "found": False,
        "data": {},
    }

    try:
        import httpx
        with httpx.Client(timeout=8, verify=False) as client:
            r = client.get(f"https://keybase.io/_/api/1.0/user/lookup.json?usernames={username}")
            if r.status_code == 200:
                data = r.json()
                if data.get("status", {}).get("code") == 0:
                    them = data.get("them", [])
                    if them:
                        result["found"] = True
                        profile = them[0]
                        result["data"] = {
                            "id": profile.get("id"),
                            "basics": profile.get("basics", {}),
                            "profile": profile.get("profile", {}),
                            "pictures": profile.get("pictures", {}),
                            "cryptocurrency_addresses": list(profile.get("cryptocurrency_addresses", {}).keys()),
                            "proofs_summary": list(profile.get("proofs_summary", {}).get("proof_types", [])),
                        }
    except Exception as e:
        result["error"] = str(e)

    return result


def check_psbdmp(email: str = None, username: str = None) -> dict:
    """
    Check Pastebin dumps via psbdmp.ws
    """
    query = email or username
    result = {"source": "Pasteddumps", "query": query, "found": False, "data": []}

    try:
        import httpx
        headers = {"User-Agent": "Mozilla/5.0"}
        with httpx.Client(timeout=10, headers=headers, verify=False) as client:
            r = client.get(f"https://psbdmp.ws/api/search/{query}")
            if r.status_code == 200:
                data = r.json()
                if data:
                    result["found"] = True
                    result["data"] = data[:5]
    except Exception as e:
        result["error"] = str(e)

    return result