import streamlit as st
import pandas as pd
import plotly.express as px
import json
from state_mapper import state_map

st.set_page_config(layout="wide")
st.title("🇮🇳 Aadhaar Pulse AI+ — National Digital Inclusion & Service Intelligence")

# ============================
# LOAD DATA
# ============================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

# Convert numeric columns
cols = ["rush_index", "digital_literacy_score", "migration_score"]
for c in cols:
    data[c] = pd.to_numeric(data[c], errors="coerce")

# Normalize state names using mapping
data["state"] = data["state"].map(state_map)
data = data.dropna(subset=["state"])

# ============================
# LOAD INDIA GEOJSON
# ============================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

# ============================
# AGGREGATE TO STATE LEVEL
# ============================
state_data = data.groupby("state")[cols].mean().reset_index()

# ============================
# KPI PANEL
# ============================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total States", state_data["state"].nunique())
c2.metric("High Rush States", (state_data["rush_index"] > state_data["rush_index"].quantile(0.9)).sum())
c3.metric("Low Literacy States", (state_data["digital_literacy_score"] < state_data["digital_literacy_score"].quantile(0.25)).sum())
c4.metric("Migration Hotspots", (state_data["migration_score"] > state_data["migration_score"].quantile(0.9)).sum())

# ============================
# INDICATOR SELECT
# ============================
indicator = st.selectbox(
    "Select Indicator",
    ["rush_index", "digital_literacy_score", "migration_score"]
)

# ============================
# INDIA HEAT MAP
# ============================
fig = px.choropleth(
    state_data,
    geojson=india_geo,
    featureidkey="properties.NAME_1",
    locations="state",
    color=indicator,
    color_continuous_scale="RdYlGn",
    title="India Aadhaar " + indicator.replace("_", " ").title()
)
fig.update_geos(fitbounds="locations", visible=False)

st.plotly_chart(fig, width="stretch")

# ============================
# STATE DRILLDOWN
# ============================
st.subheader("State Drilldown")

selected_state = st.selectbox("Select State", state_data["state"].unique())

districts = data[data["state"] == selected_state]

st.dataframe(
    districts[["district", "rush_index", "digital_literacy_score", "migration_score"]]
    .sort_values("rush_index", ascending=False)
)

# ============================
# CONTEXT AI
# ============================
st.subheader("AI Context Engine")

r = districts["rush_index"].mean()
l = districts["digital_literacy_score"].mean()
m = districts["migration_score"].mean()

if r > state_data["rush_index"].quantile(0.8) and m > state_data["migration_score"].quantile(0.8):
    st.error("High Aadhaar rush likely due to labour migration or urban expansion")
elif r > state_data["rush_index"].quantile(0.8) and l > state_data["digital_literacy_score"].quantile(0.6):
    st.warning("High Aadhaar activity driven by digital awareness drives")
elif r < state_data["rush_index"].quantile(0.3) and l < state_data["digital_literacy_score"].quantile(0.3):
    st.info("Digital exclusion zone – Aadhaar outreach required")
else:
    st.success("Normal Aadhaar activity")

# ============================
# EXPLAINABLE AI
# ============================
with st.expander("How AI Works"):
    st.write("""
    **Rush Index** = Aadhaar activity per active day  
    **Digital Literacy** = Updates ÷ Enrolments  
    **Migration Score** = Adult Aadhaar ÷ Child Aadhaar  
    """)
