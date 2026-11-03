"""Central configuration.

All values can be overridden with environment variables prefixed with ``MCI_``
(see ``.env.example``). Secrets are typed as ``SecretStr`` so they are never
printed by accident (``repr`` shows ``**********``).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Phrase the user must set *exactly* to unlock live trading (together with other gates).
LIVE_TRADING_CONFIRMATION_PHRASE = "I UNDERSTAND I CAN LOSE ALL FUNDS IN THE DEDICATED WALLET"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- general -----------------------------------------------------------------
    env: Literal["dev", "prod", "test"] = "dev"
    run_mode: Literal["server", "github"] = "server"  # github = scheduled windows on GitHub Actions
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/mci.db"
    chain: str = "solana"

    # --- capital & risk -----------------------------------------------------------
    initial_capital_sol: float = 2.0
    risk_profile: Literal["conservative", "moderate", "aggressive"] = "moderate"
    enabled_strategies: str = "A,B,C,D,E"

    # --- trading mode -------------------------------------------------------------
    # 'paper' is the default. 'live' is only honoured if ALL live gates pass.
    trading_mode: Literal["paper", "live"] = "paper"
    live_trading_enabled: bool = False
    live_trading_confirmation: str = ""
    live_wallet_keyfile: str = ""  # path to a JSON keypair file OUTSIDE the repo (chmod 600)
    live_max_spend_per_trade_sol: float = 0.1
    live_max_daily_spend_sol: float = 0.5
    live_max_per_token_sol: float = 0.2
    live_min_wallet_reserve_sol: float = 0.05  # always keep for fees/rent

    # --- data sources -------------------------------------------------------------
    dexscreener_base_url: str = "https://api.dexscreener.com"
    geckoterminal_base_url: str = "https://api.geckoterminal.com/api/v2"
    # the public limit is not published; 25/min with bursts got 429 on a dedicated VPS IP (Nov 2026).
    # This is the ceiling: the scanner halves it on every 429 and raises it slowly after successes.
    geckoterminal_calls_per_minute: int = 12
    jupiter_base_url: str = "https://lite-api.jup.ag"
    jupiter_api_key: SecretStr = SecretStr("")
    jupiter_requests_per_second: float = 0.5  # keyless limit documented in 2026
    rugcheck_base_url: str = "https://api.rugcheck.xyz"
    pumpportal_ws_url: str = "wss://pumpportal.fun/api/data"
    pumpportal_enabled: bool = True
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    solana_rpc_rps: float = 2.0  # public endpoint: 100 requests / 10 s per IP; we stay far below
    # free real-time pump.fun data: public Solana WebSocket, logsSubscribe on the pump program (no key, no cost)
    solana_ws_url: str = "wss://api.mainnet-beta.solana.com"
    chain_stream_enabled: bool = True
    onchain_enabled: bool = True  # own on-chain security checks, curve state, wallet intelligence
    experiments_enabled: bool = True  # shadow experiments x_safe and x_curve (virtual portfolios)
    # PumpPortal trade subscriptions now require an API key funded with SOL (paid): disabled, replaced by the
    # free chain stream. New-token events (free) are still used.
    pumpportal_trades_enabled: bool = False
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    kraken_base_url: str = "https://api.kraken.com"

    # Optional social sources (all disabled unless credentials are provided)
    reddit_client_id: str = ""
    reddit_client_secret: SecretStr = SecretStr("")
    reddit_user_agent: str = "mci/0.1 (personal research bot)"
    telegram_public_scrape_enabled: bool = False

    # Optional: Dune (free account) to import a survivorship-free historical universe of launches
    dune_api_key: SecretStr = SecretStr("")
    data_dir: str = "data"

    # --- scanner ------------------------------------------------------------------
    scan_interval_seconds: int = 60
    position_monitor_interval_seconds: int = 20
    max_tracked_tokens: int = 400
    candidate_pool_size: int = 30  # tokens enriched with expensive calls per cycle
    min_liquidity_usd_track: float = 5_000.0

    # --- execution cost model -----------------------------------------------------
    priority_fee_sol: float = 0.0001
    jito_tip_sol: float = 0.0
    default_slippage_bps: int = 300
    signal_detection_delay_seconds: int = 20

    # --- telegram -----------------------------------------------------------------
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_ids: str = ""  # comma separated list of allowed chat ids
    telegram_min_score_alert: float = 75.0
    # trades = only buys and sells (full or partial); all = also signals, token alerts, daily report, notices.
    # Command replies (/status, /daily, ...) are always sent.
    telegram_notify: Literal["trades", "all"] = "trades"
    # Laboratorio: second virtual paper portfolio without risk limits (dashboard page "Laboratorio")
    lab_enabled: bool = True
    telegram_alert_cooldown_minutes: int = 240

    # --- dashboard / api ----------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    dashboard_username: str = "admin"
    dashboard_password: SecretStr = SecretStr("")
    api_secret_key: SecretStr = SecretStr("")
    api_token_ttl_hours: int = 24
    frontend_dist_dir: str = str(Path(__file__).resolve().parents[2] / "frontend" / "dist")

    # --- reports ------------------------------------------------------------------
    daily_report_hour_utc: int = 21
    timezone: str = "Europe/Rome"

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Neon/Supabase/Render give postgres:// URLs; SQLAlchemy+psycopg3 wants postgresql+psycopg://
        if v.startswith("postgres://"):
            v = "postgresql+psycopg://" + v[len("postgres://"):]
        elif v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    # --- helpers ------------------------------------------------------------------
    @property
    def allowed_chat_ids(self) -> set[int]:
        out: set[int] = set()
        for part in self.telegram_chat_ids.split(","):
            part = part.strip()
            if part:
                try:
                    out.add(int(part))
                except ValueError:
                    continue
        return out

    @property
    def strategies(self) -> list[str]:
        return [s.strip().upper() for s in self.enabled_strategies.split(",") if s.strip()]

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token.get_secret_value()) and bool(self.allowed_chat_ids)

    def live_gate_failures(self) -> list[str]:
        """Return the list of reasons why live trading is NOT allowed (empty = allowed)."""
        reasons: list[str] = []
        if self.trading_mode != "live":
            reasons.append("trading_mode non è 'live'")
        if not self.live_trading_enabled:
            reasons.append("MCI_LIVE_TRADING_ENABLED non è true")
        if self.live_trading_confirmation != LIVE_TRADING_CONFIRMATION_PHRASE:
            reasons.append("frase di conferma MCI_LIVE_TRADING_CONFIRMATION mancante o errata")
        if not self.live_wallet_keyfile:
            reasons.append("MCI_LIVE_WALLET_KEYFILE non configurato")
        elif not Path(self.live_wallet_keyfile).exists():
            reasons.append("file della chiave del wallet dedicato non trovato")
        return reasons


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


# DEX fee assumptions per venue (fraction per side). Sources conflict (see RESEARCH_REPORT §2.2),
# so values are deliberately conservative and configurable.
VENUE_FEES: dict[str, float] = {
    "pumpfun": 0.0125,      # bonding curve, 1.25% total (conservative of conflicting sources)
    "pump": 0.0125,
    "pumpswap": 0.010,      # tiered 1.25% -> 0.30% by market cap; refined in costs.dex_fee()
    "raydium": 0.0025,
    "raydium-clmm": 0.0025,
    "raydium-cpmm": 0.0025,
    "meteora": 0.0050,
    "meteoradbc": 0.0100,
    "orca": 0.0030,
    "letsbonk": 0.0100,
    "default": 0.0100,
}
