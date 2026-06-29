# GHOST — Deep Extract Module
# Extrait les informations PERSONNELLES depuis les profils trouves
# Objectif: montrer que l'anonymat n'existe pas

import re
import json
import httpx
from pathlib import Path
from typing import Optional
from datetime import datetime

# ── Extraction depuis les profils sociaux ────────────────

def extract_twitter_info(username: str) -> dict:
    """Extrait infos depuis Twitter/X (via nitter ou scraping)"""
    result = {"platform": "Twitter/X", "username": username, "url": f"https://x.com/{username}"}
    
    # Essayer nitter (instances publiques)
    nitter_instances = [
        "nitter.net",
        "nitter.privacydev.net",
        "nitter.poast.org",
    ]
    
    for instance in nitter_instances:
        try:
            url = f"https://{instance}/{username}"
            r = httpx.get(url, timeout=10, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                text = r.text
                
                # Bio
                bio_match = re.search(r'class="profile-bio"[^>]*>([^<]+)', text)
                if bio_match:
                    result["bio"] = bio_match.group(1).strip()
                
                # Nom display
                name_match = re.search(r'class="profile-card-fullname"[^>]*>([^<]+)', text)
                if name_match:
                    result["display_name"] = name_match.group(1).strip()
                
                # Location
                loc_match = re.search(r'class="profile-location"[^>]*>([^<]+)', text)
                if loc_match:
                    result["location"] = loc_match.group(1).strip()
                
                # Date inscription
                join_match = re.search(r'class="profile-joindate"[^>]*>[^<]*<span[^>]*title="([^"]+)"', text)
                if join_match:
                    result["joined"] = join_match.group(1).strip()
                
                # Following/followers
                stats = re.findall(r'class="profile-stat-num"[^>]*>([^<]+)<', text)
                if len(stats) >= 2:
                    result["following"] = stats[0].strip()
                    result["followers"] = stats[1].strip()
                
                # Site web
                url_match = re.search(r'class="profile-url"[^>]*>([^<]+)', text)
                if url_match:
                    result["website"] = url_match.group(1).strip()
                
                result["source"] = instance
                break
                
        except Exception:
            continue
    
    return result


def extract_instagram_info(username: str) -> dict:
    """Extrait infos depuis Instagram (page publique)"""
    result = {"platform": "Instagram", "username": username, "url": f"https://instagram.com/{username}"}
    
    try:
        url = f"https://www.instagram.com/{username}/"
        r = httpx.get(url, timeout=10, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"})
        
        if r.status_code == 200:
            text = r.text
            
            # Bio (dans le JSON embarqué)
            bio_match = re.search(r'"biography":"([^"]+)"', text)
            if bio_match:
                result["bio"] = bio_match.group(1).encode().decode("unicode_escape")
            
            # Nom complet
            name_match = re.search(r'"full_name":"([^"]+)"', text)
            if name_match:
                result["full_name"] = name_match.group(1).encode().decode("unicode_escape")
            
            # Vérifié
            verified = re.search(r'"is_verified":(\w+)', text)
            if verified:
                result["verified"] = verified.group(1) == "true"
            
            # Followers
            followers_match = re.search(r'"edge_followed_by":\{[^}]*"count":(\d+)', text)
            if followers_match:
                result["followers"] = int(followers_match.group(1))
            
            # Following
            following_match = re.search(r'"edge_follow":\{[^}]*"count":(\d+)', text)
            if following_match:
                result["following"] = int(following_match.group(1))
            
            # Posts count
            posts_match = re.search(r'"edge_owner_to_timeline_media":\{[^}]*"count":(\d+)', text)
            if posts_match:
                result["posts"] = int(posts_match.group(1))
            
            # Email dans la bio
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', result.get("bio", ""))
            if email_match:
                result["email_in_bio"] = email_match.group(0)
            
            # Liens dans la bio
            url_match = re.search(r'(https?://[^\s]+)', result.get("bio", ""))
            if url_match:
                result["link_in_bio"] = url_match.group(1)
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def extract_github_info(username: str) -> dict:
    """Extrait infos depuis GitHub (API + page)"""
    result = {"platform": "GitHub", "username": username, "url": f"https://github.com/{username}"}
    
    try:
        # API GitHub
        r = httpx.get(f"https://api.github.com/users/{username}", timeout=10,
                     headers={"User-Agent": "GHOST-OSINT"})
        
        if r.status_code == 200:
            data = r.json()
            result["name"] = data.get("name")
            result["bio"] = data.get("bio")
            result["location"] = data.get("location")
            result["company"] = data.get("company")
            result["blog"] = data.get("blog")
            result["email"] = data.get("email")
            result["twitter"] = data.get("twitter_username")
            result["public_repos"] = data.get("public_repos")
            result["followers"] = data.get("followers")
            result["following"] = data.get("following")
            result["created_at"] = data.get("created_at")
            result["avatar_url"] = data.get("avatar_url")
            
            # Emails dans les commits publics
            events_r = httpx.get(f"https://api.github.com/users/{username}/events/public", timeout=10,
                               headers={"User-Agent": "GHOST-OSINT"})
            if events_r.status_code == 200:
                emails = set()
                for event in events_r.json():
                    commits = event.get("payload", {}).get("commits", [])
                    for commit in commits:
                        email = commit.get("author", {}).get("email")
                        if email and "noreply" not in email:
                            emails.add(email)
                if emails:
                    result["emails_from_commits"] = list(emails)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def extract_reddit_info(username: str) -> dict:
    """Extrait infos depuis Reddit (API JSON)"""
    result = {"platform": "Reddit", "username": username, "url": f"https://reddit.com/user/{username}"}
    
    try:
        url = f"https://www.reddit.com/user/{username}/about.json"
        r = httpx.get(url, timeout=10,
                     headers={"User-Agent": "GHOST-OSINT/0.1"})
        
        if r.status_code == 200:
            data = r.json().get("data", {})
            result["display_name"] = data.get("subreddit", {}).get("title")
            result["karma"] = data.get("total_karma")
            result["comment_karma"] = data.get("comment_karma")
            result["link_karma"] = data.get("link_karma")
            result["created_utc"] = data.get("created_utc")
            result["verified_email"] = data.get("has_verified_email")
            result["avatar"] = data.get("icon_img")
            
            # Subreddits actifs (via commentaires récents)
            comments_r = httpx.get(f"https://www.reddit.com/user/{username}/comments.json?limit=100", timeout=10,
                                 headers={"User-Agent": "GHOST-OSINT/0.1"})
            if comments_r.status_code == 200:
                subreddits = {}
                for comment in comments_r.json().get("data", {}).get("children", []):
                    sub = comment.get("data", {}).get("subreddit")
                    if sub:
                        subreddits[sub] = subreddits.get(sub, 0) + 1
                result["top_subreddits"] = dict(sorted(subreddits.items(), key=lambda x: -x[1])[:10])
                
                # Extraire les opinions/keywords des commentaires
                all_text = " ".join([c.get("data", {}).get("body", "") for c in comments_r.json().get("data", {}).get("children", [])])
                # Topics fréquents
                topics = re.findall(r'\b(politique|macron|pen|ukraine|trump|poutine|israël|palestine|gauche|droite|écologie|vaccin|covid)\b', all_text.lower())
                if topics:
                    result["topics_mentioned"] = list(set(topics))
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


def extract_tiktok_info(username: str) -> dict:
    """Extrait infos depuis TikTok"""
    result = {"platform": "TikTok", "username": username, "url": f"https://tiktok.com/@{username}"}
    
    try:
        url = f"https://www.tiktok.com/@{username}"
        r = httpx.get(url, timeout=10,
                     headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"})
        
        if r.status_code == 200:
            text = r.text
            
            # Nom
            name_match = re.search(r'"nickName":"([^"]+)"', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            # Bio
            bio_match = re.search(r'"signature":"([^"]+)"', text)
            if bio_match:
                result["bio"] = bio_match.group(1).encode().decode("unicode_escape")
            
            # Followers
            followers_match = re.search(r'"followerCount":(\d+)', text)
            if followers_match:
                result["followers"] = int(followers_match.group(1))
            
            # Following
            following_match = re.search(r'"followingCount":(\d+)', text)
            if following_match:
                result["following"] = int(following_match.group(1))
            
            # Likes
            likes_match = re.search(r'"heartCount":(\d+)', text)
            if likes_match:
                result["likes"] = int(likes_match.group(1))
            
            # Vérifié
            verified = re.search(r'"verified":(\w+)', text)
            if verified:
                result["verified"] = verified.group(1) == "true"
            
            # Email dans bio
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', result.get("bio", ""))
            if email_match:
                result["email_in_bio"] = email_match.group(0)
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def extract_linkedin_info(username: str) -> dict:
    """Extrait infos depuis LinkedIn (limité sans compte)"""
    result = {"platform": "LinkedIn", "username": username, "url": f"https://linkedin.com/in/{username}"}
    
    try:
        url = f"https://www.linkedin.com/in/{username}/"
        r = httpx.get(url, timeout=10,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        
        if r.status_code == 200:
            text = r.text
            
            # Nom
            name_match = re.search(r'"firstName":"([^"]+)","lastName":"([^"]+)"', text)
            if name_match:
                result["first_name"] = name_match.group(1)
                result["last_name"] = name_match.group(2)
                result["full_name"] = f"{name_match.group(1)} {name_match.group(2)}"
            
            # Titre/Poste
            title_match = re.search(r'"headline":"([^"]+)"', text)
            if title_match:
                result["headline"] = title_match.group(1).encode().decode("unicode_escape")
            
            # Location
            loc_match = re.search(r'"locationName":"([^"]+)"', text)
            if loc_match:
                result["location"] = loc_match.group(1).encode().decode("unicode_escape")
            
            # Company
            company_match = re.search(r'"companyName":"([^"]+)"', text)
            if company_match:
                result["company"] = company_match.group(1).encode().decode("unicode_escape")
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def extract_steam_info(username: str) -> dict:
    """Extrait infos depuis Steam (via SteamID ou vanity URL)"""
    result = {"platform": "Steam", "username": username}
    
    try:
        # Chercher via steamcommunity
        url = f"https://steamcommunity.com/id/{username}/?xml=1"
        r = httpx.get(url, timeout=10,
                     headers={"User-Agent": "Mozilla/5.0"})
        
        if r.status_code == 200 and "<?xml" in r.text:
            text = r.text
            
            # Steam ID
            id_match = re.search(r'<steamID64>(\d+)</steamID64>', text)
            if id_match:
                result["steam_id"] = id_match.group(1)
            
            # Nom
            name_match = re.search(r'<steamID><!\[CDATA\[(.+)\]\]></steamID>', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            # Bio
            bio_match = re.search(r'<summary><!\[CDATA\[(.+)\]\]></summary>', text)
            if bio_match:
                result["bio"] = bio_match.group(1)
            
            # Location
            loc_match = re.search(r'<location><!\[CDATA\[(.+)\]\]></location>', text)
            if loc_match:
                result["location"] = loc_match.group(1)
            
            # Jeux favoris (via page de profil)
            games_url = f"https://steamcommunity.com/id/{username}/games/?tab=all"
            games_r = httpx.get(games_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if games_r.status_code == 200:
                games = re.findall(r'"name":"([^"]+)","hours_forever":"([^"]+)"', games_r.text)
                if games:
                    result["top_games"] = [{"name": g[0], "hours": g[1]} for g in games[:5]]
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ── Cross-platform identity correlation ──────────────────

def correlate_identities(results: list) -> dict:
    """Croise les donnees de toutes les plateformes pour identifier la personne"""
    identity = {
        "names": set(),
        "emails": set(),
        "phones": set(),
        "locations": set(),
        "companies": set(),
        "schools": set(),
        "interests": set(),
        "political_views": set(),
        "connections": [],
    }
    
    for r in results:
        if not r:
            continue
        
        # Noms
        for key in ["name", "full_name", "display_name", "first_name"]:
            if r.get(key):
                identity["names"].add(r[key].strip())
        
        # Emails
        for key in ["email", "email_in_bio"]:
            if r.get(key):
                identity["emails"].add(r[key].strip())
        
        if r.get("emails_from_commits"):
            for email in r["emails_from_commits"]:
                identity["emails"].add(email)
        
        # Locations
        for key in ["location", "currentLocation"]:
            if r.get(key):
                identity["locations"].add(r[key].strip())
        
        # Companies/Schools
        if r.get("company"):
            identity["companies"].add(r["company"].strip())
        if r.get("headline"):
            identity["companies"].add(r["headline"].strip())
        
        # Bio → intérêts
        bio = r.get("bio", "")
        if bio:
            # Détecter orientation politique
            political_keywords = {
                "gauche": ["gauche", "socialiste", "écolo", "progressiste", "anticapitaliste"],
                "droite": ["droite", "conservateur", "patriote", "nationaliste", "trump"],
                "centre": ["centre", "modéré", "apolitique"],
            }
            bio_lower = bio.lower()
            for orientation, keywords in political_keywords.items():
                if any(kw in bio_lower for kw in keywords):
                    identity["political_views"].add(orientation)
            
            # Détecter intérêts
            interest_keywords = ["gaming", "tech", "dev", "developer", "music", "sport", "photo", "travel", "crypto", "nft"]
            for interest in interest_keywords:
                if interest in bio_lower:
                    identity["interests"].add(interest)
        
        # Connexions entre plateformes
        if r.get("twitter"):
            identity["connections"].append(f"Twitter: @{r['twitter']}")
        if r.get("website"):
            identity["connections"].append(f"Site: {r['website']}")
    
    # Convert sets to lists for JSON
    return {k: list(v) if isinstance(v, set) else v for k, v in identity.items()}


# ── Rapport final d'identité ────────────────────────────

def generate_identity_report(username: str, platform_results: list, identity: dict) -> str:
    """Genere un rapport d'identite complet — style dossier"""
    
    report = f"""# 👻 GHOST Identity Dossier — `{username}`

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Target:** `{username}`
**Platforms analyzed:** {len(platform_results)}

---

## 🎯 Executive Summary

"""
    
    # Noms trouvés
    if identity["names"]:
        report += f"**Identified names:** {', '.join(identity['names'])}\n\n"
    
    # Emails
    if identity["emails"]:
        report += f"**Emails found:** {', '.join(identity['emails'])}\n\n"
    
    # Localisation
    if identity["locations"]:
        report += f"**Location:** {', '.join(identity['locations'])}\n\n"
    
    # Travail/École
    if identity["companies"]:
        report += f"**Work/Role:** {', '.join(identity['companies'])}\n\n"
    
    # Opinions politiques
    if identity["political_views"]:
        report += f"**Political leaning:** {', '.join(identity['political_views'])}\n\n"
    
    # Intérêts
    if identity["interests"]:
        report += f"**Interests:** {', '.join(identity['interests'])}\n\n"
    
    # Connexions
    if identity["connections"]:
        report += f"**Connected accounts:** {', '.join(identity['connections'])}\n\n"
    
    # ── Détails par plateforme ──
    report += "\n## 📊 Platform Details\n\n"
    
    for r in platform_results:
        if not r:
            continue
        
        platform = r.get("platform", "?")
        report += f"### {platform}\n"
        report += f"- URL: {r.get('url', '?')}\n"
        
        # Infos clés
        for key in ["display_name", "full_name", "name", "bio", "location", "company", 
                    "headline", "email", "followers", "following", "posts", "verified",
                    "joined", "created_at", "karma", "top_subreddits", "topics_mentioned",
                    "top_games", "emails_from_commits", "email_in_bio"]:
            if r.get(key):
                val = r[key]
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val[:5])
                elif isinstance(val, dict):
                    val = ", ".join(f"{k}: {v}" for k, v in list(val.items())[:5])
                report += f"- **{key}:** {val}\n"
        
        report += "\n"
    
    # ── Verdict ──
    report += "\n## 💀 Verdict\n\n"
    
    anonymity_score = 100
    if identity["names"]:
        anonymity_score -= 30
    if identity["emails"]:
        anonymity_score -= 25
    if identity["locations"]:
        anonymity_score -= 20
    if identity["companies"]:
        anonymity_score -= 15
    if identity["political_views"]:
        anonymity_score -= 10
    
    if anonymity_score < 30:
        report += f"**ANONYMITY SCORE: {anonymity_score}/100 — This person is NOT anonymous.**\n\n"
        report += "Multiple personal identifiers were found across platforms. Real name, location, work, and opinions are all exposed.\n"
    elif anonymity_score < 60:
        report += f"**ANONYMITY SCORE: {anonymity_score}/100 — Partial anonymity.**\n\n"
        report += "Some personal info was found. With more investigation, full identity could be revealed.\n"
    else:
        report += f"**ANONYMITY SCORE: {anonymity_score}/100 — Good anonymity practices.**\n\n"
        report += "Limited personal info found. This person takes privacy seriously.\n"
    
    report += f"\n---\n*Generated by GHOST v0.3 — Deep Extract Module*\n"
    
    return report
