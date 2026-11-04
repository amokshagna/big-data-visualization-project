"""Open-Meteo polling and local history for the standalone BDV project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

PROJECT_DIR = Path(__file__).resolve().parents[1]
HISTORY_PATH = PROJECT_DIR / "data" / "air_quality_history.csv"
OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
POLL_INTERVAL_MINUTES = 15
POLL_COLUMNS = (
    "observed_at",
    "city",
    "latitude",
    "longitude",
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "ozone",
    "us_aqi",
)


def fetch_current_air_quality(
    city: str,
    latitude: float,
    longitude: float,
    timeout: int = 20,
    session: requests.Session | None = None,
) -> dict[str, object]:
    """Fetch one current observation from the free Open-Meteo API."""
    client = session or requests
    response = client.get(
        OPEN_METEO_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm2_5,pm10,nitrogen_dioxide,ozone,us_aqi",
            "timezone": "UTC",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    current = response.json().get("current", {})
    if not current.get("time"):
        raise ValueError("The API response did not contain a current observation.")
    reading = {
        "observed_at": pd.to_datetime(current["time"], utc=True).isoformat(),
        "city": city,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "pm2_5": _number_or_none(current.get("pm2_5")),
        "pm10": _number_or_none(current.get("pm10")),
        "nitrogen_dioxide": _number_or_none(current.get("nitrogen_dioxide")),
        "ozone": _number_or_none(current.get("ozone")),
        "us_aqi": _number_or_none(current.get("us_aqi")),
    }
    if all(reading[column] is None for column in POLL_COLUMNS[4:]):
        raise ValueError("The API response contained no pollutant values.")
    return reading


def load_history(path: Path = HISTORY_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=POLL_COLUMNS)
    history = pd.read_csv(path, parse_dates=["observed_at"])
    history["observed_at"] = pd.to_datetime(history["observed_at"], utc=True, errors="coerce")
    for column in POLL_COLUMNS[2:]:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    return history


def append_reading(reading: dict[str, object], path: Path = HISTORY_PATH) -> pd.DataFrame:
    missing = set(POLL_COLUMNS).difference(reading)
    if missing:
        raise ValueError(f"Reading is missing columns: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    new_row = pd.DataFrame([{column: reading[column] for column in POLL_COLUMNS}])
    history = load_history(path)
    history = new_row if history.empty else pd.concat([history, new_row], ignore_index=True)
    history["observed_at"] = pd.to_datetime(history["observed_at"], utc=True, errors="coerce")
    history = (
        history.dropna(subset=["observed_at", "city"])
        .drop_duplicates(["city", "observed_at"], keep="last")
        .sort_values(["city", "observed_at"])
        .tail(10_000)
    )
    history.to_csv(path, index=False)
    return history


def poll_and_store(
    city: str,
    latitude: float,
    longitude: float,
    path: Path = HISTORY_PATH,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, dict[str, object] | None, str | None]:
    """Poll once, append on success, and return cached history on failure."""
    try:
        reading = fetch_current_air_quality(city, latitude, longitude, session=session)
        return append_reading(reading, path), reading, None
    except (requests.RequestException, ValueError, OSError) as exc:
        return load_history(path), None, str(exc)


def aqi_category(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Unavailable"
    value = float(value)
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 150:
        return "Unhealthy for sensitive groups"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very unhealthy"
    return "Hazardous"


def _number_or_none(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None
