# Container image for the phishing detection module (REST API + CLI)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code and the bundled demo dataset
COPY src ./src
COPY data ./data

# Do not run as root inside the container
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Default: REST API. The CLI is available too, e.g.:
#   docker run --rm IMAGE python -m src.cli evaluate
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
