"""Poll all BDV cities for the scheduled GitHub Actions history job."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.live_air_quality import HISTORY_PATH, append_reading, fetch_current_air_quality  # noqa: E402


CITIES = {
    "Bengaluru": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "London": (51.5072, -0.1276),
    "New York": (40.7128, -74.0060),
}


def main() -> int:
    successes = 0
    for city, (latitude, longitude) in CITIES.items():
        try:
            reading = fetch_current_air_quality(city, latitude, longitude)
            append_reading(reading, HISTORY_PATH)
            print(f"{city}: {reading['observed_at']} AQI={reading['us_aqi']}")
            successes += 1
        except Exception as exc:  # noqa: BLE001
            print(f"{city}: poll failed: {exc}", file=sys.stderr)
    return 0 if successes else 1


if __name__ == "__main__":
    raise SystemExit(main())
