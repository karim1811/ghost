# GHOST v0.2 — Deployment Guide

## Quick Deploy Options

### 1. Local (Development)
```bash
pip install -r requirements.txt
python src/main.py --pseudo TARGET --enrich
```

### 2. Docker (All-in-One)
```bash
docker build -t ghost-osint .
docker run -p 8501:8501 -p 8000:8000 ghost-osint
```

### 3. Docker Compose (Full Stack)
```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

### 4. Cloud Platforms

#### Railway (Recommended — Free Tier)
```bash
# Install CLI
npm i -g @railway/cli

# Login & deploy
railway login
railway init
railway up

# Set env vars in dashboard
# → OPENROUTER_API_KEY, AZURE_FACE_API_KEY, etc.
```

#### Render (Free Tier)
1. Connect GitHub repo to Render
2. Create Web Service:
   - Build: `pip install -r requirements.txt`
   - Start: `python ghost-api.py`
3. Add env vars in dashboard

#### Vercel (Serverless)
```bash
npm i -g vercel
vercel --prod
```

#### Streamlit Cloud (Dashboard Only — Free)
1. Push to GitHub
2. Go to https://share.streamlit.io
3. Connect repo → Select `dashboard.py`
4. Deploy

---

## API Keys Setup

### Free Tiers
| Service | Free Tier | Get Key |
|---------|----------|---------|
| Azure Face API | 30k/mo | https://azure.microsoft.com |
| HaveIBeenPwned | 1.5s rate limit | https://haveibeenpwned.com/API/Key |
| OpenRouter | Pay-per-use | https://openrouter.ai/keys |

### Paid Services
| Service | Price | Get Key |
|---------|-------|---------|
| FaceOnLive | From $0.01/search | https://faceonlive.com |
| DeHashed | From $5/query | https://dehashed.com/api |
| LeakCheck | From 5/mo | https://leakcheck.io |

---

## Environment Variables

```bash
# AI Enrichment
OPENROUTER_API_KEY=sk-or-xxx...

# Face Recognition
FACEONLIVE_API_KEY=xxx...
AZURE_FACE_API_KEY=xxx...
AZURE_FACE_ENDPOINT=https://xxx.cognitiveservices.azure.com

# Breach Search
HIBP_API_KEY=xxx...
DEHASHED_API_KEY=xxx...
DEHASHED_EMAIL=your@email.com
LEAKCHECK_API_KEY=xxx...

# Telegram
GHOST_BOT_TOKEN=123456:ABC...

# Security
GHOST_API_KEY=generate-random-hex
GHOST_ENRICH_KEY=generate-random-hex
```

---

## Production Checklist

- [ ] Set strong API keys (GHOST_API_KEY, GHOST_ENRICH_KEY)
- [ ] Use HTTPS (reverse proxy with nginx/caddy)
- [ ] Set up rate limiting
- [ ] Configure log rotation
- [ ] Set up monitoring (UptimeRobot, etc.)
- [ ] Back up reports/ directory
- [ ] Set up Stripe for payments (credits system)
- [ ] Configure CORS for API
- [ ] Set up error tracking (Sentry)

---

## Architecture for Production

```
                    ┌─────────────┐
                    │   Users     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌────┴────┐
        │ Dashboard │ │Telegram│ │ REST API│
        │ Streamlit │ │  Bot   │ │ FastAPI │
        └─────┬─────┘ └───┬────┘ └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────┴──────┐
                    │   Scanner   │
                    │   Engine    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌────┴────┐
        │ Face APIs │ │ Breach │ │   AI    │
        │ Azure/Face│ │ Search │ │Enrich   │
        │ OnLive    │ │DeHashed│ │OpenRoutr│
        └───────────┘ └────────┘ └─────────┘
```
