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
st.set_page_config(
    page_title="Aadhaar Pulse AI+",
    layout="wide"
)

st.title("🇮🇳 Aadhaar Pulse AI+ — National Fraud & Service Intelligence")

# =========================
# LOAD DATA
# =========================
data = pd.read_csv("Aadhaar_Intelligence_Indicators.csv")

NUM_COLS = ["rush_index", "digital_literacy_score", "migration_score"]
for col in NUM_COLS:
    data[col] = pd.to_numeric(data[col], errors="coerce")

# Normalize state names (dataset)
data["state"] = data["state"].replace(state_map)
data = data.dropna(subset=["state"])

# =========================
# LOAD & FIX GEOJSON
# =========================
with open("india_states.geojson", "r", encoding="utf-8") as f:
    india_geo = json.load(f)

VALID_REGIONS = set(state_map.values())

fixed_features = []
for feature in india_geo["features"]:
    name = feature["properties"].get("NAME_1")

    # 🔧 Legacy name fixes
    if name == "Orissa":
        name = "Odisha"
    if name == "Uttaranchal":
        name = "Uttarakhand"

    feature["properties"]["NAME_1"] = name

    if name in VALID_REGIONS:
        fixed_features.append(feature)

india_geo["features"] = fixed_features

# =========================
# FRAUD ENGINE (AI LOGIC)
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
    "High-Risk Aadhaar Fraud": "Immediate biometric audit & UIDAI review",
    "Possible Duplicate / Migration Fraud": "Cross-state Aadhaar linkage check",
    "Digital Identity Misuse Risk": "Assisted Aadhaar update & awareness drive",
    "Normal": "No action required"
})

# =========================
# KPI PANEL (FIXED COUNT)
# =========================
TOTAL_OFFICIAL_REGIONS = 36  # 28 States + 8 UTs

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total States & UTs", TOTAL_OFFICIAL_REGIONS)
k2.metric("High Fraud Risk Districts", (data["fraud_category"] == "High-Risk Aadhaar Fraud").sum())
k3.metric("Migration Risk Districts", (data["fraud_category"] == "Possible Duplicate / Migration Fraud").sum())
k4.metric("Digital Misuse Risk Districts", (data["fraud_category"] == "Digital Identity Misuse Risk").sum())

# =========================
# STATE AGGREGATION
# =========================
state_data = (
    data.groupby("state")[NUM_COLS]
    .mean()
    .reset_index()
)

# =========================
# INDIA HEATMAP
# =========================
indicator = st.selectbox(
    "Select Indicator",
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
fig.update_layout(height=600, margin={"r":0,"t":50,"l":0,"b":0})
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

s1, s2, s3 = st.columns(3)
s1.metric("Rush Index", round(state_row["rush_index"], 2))
s2.metric("Migration Index", round(state_row["migration_score"], 2))
s3.metric("Digital Literacy", round(state_row["digital_literacy_score"], 2))

# =========================
# DISTRICT FRAUD ANALYSIS
# =========================
st.subheader("🚨 District Fraud Analysis")

district_view = data[data["state"] == selected_state]

st.dataframe(
    district_view[
        ["district", "fraud_category", "fraud_risk_score", "recommended_action"]
    ].sort_values("fraud_risk_score", ascending=False),
    use_container_width=True
)

# =========================
# PDF REPORT GENERATOR
# =========================
def generate_fraud_report(df):
    filename = f"UIDAI_Fraud_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
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
    return filename

st.subheader("📄 Official UIDAI Fraud Report")

if st.button("Generate PDF Fraud Report"):
    pdf_file = generate_fraud_report(data)
    with open(pdf_file, "rb") as f:
        st.download_button(
            "⬇️ Download Report",
            f,
            file_name=pdf_file,
            mime="application/pdf"
        )

# =========================
# EXPLAINABLE AI
# =========================
with st.expander("🧠 Explainable AI Logic"):
    st.markdown("""
**Fraud Risk Score Formula**

0.4 × Rush Index  
0.4 × Migration Index  
0.2 × (1 − Digital Literacy)

• No personal or biometric data used  
• Fully UIDAI policy compliant  
• Designed for national monitoring
""")

# =========================
# AUTO REFRESH
# =========================
st.caption("🔄 Auto-refresh every 30 seconds")
time.sleep(30)
st.rerun()
