# Al Basmah AI Media Studio - production image (amd64 + arm64)
# Ubuntu 24.04 = same FFmpeg 6.1 (with vid.stab, libass, x264) the test-suite ran on.
ARG BASE=ubuntu:24.04
FROM ${BASE}
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_CERT=/etc/ssl/certs/ca-certificates.crt PATH=/opt/venv/bin:$PATH
# optional corporate/proxy CA certificates (*.crt) - empty in normal builds
COPY deploy/extra-ca/ /usr/local/share/ca-certificates/
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg python3 python3-venv libfribidi0 libharfbuzz0b ca-certificates \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/venv
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
COPY assets ./assets
COPY deploy/entrypoint.sh ./entrypoint.sh
RUN useradd -m -u 1001 studio && mkdir -p /data && chown studio /data && chmod +x entrypoint.sh
USER studio
ENV STUDIO_DATA_DIR=/data PORT=8000
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
ENTRYPOINT ["./entrypoint.sh"]
