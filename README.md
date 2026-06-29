# GHOST v0.3 — AI-Enhanced OSINT Engine

```
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   OSINT Engine v0.3 | No One Is Invisible
```

**GitHub:** [karim1811/ghost](https://github.com/karim1811/ghost)

---

## What is GHOST?

AI-powered investigation engine that reveals anonymous online profiles. Scan 700+ platforms, search faces across the internet, check data breaches, enrich with AI.

**Use case:** When anonymous accounts insult/harass, show them they're NOT untraceable.

---

## Quick Start

```bash
git clone https://github.com/karim1811/ghost.git
cd ghost
pip install -r requirements.txt

# Basic scan (FREE — 69 platforms)
python src/main.py --pseudo TARGET

# Deep scan + AI enrichment
python src/main.py --pseudo TARGET --deep --enrich

# Face search
python src/main.py --image photo.jpg --face-search

# Breach check
python src/main.py --email EMAIL@DOMAIN.COM --breach-check

# Dashboard
streamlit run dashboard.py
```

---

## Features

### Platform Scanning (700+ sites)
- 69 platforms via HEAD requests
- 700+ sites via WhatsMyName integration
- GitHub, Reddit, Steam deep analysis
- Behavioral fingerprinting

### AI Enrichment
- Identity resolution (names, locations, languages)
- Banner/photo geolocation (computer vision)
- Spotify/taste analysis
- Social graph mapping
- Web mentions & indexed content
- AI-generated verdict

### Face Recognition
- **FaceOnLive** — reverse face search (PimEyes alternative)
- **Azure Face API** — detection, verification, similarity (free 30k/mo)
- Face comparison (same person detection)
- Liveness detection (anti-spoofing)

### Data Breach Search
- **HaveIBeenPwned** — email breaches (free with key)
- **HIBP Password Check** — exposed passwords (always free, k-anonymity)
- **DeHashed** — deep breach search (paid, API access)
- **LeakCheck** — breach search alternative (paid)

### Dashboard (Web UI)
- Launch scans from browser
- Browse reports with markdown rendering
- Scan history & export
- Deploy free: Streamlit Cloud

### Telegram Bot
- `/scan USERNAME` — quick scan
- `/deep USERNAME` — full + AI enrichment
- `/reports` — recent reports

### REST API
- `POST /scan` — start scan
- `GET /scan/{id}` — check status
- `GET /reports` — list reports
- JSON responses, API key auth

### Credits System
- 3 free scans/day
- Pay-per-scan packages
- Pro/Enterprise unlimited

---

## Deployment

### Docker (One Command)
```bash
docker build -t ghost-osint .
docker run -p 8501:8501 ghost-osint
```

### Docker Compose (Full Stack)
```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
# → Dashboard: :8501, API: :8000, Enrichment: :4567
```

### Cloud Platforms
| Platform | Type | Cost | Deploy |
|----------|------|------|--------|
| Railway | Full stack | Free tier | `railway up` |
| Render | API/Worker | Free tier | Connect repo |
| Streamlit Cloud | Dashboard | Free | share.streamlit.io |
| Vercel | Serverless | Free tier | `vercel --prod` |

See [docs/deploy.md](docs/deploy.md) for detailed instructions.

---

## API Keys

### Free Tiers Available
| Service | Free Tier | Get Key |
|---------|----------|---------|
| Azure Face API | 30,000 tx/month | [azure.microsoft.com](https://azure.microsoft.com) |
| HaveIBeenPwned | Rate-limited | [haveibeenpwned.com/API/Key](https://haveibeenpwned.com/API/Key) |
| OpenRouter | Pay-per-use | [openrouter.ai](https://openrouter.ai/keys) |

### Paid Services
| Service | Pricing | Get Key |
|---------|---------|---------|
| FaceOnLive | From $0.01/search | [faceonlive.com](https://faceonlive.com) |
| DeHashed | From $5/query | [dehashed.com/api](https://dehashed.com/api) |
| LeakCheck | From $5/month | [leakcheck.io](https://leakcheck.io) |

---

## Project Structure

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
│       ├── face_compare.py      # Face comparison (local)
│       ├── face_recognition.py  # FaceOnLive + Azure Face NEW
│       ├── breach_search.py     # DeHashed + LeakCheck + HIBP NEW
│       ├── social_graph.py      # Cross-platform identity
│       ├── detection_patterns.py
│       ├── report.py            # Standard report generator
│       └── enrich.py            # AI enrichment client
├── dashboard.py                 # Streamlit web UI
├── ghost-bot.py                 # Telegram bot
├── ghost-api.py                 # REST API
├── ghost-enrich-server.py       # Enrichment server
├── credits.py                   # Credits/billing system
├── Dockerfile                   # Docker build
├── docker-compose.yml           # Full stack
├── .env.example                 # Config template
├── requirements.txt
├── docs/
│   └── deploy.md                # Deployment guide
└── reports/                     # Generated reports
```

---

## CLI Commands

```bash
# Scanning
python src/main.py --pseudo USERNAME
python src/main.py --pseudo USERNAME --deep
python src/main.py --pseudo USERNAME --whatsmyname
python src/main.py --pseudo USERNAME --identity
python src/main.py --email EMAIL@DOMAIN.COM

# Face analysis
python src/main.py --image photo.jpg --face-search
python src/main.py --image photo.jpg --face-analyze
python src/main.py --compare photo1.jpg photo2.jpg

# Breach search
python src/main.py --email EMAIL --breach-check

# Export
python src/main.py --pseudo USERNAME --export json
python src/main.py --pseudo USERNAME --enrich --export markdown

# Dashboard (streamlit run dashboard.py)

# Credits system is integrated — first 3 scans/day free
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     GHOST v0.3                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Interfaces: CLI │ Dashboard │ Telegram │ REST API       │
│                          │                               │
│                   ┌──────┴──────┐                        │
│                   │   Scanner   │                        │
│                   │   Engine    │                        │
│                   └──────┬──────┘                        │
│                          │                               │
│         ┌────────────────┼────────────────┐              │
│         │                │                │              │
│  ┌──────┴──────┐  ┌─────┴──────┐  ┌─────┴──────┐      │
│  │ Face Recog  │  │  Breach    │  │  AI        │      │
│  │ FaceOnLive  │  │  Search    │  │  Enrich    │      │
│  │ Azure Face  │  │ DeHashed   │  │ OpenRouter │      │
│  │ Local Compare│  │ LeakCheck │  │ Hermes     │      │
│  └─────────────┘  │ HIBP       │  └────────────┘      │
│                    └────────────┘                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Roadmap

- [x] v0.1 — Basic scanner (69 platforms)
- [x] v0.2 — AI enrichment + Dashboard + Bot + API + Credits
- [x] v0.3 — Face recognition + Breach search + Docker deploy
- [ ] v0.4 — Collaborative investigations (multi-user)
- [ ] v0.5 — Mobile app (React Native)
- [ ] v0.6 — Advanced social network analysis
- [ ] v0.7 — Dark web monitoring integration

---

## Monetization

| Plan | Price | Features |
|------|-------|----------|
| Free | 0€ | 3 scans/day, basic reports |
| Starter | 4.99€ | 10 scans, AI enrichment |
| Pro | 19.99€ | 50 scans, face search, breach check |
| Unlimited | 49.99€/mo | Everything unlimited |

---

## License

MIT — Free for personal and commercial use.

---

## Author

**karim1811** — [@karim1811](https://github.com/karim1811)
