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

num_cols = ["rush_index", "digital_literacy_score", "migration_score"]
for c in num_cols:
    data[c] = pd.to_numeric(data[c], errors="coerce")

# Normalize states
data["state"] = data["state"].replace(state_map)
data = data.dropna(subset=["state"])

VALID_STATES = set(state_map.values())

# =========================
# LOAD & FILTER GEOJSON
# =========================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

filtered_features = []
for feature in india_geo["features"]:
    name = feature["properties"].get("NAME_1")

    if name == "Orissa":
        name = "Odisha"
        feature["properties"]["NAME_1"] = "Odisha"

    if name in VALID_STATES:
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

action_map = {
    "High-Risk Aadhaar Fraud": "Immediate biometric audit",
    "Possible Duplicate / Migration Fraud": "Cross-state Aadhaar verification",
    "Digital Identity Misuse Risk": "Local assisted update drive",
    "Normal": "No action required"
}
data["recommended_action"] = data["fraud_category"].map(action_map)

# =========================
# KPI PANEL (UNCHANGED)
# =========================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total States & UTs", len(data["state"].unique()))
c2.metric("High Fraud Risk Districts", (data["fraud_category"] == "High-Risk Aadhaar Fraud").sum())
c3.metric("Migration Risk Districts", (data["fraud_category"] == "Possible Duplicate / Migration Fraud").sum())
c4.metric("Digital Misuse Risk Districts", (data["fraud_category"] == "Digital Identity Misuse Risk").sum())

# =========================
# STATE AGGREGATION
# =========================
state_data = data.groupby("state")[num_cols].mean().reset_index()

# =========================
# INDIA MAP (UNCHANGED)
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
# STATE DRILLDOWN (UNCHANGED)
# =========================
st.subheader("📊 State-Level Indicators")

selected_state = st.selectbox("Select State", sorted(state_data["state"].unique()))
state_row = state_data[state_data["state"] == selected_state].iloc[0]

sc1, sc2, sc3 = st.columns(3)
sc1.metric("Rush Index", round(state_row["rush_index"], 2))
sc2.metric("Migration Index", round(state_row["migration_score"], 2))
sc3.metric("Digital Literacy", round(state_row["digital_literacy_score"], 2))

# =========================
# DISTRICT FRAUD TABLE (UNCHANGED)
# =========================
st.subheader("🚨 District Fraud Analysis")

district_view = data[data["state"] == selected_state]

st.dataframe(
    district_view[
        [
            "district",
            "rush_index",
            "migration_score",
            "digital_literacy_score",
            "fraud_risk_score",
            "fraud_category",
            "recommended_action"
        ]
    ].sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# =====================================================================
# 🆕 ADDITION 1 — STATE-LEVEL TABLE (LIKE DISTRICT TABLE)
# =====================================================================
st.subheader("🏛️ State-Level Detailed Indicators")

state_table = (
    data.groupby("state")
    .agg({
        "rush_index": "mean",
        "migration_score": "mean",
        "digital_literacy_score": "mean",
        "fraud_risk_score": "mean"
    })
    .reset_index()
)

def classify_state_fraud(row):
    if row["fraud_risk_score"] > state_table["fraud_risk_score"].quantile(0.9):
        return "High-Risk Aadhaar Fraud"
    elif row["migration_score"] > state_table["migration_score"].quantile(0.9):
        return "Migration Risk"
    elif row["digital_literacy_score"] < state_table["digital_literacy_score"].quantile(0.25):
        return "Digital Misuse Risk"
    else:
        return "Normal"

state_table["fraud_category"] = state_table.apply(classify_state_fraud, axis=1)

state_action_map = {
    "High-Risk Aadhaar Fraud": "State-wide audit",
    "Migration Risk": "Inter-state verification",
    "Digital Misuse Risk": "Awareness drive",
    "Normal": "No action required"
}

state_table["recommended_action"] = state_table["fraud_category"].map(state_action_map)

st.dataframe(
    state_table.sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# =====================================================================
# 🆕 ADDITION 2 — STATE-WISE BAR GRAPHS (SEPARATE)
# =====================================================================
st.subheader("📊 State-Level Visual Analytics")

fig_sr = px.bar(
    state_table.sort_values("rush_index", ascending=False),
    x="state", y="rush_index",
    title="State-wise Rush Index",
    color="rush_index", color_continuous_scale="Reds"
)
fig_sr.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_sr, width="stretch")

fig_sm = px.bar(
    state_table.sort_values("migration_score", ascending=False),
    x="state", y="migration_score",
    title="State-wise Migration Index",
    color="migration_score", color_continuous_scale="Oranges"
)
fig_sm.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_sm, width="stretch")

fig_sl = px.bar(
    state_table.sort_values("digital_literacy_score"),
    x="state", y="digital_literacy_score",
    title="State-wise Digital Literacy",
    color="digital_literacy_score", color_continuous_scale="Greens"
)
fig_sl.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_sl, width="stretch")

fig_sf = px.bar(
    state_table.sort_values("fraud_risk_score", ascending=False),
    x="state", y="fraud_risk_score",
    title="State-wise Fraud Risk Score",
    color="fraud_risk_score", color_continuous_scale="RdYlGn_r"
)
fig_sf.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_sf, width="stretch")

# =====================================================================
# 🆕 ADDITION 3 — EXPLAINABLE AI PANEL
# =====================================================================
with st.expander("🧠 How AI Works"):
    st.markdown("""
**Fraud Risk Score**  
`0.4 × Rush Index + 0.4 × Migration Index + 0.2 × (1 − Digital Literacy)`

**Interpretation**
- High Rush → Service pressure / duplicate attempts
- High Migration → Cross-region identity reuse
- Low Literacy → Assisted misuse risk

✔ No biometric data  
✔ No personal identifiers  
✔ Fully policy-compliant
""")

# =========================
# AUTO REFRESH (UNCHANGED)
# =========================
st.caption("🔄 Auto-refresh every 30 seconds")
time.sleep(30)
st.rerun()
