#!/usr/bin/env bash
# Memecoin Intelligence - installazione e aggiornamento automatici su una VPS Ubuntu 22.04/24.04
# (qualsiasi provider: Hetzner, OVH, Netcup, Contabo, Oracle...). Va eseguito come root.
#
#   bash vps.sh install   prima installazione; si può rilanciare (non cancella dati né segreti)
#   bash vps.sh update    passa all'ultimo commit di main con la CI verde (lo fa il timer ogni 10 min);
#                         se la nuova versione non parte, torna da sola alla precedente
#   bash vps.sh status    stato di servizi, bot, memoria e disco
#
# Le impostazioni personali stanno SOLO in /etc/mci/config.env (permessi 600, mai nel repository):
#   MCI_TELEGRAM_BOT_TOKEN=   token di @BotFather
#   MCI_TELEGRAM_CHAT_IDS=    il tuo chat id
#   DOMAIN=                   facoltativo, es. nome.duckdns.org -> dashboard HTTPS
#   DUCKDNS_TOKEN=            facoltativo, tiene aggiornato il nome DuckDNS
#   MCI_DASHBOARD_PASSWORD=   facoltativa: se vuota ne viene generata una e inviata su Telegram
#   MCI_JUPITER_API_KEY=      facoltativa
# Il trading resta in modalità PAPER: questo script non abilita mai il trading reale.
set -euo pipefail

REPO="${MCI_REPO:-gennaro-rescigno/percorso-tutor}"
REF="${MCI_REF:-main}"
BASE=/opt/mci
SRC=$BASE/repo
APP=$SRC/memecoin-intelligence
CONF=/etc/mci/config.env
LOG=/var/log/mci-deploy.log
STATE_URL="https://raw.githubusercontent.com/$REPO/bot-state/state.json"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG" >&2; }

need_root() {
  if [ "$(id -u)" != 0 ]; then echo "Esegui come root: sudo bash $0 $*"; exit 1; fi
  mkdir -p "$(dirname "$LOG")" && touch "$LOG" && chmod 600 "$LOG"
}

# --- KEY=VALUE files, read/written with python (no sed escaping problems with tokens) ---
kv_get() { # FILE KEY
  [ -f "$1" ] || return 0
  python3 - "$1" "$2" <<'PY'
import sys
val = ""
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if line.startswith(sys.argv[2] + "="):
        val = line.split("=", 1)[1].strip().strip('"').strip("'")
print(val)
PY
}

kv_set() { # FILE KEY VALUE
  python3 - "$1" "$2" "$3" <<'PY'
import sys
path, key, value = sys.argv[1:4]
lines = open(path, encoding="utf-8").read().splitlines()
out, done = [], False
for line in lines:
    if line.startswith(key + "="):
        if not done:
            out.append(f"{key}={value}")
            done = True
        continue
    out.append(line)
if not done:
    out.append(f"{key}={value}")
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
}

conf() { # KEY -> value from the personal config; template placeholders count as empty
  local v
  v=$(kv_get "$CONF" "$1")
  [[ "$v" == INCOLLA_QUI* ]] && v=""
  printf '%s\n' "$v"
}

# --- Telegram: the token goes through curl's config on stdin, never on the command line or in logs ---
tg() {
  local token chats c
  token=$(conf MCI_TELEGRAM_BOT_TOKEN)
  chats=$(conf MCI_TELEGRAM_CHAT_IDS)
  [ -n "$token" ] && [ -n "$chats" ] || return 0
  for c in ${chats//,/ }; do
    printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$token" |
      curl -fsS -m 20 -o /dev/null -K - --data-urlencode "chat_id=$c" --data-urlencode "text=$1" ||
      log "Telegram: invio non riuscito (controlla token e chat id in $CONF)"
  done
}

profiles() { if [ -n "$(kv_get "$APP/.env" DOMAIN)" ]; then echo "--profile web"; fi; return 0; }
# shellcheck disable=SC2046
dc() { (cd "$APP" && docker compose $(profiles) "$@"); }

api_health() { # prints the /api/health JSON of the running api container
  dc exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).read().decode())" 2>/dev/null
}

worker_stable() {
  local id
  id=$(dc ps -q worker 2>/dev/null)
  [ -n "$id" ] && [ "$(docker inspect -f '{{.State.Running}} {{.RestartCount}}' "$id" 2>/dev/null)" = "true 0" ]
}

