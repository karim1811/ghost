# GHOST OSINT Engine — Dockerfile
# Build: docker build -t ghost-osint .
# Run: docker run -p 8501:8501 -p 8000:8000 -v ghost-reports:/app/reports ghost-osint

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

# Environment (override at runtime)
ENV GHOST_ENRICH_MODE=file
ENV GHOST_API_PORT=8000
ENV GHOST_ENRICH_PORT=4567

# Expose ports
# 8501 = Dashboard, 8000 = API, 4567 = Enrichment
EXPOSE 8501 8000 4567

# Default: run dashboard
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
