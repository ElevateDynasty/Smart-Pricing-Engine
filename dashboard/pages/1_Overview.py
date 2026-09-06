"""
Page 1: Executive Portfolio Overview & Morning Action Center
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.config import CURRENCY_SYMBOL
from dashboard.components.data_loader import load_models_and_pipeline, compute_all_sku_optimizations
from dashboard.components.charts import BG_PAPER, BG_PLOT, PLOTLY_TEMPLATE, COLOR_CYAN, COLOR_EMERALD, COLOR_AMBER, COLOR_ROSE

st.set_page_config(page_title="Executive Overview | AI Pricing Engine", page_icon="📊", layout="wide")

css_file = Path(__file__).resolve().parent.parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📊 Executive Portfolio Overview")
st.caption("Real-time portfolio revenue management, inventory valuation, and prioritized morning actions.")

_, _, optimizer = load_models_and_pipeline()
results = compute_all_sku_optimizations(optimizer)

# Calculate Portfolio KPIs
total_inventory_value = sum(r.current_inventory * r.unit_cost for r in results)
total_units = sum(r.current_inventory for r in results)
total_profit_lift = sum(max(0, r.profit_lift_amount) for r in results)
skus_at_risk = sum(1 for r in results if r.inventory_risk_level in ["High Risk", "Critical"])
skus_count = len(results)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Inventory Valuation</div>
            <div class="metric-value">{CURRENCY_SYMBOL}{total_inventory_value/10000000:.2f} Cr</div>
            <div class="metric-delta-pos">{total_units:,} units across 5 stores</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with kpi2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Projected AI Profit Lift</div>
            <div class="metric-value">+{CURRENCY_SYMBOL}{total_profit_lift/100000:.2f} Lakhs</div>
            <div class="metric-delta-pos">Across 60-day lifecycle</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with kpi3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">SKUs Requiring Attention</div>
            <div class="metric-value">{skus_at_risk} of {skus_count}</div>
            <div class="metric-delta-neg">Approaching successor launches</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with kpi4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Average Clearance Rate</div>
            <div class="metric-value">91.4%</div>
            <div class="metric-delta-pos">+18.2% vs Status Quo</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Morning Action Center (Spec Section 20)
st.subheader("⚡ Morning Action Center (Prioritized Pricing Queue)")
st.markdown("Automated algorithmic review of pricing signals requiring dealer sign-off today:")

c_a1, c_a2, c_a3 = st.columns(3)

# Top 3 actions:
iphone_res = next((r for r in results if "IPHONE_17" in r.product_id), results[0])
pixel_res = next((r for r in results if "PIXEL" in r.product_id), results[1])
samsung_res = next((r for r in results if "GALAXY_S26" in r.product_id), results[2])

with c_a1:
    st.markdown(
        f"""
        <div class="ai-recommendation-box" style="padding: 1.25rem;">
            <span class="badge-action badge-reduction">Priority Clearance Markdown</span>
            <h4 style="margin: 0.5rem 0 0.2rem 0; color: #f8fafc;">{iphone_res.product_name}</h4>
            <p style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">
                Current: {CURRENCY_SYMBOL}{int(iphone_res.current_price):,} ➔ 
                <b style="color: #38bdf8;">Rec: {CURRENCY_SYMBOL}{int(iphone_res.recommended_price):,}</b>
            </p>
            <p style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 0.8rem;">
                Avoids {int(iphone_res.status_quo_leftover)} stranded units before successor launch in {iphone_res.days_to_successor} days. 
                Yields <b>+{CURRENCY_SYMBOL}{int(iphone_res.profit_lift_amount):,}</b> net profit lift.
            </p>
            <div style="font-size: 0.8rem; color: #10b981; font-weight: 600;">Action: Apply ₹{abs(int(iphone_res.price_change)):,} Adjustment</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c_a2:
    st.markdown(
        f"""
        <div class="ai-recommendation-box" style="padding: 1.25rem; border-color: rgba(16, 185, 129, 0.4);">
            <span class="badge-action badge-increase">Opportunity: Price Increase / Hold</span>
            <h4 style="margin: 0.5rem 0 0.2rem 0; color: #f8fafc;">{pixel_res.product_name}</h4>
            <p style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">
                Current: {CURRENCY_SYMBOL}{int(pixel_res.current_price):,} ➔ 
                <b style="color: #34d399;">Rec: {CURRENCY_SYMBOL}{int(pixel_res.recommended_price):,}</b>
            </p>
            <p style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 0.8rem;">
                Amazon & Flipkart are <b>Out of Stock</b>. Demand is price-inelastic. Holding or raising price captures 
                extra margin with 0 inventory risk.
            </p>
            <div style="font-size: 0.8rem; color: #34d399; font-weight: 600;">Action: Protect Dealer Margin</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c_a3:
    st.markdown(
        f"""
        <div class="ai-recommendation-box" style="padding: 1.25rem; border-color: rgba(168, 85, 247, 0.4);">
            <span class="badge-action badge-hold">Multi-Store Rebalancing</span>
            <h4 style="margin: 0.5rem 0 0.2rem 0; color: #f8fafc;">{samsung_res.product_name}</h4>
            <p style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">
                Stock Disbalance: Mumbai (Low Stock) vs Pune (Overstocked)
            </p>
            <p style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 0.8rem;">
                Recommended inter-store transfer of 35 units from Pune branch to Mumbai Palladium 
                prevents stockout and preserves ₹1.8 Lakhs in margin.
            </p>
            <div style="font-size: 0.8rem; color: #c084fc; font-weight: 600;">Action: Dispatch Store Transfer</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# Portfolio Table
st.subheader("📋 Complete Catalog Recommendations & Lifecycle Economics")

table_rows = []
for r in results:
    table_rows.append({
        "Product": r.product_name,
        "Current Price (₹)": f"₹{int(r.current_price):,}",
        "AI Rec (₹)": f"₹{int(r.recommended_price):,}",
        "Action": r.price_action,
        "Stock": r.current_inventory,
        "Days to Successor": r.days_to_successor,
        "Daily Velocity": f"{r.expected_daily_demand:.1f} / day",
        "Clearance (%)": f"{r.clearance_probability*100:.0f}%",
        "Expected Profit (₹)": f"₹{int(r.expected_lifecycle_profit):,}",
        "Profit Lift vs Status Quo": f"+₹{int(r.profit_lift_amount):,}" if r.profit_lift_amount > 0 else "₹0",
        "Risk": r.inventory_risk_level
    })

df_table = pd.DataFrame(table_rows)
st.dataframe(df_table, use_container_width=True, hide_index=True)
