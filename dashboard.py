import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from state_mapper import state_map

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("🇮🇳 Aadhaar Pulse AI+ — National Fraud & Service Intelligence")

# =========================
# LOAD DATA
# =========================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

# numeric safety
num_cols = ["rush_index", "digital_literacy_score", "migration_score"]
for c in num_cols:
    data[c] = pd.to_numeric(data[c], errors="coerce")

# normalize state names
data["state"] = data["state"].map(state_map)
data = data.dropna(subset=["state"])

# =========================
# FRAUD LOGIC (CORE AI)
# =========================

# Fraud Risk Score (Explainable AI)
data["fraud_risk_score"] = (
    0.4 * data["rush_index"] +
    0.4 * data["migration_score"] +
    0.2 * (1 - data["digital_literacy_score"])
)

# Fraud Category
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

# Recommended Action
action_map = {
    "High-Risk Aadhaar Fraud": "Immediate field audit & biometric re-verification",
    "Possible Duplicate / Migration Fraud": "Cross-state Aadhaar linkage review",
    "Digital Identity Misuse Risk": "Local Aadhaar awareness & assisted update drive",
    "Normal": "No action required"
}
data["recommended_action"] = data["fraud_category"].map(action_map)

# =========================
# KPI PANEL
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Districts", len(data))
c2.metric("High Fraud Risk", (data["fraud_category"] == "High-Risk Aadhaar Fraud").sum())
c3.metric("Migration Risk", (data["fraud_category"] == "Possible Duplicate / Migration Fraud").sum())
c4.metric("Digital Misuse Risk", (data["fraud_category"] == "Digital Identity Misuse Risk").sum())

# =========================
# STATE AGGREGATION
# =========================
state_data = data.groupby("state")[num_cols].mean().reset_index()

# =========================
# INDIA MAP
# =========================
with open("india_states.geojson") as f:
    india_geo = json.load(f)

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
    color_continuous_scale="RdYlGn",
    title=f"India Aadhaar {indicator.replace('_',' ').title()}"
)
fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, use_container_width=True)

# =========================
# STATE → DISTRICT DRILLDOWN
# =========================
st.subheader("📍 District Fraud Drilldown")

selected_state = st.selectbox("Select State", state_data["state"].unique())
district_view = data[data["state"] == selected_state]

st.dataframe(
    district_view[
        ["district", "fraud_category", "fraud_risk_score", "recommended_action"]
    ].sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# =========================
# FRAUD ALERTS
# =========================
st.subheader("🚨 Live Fraud Alerts")

alerts = district_view[district_view["fraud_category"] != "Normal"]

if alerts.empty:
    st.success("No critical fraud detected in this state.")
else:
    for _, r in alerts.head(5).iterrows():
        st.error(
            f"{r['district']} → {r['fraud_category']} | Action: {r['recommended_action']}"
        )

# =========================
# PDF REPORT GENERATOR
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

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "High-Risk Districts")
    y -= 20

    c.setFont("Helvetica", 9)
    for _, r in df[df["fraud_category"] != "Normal"].head(15).iterrows():
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

# =========================
# REPORT BUTTON
# =========================
st.subheader("📄 Official UIDAI Fraud Report")

if st.button("Generate PDF Fraud Report"):
    pdf = generate_fraud_report(data)
    with open(pdf, "rb") as f:
        st.download_button(
            "⬇️ Download Report",
            f,
            file_name=pdf,
            mime="application/pdf"
        )

# =========================
# EXPLAINABLE AI
# =========================
with st.expander("🧠 Explainable AI Logic"):
    st.write("""
    Fraud Risk Score =
    0.4 × Rush Index +
    0.4 × Migration Score +
    0.2 × (1 − Digital Literacy)

    • No biometric or personal data used  
    • Fully policy-compliant  
    • Designed for UIDAI monitoring
    """)
