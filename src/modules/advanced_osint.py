# GHOST — Advanced OSINT Module
# Google Dorking + Wayback Machine + Reverse Image Search

import re
import json
import time
import httpx
from pathlib import Path
from typing import Optional
from datetime import datetime


# ── Google Dorking ───────────────────────────────────────

def google_dork(username: str, full_name: str = None) -> dict:
    """
    Genere et execute des Google Dorks pour trouver des infos personnelles.
    """
    result = {
        "tool": "Google Dorking",
        "username": username,
        "queries": [],
        "findings": [],
    }
    
    # Construire les dorks
    dorks = [
        # Infos de base
        f'"{username}" email OR email',
        f'"{username}" phone OR telephone',
        f'"{username}" address OR adresse',
        f'"{username}" site:linkedin.com',
        f'"{username}" site:facebook.com',
        f'"{username}" site:instagram.com',
        f'"{username}" site:twitter.com',
        f'"{username}" site:github.com',
        f'"{username}" site:reddit.com',
        
        # Fuites de données
        f'"{username}" filetype:pdf',
        f'"{username}" filetype:xls OR filetype:xlsx',
        f'"{username}" filetype:doc OR filetype:docx',
        
        # Sites de rencontres
        f'"{username}" site:tinder.com OR site:okcupid.com',
        f'"{username}" site:badoo.com OR site:meetic.fr',
        f'"{username}" "looking for" OR "meet me"',
        
        # Forums et commentaires
        f'"{username}" site:forum.*',
        f'"{username}" inurl:profile OR inurl:user',
        
        # Images
        f'"{username}" filetype:jpg OR filetype:png',
        f'"{username}" site:pinterest.com',
        
        # Infos pro
        f'"{username}" "works at" OR "travaille chez"',
        f'"{username}" "studies at" OR "étudie à"',
    ]
    
    # Si on a le vrai nom, ajouter des dorks
    if full_name:
        dorks.extend([
            f'"{full_name}" email',
            f'"{full_name}" phone',
            f'"{full_name}" site:linkedin.com',
            f'"{full_name}" site:facebook.com',
            f'"{full_name}" address',
        ])
    
    result["queries"] = dorks
    
    # Executer les recherches (via web_search si disponible, sinon manuel)
    # Note: sur Render, on passe par l'API qui appelle web_search
    # Ici on retourne les URLs de recherche pour consultation manuelle
    
    for dork in dorks:
        search_url = f"https://www.google.com/search?q={dork.replace(' ', '+')}"
        result["findings"].append({
            "query": dork,
            "search_url": search_url,
        })
    
    return result


# ── Wayback Machine ─────────────────────────────────────

