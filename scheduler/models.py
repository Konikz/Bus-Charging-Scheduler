from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    from_node: str
    to_node: str
    distance_km: float


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    chargers: int
    charge_minutes: int


@dataclass(frozen=True)
class Bus:
    id: str
    operator: str
    origin: str
    destination: str
    departure: int


@dataclass(frozen=True)
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    speed_kmph: float
    battery_range_km: float
    route: list[Segment]
    stations: dict[str, Station]
    buses: list[Bus]
    weights: Weights


@dataclass(frozen=True)
class ChargeStop:
    station_id: str
    arrival: int
    charge_start: int
    charge_end: int
    wait_minutes: int
    charger: int


@dataclass
class BusSchedule:
    bus: Bus
    plan: list[str]
    stops: list[ChargeStop]
    final_arrival: int
    total_wait_minutes: int
    total_trip_minutes: int
    events: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class Reservation:
    bus_id: str
    operator: str
    station_id: str
    arrival: int
    start: int
    end: int
    wait_minutes: int
    charger: int
