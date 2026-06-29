# GHOST OSINT Engine — Dockerfile (Optimized for Render)
# Single container: API + Enrichment together

FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY src/ src/
COPY dashboard.py .
COPY ghost-api.py .
COPY ghost-bot.py .
COPY ghost-enrich-server.py .
COPY credits.py .

# Create dirs
RUN mkdir -p reports pending

# Environment
ENV GHOST_ENRICH_MODE=file
ENV GHOST_API_PORT=8000
ENV GHOST_ENRICH_PORT=4567
ENV PYTHONUNBUFFERED=1

# Expose
EXPOSE 8000 4567

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start both API and Enrichment
CMD ["sh", "-c", "python ghost-enrich-server.py & python ghost-api.py"]
