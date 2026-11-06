"""Run the real API against the offline FakeFPL league (no FPL traffic).

Used for frontend development and the web e2e tests:

    python -m scripts.fake_server            # http://127.0.0.1:8000
    PORT=8001 python -m scripts.fake_server

League 424242 is the fixture league (GW 1-10 available); any other ID returns 404.
League 500500 is a 100-manager league to exercise the "top 50" state.
"""
from __future__ import annotations

import os

import uvicorn

from app.main import create_app
from tests.fake_fpl import LEAGUE_ID, FakeFPL, build_fixtures

BIG_LEAGUE_ID = 500500


class MultiLeagueFake(FakeFPL):
    """FakeFPL serving the normal fixture league plus a big one."""

    def __init__(self):
        super().__init__()
        self.big = FakeFPL(build_fixtures(extra_managers=94))
        self.big.fx["league"]["name"] = "Big Public League"

    async def league_standings(self, league_id, page=1):
        if league_id == BIG_LEAGUE_ID:
            return await self.big.league_standings(LEAGUE_ID, page)
        return await super().league_standings(league_id, page)

    async def entry_picks(self, entry_id, gw):
        if entry_id >= 200:
            return await self.big.entry_picks(entry_id, gw)
        return await super().entry_picks(entry_id, gw)


def main() -> None:
    app = create_app()
    app.state.fpl = MultiLeagueFake()
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")), log_level="warning")


if __name__ == "__main__":
    main()
