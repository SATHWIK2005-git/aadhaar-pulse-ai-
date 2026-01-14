import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
from state_mapper import state_map

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Aadhaar Pulse AI+",
    layout="wide"
)

st.title("🇮🇳 Aadhaar Pulse AI+ — National Digital Identity Intelligence")

# =========================
# LOAD DATA
# =========================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

# Safe numeric conversion
numeric_cols = ["rush_index", "digital_literacy_score", "migration_score"]
for col in numeric_cols:
    data[col] = pd.to_numeric(data[col], errors="coerce")

# Normalize state names (CRITICAL)
data["state"] = data["state"].replace(state_map)
data = data.dropna(subset=["state"])

# =========================
# LOAD INDIA GEOJSON
# =========================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

# =========================
# AGGREGATE TO STATE LEVEL
# =========================
state_data = (
    data.groupby("state")[numeric_cols]
    .mean()
    .reset_index()
)

# =========================
# KPI PANEL
# =========================
k1, k2, k3, k4 = st.columns(4)

k1.metric("Total States", state_data["state"].nunique())
k2.metric(
    "High Rush States",
    (state_data["rush_index"] > state_data["rush_index"].quantile(0.9)).sum()
)
k3.metric(
    "Low Literacy States",
    (state_data["digital_literacy_score"] < state_data["digital_literacy_score"].quantile(0.25)).sum()
)
k4.metric(
    "Migration Hotspots",
    (state_data["migration_score"] > state_data["migration_score"].quantile(0.9)).sum()
)

# =========================
# INDICATOR SELECTOR
# =========================
indicator = st.selectbox(
    "Select National Indicator",
    {
        "rush_index": "Rush Index (Service Load)",
        "digital_literacy_score": "Digital Literacy",
        "migration_score": "Migration Index"
    }.keys(),
    format_func=lambda x: {
        "rush_index": "Rush Index (Service Load)",
        "digital_literacy_score": "Digital Literacy",
        "migration_score": "Migration Index"
    }[x]
)

# =========================
# INDIA STATE HEATMAP
# =========================
fig = px.choropleth(
    state_data,
    geojson=india_geo,
    featureidkey="properties.NAME_1",
    locations="state",
    color=indicator,
    color_continuous_scale="RdYlGn_r",  # red = high pressure
    title=f"India Aadhaar — {indicator.replace('_',' ').title()}",
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin={"r":0,"t":50,"l":0,"b":0},
    height=600
)

st.plotly_chart(fig, width="stretch")

# =========================
# STATE DRILLDOWN
# =========================
st.subheader("📍 State Drill-Down")

selected_state = st.selectbox(
    "Select State",
    sorted(state_data["state"].unique())
)

district_data = data[data["state"] == selected_state]

st.dataframe(
    district_data[
        ["district", "rush_index", "digital_literacy_score", "migration_score"]
    ].sort_values("rush_index", ascending=False),
    use_container_width=True
)

# =========================
# CONTEXT AI ENGINE
# =========================
st.subheader("🧠 AI Context Engine")

r = district_data["rush_index"].mean()
l = district_data["digital_literacy_score"].mean()
m = district_data["migration_score"].mean()

if r > state_data["rush_index"].quantile(0.8) and m > state_data["migration_score"].quantile(0.8):
    st.error("High Aadhaar rush likely due to labour migration or urban influx")
elif r > state_data["rush_index"].quantile(0.8) and l > state_data["digital_literacy_score"].quantile(0.6):
    st.warning("High Aadhaar activity driven by digital awareness / scheme drives")
elif r < state_data["rush_index"].quantile(0.3) and l < state_data["digital_literacy_score"].quantile(0.3):
    st.info("Digital exclusion zone — targeted outreach required")
else:
    st.success("Normal Aadhaar activity observed")

# =========================
# DATA QUALITY MONITOR
# =========================
st.subheader("📊 Data Quality Monitor")

missing_pct = data.isnull().mean().mean() * 100
outlier_pct = (data["rush_index"] > data["rush_index"].quantile(0.99)).mean() * 100

st.write(f"• Missing Data: **{missing_pct:.2f}%**")
st.write(f"• Extreme Outliers: **{outlier_pct:.2f}%**")

# =========================
# EXPLAINABLE AI
# =========================
with st.expander("ℹ️ Explainable AI — How indicators are computed"):
    st.markdown("""
**Rush Index**  
Aadhaar enrolments + updates per active service day  

**Digital Literacy Score**  
Updates ÷ Enrolments  

**Migration Index**  
Adult Aadhaar ÷ Child Aadhaar  

**Interpretation**  
• High Rush → Service overload  
• Low Literacy → Digital exclusion  
• High Migration → Workforce movement  
""")

# =========================
# AUTO REFRESH (SAFE)
# =========================
st.caption("🔄 Auto-refresh every 30 seconds")
time.sleep(30)
st.rerun()
