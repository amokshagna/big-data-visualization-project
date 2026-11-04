"""Standalone Streamlit application for live air-quality monitoring."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from src.live_air_quality import (  # noqa: E402
    POLL_INTERVAL_MINUTES,
    aqi_category,
    poll_and_store,
)

st.set_page_config(page_title="BDV Live Air Quality", page_icon="🌫️", layout="wide")
st.title("BDV — Live Air-Quality Monitor")
st.caption(
    "Standalone project · Open-Meteo Air Quality API · automatic refresh every "
    f"{POLL_INTERVAL_MINUTES} minutes"
)

cities = {
    "Bengaluru": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "London": (51.5072, -0.1276),
    "New York": (40.7128, -74.0060),
}
city = st.selectbox("Monitoring location", list(cities))
latitude, longitude = cities[city]


@st.fragment(run_every="15m")
def monitor() -> None:
    history, latest, error = poll_and_store(city, latitude, longitude)
    city_history = history[history["city"] == city].sort_values("observed_at")
    if latest is not None:
        st.success(f"Updated from Open-Meteo at {latest['observed_at']} UTC.")
    elif error:
        st.warning(f"API unavailable; using cached history. Details: {error}")
    if city_history.empty:
        st.info("No cached reading yet. A successful poll will create the history file.")
        return

    latest_row = city_history.iloc[-1]
    metrics = st.columns(5)
    metrics[0].metric("US AQI", _format(latest_row["us_aqi"], ""))
    metrics[1].metric("Category", aqi_category(latest_row["us_aqi"]))
    metrics[2].metric("PM2.5", _format(latest_row["pm2_5"], " µg/m³"))
    metrics[3].metric("PM10", _format(latest_row["pm10"], " µg/m³"))
    metrics[4].metric("Observed", latest_row["observed_at"].strftime("%Y-%m-%d %H:%M UTC"))

    st.markdown("### Air-quality visual analytics")
    gauge_col, radar_col = st.columns(2)
    with gauge_col:
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(latest_row["us_aqi"]) if pd.notna(latest_row["us_aqi"]) else 0,
                title={"text": "Current US AQI"},
                gauge={
                    "axis": {"range": [0, 300]},
                    "bar": {"color": _aqi_color(latest_row["us_aqi"])},
                    "steps": [
                        {"range": [0, 50], "color": "#22c55e"},
                        {"range": [50, 100], "color": "#facc15"},
                        {"range": [100, 150], "color": "#fb923c"},
                        {"range": [150, 200], "color": "#ef4444"},
                        {"range": [200, 300], "color": "#a855f7"},
                    ],
                },
            )
        )
        gauge.update_layout(height=310, margin=dict(l=20, r=20, t=55, b=15))
        st.plotly_chart(gauge, use_container_width=True)
    with radar_col:
        latest_pollutants = {
            "PM2.5": float(latest_row["pm2_5"]) if pd.notna(latest_row["pm2_5"]) else 0,
            "PM10": float(latest_row["pm10"]) if pd.notna(latest_row["pm10"]) else 0,
            "NO₂": float(latest_row["nitrogen_dioxide"]) if pd.notna(latest_row["nitrogen_dioxide"]) else 0,
            "O₃": float(latest_row["ozone"]) if pd.notna(latest_row["ozone"]) else 0,
        }
        radar = go.Figure(
            go.Scatterpolar(
                r=list(latest_pollutants.values()) + [list(latest_pollutants.values())[0]],
                theta=list(latest_pollutants) + [list(latest_pollutants)[0]],
                fill="toself",
                line_color="#0f766e",
                fillcolor="rgba(15,118,110,.3)",
                name="Latest reading",
            )
        )
        radar.update_layout(
            title="Pollutant profile",
            height=310,
            polar={"radialaxis": {"visible": True}},
            margin=dict(l=35, r=35, t=55, b=15),
            showlegend=False,
        )
        st.plotly_chart(radar, use_container_width=True)

    chart_data = city_history.set_index("observed_at")[
        ["pm2_5", "pm10", "nitrogen_dioxide", "ozone"]
    ].rename(
        columns={
            "pm2_5": "PM2.5",
            "pm10": "PM10",
            "nitrogen_dioxide": "NO₂",
            "ozone": "O₃",
        }
    )
    trend = px.line(
        chart_data.reset_index(),
        x="observed_at",
        y=chart_data.columns,
        markers=True,
        title="Pollutant concentration timeline",
        labels={"observed_at": "Observation time", "value": "Concentration"},
        color_discrete_sequence=["#0f766e", "#2563eb", "#f59e0b", "#ef4444"],
    )
    trend.update_layout(height=390, hovermode="x unified", legend_title_text="")
    st.plotly_chart(trend, use_container_width=True)

    heatmap_data = city_history.assign(
        hour=city_history["observed_at"].dt.hour,
        day=city_history["observed_at"].dt.day_name().str.slice(stop=3),
    )
    heatmap = (
        heatmap_data.pivot_table(
            index="day",
            columns="hour",
            values="us_aqi",
            aggfunc="mean",
        )
        .reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    )
    heatmap_fig = px.imshow(
        heatmap,
        aspect="auto",
        color_continuous_scale=["#22c55e", "#facc15", "#fb923c", "#ef4444", "#a855f7"],
        labels={"x": "UTC hour", "y": "Day", "color": "Mean AQI"},
        title="AQI rhythm by day and hour",
    )
    heatmap_fig.update_layout(height=330, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(heatmap_fig, use_container_width=True)

    pollutant_summary = pd.DataFrame(
        {
            "Pollutant": ["PM2.5", "PM10", "NO₂", "O₃"],
            "Latest": list(latest_pollutants.values()),
            "24h average": [
                city_history["pm2_5"].mean(),
                city_history["pm10"].mean(),
                city_history["nitrogen_dioxide"].mean(),
                city_history["ozone"].mean(),
            ],
        }
    ).melt(id_vars="Pollutant", var_name="Measure", value_name="Value")
    comparison = px.bar(
        pollutant_summary,
        x="Pollutant",
        y="Value",
        color="Measure",
        barmode="group",
        title="Latest reading versus local history average",
        color_discrete_sequence=["#0f766e", "#94a3b8"],
    )
    comparison.update_layout(height=340, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(comparison, use_container_width=True)

    st.dataframe(city_history.tail(20), use_container_width=True, hide_index=True)
    st.caption(
        "Source: Open-Meteo Air Quality API. Values are model-based, not direct "
        "regulatory-station measurements. Local history is stored in "
        "`BDV/data/air_quality_history.csv`."
    )


def _format(value: object, suffix: str) -> str:
    return f"{float(value):.1f}{suffix}" if pd.notna(value) else "n/a"


def _aqi_color(value: object) -> str:
    if pd.isna(value):
        return "#64748b"
    value = float(value)
    if value <= 50:
        return "#16a34a"
    if value <= 100:
        return "#ca8a04"
    if value <= 150:
        return "#ea580c"
    if value <= 200:
        return "#dc2626"
    return "#7e22ce"


monitor()
