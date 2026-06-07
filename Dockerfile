FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create data dir for SQLite state (mounted as volume in production)
RUN mkdir -p /data && chmod 777 /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Governance control plane on 8000, Specialist layer on 8080, Slack on 3001
EXPOSE 8000 8080 3001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run the governance control plane
# Override with: docker run ... python main.py --specialists
CMD ["python", "main.py", "--serve", "--port", "8000"]
