# GHOST — Identity Dossier Module
# Genere une fiche d'identite complete et consultable
# Objectif: prouver que la personne n'est PAS anonyme

import re
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Deep Profile Scraper ─────────────────────────────────

def deep_scrape_profile(platform: str, username: str) -> dict:
    """Scrape en profondeur un profil specifique"""
    
    scrapers = {
        "twitter": scrape_twitter,
        "x": scrape_twitter,
        "instagram": scrape_instagram,
        "github": scrape_github,
        "reddit": scrape_reddit,
        "tiktok": scrape_tiktok,
        "linkedin": scrape_linkedin,
        "steam": scrape_steam,
        "twitch": scrape_twitch,
        "youtube": scrape_youtube,
        "pinterest": scrape_pinterest,
    }
    
    scraper = scrapers.get(platform)
    if scraper:
        return scraper(username)
    
    return {"platform": platform, "username": username, "error": "No scraper available"}


def scrape_twitter(username: str) -> dict:
    """Scrape Twitter/X via Nitter instances"""
    result = {
        "platform": "Twitter/X",
        "username": username,
        "url": f"https://x.com/{username}",
        "display_name": None,
        "bio": None,
        "location": None,
        "website": None,
        "joined": None,
        "following": None,
        "followers": None,
        "tweets_count": None,
        "email_in_bio": None,
        "political_leaning": None,
        "recent_tweets": [],
        "links": [],
    }
    
    nitter_instances = [
        "nitter.privacydev.net",
        "nitter.poast.org", 
        "nitter.1d4.us",
        "nitter.cz",
    ]
    
    for instance in nitter_instances:
        try:
            # Page principale
            r = httpx.get(f"https://{instance}/{username}", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if r.status_code != 200:
                continue
            
            text = r.text
            
            # Display name
            name_match = re.search(r'class="profile-card-fullname"[^>]*>\s*<a[^>]*>([^<]+)', text)
            if name_match:
                result["display_name"] = name_match.group(1).strip()
            
            # Bio
            bio_match = re.search(r'class="profile-bio"[^>]*>\s*<p>([^<]+)', text)
            if bio_match:
                result["bio"] = bio_match.group(1).strip()
                # Chercher email dans bio
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', result["bio"])
                if email_match:
                    result["email_in_bio"] = email_match.group(0)
                # Chercher liens dans bio
                links = re.findall(r'https?://[^\s<]+', result["bio"])
                if links:
                    result["links"] = links
            
            # Location
            loc_match = re.search(r'class="profile-location"[^>]*>\s*<span[^>]*>([^<]+)', text)
            if loc_match:
                result["location"] = loc_match.group(1).strip()
            
            # Website
            web_match = re.search(r'class="profile-url"[^>]*>\s*<a[^>]*href="([^"]+)"', text)
            if web_match:
                result["website"] = web_match.group(1).strip()
            
            # Stats
            stats = re.findall(r'class="profile-stat-num"[^>]*>([^<]+)<', text)
            if len(stats) >= 3:
                result["following"] = stats[0].strip().replace(",", "")
                result["followers"] = stats[1].strip().replace(",", "")
                result["tweets_count"] = stats[2].strip().replace(",", "")
            
            # Date inscription
            join_match = re.search(r'class="profile-joindate"[^>]*>.*?<span[^>]*title="([^"]+)"', text)
            if join_match:
                result["joined"] = join_match.group(1).strip()
            
            # Tweets récents
            tweets = re.findall(r'class="tweet-content[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL)
            for tweet in tweets[:10]:
                clean = re.sub(r'<[^>]+>', '', tweet).strip()
                if clean and len(clean) > 10:
                    result["recent_tweets"].append(clean[:200])
            
            # Detecter orientation politique
            all_text = " ".join([result.get("bio", "")] + result["recent_tweets"]).lower()
            political_keywords = {
                "left": ["gauche", "macron", "mélenchon", "eelv", "socialiste", "progressiste", "antifa"],
                "right": ["le pen", "zemmour", "rn", "reconquête", "conservateur", "patriote", "souverainiste"],
                "centrist": ["centre", "modéré", "républicain", "macroniste"],
                "conspiracy": ["complot", "fake", "démagogue", "système", "caste", "élite"],
            }
            for leaning, keywords in political_keywords.items():
                if any(kw in all_text for kw in keywords):
                    result["political_leaning"] = leaning
                    break
            
            result["source"] = instance
            break
            
        except Exception as e:
            continue
    
    return result


def scrape_instagram(username: str) -> dict:
    """Scrape Instagram (donnees publiques)"""
    result = {
        "platform": "Instagram",
        "username": username,
        "url": f"https://instagram.com/{username}",
        "full_name": None,
        "bio": None,
        "followers": None,
        "following": None,
        "posts": None,
        "verified": False,
        "email_in_bio": None,
        "external_links": [],
        "recent_captions": [],
    }
    
    try:
        r = httpx.get(f"https://www.instagram.com/{username}/", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"})
        
        if r.status_code == 200:
            text = r.text
            
            # JSON embarqué
            json_match = re.search(r'window\._sharedData\s*=\s*({.+?});</script>', text)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    user = data.get("entry_data", {}).get("ProfilePage", [{}])[0].get("graphql", {}).get("user", {})
                    
                    result["full_name"] = user.get("full_name")
                    result["bio"] = user.get("biography")
                    result["followers"] = user.get("edge_followed_by", {}).get("count")
                    result["following"] = user.get("edge_follow", {}).get("count")
                    result["posts"] = user.get("edge_owner_to_timeline_media", {}).get("count")
                    result["verified"] = user.get("is_verified", False)
                    
                    # Liens externes
                    if user.get("external_url"):
                        result["external_links"].append(user["external_url"])
                    
                    # Captions récentes
                    edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
                    for edge in edges[:10]:
                        node = edge.get("node", {})
                        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                        if caption_edges:
                            caption = caption_edges[0].get("node", {}).get("text", "")
                            if caption:
                                result["recent_captions"].append(caption[:200])
                    
                    # Email dans bio
                    if result["bio"]:
                        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', result["bio"])
                        if email_match:
                            result["email_in_bio"] = email_match.group(0)
                        
                        links = re.findall(r'https?://[^\s]+', result["bio"])
                        result["external_links"].extend(links)
                        
                except json.JSONDecodeError:
                    pass
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_github(username: str) -> dict:
    """Scrape GitHub (API + page)"""
    result = {
        "platform": "GitHub",
        "username": username,
        "url": f"https://github.com/{username}",
        "name": None,
        "bio": None,
        "location": None,
        "company": None,
        "blog": None,
        "email": None,
        "twitter": None,
        "public_repos": 0,
        "followers": 0,
        "following": 0,
        "created_at": None,
        "top_languages": [],
        "emails_from_commits": [],
        "recent_activity": [],
    }
    
    try:
        # API
        r = httpx.get(f"https://api.github.com/users/{username}", timeout=15,
                     headers={"User-Agent": "GHOST-OSINT", "Accept": "application/vnd.github.v3+json"})
        
        if r.status_code == 200:
            data = r.json()
            result["name"] = data.get("name")
            result["bio"] = data.get("bio")
            result["location"] = data.get("location")
            result["company"] = data.get("company")
            result["blog"] = data.get("blog")
            result["email"] = data.get("email")
            result["twitter"] = data.get("twitter_username")
            result["public_repos"] = data.get("public_repos", 0)
            result["followers"] = data.get("followers", 0)
            result["following"] = data.get("following", 0)
            result["created_at"] = data.get("created_at")
            
            # Repos pour langages
            repos_r = httpx.get(f"https://api.github.com/users/{username}/repos?per_page=30&sort=updated", timeout=15,
                              headers={"User-Agent": "GHOST-OSINT", "Accept": "application/vnd.github.v3+json"})
            if repos_r.status_code == 200:
                languages = {}
                for repo in repos_r.json():
                    lang = repo.get("language")
                    if lang:
                        languages[lang] = languages.get(lang, 0) + 1
                result["top_languages"] = sorted(languages.items(), key=lambda x: -x[1])[:5]
            
            # Emails from commits
            events_r = httpx.get(f"https://api.github.com/users/{username}/events/public?per_page=100", timeout=15,
                               headers={"User-Agent": "GHOST-OSINT", "Accept": "application/vnd.github.v3+json"})
            if events_r.status_code == 200:
                emails = set()
                for event in events_r.json():
                    commits = event.get("payload", {}).get("commits", [])
                    for commit in commits:
                        email = commit.get("author", {}).get("email")
                        if email and "noreply" not in email:
                            emails.add(email)
                result["emails_from_commits"] = list(emails)
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_reddit(username: str) -> dict:
    """Scrape Reddit (API JSON)"""
    result = {
        "platform": "Reddit",
        "username": username,
        "url": f"https://reddit.com/user/{username}",
        "display_name": None,
        "total_karma": 0,
        "comment_karma": 0,
        "link_karma": 0,
        "created_utc": None,
        "verified_email": False,
        "top_subreddits": {},
        "recent_comments": [],
        "recent_posts": [],
        "political_mentions": [],
        "personal_info": [],
    }
    
    try:
        # About
        r = httpx.get(f"https://www.reddit.com/user/{username}/about.json", timeout=15,
                     headers={"User-Agent": "GHOST-OSINT/0.1 (by /u/GHOST-OSINT)"})
        
        if r.status_code == 200:
            data = r.json().get("data", {})
            result["display_name"] = data.get("name")
            result["total_karma"] = data.get("total_karma", 0)
            result["comment_karma"] = data.get("comment_karma", 0)
            result["link_karma"] = data.get("link_karma", 0)
            result["created_utc"] = data.get("created_utc")
            result["verified_email"] = data.get("has_verified_email", False)
        
        # Commentaires récents
        comments_r = httpx.get(f"https://www.reddit.com/user/{username}/comments.json?limit=100&sort=new", timeout=15,
                             headers={"User-Agent": "GHOST-OSINT/0.1 (by /u/GHOST-OSINT)"})
        if comments_r.status_code == 200:
            for comment in comments_r.json().get("data", {}).get("children", []):
                body = comment.get("data", {}).get("body", "")
                subreddit = comment.get("data", {}).get("subreddit", "")
                
                if body:
                    result["recent_comments"].append({
                        "subreddit": subreddit,
                        "text": body[:300],
                        "url": f"https://reddit.com{comment.get('data', {}).get('permalink', '')}"
                    })
                
                # Subreddits actifs
                result["top_subreddits"][subreddit] = result["top_subreddits"].get(subreddit, 0) + 1
        
        # Posts récents
        posts_r = httpx.get(f"https://www.reddit.com/user/{username}/submitted.json?limit=50&sort=new", timeout=15,
                          headers={"User-Agent": "GHOST-OSINT/0.1 (by /u/GHOST-OSINT)"})
        if posts_r.status_code == 200:
            for post in posts_r.json().get("data", {}).get("children", []):
                title = post.get("data", {}).get("title", "")
                selftext = post.get("data", {}).get("selftext", "")
                subreddit = post.get("data", {}).get("subreddit", "")
                
                if title or selftext:
                    result["recent_posts"].append({
                        "subreddit": subreddit,
                        "title": title,
                        "text": selftext[:300] if selftext else "",
                        "url": f"https://reddit.com{post.get('data', {}).get('permalink', '')}"
                    })
        
        # Detecter mentions politiques et infos personnelles
        all_text = " ".join([c["text"] for c in result["recent_comments"]] + [p.get("text", "") for p in result["recent_posts"]])
        all_text_lower = all_text.lower()
        
        political_keywords = {
            "left": ["gauche", "socialiste", "mélenchon", "eelv", "communiste", "antifa", "progressiste"],
            "right": ["droite", "le pen", "zemmour", "rn", "reconquête", "conservateur", "patriote"],
            "libertarian": ["libéral", "libertarien", "anarchiste"],
        }
        for leaning, keywords in political_keywords.items():
            if any(kw in all_text_lower for kw in keywords):
                result["political_mentions"].append(leaning)
        
        # Detecter infos personnelles (age, ville, travail, etc.)
        personal_patterns = {
            "age": r"\b(\d{1,2})\s*ans?\b",
            "location": r"\b(?:habite|vit|basé?)\s+(?:à|en|au)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "work": r"\b(?:travail|bosse|poste)\s+(?:chez|à|en)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "school": r"\b(?:étudie|école|fac|université)\s+(?:à|en)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        }
        for info_type, pattern in personal_patterns.items():
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                result["personal_info"].append({"type": info_type, "values": list(set(matches))})
        
        # Top subreddits sorted
        result["top_subreddits"] = dict(sorted(result["top_subreddits"].items(), key=lambda x: -x[1])[:10])
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_tiktok(username: str) -> dict:
    """Scrape TikTok"""
    result = {
        "platform": "TikTok",
        "username": username,
        "url": f"https://tiktok.com/@{username}",
        "display_name": None,
        "bio": None,
        "followers": None,
        "following": None,
        "likes": None,
        "verified": False,
        "email_in_bio": None,
    }
    
    try:
        r = httpx.get(f"https://www.tiktok.com/@{username}", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"})
        
        if r.status_code == 200:
            text = r.text
            
            name_match = re.search(r'"nickName":"([^"]+)"', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            bio_match = re.search(r'"signature":"([^"]+)"', text)
            if bio_match:
                result["bio"] = bio_match.group(1).encode().decode("unicode_escape")
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', result["bio"])
                if email_match:
                    result["email_in_bio"] = email_match.group(0)
            
            followers_match = re.search(r'"followerCount":(\d+)', text)
            if followers_match:
                result["followers"] = int(followers_match.group(1))
            
            following_match = re.search(r'"followingCount":(\d+)', text)
            if following_match:
                result["following"] = int(following_match.group(1))
            
            likes_match = re.search(r'"heartCount":(\d+)', text)
            if likes_match:
                result["likes"] = int(likes_match.group(1))
            
            verified = re.search(r'"verified":(\w+)', text)
            if verified:
                result["verified"] = verified.group(1) == "true"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_linkedin(username: str) -> dict:
    """Scrape LinkedIn (limité sans compte)"""
    result = {
        "platform": "LinkedIn",
        "username": username,
        "url": f"https://linkedin.com/in/{username}",
        "first_name": None,
        "last_name": None,
        "full_name": None,
        "headline": None,
        "location": None,
        "company": None,
    }
    
    try:
        r = httpx.get(f"https://www.linkedin.com/in/{username}/", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        
        if r.status_code == 200:
            text = r.text
            
            name_match = re.search(r'"firstName":"([^"]+)","lastName":"([^"]+)"', text)
            if name_match:
                result["first_name"] = name_match.group(1)
                result["last_name"] = name_match.group(2)
                result["full_name"] = f"{name_match.group(1)} {name_match.group(2)}"
            
            headline_match = re.search(r'"headline":"([^"]+)"', text)
            if headline_match:
                result["headline"] = headline_match.group(1).encode().decode("unicode_escape")
            
            loc_match = re.search(r'"locationName":"([^"]+)"', text)
            if loc_match:
                result["location"] = loc_match.group(1).encode().decode("unicode_escape")
            
            company_match = re.search(r'"companyName":"([^"]+)"', text)
            if company_match:
                result["company"] = company_match.group(1).encode().decode("unicode_escape")
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_steam(username: str) -> dict:
    """Scrape Steam"""
    result = {
        "platform": "Steam",
        "username": username,
        "url": f"https://steamcommunity.com/id/{username}/",
        "display_name": None,
        "bio": None,
        "location": None,
        "top_games": [],
    }
    
    try:
        r = httpx.get(f"https://steamcommunity.com/id/{username}/?xml=1", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0"})
        
        if r.status_code == 200 and "<?xml" in r.text:
            text = r.text
            
            name_match = re.search(r'<steamID><!\[CDATA\[(.+)\]\]></steamID>', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            bio_match = re.search(r'<summary><!\[CDATA\[(.+)\]\]></summary>', text)
            if bio_match:
                result["bio"] = bio_match.group(1)
            
            loc_match = re.search(r'<location><!\[CDATA\[(.+)\]\]></location>', text)
            if loc_match:
                result["location"] = loc_match.group(1)
            
            # Jeux
            games_r = httpx.get(f"https://steamcommunity.com/id/{username}/games/?tab=all", timeout=15,
                              headers={"User-Agent": "Mozilla/5.0"})
            if games_r.status_code == 200:
                games = re.findall(r'"name":"([^"]+)","hours_forever":"([^"]+)"', games_r.text)
                result["top_games"] = [{"name": g[0], "hours": g[1]} for g in games[:5]]
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_twitch(username: str) -> dict:
    """Scrape Twitch"""
    result = {
        "platform": "Twitch",
        "username": username,
        "url": f"https://twitch.tv/{username}",
        "display_name": None,
        "bio": None,
        "followers": None,
    }
    
    try:
        r = httpx.get(f"https://www.twitch.tv/{username}", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        if r.status_code == 200:
            text = r.text
            
            name_match = re.search(r'"displayName":"([^"]+)"', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            bio_match = re.search(r'"description":"([^"]+)"', text)
            if bio_match:
                result["bio"] = bio_match.group(1).encode().decode("unicode_escape")
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_youtube(username: str) -> dict:
    """Scrape YouTube"""
    result = {
        "platform": "YouTube",
        "username": username,
        "url": f"https://youtube.com/@{username}",
        "display_name": None,
        "description": None,
        "subscribers": None,
    }
    
    try:
        r = httpx.get(f"https://www.youtube.com/@{username}/about", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        if r.status_code == 200:
            text = r.text
            
            name_match = re.search(r'"title":"([^"]+)"', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            desc_match = re.search(r'"description":"([^"]+)"', text)
            if desc_match:
                result["description"] = desc_match.group(1).encode().decode("unicode_escape")
            
            sub_match = re.search(r'"subscriberCountText":"([^"]+)"', text)
            if sub_match:
                result["subscribers"] = sub_match.group(1)
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def scrape_pinterest(username: str) -> dict:
    """Scrape Pinterest"""
    result = {
        "platform": "Pinterest",
        "username": username,
        "url": f"https://pinterest.com/{username}/",
        "display_name": None,
        "bio": None,
        "followers": None,
    }
    
    try:
        r = httpx.get(f"https://www.pinterest.com/{username}/", timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        if r.status_code == 200:
            text = r.text
            
            name_match = re.search(r'"full_name":"([^"]+)"', text)
            if name_match:
                result["display_name"] = name_match.group(1)
            
            bio_match = re.search(r'"about":"([^"]+)"', text)
            if bio_match:
                result["bio"] = bio_match.group(1)
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ── Identity Dossier Generator ──────────────────────────

def generate_dossier(username: str, profiles: list, advanced: dict = None, additional_sites: list = None) -> str:
    """Genere un dossier d'identite complet et consultable
    
    Args:
        username: pseudo cible
        profiles: liste des profils scrapes
        advanced: resultats advanced_osint (photos, google dorks, wayback, personal_info)
        additional_sites: sites trouves par WhatsMyName
    """
    
    # Collecter toutes les infos
    all_names = set()
    all_emails = set()
    all_locations = set()
    all_companies = set()
    all_schools = set()
    all_websites = set()
    all_twitter = set()
    political_views = set()
    all_bios = []
    all_links = []
    personal_quotes = []
    
    for p in profiles:
        if not p:
            continue
        
        # Noms
        for key in ["display_name", "full_name", "name", "first_name"]:
            if p.get(key):
                name = p[key].strip()
                if name and len(name) > 1:
                    all_names.add(name)
        
        # Emails
        for key in ["email", "email_in_bio"]:
            if p.get(key):
                all_emails.add(p[key])
        if p.get("emails_from_commits"):
            for e in p["emails_from_commits"]:
                all_emails.add(e)
        
        # Locations
        if p.get("location"):
            all_locations.add(p["location"])
        
        # Companies/Work
        for key in ["company", "headline"]:
            if p.get(key):
                all_companies.add(p[key])
        
        # Websites
        if p.get("website"):
            all_websites.add(p["website"])
        if p.get("blog"):
            all_websites.add(p["blog"])
        if p.get("external_links"):
            for link in p["external_links"]:
                all_websites.add(link)
        if p.get("links"):
            for link in p["links"]:
                all_websites.add(link)
        
        # Twitter lié
        if p.get("twitter"):
            all_twitter.add(p["twitter"])
        
        # Bios
        if p.get("bio"):
            all_bios.append((p["platform"], p["bio"]))
        
        # Political views
        if p.get("political_leaning"):
            political_views.add(p["political_leaning"])
        if p.get("political_mentions"):
            for m in p["political_mentions"]:
                political_views.add(m)
        
        # Citations personnelles (tweets, comments)
        if p.get("recent_tweets"):
            for tweet in p["recent_tweets"][:5]:
                personal_quotes.append(("Twitter", tweet))
        if p.get("recent_comments"):
            for comment in p["recent_comments"][:5]:
                personal_quotes.append((f"Reddit/r/{comment['subreddit']}", comment["text"], comment.get("url", "")))
        if p.get("recent_captions"):
            for caption in p["recent_captions"][:5]:
                personal_quotes.append(("Instagram", caption))
    
    # Calculer score anonymat
    anonymity_score = 100
    if all_names: anonymity_score -= 25
    if all_emails: anonymity_score -= 25
    if all_locations: anonymity_score -= 20
    if all_companies: anonymity_score -= 15
    if political_views: anonymity_score -= 10
    if personal_quotes: anonymity_score -= 5
    anonymity_score = max(0, anonymity_score)
    
    # Generer le dossier HTML
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GHOST Dossier — {username}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; line-height: 1.6; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        
        .header {{ text-align: center; padding: 40px 0; border-bottom: 2px solid #ff4b4b; margin-bottom: 30px; }}
        .header h1 {{ color: #ff4b4b; font-size: 2.5rem; }}
        .header .subtitle {{ color: #888; margin-top: 10px; }}
        
        .anonymity-score {{ 
            display: inline-block; padding: 15px 30px; border-radius: 10px; 
            font-size: 1.2rem; font-weight: bold; margin-top: 20px;
        }}
        .score-low {{ background: #ff4b4b33; color: #ff4b4b; border: 2px solid #ff4b4b; }}
        .score-medium {{ background: #ffaa0033; color: #ffaa00; border: 2px solid #ffaa00; }}
        .score-high {{ background: #00ff8833; color: #00ff88; border: 2px solid #00ff88; }}
        
        .section {{ background: #12121a; border: 1px solid #2a2a3a; border-radius: 10px; padding: 25px; margin-bottom: 20px; }}
        .section h2 {{ color: #ff4b4b; margin-bottom: 15px; font-size: 1.3rem; }}
        .section h3 {{ color: #ff8888; margin: 15px 0 10px 0; font-size: 1.1rem; }}
        
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
        .info-item {{ background: #1a1a25; padding: 15px; border-radius: 8px; border-left: 3px solid #ff4b4b; }}
        .info-item .label {{ color: #888; font-size: 0.85rem; text-transform: uppercase; }}
        .info-item .value {{ color: #fff; font-size: 1rem; margin-top: 5px; }}
        
        a {{ color: #58a6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        
        .quote {{ 
            background: #1a1a25; padding: 15px; border-radius: 8px; margin: 10px 0; 
            border-left: 3px solid #58a6ff; font-style: italic;
        }}
        .quote .source {{ color: #888; font-size: 0.8rem; margin-top: 5px; font-style: normal; }}
        
        .platform-section {{ margin-bottom: 20px; }}
        .platform-header {{ 
            background: #1a1a25; padding: 12px 20px; border-radius: 8px 8px 0 0; 
            border-bottom: 2px solid #ff4b4b; font-weight: bold;
        }}
        .platform-content {{ background: #0f0f18; padding: 20px; border-radius: 0 0 8px 8px; }}
        
        .verdict {{ 
            text-align: center; padding: 30px; border-radius: 10px; margin-top: 30px;
            background: {"#ff4b4b22" if anonymity_score < 40 else "#ffaa0022" if anonymity_score < 70 else "#00ff8822"};
            border: 2px solid {"#ff4b4b" if anonymity_score < 40 else "#ffaa00" if anonymity_score < 70 else "#00ff88"};
        }}
        .verdict h2 {{ color: {"#ff4b4b" if anonymity_score < 40 else "#ffaa00" if anonymity_score < 70 else "#00ff88"}; font-size: 1.5rem; }}
        
        .footer {{ text-align: center; padding: 30px; color: #555; font-size: 0.85rem; margin-top: 40px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👻 GHOST Identity Dossier</h1>
            <p class="subtitle">Target: <strong>@{username}</strong> | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
            <div class="anonymity-score {"score-low" if anonymity_score < 40 else "score-medium" if anonymity_score < 70 else "score-high"}">
                ANONYMITY SCORE: {anonymity_score}/100
                {" — NOT ANONYMOUS" if anonymity_score < 40 else " — PARTIAL ANONYMITY" if anonymity_score < 70 else " — GOOD ANONYMITY"}
            </div>
        </div>
        
        <!-- IDENTITY SECTION -->
        <div class="section">
            <h2>🎯 Identity Summary</h2>
            <div class="info-grid">
"""
    
    # Noms
    if all_names:
        html += f"""
                <div class="info-item">
                    <div class="label">Names Found</div>
                    <div class="value">{'<br>'.join(f'• {n}' for n in all_names)}</div>
                </div>"""
    
    # Emails
    if all_emails:
        html += f"""
                <div class="info-item">
                    <div class="label">Emails</div>
                    <div class="value">{'<br>'.join(f'• <a href="mailto:{e}">{e}</a>' for e in all_emails)}</div>
                </div>"""
    
    # Locations
    if all_locations:
        html += f"""
                <div class="info-item">
                    <div class="label">Location</div>
                    <div class="value">{'<br>'.join(f'• {l}' for l in all_locations)}</div>
                </div>"""
    
    # Work/Company
    if all_companies:
        html += f"""
                <div class="info-item">
                    <div class="label">Work / Role</div>
                    <div class="value">{'<br>'.join(f'• {c}' for c in all_companies)}</div>
                </div>"""
    
    # Websites
    if all_websites:
        html += f"""
                <div class="info-item">
                    <div class="label">Websites</div>
                    <div class="value">{'<br>'.join(f'• <a href="{w}" target="_blank">{w}</a>' for w in all_websites)}</div>
                </div>"""
    
    # Twitter lié
    if all_twitter:
        html += f"""
                <div class="info-item">
                    <div class="label">Linked Twitter</div>
                    <div class="value">{'<br>'.join(f'• <a href="https://x.com/{t}" target="_blank">@{t}</a>' for t in all_twitter)}</div>
                </div>"""
    
    # Political views
    if political_views:
        html += f"""
                <div class="info-item">
                    <div class="label">Political Views</div>
                    <div class="value">{'<br>'.join(f'• {p}' for p in political_views)}</div>
                </div>"""
    
    html += """
            </div>
        </div>"""
    
    # BIOS section
    if all_bios:
        html += """
        <div class="section">
            <h2>📝 Bios & Descriptions</h2>"""
        for platform, bio in all_bios:
            html += f"""
            <div class="quote">
                <strong>{platform}:</strong> {bio}
            </div>"""
        html += """
        </div>"""
    
    # Personal quotes
    if personal_quotes:
        html += """
        <div class="section">
            <h2>💬 Personal Statements</h2>
            <p style="color:#888;margin-bottom:15px;">Things this person said publicly:</p>"""
        for item in personal_quotes[:15]:
            if len(item) == 3:
                platform, text, url = item
                html += f"""
            <div class="quote">
                {text[:300]}
                <div class="source">
                    — {platform} 
                    {f'<a href="{url}" target="_blank">View original</a>' if url else ''}
                </div>
            </div>"""
            else:
                platform, text = item
                html += f"""
            <div class="quote">
                {text[:300]}
                <div class="source">— {platform}</div>
            </div>"""
        html += """
        </div>"""
    
    # Platform details
    html += """
        <div class="section">
            <h2>📊 Platform Profiles</h2>"""
    
    for p in profiles:
        if not p:
            continue
        
        platform = p.get("platform", "?")
        url = p.get("url", "#")
        
        html += f"""
            <div class="platform-section">
                <div class="platform-header">
                    <a href="{url}" target="_blank">{platform} ↗</a>
                </div>
                <div class="platform-content">"""
        
        # Infos spécifiques
        for key, label in [
            ("display_name", "Display Name"),
            ("full_name", "Full Name"),
            ("bio", "Bio"),
            ("location", "Location"),
            ("company", "Company"),
            ("headline", "Headline"),
            ("followers", "Followers"),
            ("following", "Following"),
            ("posts", "Posts"),
            ("verified", "Verified"),
            ("joined", "Joined"),
            ("karma", "Karma"),
            ("top_languages", "Top Languages"),
            ("top_subreddits", "Top Subreddits"),
            ("top_games", "Top Games"),
        ]:
            if p.get(key):
                val = p[key]
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val[:5])
                elif isinstance(val, dict):
                    val = ", ".join(f"{k}: {v}" for k, v in list(val.items())[:5])
                html += f"""
                    <div style="margin:5px 0;"><strong>{label}:</strong> {val}</div>"""
        
        html += """
                </div>
            </div>"""
    
    html += """
        </div>"""
    
    # ── PHOTO GALLERY ──
    if advanced and advanced.get("photos"):
        photos = advanced["photos"]
        html += """
        <div class="section">
            <h2>📷 Photo Gallery</h2>
            <p style="color:#888;margin-bottom:15px;">""" + str(len(photos)) + """ photos found across platforms:</p>
            <div class="photo-gallery">"""
        
        for photo in photos[:20]:
            url = photo.get("url", "")
            source = photo.get("source", "unknown")
            if url:
                html += f"""
                <div class="photo-item">
                    <a href="{url}" target="_blank">
                        <img src="{url}" alt="{source}" loading="lazy" onerror="this.style.display='none'">
                    </a>
                    <div class="platform">{source}</div>
                    <button class="download" onclick="window.open('{url}', '_blank')">📥</button>
                </div>"""
        
        html += """
            </div>
        </div>"""
    
    # ── GOOGLE DORKS ──
    if advanced and advanced.get("google_dorks"):
        dorks = advanced["google_dorks"].get("findings", [])
        if dorks:
            html += """
            <div class="section">
                <h2>🔍 Google Dorks</h2>
                <p style="color:#888;margin-bottom:15px;">Click to search for leaked information:</p>"""
            
            for dork in dorks[:15]:
                query = dork.get("query", "")
                search_url = dork.get("search_url", "")
                if query:
                    html += f"""
                <a href="{search_url}" target="_blank" class="profile-link">
                    <span class="platform">🔎</span>
                    <span class="url">{query}</span>
                </a>"""
            
            html += """
            </div>"""
    
    # ── WAYBACK MACHINE ──
    if advanced and advanced.get("wayback"):
        snapshots = advanced["wayback"].get("snapshots", [])
        if snapshots:
            html += """
            <div class="section">
                <h2>🕰️ Wayback Machine</h2>
                <p style="color:#888;margin-bottom:15px;">""" + str(len(snapshots)) + """ historical snapshots found:</p>"""
            
            for snap in snapshots[:10]:
                wayback_url = snap.get("wayback_url", "")
                original = snap.get("original_url", "")
                timestamp = snap.get("timestamp", "")
                if wayback_url:
                    html += f"""
                <a href="{wayback_url}" target="_blank" class="profile-link">
                    <span class="platform">{timestamp[:10] if timestamp else '?'}</span>
                    <span class="url">{original}</span>
                </a>"""
            
            html += """
            </div>"""
    
    # ── PERSONAL INFO ──
    if advanced and advanced.get("personal_info"):
        pi = advanced["personal_info"]
        has_personal = any(pi.get(k) for k in ["emails", "phones", "ages", "locations", "work", "school", "political_views", "personal_anecdotes"])
        
        if has_personal:
            html += """
            <div class="section">
                <h2>🎯 Personal Information Extracted</h2>
                <div class="info-grid">"""
            
            for key, label in [
                ("emails", "Emails Found"),
                ("phones", "Phone Numbers"),
                ("ages", "Age Mentions"),
                ("locations", "Locations"),
                ("work", "Work/Job"),
                ("school", "School/Studies"),
                ("relationship_status", "Relationship"),
                ("interests", "Interests"),
                ("political_views", "Political Views"),
            ]:
                values = pi.get(key, [])
                if values:
                    if isinstance(values, list):
                        val_str = ", ".join(str(v) for v in values[:5])
                    else:
                        val_str = str(values)
                    html += f"""
                    <div class="info-item">
                        <div class="label">{label}</div>
                        <div class="value">{val_str}</div>
                    </div>"""
            
            html += """
                </div>"""
            
            # Personal anecdotes
            anecdotes = pi.get("personal_anecdotes", [])
            if anecdotes:
                html += """
                <h3 style="margin-top:20px;">Personal Statements</h3>"""
                for anecdote in anecdotes[:10]:
                    html += f"""
                <div class="quote">
                    "{anecdote}"
                </div>"""
            
            html += """
            </div>"""
    
    # ── ADDITIONAL SITES (WhatsMyName) ──
    if additional_sites:
        html += """
        <div class="section">
            <h2>🌐 Additional Sites Found</h2>
            <p style="color:#888;margin-bottom:15px;">""" + str(len(additional_sites)) + """ additional profiles found:</p>"""
        
        for site in additional_sites[:30]:
            site_name = site.get("site", "?")
            site_url = site.get("url", "")
            category = site.get("category", "")
            if site_url:
                html += f"""
            <a href="{site_url}" target="_blank" class="profile-link">
                <span class="platform">{site_name}</span>
                <span class="url">{category} • {site_url}</span>
            </a>"""
        
        html += """
        </div>"""
    
    # Verdict
    if anonymity_score < 40:
        verdict_text = "This person is NOT anonymous. Multiple personal identifiers were found. Real name, location, work, emails, and opinions are all exposed."
    elif anonymity_score < 70:
        verdict_text = "Partial anonymity. Some personal info was found. With more investigation, full identity could be revealed."
    else:
        verdict_text = "Good anonymity practices detected. Limited personal info found."
    
    html += f"""
        <div class="verdict">
            <h2>💀 Verdict</h2>
            <p style="margin-top:15px;font-size:1.1rem;">{verdict_text}</p>
            <p style="margin-top:10px;color:#888;">
                This dossier was generated by analyzing publicly available data across {len(profiles)} platforms.
            </p>
        </div>
        
        <div class="footer">
            <p>Generated by GHOST OSINT Engine v0.3</p>
            <p style="margin-top:5px;">This report contains only publicly available information.</p>
        </div>
    </div>
</body>
</html>"""
    
    return html
