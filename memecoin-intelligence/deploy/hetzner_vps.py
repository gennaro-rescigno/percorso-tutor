#!/usr/bin/env python3
"""Create the bot's VPS on the owner's Hetzner Cloud account (used by the memecoin-vps-create workflow).

  plan        cheapest available option (>= 4 GB RAM, EU) with its monthly price; buys nothing
  create      creates the server "memecoin-bot" with deploy/cloud-config.yaml (PAID: run only with consent)
  delete-key  removes the temporary SSH key used to verify the installation

Environment (GitHub secrets): HCLOUD_TOKEN, MCI_TELEGRAM_BOT_TOKEN, MCI_TELEGRAM_CHAT_IDS, MCI_JUPITER_API_KEY (opt.).
Secrets are validated and never printed; only the standard library is used.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.hetzner.cloud/v1"
EU_LOCATIONS = ("fsn1", "nbg1", "hel1")
NAME = "memecoin-bot"
TEMPLATE = Path(__file__).with_name("cloud-config.yaml")


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['HCLOUD_TOKEN']}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        sys.exit(f"Errore API Hetzner {e.code} su {method} {path}: {detail}")


def _eur(x) -> float:
    return float(x or 0)


def ipv4_monthly_gross() -> dict[str, float]:
    """Primary IPv4 is billed separately; returns location -> gross €/month (empty if the API shape differs)."""
    out: dict[str, float] = {}
    try:
        for ip in call("GET", "/pricing")["pricing"].get("primary_ips", []):
            if ip.get("type") == "ipv4":
                for p in ip.get("prices", []):
                    out[p["location"]] = _eur(p["price_monthly"]["gross"])
    except (KeyError, TypeError):
        pass
    return out


def available_locations(t: dict) -> set[str]:
    """Locations where a server type can be ordered now. Since 2026 the API reports this per server type
    (server_types[].locations[].available); the old /datacenters endpoint answers 410 Gone."""
    out = set()
    for entry in t.get("locations") or []:
        name = entry.get("name") or (entry.get("location") or {}).get("name")
        if name and entry.get("available", False) and not entry.get("deprecation"):
            out.add(name)
    return out


def options(max_eur: float, min_ram_gb: float) -> list[dict]:
    types = call("GET", "/server_types?per_page=50")["server_types"]
    ipv4 = ipv4_monthly_gross()
    out = []
    for t in types:
        if t.get("deprecation") or t.get("deprecated") or t.get("cpu_type") != "shared" or t["memory"] < min_ram_gb:
            continue
        where = available_locations(t)
        for p in t["prices"]:
            loc = p["location"]
            if loc not in EU_LOCATIONS or loc not in where:
                continue
            server = _eur(p["price_monthly"]["gross"])
            total = server + ipv4.get(loc, 0.0)
            if total <= max_eur:
                out.append({"type": t["name"], "location": loc, "cores": t["cores"], "memory": t["memory"],
                            "disk": t["disk"], "arch": t.get("architecture", "x86"), "server_eur": server,
                            "ipv4_eur": ipv4.get(loc), "total_eur": total})
    return sorted(out, key=lambda o: (o["total_eur"], -o["memory"]))


def describe(o: dict) -> str:
    ip = f" + IPv4 {o['ipv4_eur']:.2f} €" if o["ipv4_eur"] is not None else " (IPv4 non incluso: prezzo non letto)"
    return (f"{o['type']} a {o['location']}: {o['cores']} vCPU, {o['memory']:g} GB RAM, {o['disk']} GB disco, "
            f"{o['arch']} — server {o['server_eur']:.2f} €{ip} = {o['total_eur']:.2f} €/mese IVA inclusa (pagamento a ore)")


def user_data() -> str:
    token = os.environ.get("MCI_TELEGRAM_BOT_TOKEN", "").strip()
    chats = os.environ.get("MCI_TELEGRAM_CHAT_IDS", "").strip()
    jup = os.environ.get("MCI_JUPITER_API_KEY", "").strip()
    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{20,}", token):
        sys.exit("Il secret MCI_TELEGRAM_BOT_TOKEN manca o non ha il formato di un token di BotFather")
    if not re.fullmatch(r"-?\d+(,\s*-?\d+)*", chats):
        sys.exit("Il secret MCI_TELEGRAM_CHAT_IDS manca o non è un elenco di numeri")
    if not re.fullmatch(r"[A-Za-z0-9_-]*", jup):
        sys.exit("Il secret MCI_JUPITER_API_KEY contiene caratteri non validi")
    text = TEMPLATE.read_text()
    for placeholder, value in (("INCOLLA_QUI_IL_TOKEN_DI_BOTFATHER", token), ("INCOLLA_QUI_IL_TUO_CHAT_ID", chats)):
        assert placeholder in text
        text = text.replace(placeholder, value)
    if jup:
        text = text.replace("MCI_JUPITER_API_KEY=\n", f"MCI_JUPITER_API_KEY={jup}\n", 1)
    return text


def gh_output(**kv) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["plan", "create", "delete-key"])
    ap.add_argument("--max-eur", type=float, default=10.0)
    ap.add_argument("--min-ram", type=float, default=4.0)
    ap.add_argument("--ssh-pub")
    ap.add_argument("--key-name")
    ap.add_argument("--key-id")
    a = ap.parse_args()
    if not os.environ.get("HCLOUD_TOKEN"):
        sys.exit("Manca il secret HCLOUD_TOKEN (Hetzner → progetto → Security → API tokens, permessi Read & Write)")

    if a.action == "delete-key":
        call("DELETE", f"/ssh_keys/{int(a.key_id)}")
        print("chiave temporanea rimossa dall'account Hetzner")
        return

    existing = call("GET", f"/servers?name={NAME}")["servers"]
    if existing:
        s = existing[0]
        print(f"Esiste già un server '{NAME}' ({s['server_type']['name']}, IP {s['public_net']['ipv4']['ip']}): "
              "non ne creo un secondo.")
        if a.action == "create":
            gh_output(exists=1)
            sys.exit(1)
        return
    opts = options(a.max_eur, a.min_ram)
    if not opts:
        print("Disponibilità attuale dei tipi condivisi in Europa (per capire perché nessuno va bene):")
        for t in call("GET", "/server_types?per_page=50")["server_types"]:
            if t.get("cpu_type") == "shared":
                prices = {p["location"]: _eur(p["price_monthly"]["gross"]) for p in t["prices"]}
                where = sorted(available_locations(t) & set(EU_LOCATIONS))
                print(f"  {t['name']}: {t['memory']:g} GB, disponibile in {where or 'nessuna location UE'}, "
                      f"prezzi {prices}")
        sys.exit(f"Nessun server con almeno {a.min_ram:g} GB di RAM disponibile in Europa entro {a.max_eur:.2f} €/mese.")
    print("Opzioni disponibili ora (dalla più economica):")
    for o in opts[:6]:
        print("  - " + describe(o))
    best = opts[0]
    print(f"SCELTA: {describe(best)}")
    if a.action == "plan":
        user_data()  # validates the Telegram secrets now, so 'create' cannot fail on them later
        print("Nessun acquisto effettuato (solo piano). I secret Telegram sono presenti e validi.")
        return

    ud = user_data()
    key = call("POST", "/ssh_keys", {"name": a.key_name, "public_key": Path(a.ssh_pub).read_text().strip()})["ssh_key"]
    gh_output(key_id=key["id"])
    r = call("POST", "/servers", {
        "name": NAME, "server_type": best["type"], "location": best["location"], "image": "ubuntu-24.04",
        "user_data": ud, "ssh_keys": [key["id"]], "start_after_create": True,
        "public_net": {"enable_ipv4": True, "enable_ipv6": True}, "labels": {"app": "memecoin-intelligence"},
    })
    srv = r["server"]
    ip = srv["public_net"]["ipv4"]["ip"]
    gh_output(server_id=srv["id"], ip=ip)
    print(f"Server creato: id {srv['id']}, IP {ip}. L'installazione automatica parte al primo avvio.")


if __name__ == "__main__":
    main()
