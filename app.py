# weather_app.py
# Streamlit interface to the U.S. National Weather Service API
import streamlit as st
import requests, pandas as pd, matplotlib.pyplot as plt
from datetime import datetime, timezone

st.set_page_config(page_title="Local Weather (NWS)", layout="wide")
st.title("🇺🇸  National Weather Service — Local Weather")

# -------- helpers -----------------------------------------------------------
UA = "StreamlitNWS/1.0 (you@example.com)"   # <-- put a real contact here

@st.cache_data(show_spinner=False)
def fetch(url: str) -> dict:
    r = requests.get(url, headers={
        "Accept": "application/geo+json",
        "User-Agent": UA
    }, timeout=10)
    r.raise_for_status()
    return r.json()

def points_meta(lat, lon):
    p = fetch(f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}")["properties"]
    return {
        "city":  p.get("relativeLocation", {}).get("properties", {}).get("city", ""),
        "state": p.get("relativeLocation", {}).get("properties", {}).get("state", ""),
        "forecast":        p["forecast"],        # seven‑day
        "forecastHourly":  p["forecastHourly"],  # hourly
        "observationStations": p["observationStations"]
    }

def latest_obs(stations_url):
    sid = fetch(stations_url)["features"][0]["properties"]["stationIdentifier"]
    return fetch(f"https://api.weather.gov/stations/{sid}/observations/latest")["properties"]

def hourly_df(url):
    periods = fetch(url)["properties"]["periods"]
    df = pd.DataFrame(periods)[["startTime","temperature","temperatureUnit",
                                "windSpeed","shortForecast","icon"]]
    df["startTime"] = pd.to_datetime(df["startTime"])
    return df

def daily_df(url):
    periods = fetch(url)["properties"]["periods"]
    return pd.DataFrame(periods)[["name","temperature","temperatureUnit",
                                  "windSpeed","shortForecast","icon"]]

# -------- sidebar -----------------------------------------------------------
with st.sidebar:
    st.header("Your Location")
    c1, c2 = st.columns(2)
    lat = c1.number_input("Latitude",  value=40.89, format="%.4f")
    lon = c2.number_input("Longitude", value=-73.36, format="%.4f")
    go  = st.button("Get Weather")

# -------- main workflow ------------------------------------------------------
if go:
    try:
        meta = points_meta(lat, lon)
        st.success(f"Weather for {meta['city']}, {meta['state']}  "
                   f"({lat:.4f}, {lon:.4f})")

        # --- current conditions ---
        obs = latest_obs(meta["observationStations"])
        colA, colB = st.columns([1, 3])
        colA.image(obs["icon"], width=100)
        temp = obs["temperature"]["value"]
        unit = obs["temperature"]["unitCode"].split(":")[-1]
        colB.markdown(f"### {obs['textDescription']}")
        colB.markdown(f"**Temp:** {temp:.1f} {unit}")
        colB.markdown(f"**Wind:** {obs['windSpeed']['value'] or 0:.0f} km/h "
                      f"{obs['windDirection']['value'] or ''}°")

        # FIX: handle both “…Z” and full “+00:00” offsets safely
        ts_iso = obs["timestamp"].replace("Z", "+00:00")
        ts = datetime.fromisoformat(ts_iso).astimezone(timezone.utc) \
                                            .strftime('%Y‑%m‑%d %H:%M UTC')
        colB.caption(f"Updated {ts}")

        # --- tabs: Hourly / 7‑Day ---
        tab1, tab2 = st.tabs(["Hourly", "Seven‑Day"])

        with tab1:
            hdf = hourly_df(meta["forecastHourly"])
            st.dataframe(
                hdf.head(24)[["startTime","temperature","temperatureUnit",
                              "windSpeed","shortForecast"]],
                height=400, use_container_width=True)

            fig, ax = plt.subplots()
            ax.plot(hdf["startTime"][:24], hdf["temperature"][:24])
            ax.set_xlabel("Time")
            ax.set_ylabel(f"Temp ({hdf['temperatureUnit'][0]})")
            ax.set_title("Next 24 h Temperature")
            ax.grid(True)
            st.pyplot(fig, transparent=True)

        with tab2:
            ddf = daily_df(meta["forecast"])
            for _, row in ddf.iterrows():
                c1, c2 = st.columns([1, 4])
                c1.image(row["icon"], width=80)
                c2.markdown(f"**{row['name']}** — {row['shortForecast']}  \n"
                            f"{row['temperature']} {row['temperatureUnit']}  \n"
                            f"Wind: {row['windSpeed']}")

    except Exception as e:
        st.error(f"Oops: {e}")

