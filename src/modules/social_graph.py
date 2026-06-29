# GHOST — Social Graph & Behavioral Fingerprinting Module
# Analyze connections, writing style, and activity patterns

import re
import json
from datetime import datetime
from .http_utils import get_check, api_get, get_headers


def analyze_github_profile(username: str) -> dict:
    """
    Deep GitHub profile analysis — reveals email, location, activity,
    connected accounts, commit patterns, timezone, etc.
    """
    result = {"platform": "GitHub Deep", "username": username, "data": {}}

    # Get user profile
    api_result = api_get(f"https://api.github.com/users/{username}")
    if not api_result["exists"]:
        result["error"] = "Not found"
        return result

    data = api_result["data"]
    result["data"] = {
        "name": data.get("name"),
        "bio": data.get("bio"),
        "company": data.get("company"),
        "location": data.get("location"),
        "email": data.get("email"),
        "blog": data.get("blog"),
        "twitter": data.get("twitter_username"),
        "hireable": data.get("hireable"),
        "public_repos": data.get("public_repos"),
        "public_gists": data.get("public_gists"),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "avatar_url": data.get("avatar_url"),
        "type": data.get("type"),
    }

    # Get repos (public)
    repos_result = api_get(f"https://api.github.com/users/{username}/repos?per_page=30")
    if repos_result["exists"] and repos_result.get("data"):
        repos = repos_result["data"]
        if isinstance(repos, list):
            languages = {}
            for repo in repos:
                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
            result["data"]["top_languages"] = languages
            result["data"]["repo_count"] = len(repos)

    # Get events (public) for timezone analysis
    events_result = api_get(f"https://api.github.com/users/{username}/events/public?per_page=30")
    if events_result["exists"]:
        events = events_result["data"]
        if isinstance(events, list):
            hours = []
            for event in events:
                created = event.get("created_at", "")
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        hours.append(dt.hour)
                    except:
                        pass
            if hours:
                from collections import Counter
                hour_counts = Counter(hours)
                peak_hour = hour_counts.most_common(1)[0][0]
                result["data"]["peak_activity_hour_utc"] = peak_hour
                result["data"]["likely_timezone"] = guess_timezone(peak_hour)

    # Get email from commits
    events_result2 = api_get(f"https://api.github.com/users/{username}/events/public?per_page=100")
    if events_result2["exists"]:
        events = events_result2["data"]
        emails = set()
        if isinstance(events, list):
            for event in events:
                payload = event.get("payload", {})
                commits = payload.get("commits", [])
                for commit in commits:
                    author = commit.get("author", {})
                    email = author.get("email")
                    if email and "noreply" not in email:
                        emails.add(email)
        if emails:
            result["data"]["emails_from_commits"] = list(emails)

    return result


def guess_timezone(peak_hour_utc: int) -> str:
    """
    Guess timezone based on peak activity hour (UTC).
    People are typically awake 8-23h in their local timezone.
    """
    # If they peak at 0-6 UTC, they are likely Europe/Africa
    # If 7-15 UTC, Europe/West Africa
    # If 15-23 UTC, Americas
    # If 0-8 UTC, Asia
    if 7 <= peak_hour_utc <= 18:
        return "Europe/Africa (UTC+0 to +3)"
    elif 19 <= peak_hour_utc or peak_hour_utc <= 3:
        return "Americas (UTC-5 to -8)"
    elif 4 <= peak_hour_utc <= 12:
        return "Europe/Middle East (UTC+1 to +4)"
    else:
        return "Asia/Pacific"


