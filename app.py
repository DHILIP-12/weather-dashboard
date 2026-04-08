# ================= IMPORTS =================
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# ================= CONFIG =================
API_KEY = st.secrets["API_KEY"]

st.set_page_config(page_title="WeatherWise Pro", layout="wide")

# ================= HEADER FIX =================
st.markdown("""
<style>
header[data-testid="stHeader"] {
    background: rgba(0,0,0,0.85);
}
button[kind="header"] {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ================= STATE =================
if "unit" not in st.session_state:
    st.session_state.unit = "Celsius"

# ================= UTILS =================
def get_unit_group(unit):
    return "metric" if unit == "Celsius" else "us"

def temp_symbol(unit):
    return "°C" if unit == "Celsius" else "°F"

def wind_unit(unit):
    return "km/h" if unit == "Celsius" else "mph"

# ================= WEATHER API =================
@st.cache_data(ttl=600)
def fetch_weather(city, unit):
    try:
        unit_group = get_unit_group(unit)

        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}"

        params = {
            "unitGroup": unit_group,
            "key": API_KEY,
            "contentType": "json"
        }

        res = requests.get(url, params=params, timeout=8)

        if res.status_code != 200:
            return None

        try:
            return res.json()
        except:
            return None

    except:
        return None

# ================= SAFE CITY SEARCH =================
@st.cache_data(ttl=86400)
def search_city(query):
    if not query or len(query) < 2:
        return []

    try:
        url = "https://nominatim.openstreetmap.org/search"

        headers = {
            "User-Agent": "weatherwise-pro-app"
        }

        params = {
            "q": query,
            "countrycodes": "in",
            "format": "json",
            "limit": 5
        }

        res = requests.get(url, params=params, headers=headers, timeout=5)

        if res.status_code != 200:
            return []

        try:
            data = res.json()
        except:
            return []

        if not data:
            return []

        return [place["display_name"] for place in data]

    except:
        return []

# ================= UI =================
def kpi_card(title, value, icon):
    st.markdown(f"""
    <div style='padding:18px;border-radius:14px;
    background: rgba(0,0,0,0.4);
    box-shadow: 0px 4px 15px rgba(0,0,0,0.3);'>
        <h5>{icon} {title}</h5>
        <h2>{value}</h2>
    </div>
    """, unsafe_allow_html=True)

def set_background(condition):
    if "rain" in condition.lower():
        bg = "linear-gradient(to right, #373B44, #4286f4)"
    elif "cloud" in condition.lower():
        bg = "linear-gradient(to right, #757F9A, #D7DDE8)"
    else:
        bg = "linear-gradient(to right, #1e3c72, #2a5298)"

    st.markdown(f"""
    <style>
    .stApp {{
        background: {bg};
        color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

# ================= SIDEBAR =================
st.sidebar.title("⚙ Control Panel")

query = st.sidebar.text_input("🔍 Search City (India)", "Salem")

results = search_city(query)

if results:
    selected = st.sidebar.selectbox("Select Location", results)
    city = selected.split(",")[0]
else:
    st.sidebar.warning("⚠ No results found")
    city = query if query else "Salem"

days = st.sidebar.slider("Forecast Days", 1, 10, 7)

unit = st.sidebar.radio("Unit", ["Celsius", "Fahrenheit"])
st.session_state.unit = unit

live_mode = st.sidebar.toggle("🔴 Live Mode")

# ================= FETCH DATA =================
with st.spinner("Fetching weather data..."):
    data = fetch_weather(city, unit)

if not data or "currentConditions" not in data:
    st.error("❌ Failed to fetch weather data")
    st.stop()

# ================= BACKGROUND =================
condition = data["currentConditions"]["conditions"]
set_background(condition)

# ================= MAIN =================
st.title("🌦 WeatherWise Pro")

symbol = temp_symbol(unit)
w_unit = wind_unit(unit)

current = data["currentConditions"]

# ================= CURRENT =================
st.subheader(f"📍 Current Weather - {city}")

kpi_card(city, f"{current['temp']}{symbol}", "🌡")

# ================= METRICS =================
st.subheader("📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    kpi_card("Feels Like", f"{current['feelslike']}{symbol}", "🥵")

with col2:
    kpi_card("Humidity", f"{current['humidity']}%", "💧")

with col3:
    kpi_card("Wind", f"{current['windspeed']} {w_unit}", "🌬")

with col4:
    kpi_card("Pressure", f"{current.get('pressure','N/A')}", "🌪")

# ================= TABS =================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "⏱ Hourly", "📅 Forecast", "🗺 Map"])

# ================= OVERVIEW =================
with tab1:
    days_data = data["days"][:days]

    temps = [d["temp"] for d in days_data]
    dates = [d["datetime"] for d in days_data]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=temps,
        mode="lines+markers",
        name="Temperature"
    ))

    fig.update_layout(
        title="Temperature Trend",
        template="plotly_dark",
        hovermode="x unified"
    )

    fig.update_traces(line=dict(width=3))

    st.plotly_chart(fig, use_container_width=True)

# ================= HOURLY =================
with tab2:
    hours = data["days"][0]["hours"]

    temps = [h["temp"] for h in hours]
    times = [h["datetime"] for h in hours]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times,
        y=temps,
        fill="tozeroy",
        name="Hourly Temp"
    ))

    fig.update_layout(
        title="Hourly Temperature",
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)

# ================= FORECAST =================
with tab3:
    df = pd.DataFrame(data["days"][:days])
    st.dataframe(df[["datetime", "tempmax", "tempmin", "humidity"]])

    csv = df.to_csv(index=False)
    st.download_button("Download Forecast", csv, "forecast.csv")

# ================= MAP =================
with tab4:
    lat = data["latitude"]
    lon = data["longitude"]

    df_map = pd.DataFrame({"lat": [lat], "lon": [lon]})
    st.map(df_map)

# ================= FOOTER =================
st.caption("Data Source: Visual Crossing API")

# ================= LIVE MODE =================
if live_mode:
    st.info("🔴 Live updating every 60 seconds...")
    st.experimental_rerun()