def wayback_search(username: str, platform: str = None) -> dict:
    """
    Recherche dans l'historique Wayback Machine.
    Trouve d'anciennes versions de profils supprimes.
    """
    result = {
        "tool": "Wayback Machine",
        "username": username,
        "snapshots": [],
    }
    
    urls_to_check = []
    
    if platform:
        # URL specifique
        urls_to_check.append(f"https://{platform}.com/{username}")
    else:
        # URLs communes
        platforms = [
            ("twitter", f"https://twitter.com/{username}"),
            ("reddit", f"https://reddit.com/user/{username}"),
            ("github", f"https://github.com/{username}"),
            ("instagram", f"https://instagram.com/{username}"),
            ("tiktok", f"https://tiktok.com/@{username}"),
        ]
        urls_to_check = [url for _, url in platforms]
    
    for url in urls_to_check:
        try:
            # API Wayback Machine
            api_url = f"https://archive.org/wayback/available?url={url}"
            r = httpx.get(api_url, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                snapshots = data.get("archived_snapshots", {})
                closest = snapshots.get("closest")
                
                if closest and closest.get("available"):
                    result["snapshots"].append({
                        "original_url": url,
                        "wayback_url": closest.get("url"),
                        "timestamp": closest.get("timestamp"),
                        "status": closest.get("status"),
                    })
            
            # Aussi chercher la liste complete des snapshots
            cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=20"
            r = httpx.get(cdx_url, timeout=10)
            
            if r.status_code == 200 and r.text.strip():
                lines = r.text.strip().split("\n")
                for line in lines[1:]:  # Skip header
                    parts = line.split(" ")
                    if len(parts) >= 3:
                        result["snapshots"].append({
                            "original_url": url,
                            "timestamp": parts[1],
                            "wayback_url": f"https://web.archive.org/web/{parts[1]}/{parts[2]}",
                        })
            
        except Exception as e:
            continue
    
    return result


# ── Reverse Image Search ────────────────────────────────

def reverse_image_search(image_url: str = None, image_path: str = None) -> dict:
    """
    Reverse image search via plusieurs moteurs.
    Retourne les URLs de recherche pour consultation.
    """
    result = {
        "tool": "Reverse Image Search",
        "image": image_url or image_path,
        "search_urls": {},
    }
    
    # Yandex (meilleur pour les visages)
    if image_url:
        result["search_urls"]["yandex"] = f"https://yandex.com/images/search?url={image_url}&rpt=imageview"
    
    # Google Lens
    if image_url:
        result["search_urls"]["google_lens"] = f"https://lens.google.com/uploadbyurl?url={image_url}"
    
    # Bing Visual Search
    if image_url:
        result["search_urls"]["bing"] = f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:{image_url}"
    
    # TinEye
    if image_url:
        result["search_urls"]["tineye"] = f"https://tineye.com/search?url={image_url}"
    
    # FaceOnLive (si API key)
    # result["search_urls"]["faceonlive"] = ...
    
    return result


# ── Photo Extractor ─────────────────────────────────────

def extract_photos_from_profile(platform: str, username: str) -> list:
    """
    Extrait les URLs de photos depuis un profil public.
    """
    photos = []
    
    try:
        if platform in ["twitter", "x"]:
            # Nitter pour les photos
            nitter_instances = ["nitter.privacydev.net", "nitter.poast.org"]
            for instance in nitter_instances:
                try:
                    r = httpx.get(f"https://{instance}/{username}/media", timeout=15,
                                 headers={"User-Agent": "Mozilla/5.0"})
                    if r.status_code == 200:
                        # Extraire les URLs d'images
                        img_urls = re.findall(r'src="(https://[^"]+\.(?:jpg|jpeg|png|gif))"', r.text)
                        photos.extend([{"url": url, "source": f"nitter/{instance}"} for url in img_urls[:20]])
                        if photos:
                            break
                except:
                    continue
        
        elif platform == "instagram":
            r = httpx.get(f"https://www.instagram.com/{username}/", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)"})
            if r.status_code == 200:
                # JSON embarqué
                json_match = re.search(r'window\._sharedData\s*=\s*({.+?});</script>', r.text)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        user = data.get("entry_data", {}).get("ProfilePage", [{}])[0].get("graphql", {}).get("user", {})
                        
                        # Photo de profil
                        if user.get("profile_pic_url_hd"):
                            photos.append({"url": user["profile_pic_url_hd"], "source": "instagram/profile"})
                        
                        # Posts photos
                        edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
                        for edge in edges[:12]:
                            node = edge.get("node", {})
                            if node.get("display_url"):
                                photos.append({"url": node["display_url"], "source": "instagram/post"})
                    except:
                        pass
        
        elif platform == "github":
            # Avatar
            avatar_url = f"https://avatars.githubusercontent.com/{username}?v=4&s=400"
            photos.append({"url": avatar_url, "source": "github/avatar"})
        
        elif platform == "reddit":
            r = httpx.get(f"https://www.reddit.com/user/{username}/about.json", timeout=15,
                         headers={"User-Agent": "GHOST-OSINT/0.1"})
            if r.status_code == 200:
                data = r.json().get("data", {})
                icon = data.get("icon_img", "")
                if icon:
                    photos.append({"url": icon.split("?")[0], "source": "reddit/avatar"})
                snoovatar = data.get("snoovatar_img", "")
                if snoovatar:
                    photos.append({"url": snoovatar.split("?")[0], "source": "reddit/snoovatar"})
        
        elif platform == "twitch":
            r = httpx.get(f"https://www.twitch.tv/{username}", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                img_match = re.search(r'"offlineImageURL":"([^"]+)"', r.text)
                if img_match:
                    photos.append({"url": img_match.group(1).replace("\\u0026", "&"), "source": "twitch/offline"})
                profile_match = re.search(r'"profileImageUrl":"([^"]+)"', r.text)
                if profile_match:
                    photos.append({"url": profile_match.group(1).replace("\\u0026", "&"), "source": "twitch/profile"})
    
    except Exception as e:
        pass
    
    return photos


# ── Personal Info Extractor ─────────────────────────────

def extract_personal_info(text: str) -> dict:
    """
    Extrait des infos personnelles d'un texte (bio, posts, commentaires).
    """
    info = {
        "emails": [],
        "phones": [],
        "ages": [],
        "locations": [],
        "work": [],
        "school": [],
        "relationship_status": [],
        "interests": [],
        "political_views": [],
        "personal_anecdotes": [],
    }
    
    text_lower = text.lower()
    
    # Emails
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    info["emails"] = list(set(emails))
    
    # Telephones (FR)
    phones = re.findall(r'(?:(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4})', text)
    info["phones"] = list(set(phones))
    
    # Age
    ages = re.findall(r'\b(\d{1,2})\s*ans?\b', text, re.IGNORECASE)
    info["ages"] = [int(a) for a in ages if 13 <= int(a) <= 99]
    
    # Localisation
    loc_patterns = [
        r'(?:habite|vit|basé?|localisé?)\s+(?:à|en|au)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:from|based in|living in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'📍\s*([A-Z][a-z]+)',
    ]
    for pattern in loc_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        info["locations"].extend(matches)
    info["locations"] = list(set(info["locations"]))
    
    # Travail
    work_patterns = [
        r'(?:travail|bosse|poste|emploi)\s+(?:chez|à|en|pour|comme)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:works? at|working at|employed at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:ingénieur|développeur|directeur|manager|consultant|freelance)',
    ]
    for pattern in work_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        info["work"].extend(matches)
    info["work"] = list(set(info["work"]))
    
    # Ecole
    school_patterns = [
        r'(?:étudie|diplômé|passé)\s+(?:à|en|au)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:studies|graduated|degree)\s+(?:at|from|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    ]
    for pattern in school_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        info["school"].extend(matches)
    info["school"] = list(set(info["school"]))
    
    # Relations
    relation_keywords = ["marié", "célibataire", "en couple", "divorcé", "mariée", "célibataire", "single", "married", "divorced"]
    for kw in relation_keywords:
        if kw in text_lower:
            info["relationship_status"].append(kw)
    
    # Interets
    interest_keywords = ["gaming", "jeux", "sport", "football", "basket", "musique", "photo", "voyage", "cuisine", "cinéma", "série", "anime", "manga", "crypto", "nft", "tech", "dev", "programming"]
    for kw in interest_keywords:
        if kw in text_lower:
            info["interests"].append(kw)
    
    # Opinions politiques
    political_keywords = {
        "left": ["gauche", "socialiste", "mélenchon", "eelv", "communiste", "progressiste", "antifa"],
        "right": ["droite", "le pen", "zemmour", "rn", "reconquête", "conservateur", "patriote", "souverainiste"],
        "centrist": ["centre", "modéré", "macroniste", "républicain"],
        "conspiracy": ["complot", "fake news", "système", "caste", "élite", "deep state"],
    }
    for leaning, keywords in political_keywords.items():
        if any(kw in text_lower for kw in keywords):
            info["political_views"].append(leaning)
    
    # Anecdotes personnelles (phrases avec "je")
    je_phrases = re.findall(r'Je\s+(?:suis|fais|aime|déteste|pense|crois|trouve)[^.]+\.', text, re.IGNORECASE)
    info["personal_anecdotes"] = je_phrases[:10]
    
    return info


# ── Full Investigation ──────────────────────────────────

def full_investigation(username: str, profiles: list) -> dict:
    """
    Lance une investigation complete:
    - Google Dorking
    - Wayback Machine
    - Photo extraction
    - Personal info extraction
    """
    result = {
        "username": username,
        "timestamp": datetime.now().isoformat(),
        "google_dorks": None,
        "wayback": None,
        "photos": [],
        "personal_info": {},
    }
    
    # Google Dorks
    result["google_dorks"] = google_dork(username)
    
    # Wayback Machine
    result["wayback"] = wayback_search(username)
    
    # Photos depuis les profils trouves
    all_photos = []
    for profile in profiles:
        if not profile:
            continue
        platform = profile.get("platform", "").lower()
        username_from_profile = profile.get("username", username)
        
        photos = extract_photos_from_profile(platform, username_from_profile)
        all_photos.extend(photos)
    
    # Dedupliquer
    seen = set()
    for photo in all_photos:
        if photo["url"] not in seen:
            seen.add(photo["url"])
            result["photos"].append(photo)
    
    # Extraire infos personnelles de tous les bios/posts
    all_text = ""
    for profile in profiles:
        if not profile:
            continue
        for key in ["bio", "recent_tweets", "recent_comments", "recent_captions", "recent_posts"]:
            val = profile.get(key)
            if val:
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            all_text += " " + item.get("text", "")
                        elif isinstance(item, str):
                            all_text += " " + item
                elif isinstance(val, str):
                    all_text += " " + val
    
    result["personal_info"] = extract_personal_info(all_text)
    
    return result
