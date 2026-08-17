# The app has zero third-party Python dependencies — it is pure stdlib — so
# there is no pip install step and the slim base is all it needs. The React
# bundle is committed in web/dist, so there is no Node build stage either.
FROM python:3.13-slim

# Do not buffer stdout: without this, log lines sit in the buffer and never
# reach CloudWatch until the process exits.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EUV_HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# Run as a non-root user. The base image's root would otherwise own the
# process, which is needless privilege for a static+JSON server.
RUN useradd --create-home --shell /usr/sbin/nologin euv
COPY --chown=euv:euv . /app
USER euv

EXPOSE 8000

# /api/health is an existing route and needs no extra dependency to call.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys;\
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4).status==200 else 1)"

CMD ["python", "serve.py"]
