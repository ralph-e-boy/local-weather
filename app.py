# weather_app.py
# Streamlit interface to the U.S. National Weather Service API
import streamlit as st
import requests, pandas as pd, matplotlib.pyplot as plt
from datetime import datetime, timezone
import json

st.set_page_config(page_title="Local Weather (NWS)", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for dark mode theme
st.markdown("""
<style>
    /* Main app styling for dark mode */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #262730;
    }
    
    /* Button styling for dark mode */
    .stButton > button {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #464649 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #464649 !important;
        border-color: #626262 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    
    .stButton > button:active {
        background-color: #1f2937 !important;
        transform: translateY(0px) !important;
    }
    
    /* Number input styling */
    .stNumberInput > div > div > input {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #464649 !important;
        border-radius: 6px !important;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.1) !important;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #464649 !important;
        border-radius: 6px !important;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.1) !important;
    }
    
    /* Multiselect styling */
    .stMultiSelect > div > div {
        background-color: #262730 !important;
        border: 1px solid #464649 !important;
        border-radius: 6px !important;
    }
    
    /* Text input styling */
    .stTextInput > div > div > input {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #464649 !important;
        border-radius: 6px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.1) !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #464649 !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #0ea5e9 !important;
        color: #ffffff !important;
        border-color: #0ea5e9 !important;
    }
    
    /* Metric styling */
    .css-1xarl3l {
        background-color: #262730 !important;
        border: 1px solid #464649 !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #464649 !important;
        border-radius: 6px !important;
    }
    
    .streamlit-expanderContent {
        background-color: #1f2937 !important;
        border: 1px solid #464649 !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
    }
    
    /* Success/Error message styling */
    .stSuccess {
        background-color: rgba(34, 197, 94, 0.1) !important;
        border-left: 4px solid #22c55e !important;
        color: #22c55e !important;
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.1) !important;
        border-left: 4px solid #ef4444 !important;
        color: #ef4444 !important;
    }
    
    .stInfo {
        background-color: rgba(59, 130, 246, 0.1) !important;
        border-left: 4px solid #3b82f6 !important;
        color: #3b82f6 !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        background-color: #262730 !important;
        color: #fafafa !important;
    }
    
    /* Container and column styling */
    .block-container {
        padding-top: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

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
    data = fetch(f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}")
    p = data["properties"]
    return {
        "city":  p.get("relativeLocation", {}).get("properties", {}).get("city", ""),
        "state": p.get("relativeLocation", {}).get("properties", {}).get("state", ""),
        "forecast":        p["forecast"],        # seven‑day
        "forecastHourly":  p["forecastHourly"],  # hourly
        "observationStations": p["observationStations"],
        "geometry": data.get("geometry", {}),  # For polygon visualization
    }

def latest_obs(stations_url):
    sid = fetch(stations_url)["features"][0]["properties"]["stationIdentifier"]
    return fetch(f"https://api.weather.gov/stations/{sid}/observations/latest")["properties"]

def hourly_df(url):
    data = fetch(url)
    properties = data["properties"]
    periods = properties["periods"]
    df = pd.DataFrame(periods)
    
    # Add additional properties columns
    for col in ["probabilityOfPrecipitation", "dewpoint", "relativeHumidity"]:
        if col in df.columns:
            if col == "probabilityOfPrecipitation":
                df["precipProb%"] = df[col].apply(lambda x: x.get("value", 0) if isinstance(x, dict) else 0)
            elif col == "dewpoint":
                df["dewpoint°C"] = df[col].apply(lambda x: round(x.get("value", 0), 1) if isinstance(x, dict) else 0)
            elif col == "relativeHumidity":
                df["humidity%"] = df[col].apply(lambda x: x.get("value", 0) if isinstance(x, dict) else 0)
    
    # Keep essential columns plus new ones
    cols = ["startTime","temperature","temperatureUnit","windSpeed","windDirection",
            "shortForecast","precipProb%","dewpoint°C","humidity%","icon"]
    df = df[[c for c in cols if c in df.columns]]
    df["startTime"] = pd.to_datetime(df["startTime"])
    
    return df, properties

def daily_df(url):
    data = fetch(url)
    properties = data["properties"]
    periods = properties["periods"]
    df = pd.DataFrame(periods)
    
    # Process detailed forecast
    cols = ["name","temperature","temperatureUnit","windSpeed","shortForecast",
            "detailedForecast","icon"]
    df = df[[c for c in cols if c in df.columns]]
    
    return df, properties

def format_timestamp(iso_string):
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return iso_string

def temp_to_color(temp_f):
    """Convert temperature in Fahrenheit to a color for visual display"""
    if temp_f >= 90:
        return "#ff4b4b"  # Hot red
    elif temp_f >= 80:
        return "#ff8c42"  # Warm orange
    elif temp_f >= 70:
        return "#ffd93d"  # Pleasant yellow
    elif temp_f >= 60:
        return "#6bcf7f"  # Mild green
    elif temp_f >= 50:
        return "#4ecdc4"  # Cool teal
    elif temp_f >= 40:
        return "#45b7d1"  # Cold blue
    elif temp_f >= 32:
        return "#5c7cfa"  # Very cold purple
    else:
        return "#748ffc"  # Freezing purple-blue

def weather_emoji(forecast_text):
    """Get weather emoji based on forecast description"""
    text = forecast_text.lower()
    if "sunny" in text or "clear" in text:
        return "☀️"
    elif "partly" in text and "cloud" in text:
        return "⛅"
    elif "cloud" in text or "overcast" in text:
        return "☁️"
    elif "rain" in text or "shower" in text:
        return "🌧️"
    elif "storm" in text or "thunder" in text:
        return "⛈️"
    elif "snow" in text:
        return "❄️"
    elif "fog" in text or "mist" in text:
        return "🌫️"
    elif "wind" in text:
        return "💨"
    else:
        return "🌤️"

def wind_direction_icon(direction):
    """Get wind direction arrow based on degrees"""
    if not direction or direction == "":
        return "🌀"
    
    try:
        deg = int(direction)
        if 337.5 <= deg or deg < 22.5:
            return "⬆️"  # N
        elif 22.5 <= deg < 67.5:
            return "↗️"  # NE
        elif 67.5 <= deg < 112.5:
            return "➡️"  # E
        elif 112.5 <= deg < 157.5:
            return "↘️"  # SE
        elif 157.5 <= deg < 202.5:
            return "⬇️"  # S
        elif 202.5 <= deg < 247.5:
            return "↙️"  # SW
        elif 247.5 <= deg < 292.5:
            return "⬅️"  # W
        elif 292.5 <= deg < 337.5:
            return "↖️"  # NW
        else:
            return "🌀"
    except:
        return "🌀"

def format_hour_display(start_time):
    """Format hour display from datetime"""
    try:
        dt = pd.to_datetime(start_time)
        return dt.strftime("%I%p").lstrip("0").lower()
    except:
        return str(start_time)

def plot_forecast_area(geometry, lat, lon):
    """Plot the forecast area polygon with the input point"""
    if geometry.get("type") == "Polygon":
        coords = geometry["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='none')
        ax.set_facecolor('none')
        ax.plot(lons, lats, 'b-', linewidth=2, label='NWS Forecast Area Boundary')
        ax.fill(lons, lats, alpha=0.3, color='blue', label='Coverage Area')
        ax.plot(lon, lat, 'ro', markersize=12, label=f'Your Location ({lat:.4f}, {lon:.4f})')
        
        # Theme the plot for dark mode
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(colors='white')
        
        ax.set_xlabel('Longitude (degrees)', fontsize=11, fontweight='bold', color='white')
        ax.set_ylabel('Latitude (degrees)', fontsize=11, fontweight='bold', color='white')
        ax.set_title('NWS Forecast Area Coverage', fontsize=14, fontweight='bold', color='white')
        
        legend = ax.legend(loc='best', fontsize=10, facecolor='none', edgecolor='white')
        for text in legend.get_texts():
            text.set_color('white')
            
        ax.grid(True, alpha=0.3, color='white')
        
        # Set aspect ratio to be equal
        ax.set_aspect('equal', adjustable='box')
        
        return fig
    return None

# -------- sidebar -----------------------------------------------------------
with st.sidebar:
    st.header("Your Location")
    c1, c2 = st.columns(2)
    lat = c1.number_input("Latitude",  value=42.3611, format="%.4f", step=0.0001)
    lon = c2.number_input("Longitude", value=-71.0570, format="%.4f", step=0.0001)
    go  = st.button("Get Weather")

    # --- current conditions ---
    if go:
        try:
            meta = points_meta(lat, lon)
            st.success(f"Weather for {meta['city']}, {meta['state']}  "
                       f"({lat:.4f}, {lon:.4f})")

            obs = latest_obs(meta["observationStations"])
            colA, colB = st.columns([1, 3])
            colA.image(obs["icon"].replace("small", "large"), width=100)
            temp = obs["temperature"]["value"]
            unit = obs["temperature"]["unitCode"].split(":")[-1]
            colB.markdown(f"### {obs['textDescription']}")
            colB.markdown(f"**Temp:** {temp:.1f} {unit}")
            colB.markdown(f"**Wind:** {obs['windSpeed']['value'] or 0:.0f} km/h "
                          f"{obs['windDirection']['value'] or ''}°")

            # FIX: handle both "…Z" and full "+00:00" offsets safely
            ts_iso = obs["timestamp"].replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_iso).astimezone(timezone.utc) \
                                                .strftime('%Y‑%m‑%d %H:%M UTC')
            colB.caption(f"Updated {ts}")
        except Exception as e:
            st.error(f"Oops: {e}")

# -------- main workflow ------------------------------------------------------
if go:
    try:
        meta = points_meta(lat, lon)
        
        # --- tabs: Hourly / 7‑Day / Forecast Info / Coverage Area ---
        tab1, tab2, tab3, tab4 = st.tabs(["Hourly", "Seven‑Day", "Forecast Info", "Coverage Area"])

        with tab1:
            hdf, h_props = hourly_df(meta["forecastHourly"])
            
            # Hourly weather cards - horizontal scrolling layout
            st.markdown("### 🕐 Hourly Forecast")
            
            # Create horizontal layout with columns for hourly data
            hours_to_show = min(24, len(hdf))  # Show up to 24 hours in columns
            
            # Display hourly cards using Streamlit columns
            cols_per_row = 6
            rows_needed = (hours_to_show + cols_per_row - 1) // cols_per_row
            
            for row_idx in range(rows_needed):
                cols = st.columns(cols_per_row)
                start_idx = row_idx * cols_per_row
                end_idx = min(start_idx + cols_per_row, hours_to_show)
                
                for col_idx, hour_idx in enumerate(range(start_idx, end_idx)):
                    with cols[col_idx]:
                        row = hdf.iloc[hour_idx]
                        
                        # Extract data with safe defaults
                        temp_val = row.get('temperature', 0)
                        temp_unit = row.get('temperatureUnit', 'F')
                        wind_speed = str(row.get('windSpeed', '0 mph')).split()[0] if row.get('windSpeed') else '0'
                        wind_dir = row.get('windDirection', '')
                        forecast = row.get('shortForecast', 'Unknown')
                        precip_prob = row.get('precipProb%', 0)
                        humidity = row.get('humidity%', 0)
                        
                        # Format time display
                        hour_display = format_hour_display(row['startTime'])
                        
                        # Get icons
                        weather_icon = weather_emoji(forecast)
                        wind_icon = wind_direction_icon(wind_dir)
                        
                        # Truncate forecast for narrow panels
                        forecast_short = forecast[:10] + "..." if len(forecast) > 10 else forecast
                        
                        # Create weather card
                        st.markdown(f"**{hour_display}**")
                        st.markdown(f"{weather_icon}")
                        st.markdown(f"**{temp_val}°{temp_unit[0]}**")
                        st.caption(f"{forecast_short}")
                        st.caption(f"{wind_icon} {wind_speed} • 💧 {precip_prob}%")
                        st.caption(f"💨 {humidity}%")
                        st.markdown("---")

            # Create enhanced visualizations
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8), facecolor='none')
            plt.style.use('seaborn-v0_8')
            
            # Set transparent background and light text for dark theme compatibility
            for ax in [ax1, ax2, ax3, ax4]:
                ax.set_facecolor('none')
                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('white')
                ax.tick_params(colors='white')
                ax.yaxis.label.set_color('white')
                ax.xaxis.label.set_color('white')
                ax.title.set_color('white')
            
            # Temperature plot
            ax1.plot(hdf["startTime"][:24], hdf["temperature"][:24], 'r-', linewidth=2, label='Temperature')
            ax1.set_xlabel("Time", fontsize=10, fontweight='bold')
            ax1.set_ylabel(f"Temperature ({hdf['temperatureUnit'][0]})", fontsize=10, fontweight='bold')
            ax1.set_title("24-Hour Temperature Forecast", fontsize=12, fontweight='bold')
            ax1.grid(True, alpha=0.3, color='white')
            ax1.tick_params(axis='x', rotation=45)
            legend1 = ax1.legend(loc='best', facecolor='none', edgecolor='white')
            for text in legend1.get_texts():
                text.set_color('white')
            
            # Humidity plot
            if "humidity%" in hdf.columns:
                ax2.plot(hdf["startTime"][:24], hdf["humidity%"][:24], 'b-', linewidth=2, label='Humidity')
                ax2.set_xlabel("Time", fontsize=10, fontweight='bold')
                ax2.set_ylabel("Relative Humidity (%)", fontsize=10, fontweight='bold')
                ax2.set_title("24-Hour Humidity Forecast", fontsize=12, fontweight='bold')
                ax2.grid(True, alpha=0.3, color='white')
                ax2.tick_params(axis='x', rotation=45)
                legend2 = ax2.legend(loc='best', facecolor='none', edgecolor='white')
                for text in legend2.get_texts():
                    text.set_color('white')
            
            # Precipitation probability
            if "precipProb%" in hdf.columns:
                ax3.bar(hdf["startTime"][:24], hdf["precipProb%"][:24], alpha=0.7, color='green', label='Precip Chance')
                ax3.set_xlabel("Time", fontsize=10, fontweight='bold')
                ax3.set_ylabel("Precipitation Probability (%)", fontsize=10, fontweight='bold')
                ax3.set_title("24-Hour Precipitation Chance", fontsize=12, fontweight='bold')
                ax3.grid(True, alpha=0.3, axis='y', color='white')
                ax3.tick_params(axis='x', rotation=45)
                legend3 = ax3.legend(loc='best', facecolor='none', edgecolor='white')
                for text in legend3.get_texts():
                    text.set_color('white')
            
            # Wind speed
            if "windSpeed" in hdf.columns:
                wind_speeds = hdf["windSpeed"][:24].str.extract(r'(\d+)').astype(float).iloc[:, 0]
                ax4.plot(hdf["startTime"][:24], wind_speeds, 'm-', linewidth=2, label='Wind Speed')
                ax4.set_xlabel("Time", fontsize=10, fontweight='bold')
                ax4.set_ylabel("Wind Speed (mph)", fontsize=10, fontweight='bold')
                ax4.set_title("24-Hour Wind Speed Forecast", fontsize=12, fontweight='bold')
                ax4.grid(True, alpha=0.3, color='white')
                ax4.tick_params(axis='x', rotation=45)
                legend4 = ax4.legend(loc='best', facecolor='none', edgecolor='white')
                for text in legend4.get_texts():
                    text.set_color('white')
            
            plt.tight_layout()
            st.pyplot(fig, transparent=True)

        with tab2:
            ddf, d_props = daily_df(meta["forecast"])
            
            # Add some magic sparkles header
            st.markdown("### ✨ 7-Day Weather Forecast")
            
            for idx, row in ddf.iterrows():
                # Create a container for each day with custom HTML for better alignment
                with st.container():
                    # Extract temperature value for coloring
                    temp_value = row['temperature']
                    temp_unit = row['temperatureUnit']
                    temp_color = temp_to_color(temp_value)
                    emoji = weather_emoji(row['shortForecast'])
                    
                    # Create a single row with all elements aligned - no separate icon column needed
                    # Modern card-style layout with weather icon as background
                    html_content = f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
                        border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 12px;
                        padding: 24px;
                        margin: 8px 0;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                        backdrop-filter: blur(10px);
                        transition: transform 0.2s ease, box-shadow 0.2s ease;
                    ">
                        <div style="display: flex; gap: 30px; align-items: flex-start;">
                            <div style="
                                background-image: url('{row["icon"].replace("small", "large")}');
                                background-size: cover;
                                background-position: center;
                                background-repeat: no-repeat;
                                border-radius: 8px;
                                padding: 16px;
                                min-width: 180px;
                                min-height: 180px;
                                text-align: center;
                                border: 1px solid rgba(255,255,255,0.05);
                                position: relative;
                                overflow: hidden;
                            ">
                            <div style="
                                position: absolute;
                                top: 0;
                                left: 0;
                                right: 0;
                                bottom: 0;
                                background: rgba(0,0,0,0.4);
                                border-radius: 8px;
                            "></div>
                            <div style="position: relative; z-index: 2;">
                                <h4 style="
                                    margin: 0 0 12px 0;
                                    color: #ffffff;
                                    font-weight: 600;
                                    font-size: 16px;
                                    letter-spacing: 0.5px;
                                    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                                ">{row['name']}</h4>
                                <div style="
                                    font-size: 48px;
                                    font-weight: 700;
                                    color: {temp_color};
                                    margin: 12px 0;
                                    line-height: 1;
                                    text-shadow: 0 3px 6px rgba(0,0,0,0.8);
                                ">{temp_value}°{temp_unit[0]}</div>
                                <div style="
                                    color: rgba(255,255,255,0.9);
                                    font-size: 14px;
                                    margin-top: 8px;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    gap: 6px;
                                    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                                ">
                                    <span>💨</span>
                                    <span>{row['windSpeed']}</span>
                                </div>
                            </div>
                            </div>
                            <div style="flex: 1; padding-left: 8px;">
                                <h5 style="
                                    color: #ffffff;
                                    margin: 0 0 16px 0;
                                    font-size: 28px;
                                    font-weight: 600;
                                    display: flex;
                                    align-items: center;
                                    gap: 8px;
                                ">
                                    <span style="font-size: 32px;">{emoji}</span>
                                    {row['shortForecast']}
                                </h5>
                                {"<p style='color: rgba(255,255,255,0.85); margin: 0; line-height: 1.6; font-size: 20px;'>" + row['detailedForecast'] + "</p>" if "detailedForecast" in row and row["detailedForecast"] else ""}
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    # Add a subtle divider between days
                    if idx < len(ddf) - 1:
                        st.markdown("<hr style='margin: 20px 0; opacity: 0.2;'>", unsafe_allow_html=True)
        
        with tab3:
            st.subheader("Forecast Metadata")
            
            # Display forecast properties
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Forecast Generator", h_props.get("forecastGenerator", "N/A"))
            with col2:
                st.metric("Units", h_props.get("units", "N/A"))
            with col3:
                if "generatedAt" in h_props:
                    st.metric("Generated At", format_timestamp(h_props["generatedAt"]))
            with col4:
                if "updateTime" in h_props:
                    st.metric("Update Time", format_timestamp(h_props["updateTime"]))
            
            if "validTimes" in h_props:
                st.info(f"**Valid Times:** {h_props['validTimes']}")
            
            # Elevation info if available
            if "elevation" in h_props:
                elev = h_props["elevation"]
                if isinstance(elev, dict):
                    st.info(f"**Elevation:** {elev.get('value', 'N/A')} {elev.get('unitCode', '').split(':')[-1]}")
            
        with tab4:
            st.subheader("Forecast Area Coverage")
            
            if "geometry" in meta and meta["geometry"]:
                fig = plot_forecast_area(meta["geometry"], lat, lon)
                if fig:
                    st.pyplot(fig, transparent=True)
                    
                    # Display polygon coordinates
                    with st.expander("Polygon Coordinates"):
                        if meta["geometry"].get("type") == "Polygon":
                            coords = meta["geometry"]["coordinates"][0]
                            coord_df = pd.DataFrame(coords, columns=["Longitude", "Latitude"])
                            st.dataframe(coord_df, use_container_width=True)
                else:
                    st.info("No polygon data available for this location")
            else:
                st.info("No geometry data available for this location")
                
    except Exception as e:
        st.error(f"Oops: {e}")
