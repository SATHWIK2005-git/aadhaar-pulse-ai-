import streamlit as st
import pandas as pd
import plotly.express as px
import time

st.set_page_config(layout="wide")
st.title("🇮🇳 Aadhaar Pulse AI+ — National Digital Inclusion & Service Intelligence")

# ================================
# LOAD DATA (from Google Drive)
# ================================
# Replace with YOUR Aadhaar Intelligence CSV link
DATA_URL = "https://drive.google.com/uc?id=PUT_YOUR_AADHAAR_INTELLIGENCE_FILE_ID_HERE"

# Your already uploaded daily file
DAILY_URL = "https://drive.google.com/uc?id=1dHESP6vfUTxUFKZgJfuHVVVtpIAF_0jk"

data = pd.read_csv(DATA_URL)
daily = pd.read_csv(DAILY_URL)

daily["date"] = pd.to_datetime(daily["date"], dayfirst=True)

# ================================
# CLEAN DATA
# ================================
data["state"] = data["state"].str.strip()
daily["state"] = daily["state"].str.strip()

cols = ["rush_index", "digital_literacy_score", "migration_score"]
for c in cols:
    data[c] = pd.to_numeric(data[c], errors="coerce")

# ================================
# AGGREGATE TO STATE
# ================================
state_data = data.groupby("state")[cols].mean().reset_index()

# ================================
# KPI PANEL
# ================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("States Covered", state_data["state"].nunique())
c2.metric("High Rush Zones", (state_data["rush_index"] > state_data["rush_index"].quantile(0.9)).sum())
c3.metric("Low Literacy Zones", (state_data["digital_literacy_score"] < state_data["digital_literacy_score"].quantile(0.25)).sum())
c4.metric("Migration Hotspots", (state_data["migration_score"] > state_data["migration_score"].quantile(0.9)).sum())

# ================================
# INDICATOR SELECTOR
# ================================
indicator = st.selectbox(
    "Select National Indicator",
    ["rush_index", "digital_literacy_score", "migration_score"]
)

# ================================
# INDIA MAP (NO GEOJSON REQUIRED)
# ================================
fig = px.choropleth(
    state_data,
    locations="state",
    locationmode="country names",
    color=indicator,
    color_continuous_scale="RdYlGn",
    title=f"India Aadhaar {indicator.replace('_',' ').title()}"
)

fig.update_geos(
    scope="asia",
    showcountries=True,
    countrycolor="black",
    lataxis_range=[6, 38],
    lonaxis_range=[68, 98]
)

st.plotly_chart(fig, width="stretch")

# ================================
# STATE DRILLDOWN
# ================================
st.subheader("District Drilldown")
selected_state = st.selectbox("Select State", state_data["state"].unique())

districts = data[data["state"] == selected_state]

st.dataframe(
    districts[["district", "rush_index", "digital_literacy_score", "migration_score"]]
    .sort_values("rush_index", ascending=False)
)

# ================================
# FORECAST ENGINE
# ================================
st.subheader("Next 7-Day Aadhaar Demand Forecast")

daily_state = daily[daily["state"] == selected_state]
trend = daily_state.groupby("date")["total_enrolment"].sum()

forecast = trend.tail(14).mean()
st.metric("Predicted Next Week Demand", int(forecast))

fig2 = px.line(trend, title="Historical Aadhaar Demand")
st.plotly_chart(fig2, width="stretch")

# ================================
# CONTEXT AI
# ================================
st.subheader("AI Context Engine")

r = districts["rush_index"].mean()
l = districts["digital_literacy_score"].mean()
m = districts["migration_score"].mean()

if r > state_data["rush_index"].quantile(0.8) and m > state_data["migration_score"].quantile(0.8):
    st.error("High Aadhaar rush likely due to labour migration or urban expansion")
elif r > state_data["rush_index"].quantile(0.8) and l > state_data["digital_literacy_score"].quantile(0.6):
    st.warning("High Aadhaar activity driven by digital awareness campaigns")
elif r < state_data["rush_index"].quantile(0.3) and l < state_data["digital_literacy_score"].quantile(0.3):
    st.info("Digital exclusion zone — outreach required")
else:
    st.success("Normal Aadhaar activity")

# ================================
# DATA QUALITY
# ================================
st.subheader("Data Quality Monitor")
missing = data.isnull().mean().mean() * 100
outliers = (data["rush_index"] > data["rush_index"].quantile(0.99)).mean() * 100
st.write(f"Missing Data: {missing:.2f}%")
st.write(f"Extreme Outliers: {outliers:.2f}%")

# ================================
# EXPLAINABLE AI
# ================================
with st.expander("How the AI works"):
    st.write("""
    **Rush Index** = Aadhaar activity per active day
