"""
Page 6: Multi-Store Inventory Balancing & Phased Pricing Roadmaps
Optimizes stock distribution across physical retail branches and generates multi-week stepped price paths.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.config import CURRENCY_SYMBOL, STORES_MASTER
from dashboard.components.data_loader import load_models_and_pipeline, compute_all_sku_optimizations
from src.optimization.multi_store_balancer import MultiStoreBalancer
from src.optimization.price_path_generator import PricePathGenerator
from dashboard.components.charts import render_store_balancing_sankey

st.set_page_config(page_title="Multi-Store Balancing | AI Pricing Engine", page_icon="🔄", layout="wide")

css_file = Path(__file__).resolve().parent.parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🔄 Multi-Store Balancing & Phased Pricing Roadmaps")
st.caption("Synchronizes physical retail store allocations with phased multi-week price markdown trajectories.")

_, _, optimizer = load_models_and_pipeline()
results = compute_all_sku_optimizations(optimizer)

tab_transfer, tab_path = st.tabs(["🚚 Inter-Store Stock Balancing", "📈 Phased Dynamic Pricing Path"])

with tab_transfer:
    st.subheader("Store Allocation Disbalance Analysis")
    st.write(
        "Detects velocity mismatches where one branch is running out of stock while another is carrying excess inventory."
    )

    # Samsung Galaxy S26 Multi-Store Balancing Showcase (Spec Section 17)
    balancer = MultiStoreBalancer()
    
    # Store data for Galaxy S26 showcase
    sample_store_data = [
        {"store_id": "STORE_MUM_01", "store_name": "Mumbai Palladium Flagship", "city": "Mumbai", "current_inventory": 20, "daily_sales_velocity": 4.2},
        {"store_id": "STORE_DEL_02", "store_name": "Delhi NCR Select Citywalk", "city": "Delhi NCR", "current_inventory": 45, "daily_sales_velocity": 3.0},
        {"store_id": "STORE_BLR_03", "store_name": "Bengaluru Indiranagar Tech Hub", "city": "Bengaluru", "current_inventory": 18, "daily_sales_velocity": 3.8},
        {"store_id": "STORE_HYD_04", "store_name": "Hyderabad Banjara Hills", "city": "Hyderabad", "current_inventory": 30, "daily_sales_velocity": 1.5},
        {"store_id": "STORE_PUN_05", "store_name": "Pune FC Road Retail", "city": "Pune", "current_inventory": 160, "daily_sales_velocity": 1.1}
    ]

    analysis = balancer.analyze_sku_across_stores(
        product_id="SKU_GALAXY_S26_256",
        product_name="Samsung Galaxy S26 256GB",
        unit_cost=72000.0,
        mrp=89999.0,
        store_data=sample_store_data
    )

    # Visual transfers chart
    st.plotly_chart(render_store_balancing_sankey(analysis["recommended_transfers"]), use_container_width=True)

    # Detailed store status table
    st.markdown("#### Branch Stock & Days-of-Supply Status")
    st.dataframe(pd.DataFrame(analysis["stores_summary"]), use_container_width=True, hide_index=True)

    if analysis["recommended_transfers"]:
        st.markdown("#### ⚡ Recommended Physical Logistics Transfers")
        for t in analysis["recommended_transfers"]:
            st.markdown(
                f"""
                <div class="briefing-card" style="border-left-color: #10b981;">
                    <div style="font-weight: 700; color: #f8fafc; font-size: 1.05rem;">
                        Move {t['transfer_units']} Units: {t['from_store_name']} ➔ {t['to_store_name']}
                    </div>
                    <div style="color: #94a3b8; font-size: 0.9rem; margin-top: 0.25rem;">
                        Logistics Cost: {CURRENCY_SYMBOL}{int(t['transfer_cost']):,} | 
                        <b style="color: #34d399;">Net Margin Preserved: +{CURRENCY_SYMBOL}{int(t['estimated_margin_saved']):,}</b>
                    </div>
                    <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 0.25rem;">
                        Rationale: {t['reason']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

with tab_path:
    st.subheader("Phased Multi-Week Pricing Schedule (Spec Section 15)")
    st.write(
        "Rather than sticking to a single static price, the AI generates a stepped pricing path across the remaining lifecycle."
    )

    chosen_r = results[0] # iPhone 17 showcase
    path_gen = PricePathGenerator(optimizer)
    
    pricing_path = path_gen.generate_pricing_path(
        product_id=chosen_r.product_id,
        product_name=chosen_r.product_name,
        current_price=chosen_r.current_price,
        mrp=chosen_r.mrp,
        unit_cost=chosen_r.unit_cost,
        current_inventory=chosen_r.current_inventory,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        total_days=chosen_r.days_to_successor,
        num_phases=4
    )

    path_df = pd.DataFrame(pricing_path)
    
    # Display schedule table
    disp_path = path_df[[
        "phase_label",
        "starting_inventory",
        "recommended_price",
        "expected_daily_sales",
        "projected_units_sold",
        "ending_inventory",
        "cumulative_clearance_pct"
    ]].copy()

    disp_path.columns = [
        "Horizon Phase",
        "Starting Stock",
        "Recommended Selling Price (₹)",
        "Velocity (Units/Day)",
        "Units Cleared in Phase",
        "Ending Stock",
        "Cumulative Clearance (%)"
    ]

    disp_path["Recommended Selling Price (₹)"] = disp_path["Recommended Selling Price (₹)"].apply(lambda x: f"₹{int(x):,}")

    st.dataframe(disp_path, use_container_width=True, hide_index=True)
