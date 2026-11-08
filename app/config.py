"""Runtime settings, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _str(name: str, default: str) -> str:
    raw = os.getenv(name)
    return raw if raw not in (None, "") else default


def _list(name: str) -> tuple[str, ...]:
    return tuple(v.strip().rstrip("/") for v in os.getenv(name, "").split(",") if v.strip())


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
    # Rendered PNG cards, keyed by (league, gw, format).
    ttl_card: int = 300

    # Cache backend and size caps (cards are ~150-250 KB each).
    cache_backend: str = "memory"
    fpl_cache_max_items: int = 5000
    card_cache_max_items: int = 300

    # Shared secret between the website and this API. When set, every /api/leagues/*
    # request must carry it in X-Internal-Key, and X-Client-IP is trusted for rate limits.
    internal_api_key: str = ""
    # Per-client-IP limits (slowapi / "limits" syntax). Empty string disables.
    rate_limit_report: str = "30/minute"
    rate_limit_card: str = "120/minute"
    # "memory://" per process; "redis://host:6379" to share limits across instances.
    rate_limit_storage_uri: str = "memory://"

    # Browser origins allowed to call the API directly. The website proxies requests
    # server-side, so this is normally empty.
    cors_origins: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            fpl_base_url=_str("FPL_BASE_URL", cls.fpl_base_url),
            max_entries=_int("MAX_ENTRIES", cls.max_entries),
            fpl_concurrency=_int("FPL_CONCURRENCY", cls.fpl_concurrency),
            fpl_max_retries=_int("FPL_MAX_RETRIES", cls.fpl_max_retries),
            ttl_bootstrap=_int("TTL_BOOTSTRAP", cls.ttl_bootstrap),
            ttl_default=_int("TTL_DEFAULT", cls.ttl_default),
            ttl_card=_int("TTL_CARD", cls.ttl_card),
            cache_backend=_str("CACHE_BACKEND", cls.cache_backend),
            fpl_cache_max_items=_int("FPL_CACHE_MAX_ITEMS", cls.fpl_cache_max_items),
            card_cache_max_items=_int("CARD_CACHE_MAX_ITEMS", cls.card_cache_max_items),
            internal_api_key=os.getenv("INTERNAL_API_KEY", ""),
            rate_limit_report=os.getenv("RATE_LIMIT_REPORT", cls.rate_limit_report),
            rate_limit_card=os.getenv("RATE_LIMIT_CARD", cls.rate_limit_card),
            rate_limit_storage_uri=_str("RATE_LIMIT_STORAGE_URI", cls.rate_limit_storage_uri),
            cors_origins=_list("CORS_ORIGINS"),
        )
