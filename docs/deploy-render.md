# GHOST — Render Deployment Guide (Step by Step)

## Prerequisites

1. GitHub account with `karim1811/ghost` repo
2. Render account (https://render.com — sign up with GitHub)
3. No credit card needed for free tier

---

## Step 1: Create Render Account

1. Go to https://render.com
2. Click **Sign Up** → **GitHub**
3. Authorize Render to access your repos
4. You're in the dashboard

---

## Step 2: Deploy REST API

1. In Render dashboard, click **New +** → **Web Service**
2. Click **Build and deploy from a Git repository**
3. Connect `karim1811/ghost` repo
4. Configure:
   ```
   Name: ghost-api
   Region: Frankfurt (or Oregon for US)
   Branch: main
   Runtime: Docker
   Plan: Free
   ```
5. Click **Advanced** → Add Environment Variables:
   ```
   GHOST_API_KEY = (generate: python -c "import secrets; print(secrets.token_hex(16))")
   GHOST_ENRICH_MODE = file
   ```
6. Click **Create Web Service**
7. Wait for build (~2-3 min)
8. Your API is live at: `https://ghost-api.onrender.com`

**Test it:**
```bash
curl https://ghost-api.onrender.com/health
# → {"status": "ok", "version": "0.2"}
```

---

## Step 3: Deploy Enrichment Server

1. Click **New +** → **Background Worker**
2. Connect same repo
3. Configure:
   ```
   Name: ghost-enrich
   Runtime: Docker
   Plan: Free
   Start Command: python ghost-enrich-server.py
   ```
4. Add env vars:
   ```
   GHOST_ENRICH_KEY = (generate another key)
   ```
5. Click **Create Worker**

---

## Step 4: Deploy Telegram Bot (Optional)

1. Click **New +** → **Background Worker**
2. Connect same repo
3. Configure:
   ```
   Name: ghost-bot
   Runtime: Docker
   Plan: Free
   Start Command: python ghost-bot.py
   ```
4. Add env var:
   ```
   GHOST_BOT_TOKEN = (your bot token from @BotFather)
   ```
5. Click **Create Worker**

---

## Step 5: Deploy Dashboard (Streamlit Cloud)

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **New app**
4. Select:
   ```
   Repository: karim1811/ghost
   Branch: main
   Main file path: dashboard.py
   ```
5. Click **Deploy**
6. Dashboard is live at: `https://karim1811-ghost-dashboard.streamlit.app`

---

## Step 6: Configure API Keys (Optional)

For face recognition and breach search, add keys in Render dashboard:

1. Go to your service → **Environment**
2. Add keys:
   ```
   OPENROUTER_API_KEY = (from openrouter.ai)
   FACEONLIVE_API_KEY = (from faceonlive.com)
   AZURE_FACE_API_KEY = (from Azure portal)
   HIBP_API_KEY = (from haveibeenpwned.com/API/Key)
   ```
3. Save → Service auto-restarts

---

## Step 7: Test Everything

```bash
# Test API
curl https://ghost-api.onrender.com/health

# Start a scan
curl -X POST https://ghost-api.onrender.com/scan \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{"target": "kijebede", "deep": true, "enrich": true}'

# Check scan status (use job_id from previous response)
curl https://ghost-api.onrender.com/scan/abc12345 \
  -H "X-API-KEY: your-api-key"

# List reports
curl https://ghost-api.onrender.com/reports \
  -H "X-API-KEY: your-api-key"
```

---

## Render Free Tier Limits

| Resource | Limit |
|----------|-------|
| Instance hours | 750/month (~31 days) |
| Bandwidth | 100GB/month |
| Build time | 500 min/month |
| Spin down | After 15min inactivity |
| Spin up time | ~30 seconds |

**Tip:** Use UptimeRobot (free) to ping your API every 5min → prevents spin down.

---

## Troubleshooting

**Build fails?**
- Check logs in Render dashboard
- Verify `requirements.txt` is valid
- Make sure `Dockerfile` is at repo root

**Service won't start?**
- Check `dockerCommand` matches your file name
- Verify env vars are set
- Check logs for Python errors

**API returns 502?**
- Service might be spinning down (free tier)
- Wait 30s and retry
- Set up UptimeRobot to keep it warm

---

## Architecture After Deploy

```
Users → Dashboard (Streamlit Cloud)
     → API (Render Web Service :8000)
     → Bot (Render Worker)
     
API → Enrichment (Render Worker :4567)
   → Face APIs (Azure/FaceOnLive)
   → Breach Search (DeHashed/LeakCheck/HIBP)
   → AI Enrichment (OpenRouter/Hermes)
```

Total cost: **0€/month**
