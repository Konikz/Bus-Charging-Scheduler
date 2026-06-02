from __future__ import annotations

from itertools import combinations

from .models import Bus, BusSchedule, ChargeStop, Reservation, Scenario
from .rules import ScheduleContext, build_rules


def schedule_scenario(scenario: Scenario) -> dict[str, object]:
    reservations: dict[str, list[Reservation]] = {
        station_id: [] for station_id in scenario.stations
    }
    schedules: list[BusSchedule] = []
    operator_wait_totals: dict[str, int] = {}
    rules = build_rules(scenario.weights)

    for bus in sorted(scenario.buses, key=lambda item: (item.departure, item.id)):
        candidates = [
            _simulate_bus(scenario, bus, plan, reservations)
            for plan in _valid_charge_plans(scenario, bus)
        ]
        context = ScheduleContext(
            existing_schedules=schedules,
            operator_wait_totals=operator_wait_totals,
            network_wait_total=sum(operator_wait_totals.values()),
        )
        best = min(candidates, key=lambda candidate: _score(candidate, context, rules))
        schedules.append(best)
        operator_wait_totals[bus.operator] = (
            operator_wait_totals.get(bus.operator, 0) + best.total_wait_minutes
        )
        for stop in best.stops:
            reservations[stop.station_id].append(
                Reservation(
                    bus_id=bus.id,
                    operator=bus.operator,
                    station_id=stop.station_id,
                    arrival=stop.arrival,
                    start=stop.charge_start,
                    end=stop.charge_end,
                    wait_minutes=stop.wait_minutes,
                    charger=stop.charger,
                )
            )

    return {
        "bus_schedules": sorted(schedules, key=lambda item: item.bus.id),
        "station_schedules": {
            station_id: sorted(items, key=lambda item: (item.start, item.bus_id))
            for station_id, items in reservations.items()
        },
    }


def _score(candidate: BusSchedule, context: ScheduleContext, rules) -> tuple[float, int, str]:
    weighted_score = sum(rule.score(candidate, context) for rule in rules)
    return (weighted_score, candidate.final_arrival, ",".join(candidate.plan))


def _valid_charge_plans(scenario: Scenario, bus: Bus) -> list[list[str]]:
    nodes, distances = _directional_route(scenario, bus)
    internal_stations = [node for node in nodes[1:-1] if node in scenario.stations]
    plans: list[list[str]] = []

    for length in range(1, len(internal_stations) + 1):
        for plan in combinations(internal_stations, length):
            if _plan_respects_range(nodes, distances, plan, scenario.battery_range_km):
                plans.append(list(plan))
    return plans


def _plan_respects_range(
    nodes: list[str], distances: dict[tuple[str, str], float], plan: tuple[str, ...], max_range: float
) -> bool:
    checkpoints = [nodes[0], *plan, nodes[-1]]
    for start, end in zip(checkpoints, checkpoints[1:]):
        if _distance_between(nodes, distances, start, end) > max_range:
            return False
    return True


def _simulate_bus(
    scenario: Scenario,
    bus: Bus,
    plan: list[str],
    reservations: dict[str, list[Reservation]],
) -> BusSchedule:
    nodes, distances = _directional_route(scenario, bus)
    current_time = bus.departure
    current_node = bus.origin
    stops: list[ChargeStop] = []
    events: list[dict[str, object]] = [
        {"type": "depart", "node": bus.origin, "time": bus.departure}
    ]

    for station_id in plan:
        travel_minutes = _travel_minutes(
            _distance_between(nodes, distances, current_node, station_id),
            scenario.speed_kmph,
        )
        arrival = current_time + travel_minutes
        start, charger_index = _next_available_slot(
            reservations[station_id],
            arrival,
            scenario.stations[station_id].charge_minutes,
            scenario.stations[station_id].chargers,
        )
        end = start + scenario.stations[station_id].charge_minutes
        stop = ChargeStop(
            station_id=station_id,
            arrival=arrival,
            charge_start=start,
            charge_end=end,
            wait_minutes=start - arrival,
            charger=charger_index + 1,
        )
        stops.append(stop)
        events.extend(
            [
                {
                    "type": "arrive_station",
                    "node": station_id,
                    "time": arrival,
                    "wait_minutes": stop.wait_minutes,
                },
                {
                    "type": "charge",
                    "node": station_id,
                    "start": start,
                    "end": end,
                    "charger": stop.charger,
                },
            ]
        )
        current_time = end
        current_node = station_id

    final_travel = _travel_minutes(
        _distance_between(nodes, distances, current_node, bus.destination),
        scenario.speed_kmph,
    )
    final_arrival = current_time + final_travel
    events.append({"type": "arrive_destination", "node": bus.destination, "time": final_arrival})

    return BusSchedule(
        bus=bus,
        plan=plan,
        stops=stops,
        final_arrival=final_arrival,
        total_wait_minutes=sum(stop.wait_minutes for stop in stops),
        total_trip_minutes=final_arrival - bus.departure,
        events=events,
    )


def _directional_route(scenario: Scenario, bus: Bus) -> tuple[list[str], dict[tuple[str, str], float]]:
    nodes = [scenario.route[0].from_node] + [segment.to_node for segment in scenario.route]
    distances = {
        (segment.from_node, segment.to_node): segment.distance_km
        for segment in scenario.route
    }
    distances.update({(to_node, from_node): value for (from_node, to_node), value in distances.items()})

    if bus.origin == nodes[0] and bus.destination == nodes[-1]:
        return nodes, distances
    if bus.origin == nodes[-1] and bus.destination == nodes[0]:
        return list(reversed(nodes)), distances
    raise ValueError(f"Bus {bus.id} does not match scenario route endpoints")


def _distance_between(
    nodes: list[str], distances: dict[tuple[str, str], float], start: str, end: str
) -> float:
    start_index = nodes.index(start)
    end_index = nodes.index(end)
    if start_index > end_index:
        raise ValueError(f"Cannot travel backward from {start} to {end}")
    total = 0.0
    for from_node, to_node in zip(nodes[start_index:end_index], nodes[start_index + 1 : end_index + 1]):
        total += distances[(from_node, to_node)]
    return total


def _travel_minutes(distance_km: float, speed_kmph: float) -> int:
    return round((distance_km / speed_kmph) * 60)


def _next_available_slot(
    reservations: list[Reservation],
    arrival: int,
    duration: int,
    charger_count: int,
) -> tuple[int, int]:
    by_charger: list[list[Reservation]] = [[] for _ in range(charger_count)]
    for reservation in sorted(reservations, key=lambda item: item.start):
        charger_index = max(0, min(charger_count - 1, reservation.charger - 1))
        by_charger[charger_index].append(reservation)

    best_start = None
    best_charger = 0
    for charger_index, charger_reservations in enumerate(by_charger):
        start = arrival
        for reservation in sorted(charger_reservations, key=lambda item: item.start):
            if start + duration <= reservation.start:
                break
            if start < reservation.end:
                start = reservation.end
        if best_start is None or start < best_start:
            best_start = start
            best_charger = charger_index
    return int(best_start if best_start is not None else arrival), best_charger