wait_healthy() { # api answers, worker heartbeat fresh, worker not crash-looping for 60 s
  local deadline=$((SECONDS + ${1:-480})) h
  while [ $SECONDS -lt $deadline ]; do
    sleep 10
    h=$(api_health || true)
    if [[ "$h" == *'"worker_alive": true'* || "$h" == *'"worker_alive":true'* ]] && worker_stable; then
      sleep 60
      if worker_stable && api_health >/dev/null; then return 0; fi
    fi
  done
  log "servizi non sani entro il tempo limite. health=${h:-nessuna risposta}"
  dc ps >>"$LOG" 2>&1 || true
  dc logs --tail 60 worker api >>"$LOG" 2>&1 || true
  return 1
}

duckdns_update() {
  local domain token sub
  domain=$(conf DOMAIN)
  token=$(conf DUCKDNS_TOKEN)
  [[ -n "$token" && "$domain" == *.duckdns.org ]] || return 0
  sub=${domain%.duckdns.org}
  if printf 'url = "https://www.duckdns.org/update?domains=%s&token=%s&ip="\n' "$sub" "$token" |
      curl -fsS -m 20 -K - | grep -q OK; then
    return 0
  fi
  log "DuckDNS: aggiornamento non riuscito (controlla DOMAIN e DUCKDNS_TOKEN)"
}

write_conf_template() {
  mkdir -p "$(dirname "$CONF")"
  cat >"$CONF" <<'EOF'
# Impostazioni personali del bot (permessi 600). Dopo una modifica: sudo bash /opt/mci/repo/memecoin-intelligence/deploy/vps.sh install
MCI_TELEGRAM_BOT_TOKEN=
MCI_TELEGRAM_CHAT_IDS=
DOMAIN=
DUCKDNS_TOKEN=
MCI_DASHBOARD_PASSWORD=
MCI_JUPITER_API_KEY=
EOF
}

