FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot.py .

# Health check for EasyPanel
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:9000/health')" || exit 1

EXPOSE 9000

CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "1", "--log-level", "info"]
