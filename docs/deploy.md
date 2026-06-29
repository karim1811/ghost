# GHOST v0.3 — Deployment Guide

## Free Deployment Options (No Railway)

### Option 1: Render (Recommended)

**Best for:** API REST + Enrichment server (long-running processes)

**Free tier:** 750 instance hours/month (~31 days), spins down after 15min inactivity

#### Deploy API on Render:

1. Go to https://render.com and sign up (GitHub login)
2. Click **New +** → **Web Service**
3. Connect your GitHub repo (`karim1811/ghost`)
4. Configure:
   - **Name:** `ghost-api`
   - **Runtime:** Docker
   - **Start Command:** `python ghost-api.py`
   - **Plan:** Free
5. Add Environment Variables:
   - `GHOST_API_KEY` = generate with `python -c "import secrets; print(secrets.token_hex(16))"`
   - `OPENROUTER_API_KEY` = your key (optional)
6. Click **Create Web Service**

#### Deploy Enrichment Server:

Same steps but:
- **Name:** `ghost-enrich`
- **Start Command:** `python ghost-enrich-server.py`

#### Deploy Telegram Bot:

Same steps but:
- **Name:** `ghost-bot`
- **Start Command:** `python ghost-bot.py`
- Add env: `GHOST_BOT_TOKEN`

---

### Option 2: Hugging Face Spaces (Dashboard Only)

**Best for:** Streamlit dashboard (free, always on)

**Free tier:** Unlimited for public repos, always running

#### Deploy Dashboard:

1. Go to https://huggingface.co/spaces
2. Click **Create new Space**
3. Configure:
   - **Space name:** `ghost-dashboard`
   - **License:** MIT
   - **SDK:** Docker
   - **Visibility:** Public
4. Create the space
5. Upload these files via Git:
   - `dashboard.py` → rename to `app.py`
   - `requirements.txt`
   - `src/` folder
6. Add a `README.md` in the space with:
   ```yaml
   ---
   title: GHOST Dashboard
   emoji: 👻
   colorFrom: red
   colorTo: purple
   sdk: docker
   app_port: 8501
   ---
   ```
7. The space will build and deploy automatically

**Alternative:** Use Streamlit Cloud (even easier)
1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Select repo → `dashboard.py`
4. Deploy (1 click)

---

### Option 3: Vercel (API Serverless)

**Best for:** REST API only (not for long scans)

**Free tier:** 100GB bandwidth, 1000 invocations/day

#### Deploy:

1. Install Vercel CLI: `npm i -g vercel`
2. In ghost directory: `vercel`
3. Follow prompts (auto-detects Python)
4. Set env vars in Vercel dashboard

**Limitation:** Serverless functions timeout at 10s (free tier), so only quick scans work.

---

### Option 4: Clever Cloud (EU-based)

**Best for:** European hosting, GDPR compliant

**Free tier:** 1 service, 256MB RAM

#### Deploy:

1. Go to https://clever-cloud.com
2. Create account
3. Add GitHub integration
4. Select repo → Docker deployment
5. Set env vars in dashboard

---

### Option 5: Koyeb

**Best for:** Simple Docker deployment

**Free tier:** 1 nano instance (always running)

#### Deploy:

1. Go to https://koyeb.com
2. Sign up with GitHub
3. Create App → Docker
4. Select repo → `Dockerfile`
5. Deploy

---

## Comparison Table

| Platform | Free Tier | Always On | Docker | Best For |
|----------|-----------|-----------|--------|----------|
| Render | 750h/mo | No (spins down) | Yes | API, Workers |
| HF Spaces | Unlimited | Yes | Yes | Dashboard |
| Streamlit Cloud | Unlimited | Yes | No | Dashboard only |
| Vercel | 100GB/mo | Yes | No | Serverless API |
| Clever Cloud | 1 service | Yes | Yes | EU hosting |
| Koyeb | 1 nano | Yes | Yes | Simple apps |

---

## Recommended Setup

For a complete free deployment:

| Component | Platform | Why |
|-----------|----------|-----|
| Dashboard | Streamlit Cloud | Easiest, always on |
| REST API | Render | Docker support, free tier |
| Enrichment | Render | Same as API |
| Telegram Bot | Render | Worker process |

Total cost: **0€/month**

---

## Environment Variables Reference

```bash
# Required for production
GHOST_API_KEY=genera...  # API auth key
GHOST_ENRICH_KEY=xxx...  # Enrichment server auth

# AI Enrichment (optional)
OPENROUTER_API_KEY=***  # Pay-per-use AI

# Face Recognition (optional)
FACEONLIVE_API_KEY=xxx......n
AZURE_FACE_API_KEY=xxx......n

# Breach Search (optional)
HIBP_API_KEY=xxx......n
DEHASHED_API_KEY=xxx......n
DEHASHED_EMAIL=your@email.com
LEAKCHECK_API_KEY=xxx......n

# Telegram (optional)
GHOST_BOT_TOKEN=123456...:ABC...

# Credits
GHOST_CREDITS_PER_SCAN=1
GHOST_CREDITS_PER_DEEP=3
GHOST_FREE_DAILY_SCANS=3
```

---

## Post-Deployment Checklist

- [ ] Set strong API keys
- [ ] Test endpoints with curl
- [ ] Configure CORS if needed
- [ ] Set up uptime monitoring (UptimeRobot — free)
- [ ] Enable HTTPS (automatic on all platforms)
- [ ] Set up log alerts
- [ ] Back up reports/ periodically
