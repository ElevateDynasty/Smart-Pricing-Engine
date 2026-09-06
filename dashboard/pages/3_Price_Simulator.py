"""
Page 3: Interactive Price Simulator & What-If Sandbox
Allows retailers to experiment with candidate selling prices and contextual variables in real time.
"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.config import CURRENCY_SYMBOL
from dashboard.components.data_loader import load_models_and_pipeline, load_catalog_and_meta
from dashboard.components.charts import (
    BG_PAPER, BG_PLOT, PLOTLY_TEMPLATE, COLOR_CYAN, COLOR_EMERALD, COLOR_AMBER, COLOR_ROSE
)

st.set_page_config(page_title="Price Simulator | AI Pricing Engine", page_icon="🎛️", layout="wide")

css_file = Path(__file__).resolve().parent.parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🎛️ Interactive Price Simulator & What-If Sandbox")
st.caption("Test hypothetical selling prices, competitor stockouts, and footfall shifts to observe live demand and profit reactions.")

forecaster, elasticity_est, optimizer = load_models_and_pipeline()
products_df, costs_df, competitors_df = load_catalog_and_meta()

# Merge catalog info
latest_date = competitors_df["date"].max()
latest_comp = competitors_df[competitors_df["date"] == latest_date].groupby("product_id").agg(
    competitor_avg_price=("competitor_price", "mean"),
    competitor_min_price=("competitor_price", "min")
).reset_index()

catalog = products_df.merge(costs_df, on="product_id", how="left").merge(latest_comp, on="product_id", how="left")
sku_dict = {f"{r['brand']} {r['model']} ({r['variant']})": r for _, r in catalog.iterrows()}

col_ctrl1, col_ctrl2 = st.columns([1.2, 1])
with col_ctrl1:
    selected_name = st.selectbox("Choose Product to Simulate:", options=list(sku_dict.keys()), index=0)
    sku_data = sku_dict[selected_name]

    mrp = float(sku_data["mrp"])
    cost = float(sku_data["unit_cost"])
    comp_avg = float(sku_data["competitor_avg_price"])
    comp_min = float(sku_data["competitor_min_price"])

    # Simulator Price Slider
    sim_price = st.slider(
        "Candidate Selling Price (₹):",
        min_value=int(cost),
        max_value=int(mrp),
        value=int(round(comp_avg * 1.01, -2)),
        step=500,
        help="Adjust price to see live demand velocity and lifecycle profit."
    )

with col_ctrl2:
    st.markdown("#### Scenario Context Modifiers")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        sim_inventory = st.number_input("Store Inventory:", min_value=10, max_value=2000, value=800 if "17" in selected_name else 250, step=50)
        sim_horizon = st.slider("Days to Successor:", min_value=15, max_value=180, value=int(sku_data["days_to_successor"]), step=5)
    with col_c2:
        comp_stockout = st.checkbox("Competitor Out of Stock?", value=False)
        footfall_boost = st.selectbox("Footfall Condition:", ["Normal Footfall", "High Traffic Mall (+25%)", "Slow Footfall (-20%)"], index=0)

footfall_mult = 1.25 if "High" in footfall_boost else (0.85 if "Slow" in footfall_boost else 1.0)

# Run Live Simulation
pred_demand = forecaster.predict_point(
    selling_price=sim_price,
    mrp=mrp,
    competitor_avg_price=comp_avg,
    competitor_min_price=comp_min,
    unit_cost=cost,
    opening_inventory=sim_inventory,
    days_to_successor=sim_horizon,
    competitor_stockout_flag=1 if comp_stockout else 0,
    footfall_index=1.2 * footfall_mult
)

pred_demand = max(0.01, float(pred_demand))
total_sales = min(float(sim_inventory), pred_demand * sim_horizon)
leftover_inv = max(0.0, float(sim_inventory) - total_sales)
clearance_days = sim_inventory / pred_demand
clearance_pct = (total_sales / sim_inventory) * 100.0

revenue = total_sales * sim_price
cogs = total_sales * cost
gross_margin = revenue - cogs
carrying_cost = ((sim_inventory + leftover_inv) / 2.0) * cost * (0.0005 + 0.12/365.0) * sim_horizon
depreciation_loss = leftover_inv * cost * 0.30
net_profit = gross_margin - carrying_cost - depreciation_loss

st.markdown("<br>", unsafe_allow_html=True)

# Live KPIs
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Predicted Sales Velocity</div>
            <div class="metric-value">{pred_demand:.1f}</div>
            <div class="metric-delta-pos">units / day</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Expected Net Profit</div>
            <div class="metric-value">{CURRENCY_SYMBOL}{int(net_profit):,}</div>
            <div class="metric-delta-pos">Over {sim_horizon} days</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Projected Clearance</div>
            <div class="metric-value">{clearance_days:.0f} Days</div>
            <div class="{'metric-delta-pos' if clearance_days <= sim_horizon else 'metric-delta-neg'}">
                {'Clears within deadline' if clearance_days <= sim_horizon else 'Exceeds horizon!'}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Clearance Percentage</div>
            <div class="metric-value">{clearance_pct:.1f}%</div>
            <div class="{'metric-delta-pos' if clearance_pct >= 95 else 'metric-delta-neg'}">
                {int(total_sales)} of {sim_inventory} units
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with m5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Leftover Inventory Risk</div>
            <div class="metric-value">{int(leftover_inv)} Units</div>
            <div class="{'metric-delta-neg' if leftover_inv > 0 else 'metric-delta-pos'}">
                -₹{int(depreciation_loss):,} markdown risk
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Generate Live Simulated Curve
prices_range = np.linspace(cost, mrp, 30)
demands_range = forecaster.predict_demand_curve(
    candidate_prices=prices_range,
    mrp=mrp,
    competitor_avg_price=comp_avg,
    competitor_min_price=comp_min,
    unit_cost=cost,
    opening_inventory=sim_inventory,
    days_to_successor=sim_horizon,
    competitor_stockout_flag=1 if comp_stockout else 0,
    footfall_index=1.2 * footfall_mult
)

profits_range = []
for p, d in zip(prices_range, demands_range):
    s = min(float(sim_inventory), d * sim_horizon)
    l = max(0.0, float(sim_inventory) - s)
    rev = s * p
    gm = rev - (s * cost)
    c_cost = ((sim_inventory + l) / 2.0) * cost * (0.0005 + 0.12/365.0) * sim_horizon
    dep = l * cost * 0.30
    profits_range.append((gm - c_cost - dep) / 100000.0)

fig_sim = go.Figure()
fig_sim.add_trace(go.Scatter(
    x=prices_range,
    y=profits_range,
    mode="lines",
    name="Simulated Profit Curve (₹ Lakhs)",
    line=dict(color=COLOR_CYAN, width=3.5)
))

# Highlight current simulator price
fig_sim.add_trace(go.Scatter(
    x=[sim_price],
    y=[net_profit / 100000.0],
    mode="markers+text",
    name="Selected Price Point",
    text=[f"Current Test: ₹{sim_price:,}"],
    textposition="top center",
    marker=dict(color=COLOR_EMERALD, size=16, symbol="diamond", line=dict(color="#ffffff", width=2))
))

fig_sim.update_layout(
    title=dict(text=f"<b>Live Profit Sensitivity Curve: {selected_name}</b>", font=dict(size=16)),
    template=PLOTLY_TEMPLATE,
    paper_bgcolor=BG_PAPER,
    plot_bgcolor=BG_PLOT,
    xaxis=dict(title="Selling Price (₹)", tickprefix="₹", gridcolor="rgba(255,255,255,0.06)"),
    yaxis=dict(title="Expected Total Profit (₹ Lakhs)", gridcolor="rgba(255,255,255,0.06)"),
    margin=dict(l=40, r=40, t=50, b=40)
)

st.plotly_chart(fig_sim, use_container_width=True)
