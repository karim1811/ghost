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
        Enrichment via Hermes Agent.
        Tries OpenRouter API first (if key available), then falls back to
        writing a pending file for the local Hermes agent to process.
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            result = self._call_openrouter(api_key, prompt)
            if result:
                return result

        # Fallback: write pending file for local Hermes to process
        return self._write_pending(prompt)

    def _call_openrouter(self, api_key: str, prompt: str) -> dict:
        """Call OpenRouter API for enrichment"""
        try:
            import httpx

            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("GHOST_AI_MODEL", "google/gemini-2.0-flash-001"),
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are GHOST Enrichment AI. Analyze OSINT scan results and return ONLY valid JSON with these fields: identity (likely_names, likely_location, language, interests), platform_analysis, web_context (mentions), social_graph (connections), verdict. No markdown, no explanation."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000,
                },
                timeout=60,
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                try:
                    return json.loads(content.strip())
                except json.JSONDecodeError:
                    return {"raw_analysis": content[:3000]}
        except Exception as e:
            print(f"     OpenRouter failed: {e}")
        return None

    def _write_pending(self, prompt: str) -> dict:
        """
        Writes enrichment request to pending file for local Hermes agent.
        Returns immediately with queued status — Hermes processes it asynchronously.
        """
        try:
            pending_dir = Path(__file__).parent / "pending"
            pending_dir.mkdir(exist_ok=True)

            request_id = f"ghost_{int(time.time())}"
            pending_file = pending_dir / f"{request_id}.json"

            data = {
                "id": request_id,
                "prompt": prompt,
                "created_at": datetime.now().isoformat(),
                "status": "pending",
            }
            pending_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            print(f"     → Queued: {pending_file.name}")
            print(f"     → Hermes will process it. Check: ghost --check-pending")

            return {
                "status": "queued",
                "request_id": request_id,
                "message": "Enrichment queued for AI processing. Hermes will analyze with web_search, browser, vision.",
                "pending_file": str(pending_file),
            }

        except Exception as e:
            print(f"     Write pending failed: {e}")
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
