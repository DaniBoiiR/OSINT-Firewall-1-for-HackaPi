# Aurelian Dynamics staff portal — Firewall 1 (Web Application Challenge)
#
# Small, multi-arch base so the same image builds on an x86 laptop and on a
# Raspberry Pi (arm64). No build-time network is needed beyond pip; the
# stylesheet is pre-compiled and committed, so there is no Node toolchain here.
FROM python:3.12-slim

# No .pyc files (keeps a read-only root filesystem happy) and unbuffered logs.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GUNICORN_BIND=0.0.0.0:8080

WORKDIR /srv/portal

# Dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code and assets.
COPY app.py gunicorn.conf.py ./
COPY templates ./templates
COPY static ./static

# Run as an unprivileged account. Binding to 8080 (not 80) means we need no
# privileged ports inside the container; docker-compose publishes host :80.
RUN useradd --system --uid 10001 --gid 0 --no-create-home portal \
    && chown -R 10001:0 /srv/portal
USER 10001

EXPOSE 8080

# Lightweight liveness probe (no external tools required).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3).read()==b'ok' else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
