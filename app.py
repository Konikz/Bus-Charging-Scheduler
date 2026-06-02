from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from scheduler import list_scenarios, load_scenario, schedule_scenario
from scheduler.time_utils import format_time


st.set_page_config(page_title="Bus Charging Scheduler", layout="wide")


def scenario_path(scenario_id: str) -> Path:
    return Path(__file__).resolve().parent / "data" / "scenarios" / f"{scenario_id}.json"


def buses_frame(scenario) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Bus ID": bus.id,
                "Operator": bus.operator,
                "Direction": f"{bus.origin} -> {bus.destination}",
                "Departure": format_time(bus.departure),
            }
            for bus in scenario.buses
        ]
    )


def route_frame(scenario) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "From": segment.from_node,
                "To": segment.to_node,
                "Distance km": segment.distance_km,
            }
            for segment in scenario.route
        ]
    )


def stations_frame(scenario) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Station": station.id,
                "Chargers": station.chargers,
                "Charge minutes": station.charge_minutes,
            }
            for station in scenario.stations.values()
        ]
    )


def bus_timetable_frame(result) -> pd.DataFrame:
    rows = []
    for schedule in result["bus_schedules"]:
        stops = "; ".join(
            f"{stop.station_id} arrive {format_time(stop.arrival)}, "
            f"charge {format_time(stop.charge_start)}-{format_time(stop.charge_end)}, "
            f"wait {stop.wait_minutes}m"
            for stop in schedule.stops
        )
        rows.append(
            {
                "Bus ID": schedule.bus.id,
                "Operator": schedule.bus.operator,
                "Direction": f"{schedule.bus.origin} -> {schedule.bus.destination}",
                "Departure": format_time(schedule.bus.departure),
                "Plan": " -> ".join(schedule.plan),
                "Charging timeline": stops,
                "Total wait": schedule.total_wait_minutes,
                "Arrival": format_time(schedule.final_arrival),
                "Trip minutes": schedule.total_trip_minutes,
            }
        )
    return pd.DataFrame(rows)


def station_schedule_frame(result) -> pd.DataFrame:
    rows = []
    for station_id, reservations in result["station_schedules"].items():
        for order, reservation in enumerate(reservations, start=1):
            rows.append(
                {
                    "Station": station_id,
                    "Order": order,
                    "Bus ID": reservation.bus_id,
                    "Operator": reservation.operator,
                    "Charger": reservation.charger,
                    "Arrived": format_time(reservation.arrival),
                    "Started": format_time(reservation.start),
                    "Ended": format_time(reservation.end),
                    "Wait": reservation.wait_minutes,
                }
            )
    return pd.DataFrame(rows)


st.title("Bus Charging Scheduler")

scenario_options = list_scenarios()
selected_name = st.selectbox(
    "Scenario",
    options=[name for _, name in scenario_options],
    index=0,
)
selected_id = dict((name, scenario_id) for scenario_id, name in scenario_options)[selected_name]

scenario = load_scenario(selected_id)
result = schedule_scenario(scenario)

st.caption(scenario.description)

metric_cols = st.columns(5)
metric_cols[0].metric("Buses", len(scenario.buses))
metric_cols[1].metric("Range", f"{scenario.battery_range_km:g} km")
metric_cols[2].metric("Speed", f"{scenario.speed_kmph:g} km/h")
metric_cols[3].metric("Stations", len(scenario.stations))
metric_cols[4].metric(
    "Weights",
    f"I {scenario.weights.individual:g} / O {scenario.weights.operator:g} / N {scenario.weights.overall:g}",
)

input_tab, bus_tab, station_tab, raw_tab = st.tabs(
    ["Scenario input", "Per-bus timetable", "Per-station order", "Raw data"]
)

with input_tab:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Departures")
        st.dataframe(buses_frame(scenario), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Route")
        st.dataframe(route_frame(scenario), use_container_width=True, hide_index=True)
        st.subheader("Stations")
        st.dataframe(stations_frame(scenario), use_container_width=True, hide_index=True)

with bus_tab:
    st.dataframe(bus_timetable_frame(result), use_container_width=True, hide_index=True)

with station_tab:
    station_df = station_schedule_frame(result)
    station_filter = st.segmented_control(
        "Station",
        options=["All", *scenario.stations.keys()],
        default="All",
    )
    if station_filter != "All":
        station_df = station_df[station_df["Station"] == station_filter]
    st.dataframe(station_df, use_container_width=True, hide_index=True)

with raw_tab:
    with scenario_path(selected_id).open() as fh:
        st.json(json.load(fh), expanded=False)
