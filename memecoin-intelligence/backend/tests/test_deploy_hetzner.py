"""deploy/hetzner_vps.py: picks the cheapest available EU server with enough RAM, validates secrets,
fills the cloud-config template and never buys twice. The Hetzner API is faked (shapes from the API docs)."""

import importlib.util
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "hetzner_vps.py"
TOKEN = "123456789:AAbbCCddEEffGGhhIIjjKKllMMnnOOppQQ"


def _load():
    spec = importlib.util.spec_from_file_location("hetzner_vps", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _price(loc, gross):
    return {"location": loc, "price_hourly": {"net": "0", "gross": "0"},
            "price_monthly": {"net": str(gross / 1.19), "gross": f"{gross:.4f}"}}


FAKE = {
    "/server_types?per_page=50": {"server_types": [
        {"id": 1, "name": "cx23", "cores": 2, "memory": 4.0, "disk": 40, "cpu_type": "shared", "architecture": "x86",
         "deprecation": None, "prices": [_price("fsn1", 5.49), _price("ash", 4.0)]},
        {"id": 2, "name": "cax11", "cores": 2, "memory": 4.0, "disk": 40, "cpu_type": "shared", "architecture": "arm",
         "deprecation": None, "prices": [_price("fsn1", 5.99), _price("hel1", 5.99)]},
        {"id": 3, "name": "cx11", "cores": 1, "memory": 2.0, "disk": 20, "cpu_type": "shared", "architecture": "x86",
         "deprecation": None, "prices": [_price("fsn1", 3.0)]},
        {"id": 4, "name": "ccx13", "cores": 2, "memory": 8.0, "disk": 80, "cpu_type": "dedicated",
         "architecture": "x86", "deprecation": None, "prices": [_price("fsn1", 15.0)]},
        {"id": 5, "name": "cpx22", "cores": 2, "memory": 4.0, "disk": 80, "cpu_type": "shared",
         "architecture": "x86", "deprecation": None, "prices": [_price("nbg1", 8.0)]},
    ]},
    # cx23 sold out in fsn1 (the 2026 situation), cax11 available in hel1, cpx22 in nbg1
    "/datacenters?per_page=50": {"datacenters": [
        {"location": {"name": "fsn1"}, "server_types": {"available": [3, 4]}},
        {"location": {"name": "hel1"}, "server_types": {"available": [2]}},
        {"location": {"name": "nbg1"}, "server_types": {"available": [5]}},
        {"location": {"name": "ash"}, "server_types": {"available": [1]}},
    ]},
    "/pricing": {"pricing": {"primary_ips": [{"type": "ipv4", "prices": [
        {"location": loc, "price_hourly": {"net": "0", "gross": "0"}, "price_monthly": {"net": "0.5", "gross": "0.60"}}
        for loc in ("fsn1", "nbg1", "hel1")]}]}},
    "/servers?name=memecoin-bot": {"servers": []},
}


@pytest.fixture()
def mod(monkeypatch):
    m = _load()
    calls = []

    def fake_call(method, path, body=None):
        calls.append((method, path, body))
        if method == "POST" and path == "/ssh_keys":
            return {"ssh_key": {"id": 77}}
        if method == "POST" and path == "/servers":
            return {"server": {"id": 991, "public_net": {"ipv4": {"ip": "203.0.113.7"}}}}
        return FAKE[path]

    monkeypatch.setattr(m, "call", fake_call)
    monkeypatch.setenv("HCLOUD_TOKEN", "hc-test")
    monkeypatch.setenv("MCI_TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("MCI_TELEGRAM_CHAT_IDS", "123456789")
    monkeypatch.delenv("MCI_JUPITER_API_KEY", raising=False)
    m.calls = calls
    return m


def test_cheapest_available_eu_server_with_enough_ram(mod):
    opts = mod.options(max_eur=10, min_ram_gb=4)
    assert [(o["type"], o["location"]) for o in opts] == [("cax11", "hel1"), ("cpx22", "nbg1")]
    assert opts[0]["total_eur"] == pytest.approx(6.59)  # server + IPv4
    assert "6.59 €/mese" in mod.describe(opts[0])
    assert mod.options(max_eur=6, min_ram_gb=4) == []  # price cap respected


def test_user_data_is_valid_cloud_config_with_secrets_filled(mod):
    cfg = yaml.safe_load(mod.user_data())
    content = cfg["write_files"][0]["content"]
    assert f"MCI_TELEGRAM_BOT_TOKEN={TOKEN}\n" in content and "MCI_TELEGRAM_CHAT_IDS=123456789\n" in content
    assert "INCOLLA_QUI" not in content
    assert cfg["write_files"][0]["permissions"] == "0600"


@pytest.mark.parametrize("var,value", [("MCI_TELEGRAM_BOT_TOKEN", ""), ("MCI_TELEGRAM_BOT_TOKEN", "x\nruncmd: [evil]"),
                                       ("MCI_TELEGRAM_CHAT_IDS", "12; rm -rf /")])
def test_bad_secrets_are_rejected(mod, monkeypatch, var, value):
    monkeypatch.setenv(var, value)
    with pytest.raises(SystemExit):
        mod.user_data()


def test_create_buys_the_chosen_server_once(mod, monkeypatch, tmp_path, capsys):
    pub = tmp_path / "k.pub"
    pub.write_text("ssh-ed25519 AAAA test")
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr("sys.argv", ["x", "create", "--max-eur", "10", "--ssh-pub", str(pub), "--key-name", "k"])
    mod.main()
    body = [b for m, p, b in mod.calls if m == "POST" and p == "/servers"][0]
    assert body["server_type"] == "cax11" and body["location"] == "hel1" and body["image"] == "ubuntu-24.04"
    assert body["ssh_keys"] == [77] and TOKEN in body["user_data"]
    assert "server_id=991" in out.read_text() and "ip=203.0.113.7" in out.read_text()
    assert TOKEN not in capsys.readouterr().out  # secrets never printed


def test_plan_buys_nothing_and_existing_server_is_never_duplicated(mod, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["x", "plan"])
    mod.main()
    assert not [c for c in mod.calls if c[0] == "POST"]
    FAKE_EXISTING = {"servers": [{"server_type": {"name": "cax11"}, "public_net": {"ipv4": {"ip": "203.0.113.7"}}}]}
    orig = mod.call
    monkeypatch.setattr(mod, "call", lambda m, p, b=None: FAKE_EXISTING if p == "/servers?name=memecoin-bot" else orig(m, p, b))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "o"))
    monkeypatch.setattr("sys.argv", ["x", "create", "--ssh-pub", "/nonexistent", "--key-name", "k"])
    with pytest.raises(SystemExit):
        mod.main()
    assert "exists=1" in (tmp_path / "o").read_text()
    assert not [c for c in mod.calls if c[0] == "POST"]
