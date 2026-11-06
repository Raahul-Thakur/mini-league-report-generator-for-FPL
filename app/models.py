"""Output shapes for a league report. Plain dataclasses so report.py stays dependency-free."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ManagerRef:
    entry_id: int
    team_name: str
    manager_name: str


@dataclass(frozen=True)
class PointsAward:
    """GW winner / wooden spoon."""
    manager: ManagerRef
    points: int  # GW points after transfer hits


@dataclass(frozen=True)
class CaptainAward:
    manager: ManagerRef
    player_name: str
    points: int  # player's points x multiplier
    multiplier: int  # 2, or 3 for Triple Captain
    used_vice: bool  # captain didn't play, vice-captain took the armband
    triple_captain: bool


@dataclass(frozen=True)
class BenchAward:
    manager: ManagerRef
    points: int


@dataclass(frozen=True)
class HitAward:
    manager: ManagerRef
    cost: int  # positive number of points deducted
    transfers: int


@dataclass(frozen=True)
class RankMoveAward:
    manager: ManagerRef
    previous_rank: int
    rank: int
    places: int  # positive = climbed, negative = fell


@dataclass(frozen=True)
class DifferentialAward:
    manager: ManagerRef
    player_name: str
    points: int  # player's points x multiplier for that manager
    owned_by: int  # number of analysed managers who own the player


@dataclass(frozen=True)
class ChipPlay:
    manager: ManagerRef
    chip: str  # raw FPL code, e.g. "3xc"
    chip_name: str  # display name


@dataclass(frozen=True)
class Ownership:
    player_name: str
    owners: int
    percent: float


@dataclass(frozen=True)
class Report:
    league_id: int
    league_name: str
    gameweek: int
    is_latest_gameweek: bool
    managers_analysed: int
    total_managers: int | None  # None when the league exceeds the cap (FPL doesn't give a count)
    truncated: bool  # league bigger than the free-tier cap
    winner: PointsAward | None
    wooden_spoon: PointsAward | None
    best_captain: CaptainAward | None
    worst_captain: CaptainAward | None
    bench_regret: BenchAward | None
    biggest_hit: HitAward | None
    rank_climber: RankMoveAward | None  # only for the latest GW
    rank_faller: RankMoveAward | None  # only for the latest GW
    differential_hero: DifferentialAward | None
    chips_played: list[ChipPlay] = field(default_factory=list)
    template: list[Ownership] = field(default_factory=list)
    latest_gameweek: int | None = None  # newest GW with data, for GW pickers

    def to_dict(self) -> dict:
        return asdict(self)
