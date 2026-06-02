from __future__ import annotations

import unittest

from scheduler import list_scenarios, load_scenario, schedule_scenario


def distance_between(nodes, distances, start, end):
    start_index = nodes.index(start)
    end_index = nodes.index(end)
    total = 0
    for left, right in zip(nodes[start_index:end_index], nodes[start_index + 1 : end_index + 1]):
        total += distances[(left, right)]
    return total


def directional_nodes(scenario, bus):
    nodes = [scenario.route[0].from_node] + [segment.to_node for segment in scenario.route]
    if bus.origin == nodes[-1]:
        nodes = list(reversed(nodes))
    distances = {(segment.from_node, segment.to_node): segment.distance_km for segment in scenario.route}
    distances.update({(right, left): value for (left, right), value in list(distances.items())})
    return nodes, distances


class SchedulerTest(unittest.TestCase):
    def test_all_scenarios_schedule_without_charger_overlap(self):
        self.assertEqual(len(list_scenarios()), 5)

        for scenario_id, _ in list_scenarios():
            with self.subTest(scenario_id=scenario_id):
                scenario = load_scenario(scenario_id)
                result = schedule_scenario(scenario)

                for station_id, reservations in result["station_schedules"].items():
                    station = scenario.stations[station_id]
                    for charger in range(1, station.chargers + 1):
                        charger_reservations = [
                            reservation for reservation in reservations if reservation.charger == charger
                        ]
                        ordered = sorted(charger_reservations, key=lambda item: item.start)
                        for previous, current in zip(ordered, ordered[1:]):
                            self.assertLessEqual(previous.end, current.start)

    def test_all_bus_plans_respect_range_and_fixed_charge_time(self):
        for scenario_id, _ in list_scenarios():
            with self.subTest(scenario_id=scenario_id):
                scenario = load_scenario(scenario_id)
                result = schedule_scenario(scenario)

                for schedule in result["bus_schedules"]:
                    nodes, distances = directional_nodes(scenario, schedule.bus)
                    checkpoints = [schedule.bus.origin, *schedule.plan, schedule.bus.destination]

                    for start, end in zip(checkpoints, checkpoints[1:]):
                        self.assertLessEqual(
                            distance_between(nodes, distances, start, end),
                            scenario.battery_range_km,
                        )

                    for stop in schedule.stops:
                        station = scenario.stations[stop.station_id]
                        self.assertEqual(stop.charge_end - stop.charge_start, station.charge_minutes)
                        self.assertGreaterEqual(stop.wait_minutes, 0)


if __name__ == "__main__":
    unittest.main()
