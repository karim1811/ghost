#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
# GHOST Telegram Bot
# Lance des scans OSINT depuis Telegram
# ──────────────────────────────────────────────────────────
#
# Usage:
#   export GHOST_BOT_TOKEN=your-telegram-bot-token
#   python ghost-bot.py
#
# Deploy:
#   → Railway / Render (worker process)
#   → Vercel (serverless webhook)
# ──────────────────────────────────────────────────────────

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

import httpx

# ── Config ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("GHOST_BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: Set GHOST_BOT_TOKEN environment variable")
    sys.exit(1)

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
REPORTS_DIR = ROOT / "src" / "reports"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Rate Limiting ───────────────────────────────────────
user_cooldowns = {}  # user_id -> last_scan_time
COOLDOWN_SECONDS = 30  # minimum between scans
MAX_SCAN_TIME = 180  # timeout

# ── Commands ────────────────────────────────────────────

def send_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Envoie un message Telegram"""
    try:
        httpx.post(
            f"{API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
    except Exception as e:
        print(f"Send message failed: {e}")

def send_document(chat_id: int, filepath: Path, caption: str = ""):
    """Envoie un fichier (rapport)"""
    try:
        with open(filepath, "rb") as f:
            httpx.post(
                f"{API_URL}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (filepath.name, f, "text/markdown")},
                timeout=60,
            )
    except Exception as e:
        print(f"Send document failed: {e}")

def run_scan(target: str, deep: bool = False, enrich: bool = False) -> tuple:
    """Lance un scan GHOST et retourne (stdout, report_path)"""
    cmd = [sys.executable, str(SRC_DIR / "main.py"), "--pseudo", target, "--export", "markdown"]
    if deep:
        cmd.append("--deep")
    if enrich:
        cmd.append("--enrich")

    env = os.environ.copy()
    env["GHOST_ENRICH_MODE"] = "file"

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=MAX_SCAN_TIME,
        cwd=str(ROOT),
        env=env,
    )

    # Extraire le chemin du rapport
    report_path = None
    for line in result.stdout.split("\n"):
        if "Full report:" in line:
            report_path = line.split("Full report:")[1].strip()
            break

    return result.stdout, report_path

def handle_start(chat_id: int):
    """Commande /start"""
    text = """
*GHOST OSINT Bot* 👻

Commands:
/scan <username> — Scan a profile
/deep <username> — Deep scan + enrichment
/reports — List recent reports
/help — Show help

Example:
/scan kijebede
/deep kijebede
    """
    send_message(chat_id, text)

def handle_help(chat_id: int):
    """Commande /help"""
    text = """
*GHOST Bot Commands*

• /scan <username> — Quick scan (69 platforms)
• /deep <username> — Full scan + AI enrichment
• /reports — Show last 5 reports
• /status — Bot status

*Rate limit:* 30 seconds between scans
*Timeout:* 3 minutes max per scan

*Pro tips:*
- Use /deep for complete analysis
- Reports are sent as files
- AI enrichment adds geolocation, social graph, identity
    """
    send_message(chat_id, text)

def handle_scan(chat_id: int, target: str, deep: bool = False):
    """Commande /scan ou /deep"""
    if not target:
        send_message(chat_id, "Usage: `/scan <username>` or `/deep <username>`")
        return

    # Sanitize target
    target = target.strip().replace("@", "").replace(" ", "")
    if len(target) < 2 or len(target) > 50:
        send_message(chat_id, "Invalid username (2-50 characters)")
        return

    # Rate limit
    now = time.time()
    if chat_id in user_cooldowns:
        elapsed = now - user_cooldowns[chat_id]
        if elapsed < COOLDOWN_SECONDS:
            wait = int(COOLDOWN_SECONDS - elapsed)
            send_message(chat_id, f"⏳ Wait {wait}s before next scan")
            return
    user_cooldowns[chat_id] = now

    # Confirmation
    mode = "DEEP + AI" if deep else "QUICK"
    msg = f"🔍 Scanning `{target}`... (mode: {mode})"
    send_message(chat_id, msg)

    # Run scan
    try:
        stdout, report_path = run_scan(target, deep=deep, enrich=deep)

        # Summary
        found = 0
        total = 0
        for line in stdout.split("\n"):
            if "Profiles found:" in line:
                parts = line.split(":")[-1].strip().split("/")
                if len(parts) == 2:
                    found = int(parts[0])
                    total = int(parts[1])

        time_taken = "?"
        for line in stdout.split("\n"):
            if "Total time:" in line:
                time_taken = line.split(":")[-1].strip()

        summary = f"""
✅ *Scan Complete!*

Target: `{target}`
Found: {found}/{total} platforms
Time: {time_taken}
        """
        send_message(chat_id, summary)

        # Send report file
        if report_path and Path(report_path).exists():
            send_document(
                chat_id,
                Path(report_path),
                caption=f"👻 GHOST Report — {target}"
            )
        else:
            send_message(chat_id, "Report file not found. Check /reports")

    except subprocess.TimeoutExpired:
        send_message(chat_id, "❌ Scan timed out (3 min limit)")
    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)[:200]}")

def handle_reports(chat_id: int):
    """Commande /reports"""
    if not REPORTS_DIR.exists():
        send_message(chat_id, "No reports yet.")
        return

    reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]

    if not reports:
        send_message(chat_id, "No reports yet.")
        return

    text = "*Recent Reports:*\n\n"
    for r in reports:
        # Parse target from filename
        name = r.stem.replace("ghost_enriched_", "").replace("ghost_", "")
        date = datetime.fromtimestamp(r.stat().st_mtime).strftime("%m/%d %H:%M")
        size = r.stat().st_size // 1024
        text += f"• `{name}` — {date} ({size}KB)\n"

    send_message(chat_id, text)

def handle_status(chat_id: int):
    """Commande /status"""
    import platform
    text = f"""
*GHOST Bot Status* ✅

Version: 0.2
Python: {platform.python_version()}
Platform: {platform.system()}
Uptime: running
Reports: {len(list(REPORTS_DIR.glob('*.md'))) if REPORTS_DIR.exists() else 0}
    """
    send_message(chat_id, text)

# ── Main Loop (polling) ────────────────────────────────

def main():
    print(f"""
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   Telegram Bot v0.2
""")

    print(f"  🤖 Bot token: ...{BOT_TOKEN[-6:]}")
    print(f"  📡 Polling for updates...\n")

    offset = 0

    while True:
        try:
            resp = httpx.get(
                f"{API_URL}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=60,
            )

            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1

                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")

                    if not text or not chat_id:
                        continue

                    print(f"  [{chat_id}] {text}")

                    # Route commands
                    if text.startswith("/start"):
                        handle_start(chat_id)
                    elif text.startswith("/help"):
                        handle_help(chat_id)
                    elif text.startswith("/deep "):
                        target = text[6:].strip()
                        handle_scan(chat_id, target, deep=True)
                    elif text.startswith("/scan "):
                        target = text[6:].strip()
                        handle_scan(chat_id, target, deep=False)
                    elif text == "/reports":
                        handle_reports(chat_id)
                    elif text == "/status":
                        handle_status(chat_id)
                    else:
                        send_message(chat_id, "Unknown command. Use /help")

        except httpx.TimeoutException:
            continue
        except KeyboardInterrupt:
            print("\n  👋 Bot stopped.")
            break
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
