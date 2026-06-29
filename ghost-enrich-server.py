#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
# GHOST Enrichment Server
# Serveur HTTP local qui reçoit les requêtes de GHOST
# et délègue l'enrichissement à Hermes Agent
# ──────────────────────────────────────────────────────────
#
# Usage:
#   python ghost-enrich-server.py          # démarre sur localhost:4567
#   GHOST_ENRICH_KEY=secret python ghost-enrich-server.py
#
# Déploiement production:
#   → Vercel Serverless Functions (voir docs/deploy.md)
#   → Railway / Render (voir docs/deploy.md)
# ──────────────────────────────────────────────────────────

import os
import sys
import json
import time
import hashlib
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────
HOST = os.getenv("GHOST_ENRICH_HOST", "0.0.0.0")
PORT = int(os.getenv("GHOST_ENRICH_PORT", "4567"))
API_KEY = os.getenv("GHOST_ENRICH_KEY", "")
HERMES_PATH = os.getenv("HERMES_PATH", "hermes")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max (images)

# ── Version ─────────────────────────────────────────────
VERSION = "0.2.0"
CAPABILITIES = [
    "identity_analysis",
    "banner_geolocation",
    "reverse_image_search",
    "spotify_analysis",
    "twitter_context",
    "web_mentions",
    "social_graph",
    "behavioral_fingerprint",
]


class GhostEnrichHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour les requêtes d'enrichissement GHOST"""

    def log_message(self, format, *args):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"  [{timestamp}] {args[0]}")

    def _send_json(self, data: dict, status: int = 200):
        """Envoie une réponse JSON"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _check_auth(self) -> bool:
        """Vérifie la clé API si configurée"""
        if not API_KEY:
            return True
        key = self.headers.get("X-GHOST-KEY", "")
        return key == API_KEY

    def do_GET(self):
        if self.path == "/health":
            self._send_json({
                "status": "ok",
                "version": VERSION,
                "ai_backend": "hermes",
                "capabilities": CAPABILITIES,
                "timestamp": time.time(),
            })
        elif self.path == "/":
            self._send_json({
                "service": "GHOST Enrichment Server",
                "version": VERSION,
                "endpoints": {
                    "POST /enrich": "Submit scan results for AI enrichment",
                    "GET /health": "Server health check",
                },
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/enrich":
            if not self._check_auth():
                self._send_json({"error": "Invalid API key"}, 401)
                return

            # Lire le body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > MAX_CONTENT_LENGTH:
                self._send_json({"error": "Payload too large"}, 413)
                return

            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            # Traiter la requête
            result = self._process_enrichment(payload)
            self._send_json(result)
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-GHOST-KEY")
        self.end_headers()

    def _process_enrichment(self, payload: dict) -> dict:
        """
        Traite une requête d'enrichissement.
        Délègue à Hermes Agent pour l'analyse AI.
        """
        target = payload.get("target", "")
        results = payload.get("results", [])
        mode = payload.get("mode", "full")
        images = payload.get("images", {})

        if not target:
            return {"success": False, "error": "No target specified"}

        print(f"\n  🔍 Enriching: {target}")
        print(f"     Mode: {mode} | Results: {len(results)} | Images: {len(images)}")

        # ── Déléguer à Hermes Agent ──
        try:
            # Construire le prompt pour Hermes
            prompt = self._build_hermes_prompt(target, results, mode, images)

            # Appeler Hermes en mode one-shot
            hermes_result = self._call_hermes(prompt, images)

            if hermes_result:
                return {
                    "success": True,
                    "target": target,
                    "ai_analysis": hermes_result,
                    "enriched_at": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": "Hermes Agent returned no result",
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Enrichment failed: {str(e)}",
            }

    def _build_hermes_prompt(self, target: str, results: list, mode: str, images: dict) -> str:
        """Construit le prompt à envoyer à Hermes Agent"""
        found = [r for r in results if r.get("exists")]
        platforms = ", ".join([r.get("platform", "?") for r in found[:10]])

        prompt = f"""You are GHOST Enrichment AI. Analyze these OSINT scan results and provide enrichment.

TARGET: {target}
MODE: {mode}
PLATFORMS FOUND: {platforms}
TOTAL PROFILES: {len(found)}

SCAN RESULTS (JSON):
{json.dumps(found[:20], ensure_ascii=False, default=str)[:4000]}

IMAGES ATTACHED: {list(images.keys()) if images else "None"}

Provide a JSON response with these fields:
- "identity": {{"likely_names": [...], "likely_location": "...", "language": "...", "interests": [...]}}
- "platform_analysis": {{"platform_name": {{"summary": "...", "extracted_data": {{...}}}}}}
- "banner_analysis": {{"location": "...", "confidence": 0-100, "details": "..."}} (if banner image)
- "reverse_image": {{"matches": [...]}} (if images provided)
- "web_context": {{"mentions": [...]}}
- "social_graph": {{"connections": [...]}}
- "verdict": "one sentence conclusion"

Return ONLY valid JSON, no markdown, no explanation."""

        return prompt

    def _call_hermes(self, prompt: str, images: dict) -> dict:
        """
        Appelle Hermes Agent en mode one-shot.
        Utilise `hermes chat -q` pour une réponse unique.
        """
        try:
            # Écrire le prompt dans un fichier temporaire
            tmp_dir = Path(__file__).parent / ".tmp"
            tmp_dir.mkdir(exist_ok=True)
            prompt_file = tmp_dir / "hermes_prompt.txt"
            prompt_file.write_text(prompt, encoding="utf-8")

            # Appeler Hermes
            cmd = [
                HERMES_PATH, "chat",
                "-q", prompt,
                "--toolsets", "web,browser,vision,search,file",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(Path(__file__).parent.parent),
            )

            if result.returncode == 0:
                # Essayer de parser la réponse comme JSON
                output = result.stdout.strip()
                # Extraire le JSON du markdown si nécessaire
                if "```json" in output:
                    output = output.split("```json")[1].split("```")[0]
                elif "```" in output:
                    output = output.split("```")[1].split("```")[0]

                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    # Retourner la réponse brute
                    return {"raw_analysis": output[:2000]}
            else:
                print(f"     Hermes error: {result.stderr[:200]}")
                return None

        except subprocess.TimeoutExpired:
            print("     Hermes timeout")
            return None
        except FileNotFoundError:
            print(f"     Hermes not found at: {HERMES_PATH}")
            return None
        except Exception as e:
            print(f"     Hermes call failed: {e}")
            return None


def main():
    print(f"""
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   Enrichment Server v{VERSION}
   AI-Powered OSINT Enhancement
""")

    server = HTTPServer((HOST, PORT), GhostEnrichHandler)
    print(f"  🚀 Server running on http://{HOST}:{PORT}")
    key_status = 'Configured' if API_KEY else 'None (open)'
    print(f"  🔑 API Key: {key_status}")
    print(f"  🤖 Hermes: {HERMES_PATH}")
    print(f"  📡 Capabilities: {', '.join(CAPABILITIES[:4])}...")
    print(f"\n  Ready for enrichment requests. Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  👋 Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
