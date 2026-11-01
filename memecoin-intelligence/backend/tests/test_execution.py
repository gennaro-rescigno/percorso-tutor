from pathlib import Path

import pytest

from mci.collectors.jupiter import Quote
from mci.config import LIVE_TRADING_CONFIRMATION_PHRASE, Settings
from mci.execution.base import TradeRequest
from mci.execution.costs import CostModel
from mci.execution.live import LiveExecutor, LiveTradingBlocked
from mci.execution.paper import PaperExecutor
from mci.execution.wallet import WalletError, load_wallet


class FakeJup:
    def __init__(self, buy_out=None, sell_out=None, decimals=6):
        self.buy_out, self.sell_out, self.dec = buy_out, sell_out, decimals

    def known_decimals(self, mint):
        return self.dec

    def remember_decimals(self, m, d):
        pass

    async def buy_quote(self, mint, sol, slip=300):
        if self.buy_out is None:
            return None
        return Quote("SOL", mint, int(sol * 1e9), self.buy_out, self.buy_out, 0.01, slip, ["X"], {})

    async def sell_quote(self, mint, raw, slip=300):
        if self.sell_out is None:
            return None
        return Quote(mint, "SOL", raw, self.sell_out, self.sell_out, 0.02, slip, ["X"], {})


@pytest.mark.asyncio
async def test_paper_buy_uses_real_quote():
    ex = PaperExecutor(CostModel(), FakeJup(buy_out=10_000 * 10**6), failure_rate=0.0, landing_slippage_pct=0.0)
    r = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.1, reference_price=0.1 / 10_500))
    assert r.ok and r.fill.quote_source == "jupiter"
    assert r.fill.qty == pytest.approx(10_000)
    assert r.fill.price == pytest.approx(0.1 / 10_000)
    assert r.fill.rent_sol > 0 and r.fill.network_fee_sol > 0
    assert r.fill.slippage_sol > 0  # filled worse than the reference price


@pytest.mark.asyncio
async def test_paper_falls_back_to_amm_model_then_fails_without_data():
    ex = PaperExecutor(CostModel(), FakeJup(buy_out=None), failure_rate=0.0)
    r = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.1, reference_price=1e-5, reserve_sol=200))
    assert r.ok and r.fill.quote_source == "amm_model"
    r2 = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.1))
    assert not r2.ok  # never invents a price


@pytest.mark.asyncio
async def test_paper_sell_no_route_rug_scenario():
    ex = PaperExecutor(CostModel(), FakeJup(sell_out=None), failure_rate=0.0)
    r = await ex.execute(TradeRequest(token="M", side="sell", qty=1000, reference_price=1e-5))
    assert not r.ok and "rug" in r.error


@pytest.mark.asyncio
async def test_paper_simulated_failure_charges_fee():
    ex = PaperExecutor(CostModel(), FakeJup(buy_out=1), failure_rate=1.0)
    r = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.1))
    assert not r.ok and r.simulated_failure and r.fill.network_fee_sol > 0


def test_live_executor_blocked_by_default():
    with pytest.raises(LiveTradingBlocked):
        LiveExecutor(Settings(), CostModel(), None, None)  # type: ignore[arg-type]


def test_live_gates_require_everything(tmp_path):
    s = Settings(trading_mode="live", live_trading_enabled=True)
    assert any("frase" in r for r in s.live_gate_failures())
    s2 = Settings(trading_mode="live", live_trading_enabled=True,
                  live_trading_confirmation=LIVE_TRADING_CONFIRMATION_PHRASE, live_wallet_keyfile=str(tmp_path / "nope.json"))
    assert any("non trovato" in r for r in s2.live_gate_failures())


class _W:
    pubkey = "PUB"


def _live(tmp_path, **kw):
    key = tmp_path / "k.json"
    key.write_text("[]")
    s = Settings(trading_mode="live", live_trading_enabled=True, live_trading_confirmation=LIVE_TRADING_CONFIRMATION_PHRASE,
                 live_wallet_keyfile=str(key), **kw)
    return LiveExecutor(s, CostModel(), FakeJup(), None, wallet=_W())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_live_spend_limits_and_duplicates(tmp_path):
    ex = _live(tmp_path, live_max_spend_per_trade_sol=0.1, live_max_daily_spend_sol=0.15)
    r = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.5, client_order_id="a"))
    assert not r.ok and "limite per operazione" in r.error
    r = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.05, client_order_id=""))
    assert not r.ok and "client_order_id" in r.error
    ex.spend.sent_ids.add("dup")
    r = await ex.execute(TradeRequest(token="M", side="buy", sol_amount=0.05, client_order_id="dup"))
    assert not r.ok and "duplicato" in r.error
    ex.spend.spent_today, ex.spend.day = 0.12, __import__("mci.domain", fromlist=["utcnow"]).utcnow().date().isoformat()
    r = await ex.execute(TradeRequest(token="N", side="buy", sol_amount=0.05, client_order_id="b"))
    assert not r.ok and "giornaliero" in r.error
    ex.kill("test")
    r = await ex.execute(TradeRequest(token="N", side="sell", qty=1, client_order_id="c"))
    assert not r.ok and "bloccata" in r.error


def test_wallet_must_live_outside_repo_and_be_private(tmp_path):
    inside = Path(__file__).resolve().parents[1] / "tmp_key_test.json"
    try:
        inside.write_text("[]")
        with pytest.raises(WalletError, match="repository"):
            load_wallet(str(inside))
    finally:
        inside.unlink(missing_ok=True)
    k = tmp_path / "k.json"
    k.write_text("[]")
    k.chmod(0o644)
    with pytest.raises(WalletError, match="permessi"):
        load_wallet(str(k))