cmd_install() {
  need_root
  log "=== installazione Memecoin Intelligence (repo $REPO, ref $REF) ==="
  [ -f "$CONF" ] || { write_conf_template; log "creato $CONF (vuoto)"; }
  chmod 600 "$CONF"

  export DEBIAN_FRONTEND=noninteractive
  log "pacchetti di sistema"
  apt-get -o DPkg::Lock::Timeout=600 update -q >>"$LOG" 2>&1
  apt-get -o DPkg::Lock::Timeout=600 install -y -q git curl ca-certificates openssl python3 >>"$LOG" 2>&1

  if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
    log "Docker (script ufficiale get.docker.com)"
    curl -fsSL https://get.docker.com | sh >>"$LOG" 2>&1
  fi
  systemctl enable --now docker >>"$LOG" 2>&1 || true

  local mem_mb
  mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
  if [ "$mem_mb" -lt 3500 ] && [ -z "$(swapon --noheadings 2>/dev/null)" ]; then
    log "swap 2 GB (RAM ${mem_mb} MB)"
    fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
  fi

  if [ "${MCI_SKIP_FIREWALL:-0}" != 1 ]; then
    log "firewall (solo SSH, 80, 443) e fail2ban"
    apt-get -o DPkg::Lock::Timeout=600 install -y -q ufw fail2ban >>"$LOG" 2>&1
    ufw allow 22/tcp >/dev/null && ufw allow 80/tcp >/dev/null && ufw allow 443/tcp >/dev/null
    ufw --force enable >/dev/null
    systemctl enable --now fail2ban >>"$LOG" 2>&1 || true
  fi

  if [ ! -d "$SRC/.git" ]; then
    log "scarico il codice (solo la cartella memecoin-intelligence)"
    mkdir -p "$BASE"
    git clone -q --filter=blob:none --no-checkout "https://github.com/$REPO.git" "$SRC"
    git -C "$SRC" sparse-checkout set --cone memecoin-intelligence
    git -C "$SRC" -c advice.detachedHead=false checkout -q "$REF"
  fi
  cd "$APP"
  mkdir -p reports data backups
  chown 10001 reports data

  local new_password=""
  if [ ! -f .env ]; then
    log "creo .env con segreti casuali"
    cp .env.example .env
    kv_set .env POSTGRES_PASSWORD "$(openssl rand -hex 24)"
    kv_set .env MCI_API_SECRET_KEY "$(openssl rand -hex 32)"
    kv_set .env MCI_ENV prod
    kv_set .env MCI_ENABLED_STRATEGIES "A,B,C,D,E"
  fi
  chmod 600 .env
  # paper trading is enforced on every install: real trading needs the separate manual procedure (docs/SECURITY.md)
  kv_set .env MCI_TRADING_MODE paper
  kv_set .env MCI_LIVE_TRADING_ENABLED false
  local k v
  for k in MCI_TELEGRAM_BOT_TOKEN MCI_TELEGRAM_CHAT_IDS DOMAIN MCI_JUPITER_API_KEY; do
    kv_set .env "$k" "$(conf "$k")"
  done
  if [ -n "$(kv_get .env MCI_JUPITER_API_KEY)" ]; then
    kv_set .env MCI_JUPITER_BASE_URL https://api.jup.ag
    kv_set .env MCI_JUPITER_REQUESTS_PER_SECOND 1
  else
    kv_set .env MCI_JUPITER_BASE_URL https://lite-api.jup.ag
  fi
  v=$(conf MCI_DASHBOARD_PASSWORD)
  if [ -n "$v" ]; then
    kv_set .env MCI_DASHBOARD_PASSWORD "$v"
  elif [ -z "$(kv_get .env MCI_DASHBOARD_PASSWORD)" ]; then
    new_password=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)
    kv_set .env MCI_DASHBOARD_PASSWORD "$new_password"
  fi
  if [ -n "$(kv_get .env DOMAIN)" ]; then kv_set .env COMPOSE_PROFILES web; else kv_set .env COMPOSE_PROFILES ""; fi
  if [ -z "$(conf MCI_TELEGRAM_BOT_TOKEN)" ] || [ -z "$(conf MCI_TELEGRAM_CHAT_IDS)" ]; then
    log "ATTENZIONE: token o chat id Telegram mancanti in $CONF (il bot gira lo stesso, senza notifiche)"
  fi

  duckdns_update

  log "costruisco l'immagine (la prima volta 3-8 minuti)"
  dc build >>"$LOG" 2>&1
  dc up -d db >>"$LOG" 2>&1
  local i
  for i in $(seq 1 60); do dc exec -T db pg_isready -U mci -d mci >/dev/null 2>&1 && break; sleep 2; done

  if [ "${MCI_IMPORT_STATE:-1}" = 1 ] && curl -fsSL -m 60 "$STATE_URL" -o "$BASE/state.json" 2>>"$LOG"; then
    chmod 644 "$BASE/state.json"
    log "importo lo stato del bot da GitHub (solo se il database è vuoto): $(dc run --rm --no-deps -T \
      -v "$BASE/state.json:/tmp/state.json:ro" worker mci state-import --file /tmp/state.json 2>>"$LOG" | tail -1)"
  fi

  dc up -d --remove-orphans >>"$LOG" 2>&1
  log "attendo che bot e API siano sani"
  if ! wait_healthy 600; then
    tg "❌ Installazione VPS: i servizi non sono partiti correttamente. Dettagli: sudo bash $APP/deploy/vps.sh status"
    exit 1
  fi

  if [ "${MCI_AUTO_UPDATE:-1}" = 1 ]; then
    cat >/etc/systemd/system/mci-update.service <<EOF
[Unit]
Description=Memecoin Intelligence - aggiornamento automatico da GitHub (solo versioni con CI verde)
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'cp $APP/deploy/vps.sh /run/mci-vps.sh && exec /bin/bash /run/mci-vps.sh update'
EOF
    cat >/etc/systemd/system/mci-update.timer <<'EOF'
