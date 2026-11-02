"""Runtime settings, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    # Free tier: only the top N managers of a league are analysed.
    max_entries: int = 50
    # Max simultaneous requests to the FPL API.
    fpl_concurrency: int = 5
    fpl_max_retries: int = 3
    fpl_timeout_seconds: float = 10.0
    # Cache TTLs (seconds). Static data changes rarely; GW data changes during live GWs.
    ttl_bootstrap: int = 3600
    ttl_default: int = 300

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            fpl_base_url=os.getenv("FPL_BASE_URL", cls.fpl_base_url),
            max_entries=_int("MAX_ENTRIES", cls.max_entries),
            fpl_concurrency=_int("FPL_CONCURRENCY", cls.fpl_concurrency),
            fpl_max_retries=_int("FPL_MAX_RETRIES", cls.fpl_max_retries),
            ttl_bootstrap=_int("TTL_BOOTSTRAP", cls.ttl_bootstrap),
            ttl_default=_int("TTL_DEFAULT", cls.ttl_default),
        )
