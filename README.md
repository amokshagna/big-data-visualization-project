# BDV — Live Air-Quality Monitor

This is a **separate project** from `BIa`. It does not modify or depend on the
original BIA dashboard.

BDV polls the free Open-Meteo Air Quality API every 15 minutes and plots recent
air-quality readings for a selected city. It uses API polling rather than
scraping HTML pages, stores a local CSV history, and keeps showing cached
readings when the API is temporarily unavailable.

## Run

From the repository root:

```powershell
python -m venv .venv-bdv
.\.venv-bdv\Scripts\Activate.ps1
pip install -r BDV\requirements.txt
python -m streamlit run BDV\app.py
```

The app opens at `http://localhost:8501`.

## Features

- Current US AQI, PM2.5, PM10, NO₂, and O₃
- City selector for Bengaluru, Delhi, Mumbai, London, and New York
- Automatic Streamlit fragment refresh every 15 minutes
- Local history at `BDV/data/air_quality_history.csv`
- Poll failure warning with cached-history fallback
- AQI gauge, pollutant radar, timeline, day/hour AQI heatmap, and history comparison
- API attribution and model-data limitation shown in the UI

Open-Meteo air-quality values are model-based rather than direct station
measurements. The project is suitable for a live-monitoring demonstration and
academic visualization, not regulated health advice.

## Validation

```powershell
python -m unittest discover -s BDV\tests -p "test_*.py" -v
python -m compileall -q BDV
```
