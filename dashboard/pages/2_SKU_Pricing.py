"""
Page 2: SKU Pricing Deep-Dive & Recommendation Card
Focuses on individual smartphone lifecycle analysis (featuring the flagship iPhone 17 800-unit showcase).
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
from dashboard.components.charts import (
    render_demand_and_profit_curves,
    render_inventory_trajectory_chart
)
from src.explainability.reason_generator import ReasonGenerator

st.set_page_config(page_title="SKU Pricing Deep-Dive | AI Pricing Engine", page_icon="🏷️", layout="wide")

css_file = Path(__file__).resolve().parent.parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🏷️ SKU Pricing Deep-Dive & Lifecycle Recommendation")
st.caption("Detailed unit economics, demand curve simulation, and risk mitigation per individual product.")

_, elasticity_est, optimizer = load_models_and_pipeline()
results = compute_all_sku_optimizations(optimizer)

# SKU Selector dropdown
sku_options = {r.product_name: r for r in results}
default_index = 0
for idx, name in enumerate(sku_options.keys()):
    if "iPhone 17" in name:
        default_index = idx
        break

selected_sku_name = st.selectbox(
    "Select Smartphone Model to Analyze:",
    options=list(sku_options.keys()),
    index=default_index
)

r = sku_options[selected_sku_name]
el_info = elasticity_est.get_elasticity(r.product_id)

# Prominent AI Recommendation Hero Box
action_class = "badge-hold"
if r.price_action == "Increase Price":
    action_class = "badge-increase"
elif r.price_action == "Slight Reduction":
    action_class = "badge-reduction"
elif r.price_action == "Clearance Markdown":
    action_class = "badge-markdown"

st.markdown(
    f"""
    <div class="ai-recommendation-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <span class="badge-action {action_class}">{r.price_action}</span>
            <span style="color: #94a3b8; font-size: 0.9rem;">Model Version: LightGBM v1.0 (Constrained)</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem;">
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Current Selling Price</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #f1f5f9;">{CURRENCY_SYMBOL}{int(r.current_price):,}</div>
                <div style="color: #94a3b8; font-size: 0.85rem;">MRP: {CURRENCY_SYMBOL}{int(r.mrp):,} | Cost: {CURRENCY_SYMBOL}{int(r.unit_cost):,}</div>
            </div>
            <div>
                <div style="color: #38bdf8; font-size: 0.85rem; text-transform: uppercase; font-weight: 700;">AI Recommended Price</div>
                <div style="font-size: 2.2rem; font-weight: 900; color: #38bdf8;">{CURRENCY_SYMBOL}{int(r.recommended_price):,}</div>
                <div style="color: {'#10b981' if r.price_change >= 0 else '#fbbf24'}; font-size: 0.85rem; font-weight: 600;">
                    Change: {CURRENCY_SYMBOL}{int(r.price_change):,} ({r.price_change_pct}%)
                </div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Expected Sales Velocity</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #f1f5f9;">{r.expected_daily_demand:.1f} <span style="font-size: 1rem; color: #94a3b8;">units/day</span></div>
                <div style="color: #10b981; font-size: 0.85rem;">Status Quo: {r.status_quo_daily_demand:.1f} / day</div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Clearance Horizon</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #f1f5f9;">{r.projected_clearance_days:.0f} <span style="font-size: 1rem; color: #94a3b8;">days</span></div>
                <div style="color: #38bdf8; font-size: 0.85rem;">Successor in: {r.days_to_successor} days</div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Net Expected Profit</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #10b981;">{CURRENCY_SYMBOL}{int(r.expected_lifecycle_profit):,}</div>
                <div style="color: #10b981; font-size: 0.85rem; font-weight: 600;">
                    +{CURRENCY_SYMBOL}{int(r.profit_lift_amount):,} (+{r.profit_lift_pct}%) Lift
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Retailer Explanation Briefing
memo = ReasonGenerator.generate_retailer_memo(r)
st.markdown(
    f"""
    <div class="briefing-card">
        <h4 style="color: #38bdf8; margin-top: 0;">💡 Store Manager Action Briefing: {memo['headline']}</h4>
        <p style="color: #f1f5f9; font-size: 1rem; line-height: 1.5; margin-bottom: 0.5rem;">
            {memo['key_rationale']}
        </p>
        <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0;">
            <b>Offline Channel Advantage:</b> {memo['offline_advantage']}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# Visualizations: Demand & Profit Curves + Inventory Trajectory
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig_curves = render_demand_and_profit_curves(r)
    st.plotly_chart(fig_curves, use_container_width=True)

with col_chart2:
    fig_traj = render_inventory_trajectory_chart(r)
    st.plotly_chart(fig_traj, use_container_width=True)

# Financial Breakdown Table
st.markdown("---")
st.subheader("💰 Lifecycle Financial Statement Breakdown")

col_fin1, col_fin2 = st.columns(2)
with col_fin1:
    st.markdown("#### With AI Optimal Price")
    st.table(pd.DataFrame({
        "Metric": [
            "Recommended Selling Price",
            "Units Sold over Horizon",
            "Projected Leftover Units",
            "Gross Revenue",
            "Cost of Goods Sold (COGS)",
            "Carrying & Financing Costs",
            "Depreciation Loss (Leftover)",
            "Net Expected Total Profit"
        ],
        "Value": [
            f"₹{int(r.recommended_price):,}",
            f"{int(r.expected_sales_horizon)} units",
            f"{int(r.expected_leftover_inventory)} units",
            f"₹{int(r.expected_revenue):,}",
            f"₹{int(r.expected_sales_horizon * r.unit_cost):,}",
            f"-₹{int(r.holding_and_finance_cost):,}",
            f"-₹{int(r.depreciation_loss):,}",
            f"₹{int(r.expected_lifecycle_profit):,}"
        ]
    }))

with col_fin2:
    st.markdown("#### Status Quo Baseline (Current Price)")
    st.table(pd.DataFrame({
        "Metric": [
            "Current Selling Price",
            "Units Sold over Horizon",
            "Projected Leftover Units",
            "Gross Revenue",
            "Cost of Goods Sold (COGS)",
            "Carrying & Financing Costs",
            "Depreciation Loss (Leftover)",
            "Net Expected Total Profit"
        ],
        "Value": [
            f"₹{int(r.current_price):,}",
            f"{int(r.current_inventory - r.status_quo_leftover)} units",
            f"{int(r.status_quo_leftover)} units (Stranded!)",
            f"₹{int((r.current_inventory - r.status_quo_leftover) * r.current_price):,}",
            f"₹{int((r.current_inventory - r.status_quo_leftover) * r.unit_cost):,}",
            f"-₹{int(r.holding_and_finance_cost * 1.15):,}",
            f"-₹{int(r.status_quo_leftover * r.unit_cost * 0.30):,} (Heavy Penalty)",
            f"₹{int(r.status_quo_profit):,}"
        ]
    }))
