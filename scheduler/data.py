from __future__ import annotations

import json
from pathlib import Path

from .models import Bus, Scenario, Segment, Station, Weights
from .time_utils import parse_time


SCENARIO_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


def list_scenarios() -> list[tuple[str, str]]:
    scenarios = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        with path.open() as fh:
            data = json.load(fh)
        scenarios.append((data["id"], data["name"]))
    return scenarios


def load_scenario(scenario_id: str) -> Scenario:
    path = SCENARIO_DIR / f"{scenario_id}.json"
    with path.open() as fh:
        data = json.load(fh)

    stations = {
        station["id"]: Station(
            id=station["id"],
            name=station.get("name", station["id"]),
            chargers=int(station.get("chargers", 1)),
            charge_minutes=int(station["charge_minutes"]),
        )
        for station in data["stations"]
    }

    return Scenario(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        speed_kmph=float(data["speed_kmph"]),
        battery_range_km=float(data["battery_range_km"]),
        route=[
            Segment(
                from_node=segment["from"],
                to_node=segment["to"],
                distance_km=float(segment["distance_km"]),
            )
            for segment in data["route"]
        ],
        stations=stations,
        buses=[
            Bus(
                id=bus["id"],
                operator=bus["operator"],
                origin=bus["origin"],
                destination=bus["destination"],
                departure=parse_time(bus["departure"]),
            )
            for bus in data["buses"]
        ],
        weights=Weights(**data.get("weights", {})),
    )
