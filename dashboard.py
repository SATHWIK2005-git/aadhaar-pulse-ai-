import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
from state_mapper import state_map

st.set_page_config(layout="wide")
st.title("🇮🇳 Aadhaar Pulse AI+ — National Digital Inclusion & Service Intelligence")

# ---------- Load Data ----------
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")
daily = pd.read_csv("https://drive.google.com/uc?id=1dHESP6vfUTxUFKZgJfuHVVVtpIAF_0jk")
daily["date"] = pd.to_datetime(daily["date"], dayfirst=True)

with open("india_states.geojson") as f:
    india_geo = json.load(f)

# Normalize state names
data["state"] = data["state"].map(state_map)
daily["state"] = daily["state"].map(state_map)

data = data.dropna(subset=["state"])
daily = daily.dropna(subset=["state"])

# ---------- KPIs ----------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Aadhaar Activity", int(data["rush_index"].sum()))
col2.metric("High Rush Districts", int((data["rush_index"] > data["rush_index"].quantile(0.9)).sum()))
col3.metric("Low Literacy Districts", int((data["digital_literacy_score"] < data["digital_literacy_score"].quantile(0.25)).sum()))
col4.metric("Migration Hotspots", int((data["migration_score"] > data["migration_score"].quantile(0.9)).sum()))

# ---------- State Aggregation ----------
state_data = data.groupby("state")[["rush_index","digital_literacy_score","migration_score"]].mean().reset_index()

indicator = st.selectbox(
    "Select National Indicator",
    ["rush_index","digital_literacy_score","migration_score"]
)

# ---------- India Map ----------
fig = px.choropleth(
    state_data,
    geojson=india_geo,
    featureidkey="properties.NAME_1",
    locations="state",
    color=indicator,
    color_continuous_scale="RdYlGn",
    title=f"India Aadhaar {indicator.replace('_',' ').title()}"
)
fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, use_container_width=True)

# ---------- District Drilldown ----------
st.subheader("District Drilldown")
selected_state = st.selectbox("Select State", state_data["state"].unique())

districts = data[data["state"] == selected_state]

st.dataframe(
    districts[["district","rush_index","digital_literacy_score","migration_score"]]
    .sort_values("rush_index", ascending=False)
    .head(10)
)

# ---------- Forecast ----------
st.subheader("Next 7-Day Aadhaar Demand Forecast")

daily_state = daily[daily["state"] == selected_state]
trend = daily_state.groupby("date")["total_enrolment"].sum()

forecast = trend.tail(14).mean()

st.metric("Predicted Next-Week Demand", int(forecast))

fig2 = px.line(trend, title="Historical Aadhaar Demand")
st.plotly_chart(fig2, use_container_width=True)

# ---------- Context AI ----------
st.subheader("AI Context Engine")

rush = districts["rush_index"].mean()
lit = districts["digital_literacy_score"].mean()
mig = districts["migration_score"].mean()

if rush > state_data["rush_index"].quantile(0.8) and mig > state_data["migration_score"].quantile(0.8):
    st.error("High Aadhaar rush due to migrant influx or urban expansion")
elif rush > state_data["rush_index"].quantile(0.8) and lit > state_data["digital_literacy_score"].quantile(0.6):
    st.warning("High Aadhaar activity driven by digital awareness drives")
elif rush < state_data["rush_index"].quantile(0.3) and lit < state_data["digital_literacy_score"].quantile(0.3):
    st.info("Digital exclusion zone — outreach required")
else:
    st.success("Normal Aadhaar activity")

# ---------- Data Quality ----------
st.subheader("Data Quality Monitor")

missing = data.isnull().mean().mean() * 100
outliers = (data["rush_index"] > data["rush_index"].quantile(0.99)).mean() * 100

st.write(f"Missing Data: {missing:.2f}%")
st.write(f"Extreme Outliers: {outliers:.2f}%")

# ---------- Explainable AI ----------
with st.expander("How AI Works"):
    st.write("""
    Rush Index = Aadhaar activity per active day  
    Digital Literacy = Updates ÷ Enrolments  
    Migration Score = Adult Aadhaar ÷ Child Aadhaar  
    Forecast = Moving average of last 14 days  
    """)

# ---------- Auto Refresh ----------
time.sleep(10)
st.rerun()

