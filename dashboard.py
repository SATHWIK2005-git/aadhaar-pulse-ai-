import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from state_mapper import state_map

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Aadhaar Pulse AI+",
    layout="wide"
)

st.title("🇮🇳 Aadhaar Pulse AI+ — National Fraud & Service Intelligence")

# =========================
# LOAD DATA
# =========================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

numeric_cols = ["rush_index", "digital_literacy_score", "migration_score"]
for col in numeric_cols:
    data[col] = pd.to_numeric(data[col], errors="coerce")

# Normalize states
data["state"] = data["state"].replace(state_map)
data = data.dropna(subset=["state"])

# =========================
# FRAUD ENGINE (FIXED)
# =========================
data["fraud_risk_score"] = (
    0.4 * data["rush_index"].clip(lower=0) +
    0.4 * data["migration_score"].clip(lower=0) +
    0.2 * (data["digital_literacy_score"].max() - data["digital_literacy_score"])
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
    "High-Risk Aadhaar Fraud": "Immediate biometric re-verification",
    "Possible Duplicate / Migration Fraud": "Cross-state Aadhaar linkage review",
    "Digital Identity Misuse Risk": "Local assisted Aadhaar update drive",
    "Normal": "No action required"
}
data["recommended_action"] = data["fraud_category"].map(action_map)

# =========================
# STATE AGGREGATION
# =========================
state_data = data.groupby("state")[numeric_cols].mean().reset_index()

# =========================
# KPI PANEL (FIXED)
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total States / UTs", state_data["state"].nunique())
c2.metric("High Fraud Risk Districts", (data["fraud_category"] == "High-Risk Aadhaar Fraud").sum())
c3.metric("Migration Risk Districts", (data["fraud_category"] == "Possible Duplicate / Migration Fraud").sum())
c4.metric("Digital Misuse Risk Districts", (data["fraud_category"] == "Digital Identity Misuse Risk").sum())

# =========================
# INDIA MAP
# =========================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

indicator = st.selectbox(
    "Select Indicator",
    {
        "rush_index": "Rush Index",
        "digital_literacy_score": "Digital Literacy",
        "migration_score": "Migration Index"
    }.keys(),
    format_func=lambda x: {
        "rush_index": "Rush Index",
        "digital_literacy_score": "Digital Literacy",
        "migration_score": "Migration Index"
    }[x]
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
fig.update_layout(height=600, margin=dict(l=0, r=0, t=50, b=0))
st.plotly_chart(fig, use_container_width=True)

# =========================
# STATE LEVEL INDICATORS
# =========================
st.subheader("📊 State-Level Indicators")

selected_state = st.selectbox("Select State", sorted(state_data["state"].unique()))
state_row = state_data[state_data["state"] == selected_state].iloc[0]

k1, k2, k3 = st.columns(3)
k1.metric("Rush Index", f"{state_row['rush_index']:.2f}")
k2.metric("Migration Index", f"{state_row['migration_score']:.2f}")
k3.metric("Digital Literacy", f"{state_row['digital_literacy_score']:.2f}")

# =========================
# DISTRICT LEVEL INDICATORS
# =========================
st.subheader("📍 District-Level Indicators")

districts = data[data["state"] == selected_state]

st.dataframe(
    districts[
        ["district", "rush_index", "migration_score", "digital_literacy_score"]
    ].sort_values("rush_index", ascending=False),
    use_container_width=True
)

# =========================
# DISTRICT FRAUD ANALYSIS
# =========================
st.subheader("🚨 District Fraud Analysis")

st.dataframe(
    districts[
        ["district", "fraud_category", "fraud_risk_score", "recommended_action"]
    ].sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# =========================
# PDF REPORT
# =========================
def generate_pdf(df):
    fname = f"Aadhaar_Fraud_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    c = canvas.Canvas(fname, pagesize=A4)
    w, h = A4
    y = h - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "UIDAI – Aadhaar Fraud Intelligence Report")
    y -= 30

    c.setFont("Helvetica", 10)
    for _, r in df[df["fraud_category"] != "Normal"].head(20).iterrows():
        c.drawString(
            40, y,
            f"{r['state']} | {r['district']} | {r['fraud_category']} | Risk {r['fraud_risk_score']:.2f}"
        )
        y -= 14
        if y < 80:
            c.showPage()
            y = h - 40

    c.save()
    return fname

st.subheader("📄 Official Fraud Report")

if st.button("Generate PDF Fraud Report"):
    pdf = generate_pdf(data)
    with open(pdf, "rb") as f:
        st.download_button("⬇️ Download Report", f, file_name=pdf, mime="application/pdf")

# =========================
# EXPLAINABLE AI
# =========================
with st.expander("🧠 Explainable AI Logic"):
    st.markdown("""
**Fraud Risk Score**  
= 0.4 × Rush Index  
+ 0.4 × Migration Index  
+ 0.2 × (Low Digital Literacy)

**Red Zones** → Immediate UIDAI audit  
**Yellow Zones** → Assisted service drives  
""")
