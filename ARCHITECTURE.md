# Architecture

## Approach

The scheduler uses candidate-plan generation plus weighted greedy reservation.

For each bus, the engine:

1. Builds every route-order charging plan that respects the battery range.
2. Simulates each plan against existing station reservations.
3. Scores each candidate through independent weighted rules.
4. Reserves the best candidate's charger slots.

This is intentionally not a hardcoded "charge at B and D" solution. The route, station list, charger counts, charge duration, bus departures, speed, battery range, and weights all come from scenario data.

## Why This Fit

The assignment asks for a small working scheduler that can grow. A full MILP/CP-SAT optimizer would be defensible, but it adds dependency and explanation overhead for 20 buses. This framework keeps the implementation compact while preserving the important extension points:

- Hard feasibility is handled by candidate generation and reservation checks.
- Soft preferences are independent scoring rules.
- World changes are data changes when they are physical/configuration changes.

## Data Structure

Each scenario JSON file fully describes one world:

- `route`: ordered directed segments with distances.
- `stations`: charging resources keyed by station id, including charger count and charge duration.
- `buses`: operator, origin, destination, and departure time.
- `weights`: tunable soft-rule weights.
- `battery_range_km` and `speed_kmph`: simulation constants.

The scheduler output is represented as:

- `BusSchedule`: selected plan, charge stops, waits, final arrival, full event list.
- `Reservation`: station, charger, bus, start/end, arrival, and wait.

## Anticipated Changes

Adding a station: add it to `route` and `stations` in JSON. Candidate generation reads the new route order automatically.

Changing a segment distance: edit the route segment. Range validation and travel time update automatically.

Doubling chargers at a station: change `chargers` for that station. Reservation placement already tracks charger numbers.

Changing charging time by station: change `charge_minutes` per station.

Adding an operator: use a new `operator` value in bus data. Operator scoring groups dynamically.

Adding more buses: add bus rows. The engine processes the list without fixed counts.

Changing the speed assumption: edit `speed_kmph`.

Changing weights: edit the scenario's `weights` object.

Adding another endpoint-to-endpoint direction on the same route: add buses with reversed origin/destination. The engine reverses route order for those buses.

Adding new soft rules: add a scoring rule class and register it in `build_rules`.

Adding new hard rules: filter or annotate candidates before scoring. For example, a station blackout rule would reject stops whose charge interval overlaps a closed window.

## Assumptions

- Buses are fully charged at Bengaluru and Kochi before departure.
- A bus charges to full whenever it charges.
- Buses can wait at a station after arriving.
- Travel speed is constant and stored per scenario.
- Current scenarios have one route, but the scenario schema keeps route data explicit for future route changes.

## Example: Weight Change

```json
"weights": {
  "individual": 1.0,
  "operator": 3.0,
  "overall": 1.0
}
```

## Example: New Rule

```python
@dataclass(frozen=True)
class LateArrivalRule:
    weight: float
    target_arrival: int
    name: str = "late_arrival"

    def score(self, candidate, context) -> float:
        return self.weight * max(0, candidate.final_arrival - self.target_arrival)
```
