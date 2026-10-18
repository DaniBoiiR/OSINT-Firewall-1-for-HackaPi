"""
Gunicorn configuration for the Aurelian Dynamics staff portal.

Tuned for a Raspberry Pi 4/5 (4 cores) serving ~40 concurrent participants.
The app holds only read-only challenge data in memory and keeps no
server-side session state, so multiple worker processes are safe and share
nothing that could drift between them.

Override any value with an environment variable, e.g. GUNICORN_WORKERS=2.
"""

import os

# Bind to port 80 inside the container; docker-compose maps the host port.
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:80")

# A small pool of threaded workers handles bursty, I/O-light traffic well on
# a Pi without exhausting memory. 4 workers x 4 threads = 16 concurrent
# requests, which comfortably covers ~40 participants browsing a portal.
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")

# Recycle workers periodically as a cheap safeguard against any slow leak
# over a long event day.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "2000"))
max_requests_jitter = 200

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 4

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
