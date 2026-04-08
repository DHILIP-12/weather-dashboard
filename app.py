# ================= IMPORTS =================
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="WeatherWise Pro", layout="wide")

API_KEY = st.secrets["API_KEY"]


# ================= CONFIG =================
st.markdown("""
<style>

/* ===== MAIN BACKGROUND (SOFT GREY) ===== */
.stApp {
    background-color: #e6e6e6;   /* darker than before */
    color: #1a1a1a;
}

/* ===== SIDEBAR (TONED DOWN DARK) ===== */
section[data-testid="stSidebar"] {
    background-color: #262626;   /* softer than black */
}

/* Sidebar text */
section[data-testid="stSidebar"] * {
    color: #eaeaea !important;
}

/* ===== HEADER ===== */
header[data-testid="stHeader"] {
    background: #262626;
}

/* ===== KPI CARDS ===== */
.card {
    padding: 18px;
    border-radius: 14px;
    background: #2f2f2f;
    color: #ffffff;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.25);
    text-align: center;
}

/* ===== INPUTS ===== */
input, textarea {
    background-color: #2f2f2f !important;
    color: #ffffff !important;
}

::placeholder {
    color: #bbbbbb !important;
}

/* ===== SELECT ===== */
div[data-baseweb="select"] > div {
    background-color: #2f2f2f !important;
    color: white !important;
}

/* ===== BUTTONS ===== */
div.stButton > button {
    background-color: #3a3a3a;
    color: white;
    border-radius: 8px;
}

/* ===== SLIDER ===== */
div[data-testid="stSlider"] {
    color: white;
}

/* ===== TABLE ===== */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}

</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "unit" not in st.session_state:
    st.session_state.unit = "Celsius"

# ================= UTILS =================
def get_unit_group(unit):
    return "metric" if unit == "Celsius" else "us"

def temp_symbol(unit):
    return "°C" if unit == "Celsius" else "°F"

def wind_unit(unit):
    return "km/h" if unit == "Celsius" else "mph"

# ================= API =================
@st.cache_data(ttl=600)
def fetch_weather(city, unit):
    try:
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city},IN"

        params = {
            "unitGroup": get_unit_group(unit),
            "key": API_KEY,
            "contentType": "json"
        }

        res = requests.get(url, params=params, timeout=8)

        if res.status_code != 200:
            st.error(f"API Error: {res.status_code}")
            return None

        return res.json()

    except Exception as e:
        st.error(f"Error: {e}")
        return None


# ================= CITY SEARCH =================
@st.cache_data(ttl=86400)
def search_city(query):
    if not query or len(query) < 2:
        return []

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "countrycodes": "in",
            "format": "json",
            "limit": 5
        }

        headers = {"User-Agent": "weatherwise-pro"}

        res = requests.get(url, params=params, headers=headers, timeout=5)
        data = res.json() if res.status_code == 200 else []

        return [place["display_name"] for place in data]
    except:
        return []

# ================= KPI CARD =================
def kpi_card(title, value, icon):
    st.markdown(f"""
    <div class="card">
        <h5>{icon} {title}</h5>
        <h2>{value}</h2>
    </div>
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
    city = query

days = st.sidebar.slider("Forecast Days", 1, 10, 7)
unit = st.sidebar.radio("Unit", ["Celsius", "Fahrenheit"])
live_mode = st.sidebar.toggle("🔴 Live Mode")

# ================= FETCH =================
with st.spinner("Fetching weather..."):
    data = fetch_weather(city, unit)

if not data or "currentConditions" not in data:
    st.error("❌ Failed to fetch data")
    st.stop()

current = data["currentConditions"]
symbol = temp_symbol(unit)
w_unit = wind_unit(unit)

# ================= MAIN =================
st.title("🌦 WeatherWise Pro")
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

# OVERVIEW
with tab1:
    days_data = data["days"][:days]
    temps = [d["temp"] for d in days_data]
    dates = [d["datetime"] for d in days_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=temps, mode="lines+markers"))

    fig.update_layout(template="plotly_dark", title="Temperature Trend")
    st.plotly_chart(fig, use_container_width=True)

# HOURLY
with tab2:
    hours = data["days"][0]["hours"]
    temps = [h["temp"] for h in hours]
    times = [h["datetime"] for h in hours]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=temps, fill="tozeroy"))

    fig.update_layout(template="plotly_dark", title="Hourly Temperature")
    st.plotly_chart(fig, use_container_width=True)

# FORECAST
with tab3:
    df = pd.DataFrame(data["days"][:days])
    st.dataframe(df[["datetime", "tempmax", "tempmin", "humidity"]])

    st.download_button("Download CSV", df.to_csv(index=False), "forecast.csv")

# MAP
with tab4:
    df_map = pd.DataFrame({
        "lat": [data["latitude"]],
        "lon": [data["longitude"]]
    })
    st.map(df_map)

# ================= FOOTER =================
st.caption("Data Source: Visual Crossing API")

# ================= LIVE MODE =================
if live_mode:
    st.info("🔴 Refreshing...")
    st.experimental_rerun()