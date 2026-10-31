"""Runtime configuration — everything comes from environment variables (or a local .env file).

No secret is ever hard-coded. See ``.env.example`` at the project root.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ROOT / "backend" / ".env"),
                                      env_file_encoding="utf-8", extra="ignore")

    # --- data providers -------------------------------------------------------------
    api_football_key: str | None = Field(default=None, description="API-Football (api-sports.io) key")
    api_football_base_url: str = "https://v3.football.api-sports.io"
    # set to "rapidapi" if the key was issued through RapidAPI
    api_football_mode: str = "direct"
    the_odds_api_key: str | None = None
    the_odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    the_odds_api_regions: str = "eu,uk"
    the_odds_api_markets: str = "h2h,totals"
    the_odds_api_min_interval_s: int = 120  # credits are expensive: poll less often

    # --- scanner --------------------------------------------------------------------
    poll_interval_s: int = Field(default=45, ge=30, le=60)
    scanner_enabled: bool = True
    league_whitelist: str = ""  # comma separated API-Football league ids; empty = all
    max_fixtures_per_cycle: int = 120
    form_cache_hours: int = 12
    odds_max_age_s: int = 90  # odds older than this are considered stale and never shown

    # --- value filters --------------------------------------------------------------
    min_odds: float = 1.75
    min_ev: float = 0.03  # minimum EV after prudential margin
    min_edge: float = 0.03  # p_conservative - implied probability
    max_model_market_gap: float = 0.18  # |p_model - p_market_fair| above this = anomaly, never shown
    n_param_draws: int = 200
    conservative_quantile: float = 0.10
    min_minute: int = 5  # do not evaluate before this minute (too little in-play information)
    max_minute_h2: int = 88  # do not evaluate after this minute of the 2nd half (odds/suspension risk)

    # --- storage --------------------------------------------------------------------
    database_url: str = f"sqlite:///{ROOT / 'backend' / 'data' / 'scanner.db'}"
    model_path: str = str(ROOT / "backend" / "models" / "inplay_model.json")
    prediction_log_every_s: int = 300  # full market snapshot per fixture every N seconds

    # --- server ---------------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_dist: str = str(ROOT / "frontend" / "dist")

    @property
    def leagues(self) -> set[int]:
        return {int(x) for x in self.league_whitelist.split(",") if x.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
