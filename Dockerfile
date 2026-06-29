# GHOST OSINT Engine — Dockerfile
# Build: docker build -t ghost-osint .
# Run: docker run -p 8501:8501 -p 8000:8000 ghost-osint

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
COPY README.md .

# Create dirs
RUN mkdir -p reports pending

# Environment
ENV GHOST_ENRICH_MODE=file
ENV GHOST_API_PORT=8000
ENV GHOST_ENRICH_PORT=4567
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8501 8000 4567

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${GHOST_API_PORT:-8000}/health || exit 1

# Default: run API
CMD ["python", "ghost-api.py"]
