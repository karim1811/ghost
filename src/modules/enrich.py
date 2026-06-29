# GHOST — Enrichment Module (Client)
# Envoie les résultats du scan à un serveur d'enrichissement local (Hermes AI)
# ou fonctionne en mode standalone (version gratuite)

import json
import os
import time
import httpx
from pathlib import Path
from typing import Optional
from datetime import datetime

# ── Config ──────────────────────────────────────────────
ENRICH_SERVER_URL = os.getenv("GHOST_ENRICH_URL", "http://localhost:4567")
ENRICH_API_KEY = os.getenv("GHOST_ENRICH_KEY", "")
ENRICH_TIMEOUT = int(os.getenv("GHOST_ENRICH_TIMEOUT", "120"))
ENRICH_MODE = os.getenv("GHOST_ENRICH_MODE", "server")  # "server" or "webhook"


def enrich_results(
    target: str,
    results: list,
    mode: str = "full",
    local_images: Optional[list] = None,
) -> dict:
    """
    Envoie les résultats du scan au serveur d'enrichissement Hermes.
    
    Deux modes:
    - "server": Envoie au serveur HTTP local (ghost-enrich-server.py)
    - "file": Écrit dans pending/ pour traitement par Hermes Agent
    
    Args:
        target: pseudo ou email recherché
        résultats: liste des résultats du scan GHOST
        mode: "full" (tout enrichir) ou "quick" (essentiel seulement)
        local_images: chemins vers images locales (bannière, avatar, etc.)
    
    Returns:
        dict avec les données enrichies
    """
    payload = {
        "target": target,
        "results": results,
        "mode": mode,
        "timestamp": time.time(),
    }

    # Attacher les images locales en base64 si fournies
    images = {}
    if local_images:
        import base64
        for img_path in local_images:
            if os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    images[os.path.basename(img_path)] = base64.b64encode(f.read()).decode()
        payload["images"] = images

    # Mode fichier (défaut, plus fiable)
    if ENRICH_MODE == "file":
        return _enrich_via_file(target, payload)

    # Mode serveur HTTP
    return _enrich_via_server(payload)


def _enrich_via_file(target: str, payload: dict) -> dict:
    """Écrit la requête dans un fichier pending pour traitement par Hermes"""
    pending_dir = Path(__file__).parent.parent.parent / "pending"
    pending_dir.mkdir(exist_ok=True)

    request_id = f"ghost_{int(time.time())}"
    pending_file = pending_dir / f"{request_id}.json"

    data = {
        "id": request_id,
        "target": target,
        "results": payload["results"],
        "mode": payload["mode"],
        "images": payload.get("images", {}),
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    }
    pending_file.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")

    return {
        "success": True,
        "status": "queued",
        "request_id": request_id,
        "message": f"Enrichment queued. Hermes will process: {pending_file.name}",
        "pending_file": str(pending_file),
        "ai_analysis": {
            "status": "pending",
            "raw_analysis": f"Scan results saved to {pending_file.name}. Hermes Agent will analyze with web_search, browser, vision tools.",
        }
    }


