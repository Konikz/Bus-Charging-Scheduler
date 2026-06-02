from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import BusSchedule


@dataclass(frozen=True)
class ScheduleContext:
    existing_schedules: list[BusSchedule]
    operator_wait_totals: dict[str, int]
    network_wait_total: int


class ScoringRule(Protocol):
    name: str
    weight: float

    def score(self, candidate: BusSchedule, context: ScheduleContext) -> float:
        ...


@dataclass(frozen=True)
class IndividualWaitRule:
    weight: float
    name: str = "individual"

    def score(self, candidate: BusSchedule, context: ScheduleContext) -> float:
        return self.weight * candidate.total_wait_minutes


@dataclass(frozen=True)
class OperatorSmoothnessRule:
    weight: float
    name: str = "operator"

    def score(self, candidate: BusSchedule, context: ScheduleContext) -> float:
        operator = candidate.bus.operator
        current = context.operator_wait_totals.get(operator, 0)
        operator_count = sum(
            1 for schedule in context.existing_schedules if schedule.bus.operator == operator
        )
        projected_average = (current + candidate.total_wait_minutes) / (operator_count + 1)
        return self.weight * projected_average


@dataclass(frozen=True)
class OverallNetworkRule:
    weight: float
    name: str = "overall"

    def score(self, candidate: BusSchedule, context: ScheduleContext) -> float:
        return self.weight * (candidate.total_trip_minutes + candidate.total_wait_minutes)


def build_rules(weights) -> list[ScoringRule]:
    return [
        IndividualWaitRule(weights.individual),
        OperatorSmoothnessRule(weights.operator),
        OverallNetworkRule(weights.overall),
    ]
