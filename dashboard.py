import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
from state_mapper import state_map

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Aadhaar Pulse AI+", layout="wide")
st.title("🇮🇳 Aadhaar Pulse AI+ — National Digital Identity Intelligence")

# =====================================================
# OFFICIAL STATES + UTS
# =====================================================
OFFICIAL_STATES_UTS = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
    "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya",
    "Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim",
    "Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand",
    "West Bengal",
    "Delhi","Jammu and Kashmir","Ladakh","Puducherry",
    "Chandigarh","Andaman and Nicobar Islands",
    "Dadra and Nagar Haveli and Daman and Diu","Lakshadweep"
]

# =====================================================
# LOAD DATA
# =====================================================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

numeric_cols = ["rush_index", "digital_literacy_score", "migration_score"]
for c in numeric_cols:
    data[c] = pd.to_numeric(data[c], errors="coerce")

# Normalize states (Odisha FIX applied here)
data["state"] = data["state"].replace(state_map)
data = data.dropna(subset=["state"])

# =====================================================
# LOAD INDIA MAP
# =====================================================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

# =====================================================
# STATE AGGREGATION
# =====================================================
state_data = (
    data.groupby("state")[numeric_cols]
    .mean()
    .reset_index()
)

state_data = state_data[state_data["state"].isin(OFFICIAL_STATES_UTS)]

# =====================================================
# KPI PANEL
# =====================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("States / UTs", state_data["state"].nunique())
c2.metric("High Rush States", (state_data["rush_index"] > state_data["rush_index"].quantile(0.9)).sum())
c3.metric("Low Literacy States", (state_data["digital_literacy_score"] < state_data["digital_literacy_score"].quantile(0.25)).sum())
c4.metric("Migration Hotspots", (state_data["migration_score"] > state_data["migration_score"].quantile(0.9)).sum())

# =====================================================
# MAP
# =====================================================
indicator = st.selectbox(
    "Select Indicator",
    ["rush_index", "digital_literacy_score", "migration_score"]
)

fig = px.choropleth(
    state_data,
    geojson=india_geo,
    featureidkey="properties.NAME_1",
    locations="state",
    color=indicator,
    color_continuous_scale="RdYlGn_r",
    title="India Aadhaar Heatmap"
)

fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, width="stretch")

# =====================================================
# STATE → DISTRICT DRILLDOWN
# =====================================================
st.subheader("📍 District-Level Intelligence")

selected_state = st.selectbox("Select State", sorted(state_data["state"].unique()))
districts = data[data["state"] == selected_state]

st.dataframe(
    districts[["district","rush_index","digital_literacy_score","migration_score"]]
    .sort_values("rush_index", ascending=False),
    use_container_width=True
)

# =====================================================
# 🚨 FRAUD DETECTION ENGINE
# =====================================================
st.subheader("🚨 AI Fraud Alerts")

update_abuse_thr = data["digital_literacy_score"].quantile(0.95)
migration_anomaly_thr = data["migration_score"].quantile(0.99)

fraud_df = districts[
    (districts["digital_literacy_score"] > update_abuse_thr) |
    (districts["migration_score"] > migration_anomaly_thr) |
    (
        (districts["rush_index"] > data["rush_index"].quantile(0.9)) &
        (districts["digital_literacy_score"] < data["digital_literacy_score"].quantile(0.25))
    )
]

if fraud_df.empty:
    st.success("No major fraud patterns detected")
else:
    st.error("Potential Aadhaar misuse / fraud patterns detected")
    st.dataframe(
        fraud_df[["district","rush_index","digital_literacy_score","migration_score"]],
        use_container_width=True
    )

# =====================================================
# EXPLAINABLE AI
# =====================================================
with st.expander("ℹ️ Explainable AI & Fraud Logic"):
    st.markdown("""
**Fraud Indicators Used**

• **Update Abuse** → Excessive updates compared to enrolments  
• **Migration Spike** → Abnormal adult Aadhaar creation  
• **Middlemen Pattern** → High rush + low literacy  

⚠️ Dataset is anonymised — indicators flag *risk zones*, not individuals.
""")

# =====================================================
# AUTO REFRESH
# =====================================================
st.caption("🔄 Auto-refresh every 30 seconds")
time.sleep(30)
st.rerun()
