# GHOST — Module de scraping/github/search spécialisé

from .http_utils import get_check, api_get, polite_request
import re
import json
import sys
import os


def check_github(username: str) -> dict:
    """Check GitHub via API + scraping"""
    result = {"platform": "GitHub", "exists": False, "data": {}, "url": f"https://github.com/{username}"}

    # Try API first
    api_result = api_get(f"https://api.github.com/users/{username}")
    if api_result["exists"]:
        data = api_result["data"]
        result["exists"] = True
        result["data"] = {
            "name": data.get("name"),
            "bio": data.get("bio"),
            "location": data.get("location"),
            "email": data.get("email"),
            "blog": data.get("blog"),
            "twitter": data.get("twitter_username"),
            "public_repos": data.get("public_repos"),
            "followers": data.get("followers"),
            "following": data.get("following"),
            "created_at": data.get("created_at"),
            "avatar_url": data.get("avatar_url"),
            "hireable": data.get("hireable", False),
        }
        return result

    # Fallback: scrape profile page page
    page_result = get_check(f"https://github.com/{username}")
    if "profile" in (page_result.get("title") or "").lower():
        result["exists"] = True

    return result


def check_reddit(username: str) -> dict:
    """Check Reddit via JSON API"""
    result = {"platform": "Reddit", "exists": False, "data": {}, "url": f"https://reddit.com/user/{username}"}

    # Reddit JSON API
    api_result = api_get(f"https://www.reddit.com/user/{username}/about.json")
    if api_result["exists"] and api_result["data"]:
        data = api_result["data"].get("data", {})
        result["exists"] = True
        result["data"] = {
            "name": data.get("name"),
            "karma": data.get("total_karma"),
            "created_utc": data.get("created_utc"),
            "has_verified_email": data.get("has_verified_email"),
            "is_mod": data.get("is_mod"),
            "subscribers": data.get("subreddit", {}).get("subscribers", 0),
        }
        return result

    # Fallback: check page title
    page_result = get_check(f"https://www.reddit.com/user/{username}")
    if page_result.get("exists") and "page not found" not in (page_result.get("title") or "").lower():
        result["exists"] = False  # Can't be sure
        result["status"] = "ambiguous"

    return result


def check_steam(username: str) -> dict:
    """Check Steam community page (XML API if ID64 known, else community)"""
    result = {"platform": "Steam", "exists": False, "data": {}, "url": f"https://steamcommunity.com/id/{username}"}

    page_result = polite_request(result["url"], method="get")
    if page_result.get("exists"):
        # Steam returns 200 for non-existent with error page
        content = page_result.get("content_snippet", "")
        if "The specified profile could not be found" in content:
            result["exists"] = False
        elif "steamid" in content.lower() or "g_rgProfileData" in content:
            result["exists"] = True
            result["data"]["raw"] = content[:500]

    return result


def check_hackernews(username: str) -> dict:
    """Check Hacker News profile profile"""
    result = {"platform": "Hacker News", "exists": False, "data": {}, "url": f"https://news.ycombinator.com/user?id={username}"}

    page_result = polite_request(result["url"], method="get")
    if page_result.get("exists"):
        content = page_result.get("content_snippet", "")
        if "No such user" in content:
            result["exists"] = False
        result["data"]["snippet"] = content[:300]

    return result
