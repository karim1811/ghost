#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
# GHOST REST API
# API HTTP pour scans OSINT programmables
# ──────────────────────────────────────────────────────────
#
# Usage:
#   python ghost-api.py
#   → API sur http://localhost:8000
#
# Endpoints:
#   POST /scan        — Lancer un scan
#   GET  /scan/{id}   — Statut du scan
#   GET  /reports     — Liste des rapports
#   GET  /report/{id} — Contenu dun rapport
#   GET  /health      ─ Health check
# ──────────────────────────────────────────────────────────

import os
import sys
import json
import uuid
import subprocess
import time
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = os.getenv("GHOST_API_HOST", "0.0.0.0")
PORT = int(os.getenv("GHOST_API_PORT", "8000"))
_API_KEY_ENV = "GHOST_API_KEY"
API_KEY = os.getenv(_API_KEY_ENV, "")
_ENRICH_URL_DEFAULT = "http://localhost:4567"
ENRICH_URL = os.getenv("GHOST_ENRICH_URL", _ENRICH_URL_DEFAULT)

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
REPORTS_DIR = ROOT / "src" / "reports"
jobs = {}


class GhostAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {args[0]}")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _check_auth(self):
        if not API_KEY:
            return True
        return self.headers.get("X-API-KEY", "") == API_KEY

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "version": "0.2", "timestamp": time.time()})
        elif self.path == "/reports":
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            reports = []
            if REPORTS_DIR.exists():
                for r in sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
                    reports.append({"filename": r.name, "size": r.stat().st_size,
                                    "created": datetime.fromtimestamp(r.stat().st_mtime).isoformat()})
            self._send_json({"reports": reports})
        elif self.path.startswith("/report/"):
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            fn = self.path.split("/report/")[-1]
            fp = REPORTS_DIR / fn
            if fp.exists():
                self._send_json({"filename": fn, "content": fp.read_text(encoding="utf-8")})
            else:
                self._send_json({"error": "Not found"}, 404)
        elif self.path.startswith("/scan/"):
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            jid = self.path.split("/scan/")[-1]
            if jid in jobs:
                self._send_json(jobs[jid])
            else:
                self._send_json({"error": "Job not found"}, 404)
        else:
            self._send_json({"service": "GHOST API v0.2", "endpoints": ["/scan", "/scan/{id}", "/reports", "/report/{fn}", "/health"]})

    def do_POST(self):
        if self.path == "/scan":
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            cl = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(cl))
            target = body.get("target", "").strip()
            if not target:
                return self._send_json({"error": "No target"}, 400)
            photos = body.get("photos", [])
            jid = str(uuid.uuid4())[:8]
            job = {"id": jid, "target": target, "status": "running",
                   "deep": body.get("deep", False), "enrich": body.get("enrich", True),
                   "photos": len(photos),
                   "created_at": datetime.now().isoformat(), "report_path": None, "error": None}
            jobs[jid] = job
            t = threading.Thread(target=self._run, args=(jid, target, job["deep"], job["enrich"], photos))
            t.daemon = True
            t.start()
            self._send_json({"job_id": jid, "status": "running", "target": target})

        elif self.path == "/face-search":
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            cl = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(cl))
            photos = body.get("photos", [])
            if not photos:
                return self._send_json({"error": "No photos provided"}, 400)
            
            # Save photos and run face analysis
            import base64
            photo_paths = []
            for i, photo_b64 in enumerate(photos[:2]):
                photo_data = base64.b64decode(photo_b64.split(",")[1] if "," in photo_b64 else photo_b64)
                photo_path = ROOT / "pending" / f"face_{int(time.time())}_{i}.jpg"
                photo_path.parent.mkdir(exist_ok=True)
                with open(photo_path, "wb") as f:
                    f.write(photo_data)
                photo_paths.append(str(photo_path))

            # Run face analysis
            jid = str(uuid.uuid4())[:8]
            job = {"id": jid, "target": "face-search", "status": "running",
                   "photos": len(photo_paths),
                   "created_at": datetime.now().isoformat(), "result": None, "error": None}
            jobs[jid] = job
            t = threading.Thread(target=self._run_face_search, args=(jid, photo_paths))
            t.daemon = True
            t.start()
            self._send_json({"job_id": jid, "status": "running", "photos": len(photo_paths)})

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-KEY")
        self.end_headers()

    def _run(self, jid, target, deep, enrich, photos=None):
        try:
            cmd = [sys.executable, str(SRC_DIR / "main.py"), "--pseudo", target, "--export", "markdown"]
            if deep: cmd.append("--deep")
            if enrich: cmd.append("--enrich")
            if photos:
                # Save photos temporarily and pass paths
                photo_paths = []
                import base64
                for i, photo_b64 in enumerate(photos[:2]):
                    photo_data = base64.b64decode(photo_b64.split(",")[1] if "," in photo_b64 else photo_b64)
                    photo_path = ROOT / "pending" / f"scan_{jid}_{i}.jpg"
                    photo_path.parent.mkdir(exist_ok=True)
                    with open(photo_path, "wb") as f:
                        f.write(photo_data)
                    photo_paths.append(str(photo_path))
                cmd.extend(["--images"] + photo_paths)
            env = os.environ.copy(); env["GHOST_ENRICH_MODE"] = "file"
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT), env=env)
            j = jobs[jid]
            if r.returncode == 0:
                for line in r.stdout.split("\n"):
                    if "Full report:" in line:
                        j["report_path"] = line.split("Full report:")[1].strip(); break
                j["status"] = "completed"
            else:
                j["status"] = "failed"; j["error"] = (r.stderr or "error")[:500]
            j["completed_at"] = datetime.now().isoformat()
        except subprocess.TimeoutExpired:
            jobs[jid].update({"status": "timeout", "error": "5min timeout"})
        except Exception as e:
            jobs[jid].update({"status": "error", "error": str(e)[:500]})

    def _run_face_search(self, jid, photo_paths):
        """Run face recognition analysis on uploaded photos"""
        try:
            sys.path.insert(0, str(SRC_DIR / "modules"))
            from face_recognition import full_face_analysis
            
            results = []
            for photo_path in photo_paths:
                analysis = full_face_analysis(image_path=photo_path)
                results.append(analysis)
            
            jobs[jid]["status"] = "completed"
            jobs[jid]["result"] = results
            jobs[jid]["completed_at"] = datetime.now().isoformat()
        except Exception as e:
            jobs[jid]["status"] = "failed"
            jobs[jid]["error"] = str(e)[:500]


def main():
    print(f"""
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   REST API v0.2 | OSINT as a Service
""")
    server = HTTPServer((HOST, PORT), GhostAPIHandler)
    print(f"  API running on http://{HOST}:{PORT}")
    auth_status = 'API key required' if API_KEY else 'Open'
    print(f"  Auth: {auth_status}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  API stopped.")


if __name__ == "__main__":
    main()
