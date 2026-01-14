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

# Normalize state names
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
# KPI PANEL
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total States / UTs", len(state_map.values()))
c2.metric("High Fraud Risk Districts", (data["fraud_category"] == "High-Risk Aadhaar Fraud").sum())
c3.metric("Migration Risk Districts", (data["fraud_category"] == "Possible Duplicate / Migration Fraud").sum())
c4.metric("Digital Misuse Risk Districts", (data["fraud_category"] == "Digital Identity Misuse Risk").sum())

# =========================
# STATE AGGREGATION
# =========================
state_data = data.groupby("state")[num_cols].mean().reset_index()

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
    title="India Aadhaar Heatmap"
)

fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, width="stretch")

# =========================
# STATE DRILLDOWN
# =========================
st.subheader("📊 State-Level Indicators")

selected_state = st.selectbox("Select State", sorted(state_data["state"].unique()))
state_row = state_data[state_data["state"] == selected_state].iloc[0]

sc1, sc2, sc3 = st.columns(3)
sc1.metric("Rush Index", round(state_row["rush_index"], 2))
sc2.metric("Migration Index", round(state_row["migration_score"], 2))
sc3.metric("Digital Literacy", round(state_row["digital_literacy_score"], 2))

# =========================
# DISTRICT DRILLDOWN (✅ ADDED)
# =========================
st.subheader("📍 District-Level Indicators & Fraud Analysis")

district_view = data[data["state"] == selected_state]

selected_district = st.selectbox(
    "Select District",
    sorted(district_view["district"].unique())
)

district_row = district_view[district_view["district"] == selected_district].iloc[0]

d1, d2, d3 = st.columns(3)
d1.metric("District Rush Index", round(district_row["rush_index"], 2))
d2.metric("District Migration Index", round(district_row["migration_score"], 2))
d3.metric("District Digital Literacy", round(district_row["digital_literacy_score"], 2))

st.dataframe(
    district_view[
        ["district", "fraud_category", "fraud_risk_score", "recommended_action"]
    ].sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# =========================
# PDF REPORT
# =========================
def generate_fraud_report(df):
    fname = f"UIDAI_Fraud_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    c = canvas.Canvas(fname, pagesize=A4)
    w, h = A4
    y = h - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "UIDAI – Aadhaar Fraud Intelligence Report")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Generated on: {datetime.now()}")
    y -= 30

    for _, r in df[df["fraud_category"] != "Normal"].head(25).iterrows():
        c.drawString(
            40, y,
            f"{r['state']} | {r['district']} | {r['fraud_category']} | Risk={r['fraud_risk_score']:.2f}"
        )
        y -= 12
        if y < 80:
            c.showPage()
            y = h - 40

    c.save()
    return fname

if st.button("📄 Generate UIDAI Fraud Report (PDF)"):
    pdf = generate_fraud_report(data)
    with open(pdf, "rb") as f:
        st.download_button("⬇️ Download Report", f, file_name=pdf)

# =========================
# AUTO REFRESH
# =========================
st.caption("🔄 Auto-refresh every 30 seconds")
time.sleep(30)
st.rerun()
