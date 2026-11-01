"""LIVE executor (DISABLED by default).

Can only be constructed when every gate in ``Settings.live_gate_failures()`` passes:
mode=live + MCI_LIVE_TRADING_ENABLED=true + the exact confirmation phrase + a
dedicated keypair file outside the repo. On top of that each order checks:

* kill switch and automatic block after consecutive errors;
* per-trade, daily and per-token spend limits;
* wallet balance before the operation (keeping a SOL reserve for fees/rent);
* duplicate protection: the same ``client_order_id`` is never sent twice and a
  second order for the same token+side within a short window is refused;
* on-chain confirmation polling; unconfirmed -> reported as failed/unknown, never as filled.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from mci.collectors.jupiter import JupiterCollector
from mci.collectors.solana_rpc import SolanaRpc
from mci.config import Settings
from mci.domain import LAMPORTS_PER_SOL, Fill, utcnow
from mci.execution.base import ExecResult, Executor, TradeRequest
from mci.execution.costs import CostModel, dex_fee
from mci.execution.wallet import DedicatedWallet, load_wallet
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)


class LiveTradingBlocked(Exception):
    pass


@dataclass
class SpendTracker:
    day: str = ""
    spent_today: float = 0.0
    per_token: dict[str, float] = field(default_factory=dict)
    sent_ids: set[str] = field(default_factory=set)
    recent: dict[tuple[str, str], float] = field(default_factory=dict)  # (token, side) -> monotonic time

    def roll(self) -> None:
        d = utcnow().date().isoformat()
        if d != self.day:
            self.day, self.spent_today = d, 0.0


class LiveExecutor(Executor):
    mode = "live"
    MAX_CONSECUTIVE_ERRORS = 3
    DUPLICATE_WINDOW_S = 60

    def __init__(self, settings: Settings, costs: CostModel, jupiter: JupiterCollector, rpc: SolanaRpc,
                 wallet: DedicatedWallet | None = None):
        failures = settings.live_gate_failures()
        if failures:
            raise LiveTradingBlocked("trading reale bloccato: " + "; ".join(failures))
        self.s = settings
        self.costs = costs
        self.jupiter = jupiter
        self.rpc = rpc
        self.wallet = wallet or load_wallet(settings.live_wallet_keyfile)
        self.spend = SpendTracker()
        self.consecutive_errors = 0
        self.blocked_reason: str | None = None

    def kill(self, reason: str) -> None:
        self.blocked_reason = reason

    # ------------------------------------------------------------------ guards
    def _check_limits(self, req: TradeRequest) -> str | None:
        if self.blocked_reason:
            return f"esecuzione reale bloccata: {self.blocked_reason}"
        if not req.client_order_id:
            return "client_order_id mancante"
        if req.client_order_id in self.spend.sent_ids:
            return "ordine duplicato (client_order_id già inviato)"
        key = (req.token, req.side)
        last = self.spend.recent.get(key)
        if last and time.monotonic() - last < self.DUPLICATE_WINDOW_S:
            return "ordine ripetuto sullo stesso token troppo ravvicinato"
        if req.side == "buy":
            amt = float(req.sol_amount or 0)
            self.spend.roll()
            if amt > self.s.live_max_spend_per_trade_sol:
                return f"importo {amt} SOL oltre il limite per operazione ({self.s.live_max_spend_per_trade_sol})"
            if self.spend.spent_today + amt > self.s.live_max_daily_spend_sol:
                return "limite di spesa giornaliero raggiunto"
            if self.spend.per_token.get(req.token, 0.0) + amt > self.s.live_max_per_token_sol:
                return "limite per singolo token raggiunto"
        return None

    async def _confirm(self, sig: str, timeout_s: float = 60.0) -> tuple[bool, str]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                st = await self.rpc.signature_status(sig)
            except SourceUnavailable:
                st = None
            if st:
                if st.get("err"):
                    return False, f"transazione fallita on-chain: {st['err']}"
                if st.get("confirmationStatus") in ("confirmed", "finalized"):
                    return True, st["confirmationStatus"]
            await asyncio.sleep(2)
        return False, "conferma non ricevuta entro il timeout (stato sconosciuto: verificare manualmente)"

    # ------------------------------------------------------------------ execute
    async def execute(self, req: TradeRequest) -> ExecResult:
        problem = self._check_limits(req)
        if problem:
            return ExecResult(False, error=problem)
        try:
            return await self._execute(req)
        except Exception as e:  # any unexpected error counts towards the automatic block
            self._on_error(f"{type(e).__name__}")
            return ExecResult(False, error=f"errore di esecuzione: {type(e).__name__}")

    def _on_error(self, msg: str) -> None:
        self.consecutive_errors += 1
        log.error("live execution error: %s", msg)
        if self.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
            self.blocked_reason = f"{self.consecutive_errors} errori consecutivi"

    async def _execute(self, req: TradeRequest) -> ExecResult:
        pub = self.wallet.pubkey
        balance = await self.rpc.balance_sol(pub)
        fee_reserve = self.s.live_min_wallet_reserve_sol
        if req.side == "buy":
            amt = float(req.sol_amount or 0)
            if balance - amt < fee_reserve:
                return ExecResult(False, error=f"saldo insufficiente ({balance:.4f} SOL, riserva {fee_reserve} SOL)")
            q = await self.jupiter.buy_quote(req.token, amt, req.slippage_bps)
        else:
            if balance < 0.003:
                return ExecResult(False, error="SOL insufficienti per le commissioni")
            raw_balance = await self.rpc.token_balance_raw(pub, req.token)
            dec = req.decimals if req.decimals is not None else self.jupiter.known_decimals(req.token)
            if dec is None:
                return ExecResult(False, error="decimali del token sconosciuti")
            want = int(float(req.qty or 0) * 10**dec)
            amount = min(want, raw_balance)
            if amount <= 0:
                return ExecResult(False, error="nessun saldo del token da vendere")
            q = await self.jupiter.sell_quote(req.token, amount, req.slippage_bps)
        if q is None or q.out_amount <= 0:
            return ExecResult(False, error="nessuna rotta di swap disponibile")
        if q.price_impact_pct > 0.05:
            return ExecResult(False, error=f"impatto di prezzo {q.price_impact_pct:.1%} oltre il limite di sicurezza")

        prio_lamports = int(self.costs.priority_fee_sol * LAMPORTS_PER_SOL)
        tx_b64 = await self.jupiter.swap_transaction(q, pub, prio_lamports)
        signed = self.wallet.sign_versioned_tx(tx_b64)
        self.spend.sent_ids.add(req.client_order_id)
        self.spend.recent[(req.token, req.side)] = time.monotonic()
        sig = await self.rpc.send_transaction(signed)
        ok, status = await self._confirm(sig)
        if not ok:
            self._on_error(status)
            return ExecResult(False, error=status, tx_signature=sig)
        self.consecutive_errors = 0
        fee_pct = dex_fee(req.dex_id, req.market_cap_usd)
        if req.side == "buy":
            amt = float(req.sol_amount or 0)
            self.spend.spent_today += amt
            self.spend.per_token[req.token] = self.spend.per_token.get(req.token, 0.0) + amt
            dec = self.jupiter.known_decimals(req.token) or req.decimals or 0
            qty = q.out_amount / 10**dec if dec else float(q.out_amount)
            fill = Fill(side="buy", qty=qty, price=amt / qty if qty else 0.0, sol_amount=amt, dex_fee_sol=amt * fee_pct,
                        network_fee_sol=self.costs.network_fee_sol,
                        slippage_sol=amt - amt * fee_pct - qty * (req.reference_price or 0),
                        price_impact_pct=q.price_impact_pct, quote_source="live_quote",
                        rent_sol=self.costs.ata_rent_sol if req.first_buy else 0.0)
        else:
            out = q.out_amount / LAMPORTS_PER_SOL
            qty = float(req.qty or 0)
            fill = Fill(side="sell", qty=qty, price=out / qty if qty else 0.0, sol_amount=out, dex_fee_sol=out * fee_pct,
                        network_fee_sol=self.costs.network_fee_sol,
                        slippage_sol=qty * (req.reference_price or 0) - out - out * fee_pct,
                        price_impact_pct=q.price_impact_pct, quote_source="live_quote")
        # NOTE: amounts above come from the quote. A production hardening step is to parse the
        # confirmed transaction's pre/post balances; until then fills are flagged as quote-based.
        return ExecResult(True, fill=fill, tx_signature=sig, extra={"confirmation": status, "fill_basis": "quote"})
