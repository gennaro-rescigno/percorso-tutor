#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu 22.04/24.04 VM (Oracle Cloud Always Free, Ampere A1 or AMD micro).
# For any other VPS the fully automatic installer is deploy/vps.sh (sudo bash deploy/vps.sh install).
# Run as the default 'ubuntu' user:  bash deploy/oracle-setup.sh
set -euo pipefail

echo "==> Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

echo "==> Firewall (Oracle images ship iptables rules that block 80/443)"
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
sudo sh -c 'command -v netfilter-persistent >/dev/null && netfilter-persistent save' || true
echo "    Remember to also open TCP 80/443 in the VCN Security List (Oracle console)."

echo "==> Swap (useful on 1 GB micro instances)"
if ! swapon --show | grep -q swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> Data folders (container user uid 10001 writes reports)"
mkdir -p reports backups data && sudo chown 10001 reports data

echo "==> .env"
if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
  sed -i "s|^MCI_API_SECRET_KEY=.*|MCI_API_SECRET_KEY=$(openssl rand -hex 32)|" .env
  IP=$(curl -fsS https://api.ipify.org || echo "")
  [ -n "$IP" ] && echo "    IP pubblico di questa VM: $IP  -> inseriscilo su duckdns.org"
  chmod 600 .env
  echo "    .env creato: imposta DOMAIN, MCI_DASHBOARD_PASSWORD, MCI_TELEGRAM_BOT_TOKEN, MCI_TELEGRAM_CHAT_IDS"
fi

echo "==> Fatto. Ora: nano .env  (poi)  sudo docker compose up -d --build"