def _enrich_via_server(payload: dict) -> dict:
    """Envoie au serveur HTTP d'enrichissement"""
    headers = {"Content-Type": "application/json"}
    if ENRICH_API_KEY:
        headers["X-GHOST-KEY"] = ENRICH_API_KEY

    try:
        with httpx.Client(timeout=ENRICH_TIMEOUT, verify=False) as client:
            r = client.post(
                f"{ENRICH_SERVER_URL}/enrich",
                json=payload,
                headers=headers,
            )
            if r.status_code == 200:
                return r.json()
            else:
                return {
                    "success": False,
                    "error": f"Server returned {r.status_code}: {r.text[:200]}",
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "error": f"Cannot connect to enrichment server at {ENRICH_SERVER_URL}",
            "fallback": "Use GHOST_ENRICH_MODE=file for local processing",
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Enrichment timed out ({ENRICH_TIMEOUT}s)",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def check_enrich_server() -> dict:
    """Vérifie si le serveur d'enrichissement est disponible"""
    try:
        with httpx.Client(timeout=5, verify=False) as client:
            r = client.get(f"{ENRICH_SERVER_URL}/health")
            if r.status_code == 200:
                data = r.json()
                return {
                    "available": True,
                    "version": data.get("version", "?"),
                    "ai_backend": data.get("ai_backend", "unknown"),
                    "capabilities": data.get("capabilities", []),
                }
    except Exception:
        pass
    return {
        "available": False,
        "message": "Enrichment server not running. Start with: ghost-enrich-server",
    }


def generate_enriched_report(target: str, scan_results: list, enrich_data: dict) -> str:
    """
    Génère un rapport enrichi combinant scan + données AI.
    Retourne le chemin du fichier markdown généré.
    """
    from datetime import datetime

    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(__file__).parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)

    # Stats du scan
    found = [r for r in scan_results if r.get("exists")]
    not_found = [r for r in scan_results if not r.get("exists") and not r.get("error")]
    errors = [r for r in scan_results if r.get("error")]

    report = f"""# 👻 GHOST Enriched Report — `{target}`

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Target:** `{target}`
**Scan:** {len(found)}/{len(scan_results)} profiles found
**Enrichment:** {'AI-enhanced' if enrich_data.get('success') else 'Not enriched'}

---

## Scan Summary

| Metric | Value |
|---|---|
| Platforms checked | {len(scan_results)} |
| Found | {len(found)} |
| Not found | {len(not_found)} |
| Errors | {len(errors)} |

"""

    # ── Enrichissement AI ──
    if enrich_data.get("success"):
        ai = enrich_data.get("ai_analysis", {})

        report += "\n## 🤖 AI Enrichment\n\n"

        # Identité
        if ai.get("identity"):
            identity = ai["identity"]
            report += "### Identity Insights\n\n"
            if identity.get("likely_names"):
                report += f"- **Possible names:** {', '.join(identity['likely_names'])}\n"
            if identity.get("likely_location"):
                report += f"- **Likely location:** {identity['likely_location']}\n"
            if identity.get("language"):
                report += f"- **Primary language:** {identity['language']}\n"
            if identity.get("interests"):
                report += f"- **Interests:** {', '.join(identity['interests'])}\n"
            report += "\n"

        # Analyse des profils trouvés
        if ai.get("platform_analysis"):
            report += "### Platform Analysis\n\n"
            for platform, analysis in ai["platform_analysis"].items():
                report += f"#### {platform}\n"
                if analysis.get("summary"):
                    report += f"{analysis['summary']}\n\n"
                if analysis.get("extracted_data"):
                    for k, v in analysis["extracted_data"].items():
                        report += f"- **{k}:** {v}\n"
                report += "\n"

        # Géolocalisation de bannière
        if ai.get("banner_analysis"):
            banner = ai["banner_analysis"]
            report += "### 🖼️ Banner Image Analysis\n\n"
            if banner.get("location"):
                report += f"- **Location identified:** {banner['location']}\n"
            if banner.get("confidence"):
                report += f"- **Confidence:** {banner['confidence']}%\n"
            if banner.get("details"):
                report += f"- **Details:** {banner['details']}\n"
            report += "\n"

        # Reverse image results
        if ai.get("reverse_image"):
            ri = ai["reverse_image"]
            report += "### 🔍 Reverse Image Search\n\n"
            if ri.get("matches"):
                report += f"- **Matches found:** {len(ri['matches'])}\n"
                for match in ri["matches"][:5]:
                    report += f"  - {match}\n"
            report += "\n"

        # Web context
        if ai.get("web_context"):
            wc = ai["web_context"]
            report += "### 🌐 Web Context\n\n"
            if wc.get("mentions"):
                report += f"**Online mentions:**\n"
                for mention in wc["mentions"][:10]:
                    report += f"- {mention}\n"
            report += "\n"

        # Social graph
        if ai.get("social_graph"):
            sg = ai["social_graph"]
            report += "### 🕸️ Social Connections\n\n"
            if sg.get("connections"):
                for conn in sg["connections"][:10]:
                    report += f"- {conn}\n"
            report += "\n"

    # ── Profils trouvés (détails) ──
    if found:
        report += "\n## 🔴 FOUND PROFILES\n\n"
        report += "| Platform | URL | Data |\n"
        report += "|---|---|---|\n"
        for r in found:
            platform = r.get("platform", "?")
            url = r.get("url", "")
            data_preview = str(r.get("data", ""))[:80].replace("\n", " ").replace("|", "\\|")
            report += f"| **{platform}** | {url} | {data_preview} |\n"

        report += "\n### 📊 Details\n\n"
        for r in found:
            platform = r.get("platform", "?")
            report += f"\n#### {platform}\n"
            report += f"- URL: {r.get('url', '')}\n"
            if r.get("data"):
                for key, val in r["data"].items():
                    if val and val != "N/A":
                        report += f"- **{key}:** {val}\n"
            report += "\n"

    # ── Verdict ──
    report += "\n---\n\n## 💀 Verdict\n\n"
    if enrich_data.get("success") and enrich_data.get("ai_analysis", {}).get("verdict"):
        report += enrich_data["ai_analysis"]["verdict"] + "\n"
    elif len(found) > 0:
        report += f"**{len(found)} profile(s) linked to `{target}`. Anonymity is not absolute.**\n"
    else:
        report += f"No profiles found on {len(scan_results)} platforms. The pseudonym `{target}` is rarely reused.\n"

    report += f"\n---\n*Generated by GHOST v0.2 (Enriched)*\n"

    # Sauvegarder
    filepath = report_dir / f"ghost_enriched_{target}_{date_str}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return str(filepath)
