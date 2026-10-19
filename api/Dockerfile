# FastAPI sidecar. Base pinned by digest (Renovate bumps it); all Python deps
# come as prebuilt wheels, so no compiler is needed in the image.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

# Security updates of the Debian base on every build.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt \
 && rm -rf /usr/local/lib/python3.*/ensurepip/_bundled \
 && python -m pip uninstall -y pip
# ^ pip is only needed to build the image. It (and ensurepip's bundled pip
#   wheel) vendors outdated copies of msgpack, urllib3 and setuptools that
#   scanners flag, so it is removed from the runtime image.

# Only the application code (no tests, caches or local .env files).
COPY app ./app

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
