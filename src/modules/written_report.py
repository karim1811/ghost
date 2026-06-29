# GHOST — Written Report Module
# Genere un rapport redige style journaliste
# Resume la personne, ses opinions, anecdotes personnelles

import json
from datetime import datetime
from typing import Optional


def generate_written_report(username: str, profiles: list, identity: dict) -> str:
    """
    Genere un rapport redige sur la personne.
    Style: article d'investigation / portrait.
    """
    
    # Collecter les infos
    names = set()
    locations = set()
    bios = []
    websites = set()
    emails = set()
    political_views = set()
    personal_anecdotes = []
    quotes = []
    interests = set()
    work = set()
    photos_found = []
    
    for p in profiles:
        if not p:
            continue
        
        platform = p.get("platform", "?")
        
        # Noms
        for key in ["display_name", "full_name", "name", "first_name"]:
            if p.get(key):
                names.add(p[key].strip())
        
        # Locations
        if p.get("location"):
            locations.add(p["location"].strip())
        
        # Bios
        if p.get("bio"):
            bios.append((platform, p["bio"]))
        
        # Websites
        for key in ["website", "blog", "external_links"]:
            val = p.get(key)
            if val:
                if isinstance(val, list):
                    websites.update(val)
                elif isinstance(val, str):
                    websites.add(val)
        
        # Emails
        for key in ["email", "email_in_bio"]:
            if p.get(key):
                emails.add(p[key])
        if p.get("emails_from_commits"):
            emails.update(p["emails_from_commits"])
        
        # Political views
        if p.get("political_leaning"):
            political_views.add(p["political_leaning"])
        if p.get("political_mentions"):
            political_views.update(p["political_mentions"])
        
        # Citations
        if p.get("recent_tweets"):
            for tweet in p["recent_tweets"][:5]:
                quotes.append(("Twitter", tweet))
        if p.get("recent_comments"):
            for comment in p["recent_comments"][:5]:
                quotes.append((f"Reddit/r/{comment.get('subreddit', '?')}", comment.get("text", "")[:200]))
        if p.get("recent_captions"):
            for caption in p["recent_captions"][:3]:
                quotes.append(("Instagram", caption))
        
        # Work
        for key in ["company", "headline"]:
            if p.get(key):
                work.add(p[key])
        
        # Photos
        if p.get("avatar_url"):
            photos_found.append((platform, p["avatar_url"]))
        if p.get("photos"):
            for photo in p["photos"]:
                photos_found.append((platform, photo))
    
    # ── Rediger le rapport ──
    
    report = f"""# 👻 GHOST Investigation Report

## Portrait de `{username}`

**Date:** {datetime.now().strftime("%d %B %Y")}
**Enquêteur:** GHOST OSINT Engine
**Classification:** Public

---

"""
    
    # Introduction
    report += "## 1. Introduction\n\n"
    
    if names:
        primary_name = list(names)[0]
        report += f"**{primary_name}**, connu(e) sous le pseudonyme `{username}` sur les réseaux sociaux, "
    else:
        report += f"Le pseudonyme `{username}` "
    
    report += f"a été identifié sur **{len(profiles)} plateformes** différentes. "
    
    if locations:
        report += f"Basé(e) à **{list(locations)[0]}**, "
    
    report += f"cette personne maintient une présence en ligne significative depuis plusieurs années.\n\n"
    
    # Identité
    report += "## 2. Identité\n\n"
    
    if names:
        report += "### Noms identifiés\n\n"
        for name in names:
            report += f"- **{name}**\n"
        report += "\n"
    
    if emails:
        report += "### Adresses email\n\n"
        for email in emails:
            report += f"- `{email}`\n"
        report += "\n"
    
    if locations:
        report += "### Localisation\n\n"
        for loc in locations:
            report += f"- {loc}\n"
        report += "\n"
    
    if work:
        report += "### Activité professionnelle\n\n"
        for w in work:
            report += f"- {w}\n"
        report += "\n"
    
    # Présence en ligne
    report += "## 3. Présence en ligne\n\n"
    
    if bios:
        report += "### Biographies\n\n"
        for platform, bio in bios:
            report += f"**{platform}:** {bio}\n\n"
    
    if websites:
        report += "### Liens et sites web\n\n"
        for site in websites:
            report += f"- {site}\n"
        report += "\n"
    
    # Opinions et positions
    if political_views or quotes:
        report += "## 4. Opinions et positions\n\n"
        
        if political_views:
            report += f"**Orientation politique déclarée:** {', '.join(political_views)}\n\n"
        
        if quotes:
            report += "### Déclarations publiques\n\n"
            for source, quote in quotes[:10]:
                report += f"> {quote[:250]}\n>\n> — *{source}*\n\n"
    
    # Anecdotes personnelles
    if personal_anecdotes:
        report += "## 5. Anecdotes personnelles\n\n"
        report += "Les éléments suivants ont été partagés publiquement par la personne :\n\n"
        for anecdote in personal_anecdotes:
            report += f"- {anecdote}\n"
        report += "\n"
    
    # Photos
    if photos_found:
        report += "## 6. Photos et images\n\n"
        report += f"**{len(photos_found)} images** identifiées :\n\n"
        for platform, url in photos_found[:20]:
            report += f"- [{platform}]({url})\n"
        report += "\n"
    
    # Score anonymat
    report += "## 7. Évaluation de l'anonymat\n\n"
    
    anonymity_score = 100
    if names: anonymity_score -= 25
    if emails: anonymity_score -= 20
    if locations: anonymity_score -= 20
    if work: anonymity_score -= 15
    if quotes: anonymity_score -= 10
    if political_views: anonymity_score -= 10
    anonymity_score = max(0, anonymity_score)
    
    if anonymity_score < 30:
        verdict = "Cette personne n'est **pas anonyme**. Son identité réelle, sa localisation, et ses opinions sont facilement identifiables."
    elif anonymity_score < 60:
        verdict = "Anonymat **partiel**. Des informations personnelles significatives ont été trouvées."
    else:
        verdict = "Bon niveau d'anonymat. Peu d'informations personnelles identifiables."
    
    report += f"**Score d'anonymat: {anonymity_score}/100**\n\n{verdict}\n\n"
    
    # Conclusion
    report += "## 8. Conclusion\n\n"
    report += f"L'enquête sur `{username}` a permis d'identifier **{len(profiles)} comptes** sur différentes plateformes. "
    
    if anonymity_score < 50:
        report += "Les informations recueillies démontrent que cette personne n'est pas anonyme malgré l'utilisation de pseudonymes. "
        report += "Sa véritable identité, sa localisation, et ses opinions personnelles sont accessibles publiquement.\n\n"
    
    report += "---\n\n"
    report += f"*Ce rapport a été généré automatiquement par GHOST OSINT Engine. "
    report += f"Toutes les informations contenues sont issues de sources publiques.*\n"
    
    return report
