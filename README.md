# 👻 GHOST v0.2 — AI-Enhanced OSINT Engine

```
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   OSINT Engine v0.2 | No One Is Invisible
```

**GitHub:** [karim1811/ghost](https://github.com/karim1811/ghost)

---

## 🎯 What is GHOST?

GHOST (Global Heuristic OSINT Search Tool) is an AI-powered investigation engine that reveals anonymous online profiles. Scan 700+ platforms, enrich with AI (geolocation, identity resolution, social graph), and generate professional reports.

**Use case:** When anonymous accounts insult/harass, show them they're NOT untraceable.

---

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/karim1811/ghost.git
cd ghost
pip install -r requirements.txt

# Basic scan (FREE)
python src/main.py --pseudo TARGET

# Deep scan + AI enrichment (PRO)
python src/main.py --pseudo TARGET --deep --enrich
```

---

## 📦 Components

| Component | File | Port | Purpose |
|-----------|------|------|---------|
| CLI Scanner | `src/main.py` | — | Core scanning engine |
| Dashboard | `dashboard.py` | 8501 | Web UI (Streamlit) |
| Telegram Bot | `ghost-bot.py` | — | Remote scanning via Telegram |
| REST API | `ghost-api.py` | 8000 | Programmatic access |
| Enrichment Server | `ghost-enrich-server.py` | 4567 | AI backend bridge |
| Credits System | `credits.py` | — | Monetization |

---

## 🖥️ Dashboard (Web UI)

```bash
streamlit run dashboard.py
# → http://localhost:8501
```

Features:
- Launch scans from browser
- View reports with markdown rendering
- Browse scan history
- Export reports

**Deploy to Streamlit Cloud (free):**
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → Select `dashboard.py`
4. Deploy 🎉

---

## 🤖 Telegram Bot

```bash
export GHOST_BOT_TOKEN=your-bot-token-here
python ghost-bot.py
```

Commands:
- `/scan USERNAME` — Quick scan
- `/deep USERNAME` — Full scan + AI enrichment
- `/reports` — List recent reports
- `/status` — Bot status

**Get a token:** Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`

---

## 🌐 REST API

```bash
python ghost-api.py
# → http://localhost:8000
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scan` | Start a scan |
| `GET` | `/scan/{id}` | Check scan status |
| `GET` | `/reports` | List all reports |
| `GET` | `/report/{filename}` | Get report content |
| `GET` | `/health` | Health check |

### Example

```bash
# Start a scan
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "kijebede", "deep": true, "enrich": true}'

# Check status
curl http://localhost:8000/scan/abc12345

# List reports
curl http://localhost:8000/reports
```

---

## 💰 Credits System (Monetization)

| Plan | Price | Scans |
|------|-------|-------|
| Free | 0€ | 3/day |
| Starter | 4.99€ | 10 scans |
| Pro | 19.99€ | 50 scans |
| Unlimited | 49.99€/mo | ∞ |

```python
from credits import CreditsManager
cm = CreditsManager()
cm.add_credits("user123", 10, "purchase")
cm.deduct_credits("user123", deep=True)
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     GHOST v0.2 Ecosystem                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Telegram │  │Dashboard │  │REST API  │  │CLI       │ │
│  │Bot      │  │Streamlit │  │FastAPI   │  │main.py   │ │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │            │             │              │        │
│       └────────────┴──────┬──────┴──────────────┘        │
│                           │                              │
│                    ┌──────┴──────┐                       │
│                    │  Scanner    │                       │
│                    │  Engine     │                       │
│                    │  (69+ sites)│                       │
│                    └──────┬──────┘                       │
│                           │                              │
│                    ┌──────┴──────┐                       │
│                    │  Enrichment │                       │
│                    │  Module     │                       │
│                    └──────┬──────┘                       │
│                           │                              │
│              ┌────────────┼────────────┐                 │
│              │            │            │                 │
│         ┌────┴────┐  ┌────┴────┐  ┌───┴────┐           │
│         │Hermes   │  │OpenRouter│  │Pending │           │
│         │Agent    │  │API       │  │Files   │           │
│         │(local)  │  │(cloud)   │  │(async) │           │
│         └─────────┘  └─────────┘  └────────┘           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🔧 CLI Reference

```bash
# Basic scan
python src/main.py --pseudo USERNAME

# Deep scan (Keybase, paste dumps)
python src/main.py --pseudo USERNAME --deep

# AI enrichment
python src/main.py --pseudo USERNAME --enrich

# WhatsMyName (700+ sites)
python src/main.py --pseudo USERNAME --whatsmyname

# Identity analysis
python src/main.py --pseudo USERNAME --identity

# Email investigation
python src/main.py --email EMAIL@DOMAIN.COM

# Reverse image search
python src/main.py --image photo.jpg

# Compare faces
python src/main.py --compare photo1.jpg photo2.jpg

# Export as JSON
python src/main.py --pseudo USERNAME --export json

# Check enrichment server
python src/main.py --check-enrich
```

---

## 📁 Project Structure

```
ghost/
├── src/
│   ├── main.py                  # CLI entry point
│   └── modules/
│       ├── platforms.py         # 69+ platform definitions
│       ├── http_utils.py        # HTTP helpers
│       ├── specialized.py       # GitHub, Reddit, Steam, HN
│       ├── leaks.py             # Gravatar, Keybase, Epieos
│       ├── whatsmyname.py       # 700+ sites
│       ├── reverse_image.py     # Reverse image search
│       ├── face_compare.py      # Face comparison
│       ├── social_graph.py      # Cross-platform identity
│       ├── detection_patterns.py
│       ├── report.py            # Standard report generator
│       └── enrich.py            # AI enrichment client
├── dashboard.py                 # Streamlit web UI
├── ghost-bot.py                 # Telegram bot
├── ghost-api.py                 # REST API
├── ghost-enrich-server.py       # Enrichment server
├── credits.py                   # Credits/billing system
├── requirements.txt
├── reports/                     # Generated reports
└── README.md
```

---

## 🛣️ Roadmap

- [x] v0.1 — Basic scanner (69 platforms)
- [x] v0.2 — AI enrichment + Dashboard + Bot + API + Credits
- [ ] v0.3 — FaceOnLive integration (PimEyes-like)
- [ ] v0.4 — Azure Face API integration
- [ ] v0.5 — DeHashed/LeakCheck API integration
- [ ] v0.6 — Mobile app (React Native)
- [ ] v0.7 — Collaborative investigations (multi-user)

---

## 🔐 Privacy & Ethics

- Only collects publicly available data
- No illegal access or hacking
- Designed for deterrence, not harassment
- Complies with GDPR (EU data protection)
- Users responsible for lawful use

---

## 📄 License

MIT License — Free for personal and commercial use.

---

## 👤 Author

**karim1811** — OSINT enthusiast, developer

GitHub: [@karim1811](https://github.com/karim1811)
