"""
Page 5: Competitor Intelligence & Channel Price Monitoring
Tracks online vs offline pricing gaps, stockout alerts, and multi-channel positioning.
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
from dashboard.components.data_loader import load_models_and_pipeline, load_catalog_and_meta, compute_all_sku_optimizations
from dashboard.components.charts import render_competitor_comparison_chart

st.set_page_config(page_title="Competitor Monitor | AI Pricing Engine", page_icon="🌐", layout="wide")

css_file = Path(__file__).resolve().parent.parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🌐 Online vs Offline Competitor Intelligence")
st.caption("Monitors marketplace pricing (Amazon, Flipkart) vs offline organized retail (Croma, Vijay Sales) without falling into the blind discounting trap.")

_, _, optimizer = load_models_and_pipeline()
products_df, costs_df, competitors_df = load_catalog_and_meta()
results = compute_all_sku_optimizations(optimizer)

# Competitor Stockout Alert Banner
latest_date = competitors_df["date"].max()
latest_comp_obs = competitors_df[competitors_df["date"] == latest_date]
stockouts = latest_comp_obs[latest_comp_obs["availability"] == "Out of Stock"]

if len(stockouts) > 0:
    st.markdown(
        f"""
        <div class="ai-recommendation-box" style="border-color: rgba(16, 185, 129, 0.5); padding: 1.25rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="badge-action badge-increase">Stockout Opportunity Alert</span>
                <b style="color: #34d399;">Online Supply Crunch Detected</b>
            </div>
            <p style="color: #f1f5f9; font-size: 0.95rem; margin-top: 0.5rem; margin-bottom: 0;">
                Major marketplaces report <b>Out of Stock</b> on <b>{stockouts['product_id'].iloc[0]}</b> ({stockouts['competitor'].str.cat(sep=', ')}). 
                Offline buyers have immediate walk-in demand. Do not discount; protect or increase store price!
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Select SKU to inspect channel positioning
sku_names = [r.product_name for r in results]
chosen_sku_name = st.selectbox("Select Model to Compare Against Competitors:", options=sku_names, index=0)
chosen_res = next(r for r in results if r.product_name == chosen_sku_name)

# Extract latest competitor prices for this SKU
sku_comp = latest_comp_obs[latest_comp_obs["product_id"] == chosen_res.product_id]
comp_dict = dict(zip(sku_comp["competitor"], sku_comp["competitor_price"]))

col_cp1, col_cp2 = st.columns([1.3, 1])

with col_cp1:
    fig_comp = render_competitor_comparison_chart(
        product_name=chosen_sku_name,
        current_price=chosen_res.current_price,
        recommended_price=chosen_res.recommended_price,
        mrp=chosen_res.mrp,
        competitors_dict=comp_dict
    )
    st.plotly_chart(fig_comp, use_container_width=True)

with col_cp2:
    st.markdown("#### 💡 The Online-Offline Pricing Paradox")
    st.markdown(
        """
        <div class="briefing-card">
            <h5 style="color: #38bdf8; margin-top: 0;">Why Blindly Matching Online Prices Destroys Margin:</h5>
            <ul style="color: #cbd5e1; font-size: 0.9rem; padding-left: 1.2rem;">
                <li><b>Instant Gratification:</b> Offline buyers get their phone immediately—no 2-day delivery waiting or doorstep fraud risks.</li>
                <li><b>Device Migration & Setup:</b> Store staff transfers data, applies tempered glass, and activates SIM cards on the spot.</li>
                <li><b>Tactile Verification:</b> Customers physically test camera quality, weight, and in-hand feel before committing ₹70,000+.</li>
            </ul>
            <p style="color: #10b981; font-size: 0.9rem; margin-bottom: 0; font-weight: 600;">
                Conclusion: A 1.5% to 3% offline premium over Amazon is fully sustainable and profit-maximizing.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")
st.subheader("📊 Market Overview: Price Gaps across All Retail Channels")

comp_table = []
for r in results:
    sub_c = latest_comp_obs[latest_comp_obs["product_id"] == r.product_id]
    amz_p = sub_c[sub_c["competitor"] == "Amazon India"]["competitor_price"].values
    flp_p = sub_c[sub_c["competitor"] == "Flipkart"]["competitor_price"].values
    cro_p = sub_c[sub_c["competitor"] == "Croma"]["competitor_price"].values
    
    comp_table.append({
        "Product": r.product_name,
        "Store Price": f"₹{int(r.current_price):,}",
        "AI Rec": f"₹{int(r.recommended_price):,}",
        "Amazon India": f"₹{int(amz_p[0]):,}" if len(amz_p) else "N/A",
        "Flipkart": f"₹{int(flp_p[0]):,}" if len(flp_p) else "N/A",
        "Croma": f"₹{int(cro_p[0]):,}" if len(cro_p) else "N/A",
        "MRP": f"₹{int(r.mrp):,}",
        "Competitor Availability": "Out of Stock Alert" if r.product_id in stockouts["product_id"].values else "Normal"
    })

st.dataframe(pd.DataFrame(comp_table), use_container_width=True, hide_index=True)