def analyze_reddit_user(username: str) -> dict:
    """
    Reddit profile deep analysis — karma patterns, active subreddits,
    connected accounts, writing style.
    """
    result = {"platform": "Reddit Deep", "username": username, "data": {}}

    api_result = api_get(f"https://www.reddit.com/user/{username}/about.json")
    if not api_result["exists"] or not api_result.get("data"):
        result["error"] = "Not found"
        return result

    data = api_result["data"].get("data", {})
    result["data"] = {
        "name": data.get("name"),
        "total_karma": data.get("total_karma"),
        "link_karma": data.get("link_karma"),
        "comment_karma": data.get("comment_karma"),
        "created_utc": data.get("created_utc"),
        "has_verified_email": data.get("has_verified_email"),
        "is_mod": data.get("is_mod"),
        "is_employee": data.get("is_employee"),
        "subreddit_subscribers": data.get("subreddit", {}).get("subscribers", 0),
    }

    # Get recent posts
    posts_result = api_get(f"https://www.reddit.com/user/{username}/submitted.json?limit=25")
    if posts_result["exists"] and posts_result.get("data"):
        posts = posts_result["data"].get("data", {}).get("children", [])
        active_subs = {}
        for post in posts:
            sub = post.get("data", {}).get("subreddit")
            if sub:
                active_subs[sub] = active_subs.get(sub, 0) + 1
        result["data"]["active_subreddits"] = active_subs

    # Get comments for language/behavior
    comments_result = api_get(f"https://www.reddit.com/user/{username}/comments.json?limit=25")
    if comments_result["exists"] and comments_result.get("data"):
        comments = comments_result["data"].get("data", {}).get("children", [])
        word_count = 0
        common_words = {}
        for c in comments:
            body = c.get("data", {}).get("body", "")
            word_count += len(body.split())
        result["data"]["avg_comment_length"] = word_count / max(len(comments), 1)

    return result


def analyze_steam_profile(vanity_url: str) -> dict:
    """
    Steam profile analysis — needs API key.
    """
    result = {"platform": "Steam", "steamid": vanity_url, "data": {}}
    result["note"] = "Steam requires API key (free at https://steamcommunity.com/dev/apikey)"
    return result


def cross_platform_identities(username: str, known_accounts: list = None) -> dict:
    """
    Cross-reference identities across platforms.
    Look for same email, same bio, same location, same links.
    """
    result = {"username": username, "identities": []}

    gh = analyze_github_profile(username)
    if gh.get("data"):
        gh_data = gh["data"]
        identity = {}
        if gh_data.get("email"):
            identity["email"] = gh_data["email"]
        if gh_data.get("name"):
            identity["name"] = gh_data["name"]
        if gh_data.get("location"):
            identity["location"] = gh_data["location"]
        if gh_data.get("twitter"):
            identity["twitter"] = gh_data["twitter"]
        if gh_data.get("blog"):
            identity["website"] = gh_data["blog"]
        if gh_data.get("bio"):
            identity["bio"] = gh_data["bio"]
        if identity:
            identity["source"] = "GitHub"
            result["identities"].append(identity)

    rd = analyze_reddit_user(username)
    if rd.get("data"):
        identity = {"source": "Reddit"}
        name = rd["data"].get("name")
        if name and name != username:
            identity["reddit_name"] = name
            # Search other platforms with this name
        result["identities"].append(identity)

    return result


def generate_behavioral_fingerprint(platforms_data: list) -> dict:
    """
    Generate behavioral fingerprint from multiple platform data.
    Used to link anonymous accounts to known identities.
    """
    fingerprint = {
        "username": None,
        "languages": [],
        "interests": [],
        "timezone": None,
        "emails": [],
        "names": [],
        "locations": [],
        "connected_accounts": {},
    }

    for platform in platforms_data:
        data = platform.get("data", {})
        if not data:
            continue

        # Names
        for key in ["name", "display_name"]:
            val = data.get(key)
            if val:
                fingerprint["names"].append({"value": val, "source": platform.get("platform")})

        # Emails
        for key in ["email", "emails_from_commits"]:
            val = data.get(key)
            if val:
                if isinstance(val, list):
                    for v in val:
                        fingerprint["emails"].append({"value": v, "source": platform.get("platform")})
                else:
                    fingerprint["emails"].append({"value": val, "source": platform.get("platform")})

        # Location
        for key in ["location", "currentLocation"]:
            val = data.get(key)
            if val:
                fingerprint["locations"].append({"value": val, "source": platform.get("platform")})

        # Languages
        langs = data.get("top_languages", {})
        if langs:
            fingerprint["languages"].extend(langs.keys())

        # Connected accounts
        for key in ["twitter"]:
            val = data.get(key)
            if val:
                fingerprint["connected_accounts"][key] = val

    # Dedup
    fingerprint["languages"] = list(set(fingerprint["languages"]))

    return fingerprint
