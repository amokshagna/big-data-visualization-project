from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.live_air_quality import aqi_category, append_reading, poll_and_store


READING = {
    "observed_at": "2026-11-04T12:00:00+00:00",
    "city": "Bengaluru",
    "latitude": 12.97,
    "longitude": 77.59,
    "pm2_5": 18.2,
    "pm10": 35.4,
    "nitrogen_dioxide": 12.0,
    "ozone": 64.0,
    "us_aqi": 55.0,
}


class LiveAirQualityTests(unittest.TestCase):
    def test_append_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.csv"
            self.assertEqual(len(append_reading(READING, path)), 1)
            self.assertEqual(len(append_reading(READING, path)), 1)

    def test_poll_falls_back_to_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.csv"
            append_reading(READING, path)
            session = Mock()
            session.get.side_effect = OSError("offline")
            history, latest, error = poll_and_store("Bengaluru", 12.97, 77.59, path, session)
            self.assertEqual(len(history), 1)
            self.assertIsNone(latest)
            self.assertIn("offline", error)

    def test_aqi_category(self) -> None:
        self.assertEqual(aqi_category(20), "Good")
        self.assertEqual(aqi_category(180), "Unhealthy")
