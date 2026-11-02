"""Brand settings for rendered cards. Override any of these with env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _hex(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise ValueError(f"Bad hex colour: {value!r}")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


@dataclass(frozen=True)
class Brand:
    site_name: str = "Mini-League Report"
    handle: str = "@your_handle"
    site_url: str = "yoursite.com"
    primary: str = "#FF5A36"  # vermilion
    accent: str = "#FFC83D"  # amber
    background: str = "#0E1116"
    surface: str = "#181C24"
    text: str = "#F5F7FA"
    muted: str = "#9AA4B2"

    @classmethod
    def from_env(cls) -> "Brand":
        def env(name: str, default: str) -> str:
            return os.getenv(name) or default

        b = cls(
            site_name=env("BRAND_SITE_NAME", cls.site_name),
            handle=env("BRAND_HANDLE", cls.handle),
            site_url=env("BRAND_SITE_URL", cls.site_url),
            primary=env("BRAND_PRIMARY", cls.primary),
            accent=env("BRAND_ACCENT", cls.accent),
        )
        for c in (b.primary, b.accent):
            _hex(c)  # fail fast on a typo in the env
        return b

    def rgb(self, name: str) -> tuple[int, int, int]:
        return _hex(getattr(self, name))
