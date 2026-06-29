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

## 🚀 Two Modes

### FREE Mode (Standalone)
- Scan 700+ platforms for a username
- Check email breaches (Gravatar, paste dumps)
- Reverse image search
- Face comparison
- Behavioral fingerprint
- Markdown/JSON reports

### PRO Mode (AI-Enriched)
Everything in FREE + AI-powered enrichment:
- Identity resolution (names, locations, languages)
- Banner/photo geolocation
- Spotify analysis (taste, habits)
- Twitter/X deep context (indexed tweets, interactions)
- Social graph mapping
- Web mentions & cached content
- AI-generated verdict

---

## 📦 Installation

```bash
# Clone
git clone https://github.com/karim1811/ghost.git
cd ghost

# Install dependencies
python3.13 -m pip install -r requirements.txt

# Run (FREE mode)
python src/main.py --pseudo TARGET
```

---

## 🤖 AI Enrichment Setup (PRO)

### Option A: Local Hermes Agent (Recommended for personal use)

1. **Install Hermes Agent:**
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

2. **Start the enrichment server:**
```bash
# In the ghost directory
python ghost-enrich-server.py
# → Server running on http://localhost:4567
```

3. **Run GHOST with enrichment:**
```bash
python src/main.py --pseudo TARGET --enrich
```

### Option B: Remote Enrichment Server (For production/multi-user)

Deploy the enrichment server to a cloud platform:

#### Deploy to Railway (Easiest)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login & init
railway login
railway init

# Set env vars
railway variables set GHOST_ENRICH_KEY=your-secret-key
railway variables set HERMES_PATH=hermes

# Deploy
railway up
# → You get a public URL like https://ghost-enrich.up.railway.app
```

#### Deploy to Render
1. Connect your GitHub repo to Render
2. Create a new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python ghost-enrich-server.py`
5. Add env var: `GHOST_ENRICH_KEY=your-secret-key`

#### Deploy to Vercel (Serverless)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Then use it:
```bash
python src/main.py --pseudo TARGET --enrich \
  --enrich-url https://your-server.railway.app \
  --enrich-key your-secret-key
```

---

## 🔧 Usage

### FREE Mode
```bash
# Basic scan
python src/main.py --pseudo username

# Deep scan (Keybase, pastes)
python src/main.py --pseudo username --deep

# WhatsMyName (700+ sites)
python src/main.py --pseudo username --whatsmyname

# Identity analysis
python src/main.py --pseudo username --identity

# Email investigation
python src/main.py --email test@mail.com

# Reverse image search
python src/main.py --image photo.jpg

# Compare faces
python src/main.py --compare photo1.jpg photo2.jpg

# Export as JSON
python src/main.py --pseudo username --export json
```

### PRO Mode (with AI enrichment)
```bash
# Local enrichment
python src/main.py --pseudo username --enrich

# Remote enrichment server
python src/main.py --pseudo username --enrich \
  --enrich-url https://your-server.railway.app \
  --enrich-key your-secret-key

# Check server status
python src/main.py --check-enrich
python src/main.py --check-enrich --enrich-url https://your-server.railway.app
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GHOST v0.2                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  CLI Entry  │───▶│  Scan Engine │───▶│   Report Gen  │  │
│  │  (main.py)  │    │ (platforms)  │    │  (markdown)   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                                        ▲          │
│         │ --enrich                               │          │
│         ▼                                        │          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Enrichment Module (enrich.py)           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │   │
│  │  │ HTTP Client│  │  Image     │  │   Report     │  │   │
│  │  │ (requests) │  │  Analyzer  │  │   Enricher   │  │   │
│  │  └────────────┘  └────────────┘  └──────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTP POST /enrich
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              GHOST Enrichment Server (port 4567)            │
│              (ghost-enrich-server.py)                        │
│                                                             │
│  Receives JSON ──▶ Builds prompt ──▶ Calls Hermes Agent     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Agent (AI Backend)                 │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │web_search│  │ browser  │  │  vision  │  │  file    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  Capabilities:                                              │
│  • Geolocate images        • Analyze Spotify profiles       │
│  • Find indexed tweets     • Extract web context            │
│  • Reverse image search    • Map social connections         │
│  • Identity resolution     • Behavioral analysis            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ghost/
├── src/
│   ├── main.py                    # CLI entry point
│   └── modules/
│       ├── platforms.py           # 69+ platform definitions
│       ├── http_utils.py          # HTTP helpers
│       ├── specialized.py         # GitHub, Reddit, Steam, HN
│       ├── leaks.py               # Gravatar, Keybase, Epieos
│       ├── whatsmyname.py         # 700+ sites via WhatsMyName
│       ├── reverse_image.py       # Reverse image search
│       ├── face_compare.py        # Face comparison
│       ├── social_graph.py        # Cross-platform identity
│       ├── detection_patterns.py  # False positive detection
│       ├── report.py              # Standard report generator
│       └── enrich.py              # AI enrichment client (NEW)
├── ghost-enrich-server.py         # Enrichment server (NEW)
├── requirements.txt
├── reports/                       # Generated reports
└── docs/
    └── deploy.md                  # Deployment guide
```

---

## 🔐 Security & Privacy

- **FREE mode**: Everything runs locally, no data leaves your machine
- **PRO mode**: Scan results are sent to YOUR enrichment server only
- **No data retention**: Enrichment server doesn't store results
- **API key protection**: Use `--enrich-key` for production servers
- **Rate limiting**: Built-in politeness delays on all scans

---

## 💰 Monetization Strategy

| Feature | FREE | PRO |
|---------|------|-----|
| Platform scan (69) | ✅ | ✅ |
| WhatsMyName (700+) | ✅ | ✅ |
| Email investigation | ✅ | ✅ |
| Reverse image search | ✅ | ✅ |
| Face comparison | ✅ | ✅ |
| Behavioral fingerprint | ✅ | ✅ |
| AI identity resolution | ❌ | ✅ |
| Banner geolocation | ❌ | ✅ |
| Spotify analysis | ❌ | ✅ |
| Twitter deep dive | ❌ | ✅ |
| Social graph mapping | ❌ | ✅ |
| Web mentions | ❌ | ✅ |
| Enriched reports | ❌ | ✅ |

**Pricing suggestion:**
- FREE: Standalone scanner
- PRO: 4.99€/month or 49.99€/year for AI enrichment
- API access: Pay-per-scan for third-party integrations

---

## 🛣️ Roadmap

- [x] v0.1 — Basic scanner (69 platforms)
- [x] v0.2 — AI enrichment module
- [ ] v0.3 — Web dashboard (Streamlit)
- [ ] v0.4 — Telegram/Discord bot
- [ ] v0.5 — FaceOnLive integration (PimEyes-like)
- [ ] v0.6 — Azure Face API integration
- [ ] v0.7 — DeHashed/LeakCheck API integration
- [ ] v0.8 — Mobile app (React Native)

---

## 📄 License

MIT License — Free for personal and commercial use.

---

## 👤 Author

**karim1811** — OSINT enthusiast, 42 school student

GitHub: [@karim1811](https://github.com/karim1811)
