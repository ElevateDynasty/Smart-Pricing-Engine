"""
Page 4: Inventory Risk & Product Lifecycle Radar
Identifies aging stock, calculates stranded capital, and tracks successor model launch deadlines.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.config import CURRENCY_SYMBOL
from dashboard.components.data_loader import load_models_and_pipeline, compute_all_sku_optimizations
from dashboard.components.charts import render_risk_quadrant_chart

st.set_page_config(page_title="Inventory Risk | AI Pricing Engine", page_icon="⚠️", layout="wide")

css_file = Path(__file__).resolve().parent.parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("⚠️ Inventory Risk & Lifecycle Countdown Radar")
st.caption("Proactively monitors aging stock and calculates potential depreciation write-downs prior to successor model launches.")

_, _, optimizer = load_models_and_pipeline()
results = compute_all_sku_optimizations(optimizer)

portfolio_df = pd.DataFrame([{
    "product_name": r.product_name,
    "product_id": r.product_id,
    "current_inventory": r.current_inventory,
    "unit_cost": r.unit_cost,
    "current_price": r.current_price,
    "recommended_price": r.recommended_price,
    "days_to_successor": r.days_to_successor,
    "inventory_risk_level": r.inventory_risk_level,
    "status_quo_leftover": int(r.status_quo_leftover),
    "ai_leftover": int(r.expected_leftover_inventory),
    "status_quo_depreciation": int(r.status_quo_leftover * r.unit_cost * 0.30),
    "ai_depreciation": int(r.depreciation_loss)
} for r in results])

# High-level Risk KPIs
high_risk_skus = portfolio_df[portfolio_df["inventory_risk_level"] == "High Risk"]
total_stranded_capital_sq = (portfolio_df["status_quo_leftover"] * portfolio_df["unit_cost"]).sum()
total_depreciation_sq = portfolio_df["status_quo_depreciation"].sum()
total_depreciation_ai = portfolio_df["ai_depreciation"].sum()
capital_saved = total_depreciation_sq - total_depreciation_ai

rk1, rk2, rk3 = st.columns(3)
with rk1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Status Quo Stranded Stock Risk</div>
            <div class="metric-value">{CURRENCY_SYMBOL}{total_stranded_capital_sq/100000:.1f} Lakhs</div>
            <div class="metric-delta-neg">If current prices remain unchanged</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with rk2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Depreciation Write-Down Avoided</div>
            <div class="metric-value">+{CURRENCY_SYMBOL}{capital_saved/100000:.1f} Lakhs</div>
            <div class="metric-delta-pos">Capital preserved by AI recommendations</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with rk3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Critical Attention Models</div>
            <div class="metric-value">{len(high_risk_skus)} Models</div>
            <div class="metric-delta-neg">Successor arrival in &lt; 60 days</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Risk Matrix Visualization
st.plotly_chart(render_risk_quadrant_chart(portfolio_df), use_container_width=True)

st.markdown("---")
st.subheader("📋 Successor Countdown & Leftover Exposure Table")

disp_df = portfolio_df[[
    "product_name",
    "days_to_successor",
    "current_inventory",
    "status_quo_leftover",
    "ai_leftover",
    "status_quo_depreciation",
    "ai_depreciation",
    "inventory_risk_level"
]].copy()

disp_df.columns = [
    "Product Name",
    "Days to Successor",
    "Current Stock",
    "Stranded Stock (Status Quo)",
    "Stranded Stock (AI Rec)",
    "Depreciation Penalty (Status Quo)",
    "Depreciation Penalty (AI Rec)",
    "Risk Level"
]

disp_df["Depreciation Penalty (Status Quo)"] = disp_df["Depreciation Penalty (Status Quo)"].apply(lambda x: f"₹{x:,}")
disp_df["Depreciation Penalty (AI Rec)"] = disp_df["Depreciation Penalty (AI Rec)"].apply(lambda x: f"₹{x:,}")

st.dataframe(disp_df, use_container_width=True, hide_index=True)
