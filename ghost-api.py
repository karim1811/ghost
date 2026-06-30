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
import re
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
        # API is open — auth optional
        # To secure: set GHOST_API_KEY and send X-API-KEY header
        return True

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
        elif self.path == "/purge":
            # Clear all completed jobs and reports
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            
            # Remove old jobs
            removed_jobs = 0
            for jid in list(jobs.keys()):
                job = jobs[jid]
                if job.get("status") in ("completed", "failed", "error"):
                    # Remove HTML file if exists
                    html_path = job.get("html_path")
                    if html_path:
                        try:
                            Path(html_path).unlink(missing_ok=True)
                        except:
                            pass
                    del jobs[jid]
                    removed_jobs += 1
            
            # Remove old report files
            reports_dir = ROOT / "reports"
            removed_files = 0
            if reports_dir.exists():
                for f in reports_dir.glob("*.html"):
                    try:
                        f.unlink()
                        removed_files += 1
                    except:
                        pass
            
            self._send_json({
                "success": True,
                "removed_jobs": removed_jobs,
                "removed_files": removed_files,
            })
        elif self.path.startswith("/dossier/"):
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            if jid in jobs and jobs[jid].get("html_path"):
                html_path = Path(jobs[jid]["html_path"])
                if html_path.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html_path.read_bytes())
                else:
                    self._send_json({"error": "HTML file not found"}, 404)
            else:
                self._send_json({"error": "Job not found or not completed"}, 404)
        elif self.path.startswith("/scan/"):
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            jid = self.path.split("/scan/")[-1]
            if jid in jobs:
                self._send_json(jobs[jid])
            else:
                self._send_json({"error": "Job not found"}, 404)
        else:
            self._send_json({"service": "GHOST API v0.3", "endpoints": ["/scan", "/scan/{id}", "/dossier", "/dossier/{id}", "/reports", "/report/{fn}", "/health"]})

    def do_POST(self):
        if self.path == "/scan":
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            cl = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(cl))
            target = body.get("target", "").strip()
            url = body.get("url", "").strip()
            
            # Support both target (username) and url (profile link)
            if not target and not url:
                return self._send_json({"error": "No target or url provided"}, 400)
            
            # If URL provided, extract username from it
            if url and not target:
                target = self._extract_username_from_url(url)
                if not target:
                    return self._send_json({"error": "Could not extract username from URL"}, 400)
            
            photos = body.get("photos", [])
            jid = str(uuid.uuid4())[:8]
            job = {"id": jid, "target": target, "url": url or None,
                   "status": "running",
                   "deep": body.get("deep", False), "enrich": body.get("enrich", True),
                   "photos": len(photos),
                   "created_at": datetime.now().isoformat(), "report_path": None, "error": None}
            jobs[jid] = job
            t = threading.Thread(target=self._run, args=(jid, target, job["deep"], job["enrich"], photos, url))
            t.daemon = True
            t.start()
            self._send_json({"job_id": jid, "status": "running", "target": target})

        elif self.path == "/dossier":
            # Generate full identity dossier
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            cl = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(cl))
            target = body.get("target", "").strip()
            url = body.get("url", "").strip()
            
            # Support both target and url
            if not target and not url:
                return self._send_json({"error": "No target or url provided"}, 400)
            
            if url and not target:
                target = self._extract_username_from_url(url)
                if not target:
                    return self._send_json({"error": "Could not extract username from URL"}, 400)
            
            jid = str(uuid.uuid4())[:8]
            job = {"id": jid, "target": target, "status": "running",
                   "created_at": datetime.now().isoformat(), "html_path": None, "error": None}
            jobs[jid] = job
            t = threading.Thread(target=self._run_dossier, args=(jid, target))
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

        elif self.path == "/dossier":
            # Generate identity dossier (HTML report)
            if not self._check_auth():
                return self._send_json({"error": "Invalid API key"}, 401)
            cl = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(cl))
            target = body.get("target", "").strip()
            if not target:
                return self._send_json({"error": "No target"}, 400)
            
            # Run dossier generation in background
            jid = str(uuid.uuid4())[:8]
            job = {"id": jid, "target": target, "status": "running",
                   "created_at": datetime.now().isoformat(), "html_path": None, "error": None}
            jobs[jid] = job
            t = threading.Thread(target=self._run_dossier, args=(jid, target))
            t.daemon = True
            t.start()
            self._send_json({"job_id": jid, "status": "running", "target": target})

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-KEY")
        self.end_headers()

    def _extract_username_from_url(self, url):
        """Extract username from various social media URLs"""
        import re
        url = url.strip().rstrip("/")
        
        patterns = [
            # Twitter/X
            r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
            # Instagram
            r'instagram\.com/([a-zA-Z0-9_.]+)',
            # TikTok
            r'tiktok\.com/@([a-zA-Z0-9_.]+)',
            # GitHub
            r'github\.com/([a-zA-Z0-9-]+)',
            # Reddit
            r'reddit\.com/user/([a-zA-Z0-9_-]+)',
            # YouTube
            r'youtube\.com/(?:c/|channel/|@)([a-zA-Z0-9_-]+)',
            # Twitch
            r'twitch\.tv/([a-zA-Z0-9_]+)',
            # Pinterest
            r'pinterest\.com/([a-zA-Z0-9_]+)',
            # Telegram
            r't\.me/([a-zA-Z0-9_]+)',
            # Facebook
            r'facebook\.com/([a-zA-Z0-9.]+)',
            # LinkedIn
            r'linkedin\.com/in/([a-zA-Z0-9-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1)
                # Filter out common non-username paths
                if username not in ('settings', 'home', 'explore', 'reels', 'p', 'photo'):
                    return username
        return None

    def _run(self, jid, target, deep, enrich, photos=None, url=None):
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


    def _run_dossier(self, jid, target):
        """Generate complete identity dossier — simplified for Render"""
        try:
            sys.path.insert(0, str(SRC_DIR / "modules"))
            from dossier import deep_scrape_profile, generate_dossier
            from advanced_osint import extract_photos_from_profile, extract_personal_info
            
            jobs[jid]["status_message"] = "Phase 1: Scraping social media..."
            
            # Phase 1: Scrape main platforms only (fast)
            platforms = ["twitter", "instagram", "github", "reddit", "tiktok"]
            profiles = []
            
            for platform in platforms:
                try:
                    profile = deep_scrape_profile(platform, target)
                    if profile and not profile.get("error"):
                        profiles.append(profile)
                except Exception:
                    continue
            
            jobs[jid]["status_message"] = f"Phase 2: Extracting photos & personal info..."
            
            # Phase 2: Extract photos and personal info (no external APIs)
            all_photos = []
            all_text = ""
            
            for profile in profiles:
                platform = profile.get("platform", "").lower()
                
                # Extract photos
                try:
                    photos = extract_photos_from_profile(platform, target)
                    all_photos.extend(photos)
                except:
                    pass
                
                # Collect text for personal info extraction
                for key in ["bio", "recent_tweets", "recent_comments", "recent_captions"]:
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
            
            # Extract personal info from collected text
            personal_info = extract_personal_info(all_text)
            
            # Build advanced data structure
            advanced = {
                "photos": all_photos,
                "personal_info": personal_info,
                "google_dorks": {"findings": self._generate_dorks(target, profiles)},
                "wayback": {"snapshots": []},
            }
            
            jobs[jid]["status_message"] = "Phase 3: Generating dossier..."
            
            # Phase 3: Generate HTML dossier
            html = generate_dossier(target, profiles, advanced, [])
            
            # Save
            dossier_dir = ROOT / "reports"
            dossier_dir.mkdir(exist_ok=True)
            safe_target = re.sub(r'[^\w\-.]', '_', target)[:50]
            html_path = dossier_dir / f"dossier_{safe_target}_{int(time.time())}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            
            jobs[jid]["status"] = "completed"
            jobs[jid]["html_path"] = str(html_path)
            jobs[jid]["platforms_found"] = len(profiles)
            jobs[jid]["photos_found"] = len(all_photos)
            jobs[jid]["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            jobs[jid]["status"] = "failed"
            jobs[jid]["error"] = str(e)[:500]
    
    def _generate_dorks(self, target, profiles):
        """Generate Google Dork search URLs"""
        dorks = []
        
        # From found names
        names = set()
        for p in profiles:
            for key in ["display_name", "full_name", "name"]:
                if p.get(key):
                    names.add(p[key].strip())
        
        dork_queries = [
            f'"{target}" email OR email',
            f'"{target}" phone OR telephone',
            f'"{target}" site:linkedin.com',
            f'"{target}" site:facebook.com',
            f'"{target}" site:instagram.com',
        ]
        
        for name in names:
            dork_queries.append(f'"{name}" email')
            dork_queries.append(f'"{name}" site:linkedin.com')
        
        for query in dork_queries[:15]:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            dorks.append({"query": query, "search_url": search_url})
        
        return dorks


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
