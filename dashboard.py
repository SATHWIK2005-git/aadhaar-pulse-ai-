import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from state_mapper import state_map

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Aadhaar Pulse AI+", layout="wide")
st.title("🇮🇳 Aadhaar Pulse AI+ — National Fraud & Service Intelligence")

# =========================
# LOAD DATA
# =========================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

NUM_COLS = ["rush_index", "digital_literacy_score", "migration_score"]
for c in NUM_COLS:
    data[c] = pd.to_numeric(data[c], errors="coerce")

# Normalize states
data["state"] = data["state"].replace(state_map)
data = data.dropna(subset=["state"])

# =========================
# LOAD & FIX GEOJSON
# =========================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

VALID_REGIONS = set(state_map.values())

filtered_features = []
for feature in india_geo["features"]:
    name = feature["properties"].get("NAME_1")

    if name == "Orissa":
        name = "Odisha"
    if name == "Uttaranchal":
        name = "Uttarakhand"

    feature["properties"]["NAME_1"] = name

    if name in VALID_REGIONS:
        filtered_features.append(feature)

india_geo["features"] = filtered_features

# =========================
# FRAUD ENGINE
# =========================
data["fraud_risk_score"] = (
    0.4 * data["rush_index"] +
    0.4 * data["migration_score"] +
    0.2 * (1 - data["digital_literacy_score"])
)

def classify_fraud(row):
    if row["fraud_risk_score"] > data["fraud_risk_score"].quantile(0.9):
        return "High-Risk Aadhaar Fraud"
    elif row["migration_score"] > data["migration_score"].quantile(0.9):
        return "Possible Duplicate / Migration Fraud"
    elif row["digital_literacy_score"] < data["digital_literacy_score"].quantile(0.25):
        return "Digital Identity Misuse Risk"
    else:
        return "Normal"

data["fraud_category"] = data.apply(classify_fraud, axis=1)

data["recommended_action"] = data["fraud_category"].map({
    "High-Risk Aadhaar Fraud": "Immediate biometric audit",
    "Possible Duplicate / Migration Fraud": "Cross-state Aadhaar verification",
    "Digital Identity Misuse Risk": "Local assisted update drive",
    "Normal": "No action required"
})

# =========================
# KPI PANEL
# =========================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total States & UTs", 36)
c2.metric("High Fraud Risk Districts", (data["fraud_category"] == "High-Risk Aadhaar Fraud").sum())
c3.metric("Migration Risk Districts", (data["fraud_category"] == "Possible Duplicate / Migration Fraud").sum())
c4.metric("Digital Misuse Risk Districts", (data["fraud_category"] == "Digital Identity Misuse Risk").sum())

# =========================
# STATE AGGREGATION
# =========================
state_data = data.groupby("state")[NUM_COLS + ["fraud_risk_score"]].mean().reset_index()

# =========================
# INDIA MAP
# =========================
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
    title="India Aadhaar Intelligence Heatmap"
)

fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, width="stretch")

# =========================
# STATE LEVEL INDICATORS
# =========================
st.subheader("📊 State-Level Indicators")

selected_state = st.selectbox(
    "Select State",
    sorted(state_data["state"].unique())
)

state_row = state_data[state_data["state"] == selected_state].iloc[0]

sc1, sc2, sc3 = st.columns(3)
sc1.metric("Rush Index", round(state_row["rush_index"], 2))
sc2.metric("Migration Index", round(state_row["migration_score"], 2))
sc3.metric("Digital Literacy", round(state_row["digital_literacy_score"], 2))

# =========================
# DISTRICT LEVEL TABLE
# =========================
st.subheader("🚨 District-Level Indicators & Fraud Analysis")

district_view = data[data["state"] == selected_state]

st.dataframe(
    district_view[
        [
            "district",
            "rush_index",
            "migration_score",
            "digital_literacy_score",
            "fraud_category",
            "fraud_risk_score",
            "recommended_action"
        ]
    ].sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# ==================================================
# ✅ NEW: STATE-WISE BAR GRAPH (COUNTRY LEVEL)
# ==================================================
st.subheader("📊 State-wise Aadhaar Risk & Usage Comparison")

state_bar = px.bar(
    state_data.melt(
        id_vars="state",
        value_vars=["rush_index", "migration_score", "digital_literacy_score", "fraud_risk_score"],
        var_name="Indicator",
        value_name="Score"
    ),
    x="state",
    y="Score",
    color="Indicator",
    barmode="group",
    title="State-wise Rush, Migration, Literacy & Fraud Risk"
)

st.plotly_chart(state_bar, width="stretch")

# ==================================================
# ✅ NEW: DISTRICT-WISE BAR GRAPH (SELECTED STATE)
# ==================================================
st.subheader("📊 District-wise Indicators (Selected State)")

district_bar = px.bar(
    district_view.melt(
        id_vars="district",
        value_vars=["rush_index", "migration_score", "digital_literacy_score", "fraud_risk_score"],
        var_name="Indicator",
        value_name="Score"
    ),
    x="district",
    y="Score",
    color="Indicator",
    barmode="group",
    title=f"{selected_state} — District-wise Aadhaar Indicators"
)

st.plotly_chart(district_bar, width="stretch")

# =========================
# 🧠 HOW AI WORKS
# =========================
with st.expander("🧠 How the AI Works (Explainable Intelligence)"):
    st.markdown("""
### 🔍 Core Indicators
- **Rush Index** → Measures Aadhaar service load  
- **Migration Index** → Detects adult population movement  
- **Digital Literacy Score** → Ability to manage Aadhaar digitally  

### 🚨 Fraud Risk Score
