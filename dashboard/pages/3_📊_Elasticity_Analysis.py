"""
3_📊_Elasticity_Analysis.py — Price Elasticity Analysis
========================================================
Displays overall elasticity, category comparison, what-if calculator,
and log-log regression details.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")

from src.utils.config import *
from src.models.elasticity_estimator import ElasticityEstimator
from src.data.data_pipeline import DataPipeline
from src.data.feature_engineering import FeatureEngineer
from src.visualization.plots import plot_elasticity_comparison, COLORS

st.set_page_config(page_title="Elasticity Analysis", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .glass-card {
        background: rgba(26, 26, 46, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 24px;
        margin-bottom: 20px;
    }
    .gradient-divider {
        height: 2px;
        background: linear-gradient(90deg, #6C63FF, #FF6584, #00D4AA);
        border: none; margin: 24px 0;
    }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 12px; color: #6C63FF; border-bottom: 1px solid #233554; }
    td { padding: 12px; color: #FAFAFA; border-bottom: 1px solid #233554; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Price Elasticity Analysis")
st.markdown("*Understanding how sensitive demand is to price changes across product categories.*")
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Data Loading ─────────────────────────────────────────────
@st.cache_resource
def load_elasticity_model():
    model_path = MODELS_DIR / "elasticity_model.pkl"
    if not model_path.exists():
        return None
    return ElasticityEstimator.load(str(model_path))

@st.cache_data
def load_and_prep_data():
    data_path = RAW_DATA_DIR / "sales_data.csv"
    if not data_path.exists():
        return None
    df = pd.read_csv(data_path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    pipeline = DataPipeline()
    df_clean = pipeline.clean_data(df)
    engineer = FeatureEngineer()
    df_feat = engineer.create_features(df_clean)
    return df_feat

elasticity_model = load_elasticity_model()
data = load_and_prep_data()

if elasticity_model is None or data is None:
    st.error("⚠️ **Models or data not found.** Run `python main.py` first to train models.")
    st.stop()

# ── Overall Elasticity ───────────────────────────────────────
st.header("📉 Overall Price Elasticity")
overall_beta = elasticity_model.get_elasticity()

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Overall β Coefficient", f"{overall_beta:.3f}")
with col2:
    abs_beta = abs(overall_beta)
    if abs_beta > 1:
        st.success(f"**Elastic** (|β| = {abs_beta:.2f} > 1): A 1% price increase leads to a {abs_beta:.1f}% demand decrease. The market is price-sensitive.")
    elif abs_beta < 1:
        st.info(f"**Inelastic** (|β| = {abs_beta:.2f} < 1): Demand is relatively stable despite price changes.")
    else:
        st.warning("**Unit Elastic** (|β| = 1): Revenue stays constant regardless of price changes.")

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Category Comparison Chart ────────────────────────────────
st.header("📊 Elasticity by Category")

elasticities_dict = {}
if hasattr(elasticity_model, 'category_models') and elasticity_model.category_models:
    for cat in elasticity_model.category_models:
        try:
            elasticities_dict[cat] = elasticity_model.get_elasticity(category=cat)
        except Exception:
            pass

if elasticities_dict:
    fig_elast = plot_elasticity_comparison(elasticities_dict, "Price Elasticity by Category")
    st.plotly_chart(fig_elast, use_container_width=True)
else:
    st.info("Category-level elasticities not available. Run `python main.py` to fit per-category models.")

# ── Interpretation Guide ─────────────────────────────────────
st.subheader("📖 Elasticity Interpretation Guide")
st.markdown("""
<div class="glass-card">
    <table>
        <tr><th>Elasticity Value (|ε|)</th><th>Type</th><th>Meaning</th><th>Pricing Strategy</th></tr>
        <tr>
            <td style="color: #EF5350; font-weight: bold;">|ε| > 1</td>
            <td><strong>Elastic</strong></td>
            <td>Demand is very sensitive to price</td>
            <td>Lower price → more revenue (volume wins)</td>
        </tr>
        <tr>
            <td style="color: #FFB74D; font-weight: bold;">|ε| = 1</td>
            <td><strong>Unit Elastic</strong></td>
            <td>Proportional response</td>
            <td>Revenue stays constant with price changes</td>
        </tr>
        <tr>
            <td style="color: #4CAF50; font-weight: bold;">|ε| < 1</td>
            <td><strong>Inelastic</strong></td>
            <td>Demand barely changes with price</td>
            <td>Raise price → more revenue (margin wins)</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── What Happens If Price Changes? ───────────────────────────
st.header("🧮 What Happens If Price Changes?")

product_names = {pid: info['name'] for pid, info in PRODUCT_CATALOG.items()}
selected_product = st.selectbox("Select Product", options=list(product_names.keys()), format_func=lambda x: product_names[x])

price_change_pct = st.slider("Price Change (%)", -30, 30, 0, 1)

prod_info = PRODUCT_CATALOG[selected_product]
base_price = prod_info['base_price']
base_demand = prod_info['base_demand']
cost_price_val = prod_info['cost_price']
category = prod_info['category']

# Get category-specific beta, fallback to overall
try:
    beta = elasticity_model.get_elasticity(category=category)
except Exception:
    beta = overall_beta

if beta is None or pd.isna(beta):
    beta = overall_beta

pct_price_change = price_change_pct / 100.0
pct_demand_change = beta * pct_price_change
new_demand = max(0, base_demand * (1 + pct_demand_change))
new_price = base_price * (1 + pct_price_change)

old_profit = (base_price - cost_price_val) * base_demand
new_profit = (new_price - cost_price_val) * new_demand
profit_change = new_profit - old_profit

c1, c2, c3, c4 = st.columns(4)
c1.metric("Original Demand", f"{base_demand:,.0f} units/day")
c2.metric("New Demand", f"{new_demand:,.0f} units/day", f"{pct_demand_change*100:+.1f}%")
c3.metric("New Price", f"{CURRENCY}{new_price:,.0f}", f"{price_change_pct:+d}%")
c4.metric("Profit Impact", f"{CURRENCY}{new_profit:,.0f}", f"{CURRENCY}{profit_change:+,.0f}")

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Log-Log Regression Details ───────────────────────────────
st.header("📋 Log-Log Regression Details")
with st.expander("Show Full OLS Regression Summary"):
    try:
        summary = elasticity_model.get_summary()
        st.code(summary, language="text")
    except Exception:
        st.write("Summary not available. The model may need to be retrained.")

# ── Category-wise Deep Dive ──────────────────────────────────
st.header("🔍 Category-wise Deep Dive")
if hasattr(elasticity_model, 'category_models') and elasticity_model.category_models:
    for cat, cat_result in elasticity_model.category_models.items():
        with st.expander(f"📦 {cat}"):
            try:
                beta_val = cat_result.params.get('log_price', 0.0)
                r2_val = cat_result.rsquared
                pval = cat_result.pvalues.get('log_price', 1.0)

                m1, m2, m3 = st.columns(3)
                m1.metric("Elasticity (β)", f"{beta_val:.3f}")
                m2.metric("R² Score", f"{r2_val:.4f}")
                m3.metric("p-value", f"{pval:.4f}")

                if abs(beta_val) > 1:
                    st.info(f"**{cat}** is elastic — customers are price-sensitive. Consider competitive pricing.")
                else:
                    st.info(f"**{cat}** is inelastic — customers are less price-sensitive. Consider premium pricing.")

                st.code(cat_result.summary().as_text(), language="text")
            except Exception as e:
                st.write(f"Details not available: {e}")
else:
    st.info("Category models not available. Run `python main.py` to fit per-category models.")
