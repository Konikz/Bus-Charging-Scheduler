# Bus Charging Scheduler

Python + Streamlit app for the Exponent Energy SDE take-home assignment.

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens with a scenario dropdown and shows:

- Scenario input data
- Per-bus charging timeline and final arrival
- Per-station charging order
- Raw scenario JSON

## Deploy On Streamlit Community Cloud

1. Push this repo to GitHub.
2. Create a new app on Streamlit Community Cloud.
3. Select `app.py` as the entry point.

Streamlit Cloud installs `requirements.txt` automatically.

## Change A Weight

Weights live in each scenario file under `data/scenarios/`.

```json
"weights": {
  "individual": 1.0,
  "operator": 2.0,
  "overall": 1.0
}
```

Changing one value changes the scheduler scoring for that scenario.

## Add A Scenario

Create a new JSON file in `data/scenarios/` with the same shape as the shipped files:

- `route`
- `stations`
- `battery_range_km`
- `speed_kmph`
- `weights`
- `buses`

The app discovers scenario files automatically.

## Run Checks

```bash
python -m unittest discover -s tests -v
```

## Add A New Rule

Add a class in `scheduler/rules.py` with a `score(candidate, context)` method, then include it in `build_rules`.

```python
@dataclass(frozen=True)
class LongWaitRule:
    weight: float
    threshold_minutes: int = 30
    name: str = "long_wait"

    def score(self, candidate, context) -> float:
        excess_wait = max(0, candidate.total_wait_minutes - self.threshold_minutes)
        return self.weight * excess_wait
```

The engine does not need to change because it already sums all registered scoring rules.
