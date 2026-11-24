#!/bin/bash
# Al Basmah AI Media Studio - one-shot server setup for a fresh Ubuntu 24.04 VM
# (Oracle Cloud Always Free Ampere A1, or any Ubuntu VPS).
# Paste this whole file into "Cloud-init script" when creating the VM.
# EDIT THE TWO LINES BELOW FIRST:
STUDIO_PASSWORD='ضع-هنا-كلمة-مرور-قوية-12-حرفًا-على-الأقل'
REPO_URL='https://github.com/yousef0110020-stack/al-basmah-studio.git'
# ---------------------------------------------------------------------------
set -eux
exec > /var/log/albasmah-setup.log 2>&1
export DEBIAN_FRONTEND=noninteractive
# 4 GB swap so 4K video renders never run out of memory
if [ ! -f /swapfile ]; then fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab; fi
apt-get update
apt-get install -y docker.io docker-compose-v2 git curl iptables-persistent
systemctl enable --now docker
# Oracle Ubuntu images block everything except SSH in iptables: open 80/443
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
netfilter-persistent save || true
# Free HTTPS hostname that points at this server's public IP (e.g. 129-151-1-2.sslip.io)
IP=$(curl -fsS https://api.ipify.org)
DOMAIN="${IP//./-}.sslip.io"
rm -rf /opt/albasmah && git clone --depth 1 "$REPO_URL" /opt/albasmah
cd /opt/albasmah
umask 077
printf 'STUDIO_PASSWORD=%s\nDOMAIN=%s\n' "$STUDIO_PASSWORD" "$DOMAIN" > .env
docker compose up -d --build
echo "https://$DOMAIN" > /opt/albasmah/URL.txt
echo "READY: https://$DOMAIN"
