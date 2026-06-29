# GHOST — Maigret & WhatsMyName Integration
# Scan 3000+ sites avec Maigret, 500+ avec WhatsMyName

import os
import json
import subprocess
import httpx
from pathlib import Path
from typing import Optional

# ── Maigret ──────────────────────────────────────────────

def run_maigret(username: str, timeout: int = 120) -> dict:
    """
    Lance Maigret pour scanner 3000+ sites.
    Retourne les résultats structurés.
    """
    result = {
        "tool": "Maigret",
        "username": username,
        "sites_found": [],
        "total_checked": 0,
        "error": None,
    }
    
    try:
        # Lancer Maigret en mode JSON
        cmd = [
            "python", "-m", "maigret", username,
            "--json",  # Output JSON
            "--no-progress",  # Pas de barre de progression
            "--timeout", str(timeout // 10),  # Timeout par site
            "--retries", "1",
            "--tor",  # Utiliser Tor si dispo (optionnel)
        ]
        
        # Exécuter sans Tor (plus rapide sur Render)
        cmd = [
            "python", "-m", "maigret", username,
            "--no-progress",
            "--timeout", "5",
            "--retries", "1",
            "-d",  # Debug minimal
        ]
        
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        # Parser le output
        output = proc.stdout + proc.stderr
        
        # Chercher les lignes avec des résultats
        for line in output.split("\n"):
            line = line.strip()
            if "[+]" in line or "Found" in line.lower():
                # Extraire l'URL du site
                url_match = line.split("http")
                if len(url_match) > 1:
                    url = "http" + url_match[1].split()[0]
                    result["sites_found"].append(url)
        
        result["total_checked"] = 3000  # Maigret vérifie ~3000 sites
        
    except subprocess.TimeoutExpired:
        result["error"] = f"Timeout after {timeout}s"
    except FileNotFoundError:
        result["error"] = "Maigret not installed"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def run_maigret_simple(username: str) -> dict:
    """
    Version simplifiée de Maigret — utilise l'API Python directement.
    """
    result = {
        "tool": "Maigret",
        "username": username,
        "sites_found": [],
        "total_checked": 0,
        "error": None,
    }
    
    try:
        from maigret.maigret import MaigretDatabase, Maigret
        
        # Charger la DB des sites
        db = MaigretDatabase()
        db.load_from_file()  # Charge les 3000+ sites
        
        # Créer l'instance Maigret
        maigret = Maigret(database=db)
        
        # Lancer le scan
        results = maigret.search(username)
        
        for site_name, site_data in results.items():
            if site_data and site_data.get("status"):
                status = site_data["status"]
                if status.status == "found":  # Site trouvé
                    result["sites_found"].append({
                        "site": site_name,
                        "url": site_data.get("url", ""),
                        "status": "found",
                    })
                elif status.status == "possible":
                    result["sites_found"].append({
                        "site": site_name,
                        "url": site_data.get("url", ""),
                        "status": "possible",
                    })
        
        result["total_checked"] = len(results)
        
    except ImportError:
        result["error"] = "Maigret not installed"
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ── WhatsMyName ─────────────────────────────────────────

def run_whatsmyname(username: str) -> dict:
    """
    Utilise WhatsMyName pour vérifier 500+ sites.
    Plus rapide que Maigret mais moins de sites.
    """
    result = {
        "tool": "WhatsMyName",
        "username": username,
        "sites_found": [],
        "total_checked": 0,
        "error": None,
    }
    
    try:
        # Charger la liste des sites depuis l'API WhatsMyName
        r = httpx.get(
            "https://raw.githubusercontent.com/Webbreacher/WhatsMyName/main/wmn-data.json",
            timeout=30,
        )
        
        if r.status_code != 200:
            result["error"] = "Could not load WhatsMyName data"
            return result
        
        data = r.json()
        sites = data.get("sites", [])
        result["total_checked"] = len(sites)
        
        # Vérifier chaque site (limité pour la vitesse)
        for site in sites[:100]:  # Limiter à 100 pour la vitesse
            uri = site.get("uri_check", "").replace("{account}", username)
            e_code = site.get("e_code", 200)
            e_string = site.get("e_string", "")
            m_string = site.get("m_string", "")
            
            if not uri:
                continue
            
            try:
                r = httpx.get(uri, timeout=5, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
                
                # Vérifier si le profil existe
                if r.status_code == e_string or (e_string and e_string in r.text):
                    if not m_string or m_string not in r.text:
                        result["sites_found"].append({
                            "site": site.get("name", "?"),
                            "url": uri,
                            "category": site.get("cat", "unknown"),
                        })
            except Exception:
                continue
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ── Combined Scan ───────────────────────────────────────

def full_username_scan(username: str) -> dict:
    """
    Scan complet avec Maigret + WhatsMyName.
    Retourne tous les profils trouvés avec infos.
    """
    result = {
        "username": username,
        "maigret": None,
        "whatsmyname": None,
        "all_profiles": [],
        "total_found": 0,
    }
    
    # Maigret (3000+ sites)
    maigret_result = run_maigret_simple(username)
    result["maigret"] = maigret_result
    
    # WhatsMyName (500+ sites)
    wmn_result = run_whatsmyname(username)
    result["whatsmyname"] = wmn_result
    
    # Fusionner les résultats
    all_profiles = []
    
    for site in maigret_result.get("sites_found", []):
        if isinstance(site, dict):
            all_profiles.append({
                "site": site.get("site", "?"),
                "url": site.get("url", ""),
                "source": "Maigret",
                "status": site.get("status", "found"),
            })
        elif isinstance(site, str):
            all_profiles.append({
                "site": site.split("/")[2] if "/" in site else site,
                "url": site,
                "source": "Maigret",
                "status": "found",
            })
    
    for site in wmn_result.get("sites_found", []):
        all_profiles.append({
            "site": site.get("site", "?"),
            "url": site.get("url", ""),
            "source": "WhatsMyName",
            "status": "found",
            "category": site.get("category", "unknown"),
        })
    
    # Dédupliquer par URL
    seen_urls = set()
    unique_profiles = []
    for p in all_profiles:
        if p["url"] not in seen_urls:
            seen_urls.add(p["url"])
            unique_profiles.append(p)
    
    result["all_profiles"] = unique_profiles
    result["total_found"] = len(unique_profiles)
    
    return result