[Unit]
Description=Memecoin Intelligence - controllo aggiornamenti ogni 10 minuti
[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
RandomizedDelaySec=60
[Install]
WantedBy=timers.target
EOF
    systemctl daemon-reload
    systemctl enable --now mci-update.timer >>"$LOG" 2>&1
  fi

  local domain url msg
  domain=$(kv_get .env DOMAIN)
  url=${domain:+https://$domain}
  msg="✅ VPS pronta: il bot gira 24/7 in modalità PAPER (nessun ordine reale).
Scanner ogni 60 s, controllo posizioni ogni 20 s, Pump.fun in tempo reale.
Aggiornamenti automatici: solo versioni con test superati, con ritorno automatico alla precedente se qualcosa non parte."
  if [ -n "$url" ]; then
    msg+="
Dashboard: $url  (utente: admin)"
    [ -n "$new_password" ] && msg+="
Password dashboard: $new_password
Salvala e poi cancella questo messaggio."
  else
    msg+="
Dashboard web non pubblicata: nessun DOMAIN impostato."
  fi
  tg "$msg"
  log "installazione completata. ${url:+Dashboard: $url}"
  echo "OK - installazione completata. Stato: sudo bash $APP/deploy/vps.sh status"
}

green_main_sha() { # newest commit on main whose CI passed (unauthenticated GitHub API, 6 calls/hour)
  curl -fsS -m 20 "https://api.github.com/repos/$REPO/actions/workflows/memecoin-ci.yml/runs?branch=main&status=success&per_page=1" |
    python3 -c 'import sys, json; r = json.load(sys.stdin).get("workflow_runs") or []; print(r[0]["head_sha"] if r else "")'
}

cmd_update() {
  need_root
  exec 9>/run/mci-update.lock
  flock -n 9 || exit 0
  duckdns_update
  cd "$SRC"
  git fetch -q origin main 2>>"$LOG" || { log "update: GitHub non raggiungibile, riprovo più tardi"; exit 0; }
  local cur target
  cur=$(git rev-parse HEAD)
  target=$(green_main_sha 2>>"$LOG") || { log "update: API GitHub non raggiungibile, riprovo più tardi"; exit 0; }
  [ -n "$target" ] && [ "$target" != "$cur" ] || { log "update: nessuna nuova versione"; exit 0; }
  git cat-file -e "$target^{commit}" 2>/dev/null || git fetch -q origin "$target" 2>>"$LOG" || exit 0
  if ! git merge-base --is-ancestor "$cur" "$target"; then log "update: ${target:0:7} non è successivo a ${cur:0:7}"; exit 0; fi
  if [ "${1:-}" = "--dry-run" ]; then log "update: disponibile ${cur:0:7} -> ${target:0:7} (dry run)"; exit 0; fi
  if git diff --quiet "$cur" "$target" -- memecoin-intelligence; then
    git -c advice.detachedHead=false checkout -q -f --detach "$target"
    exit 0
  fi
  log "update: ${cur:0:7} -> ${target:0:7}"
  git -c advice.detachedHead=false checkout -q -f --detach "$target"
  if dc up -d --build --remove-orphans >>"$LOG" 2>&1 && wait_healthy 480; then
    docker image prune -f >/dev/null 2>&1 || true
    docker builder prune -f --filter until=168h >/dev/null 2>&1 || true
    log "update: ok ${target:0:7}"
    # successful updates are silent by default (MCI_TELEGRAM_NOTIFY=trades: only buys and sells); failures always notify
    if [ "$(kv_get "$APP/.env" MCI_TELEGRAM_NOTIFY)" = all ]; then
      tg "🔄 Bot aggiornato alla versione ${target:0:7} (modalità PAPER)."
    fi
  else
    log "update: la nuova versione non è sana, torno a ${cur:0:7}"
    git -c advice.detachedHead=false checkout -q -f --detach "$cur"
    dc up -d --build --remove-orphans >>"$LOG" 2>&1 || true
    tg "⚠️ Aggiornamento ${target:0:7} non riuscito: ripristinata automaticamente la versione ${cur:0:7}."
  fi
}

cmd_status() {
  need_root
  echo "== versione: $(git -C "$SRC" log -1 --format='%h %cd %s' --date=short 2>/dev/null)"
  echo "== servizi"; dc ps
  echo "== salute API/bot: $(api_health || echo 'nessuna risposta')"
  echo "== modalità: $(kv_get "$APP/.env" MCI_TRADING_MODE)  profilo: $(kv_get "$APP/.env" MCI_RISK_PROFILE)"
  echo "== memoria"; free -m
  echo "== disco"; df -h / | tail -1
  echo "== timer aggiornamenti"; systemctl list-timers mci-update.timer --no-pager 2>/dev/null | head -3 || true
  echo "== ultime righe del log di installazione/aggiornamento"; tail -n 15 "$LOG"
}

case "${1:-}" in
  install) cmd_install ;;
  update) shift; cmd_update "$@" ;;
  status) cmd_status ;;
  *) echo "uso: sudo bash $0 install|update|status"; exit 2 ;;
esac
