"""
2_🎯_Price_Optimizer.py — The Star Feature
============================================
Interactive price optimization with profit curves, scenario analysis, and what-if calculator.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")

from src.utils.config import *
from src.models.demand_forecaster import DemandForecaster
from src.data.data_pipeline import DataPipeline
from src.data.feature_engineering import FeatureEngineer
from src.optimization.price_optimizer import PriceOptimizer
from src.optimization.scenario_engine import ScenarioEngine
from src.visualization.plots import (
    plot_profit_curve, plot_demand_curve, plot_scenario_comparison, COLORS
)

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(page_title="Price Optimizer", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    .kpi-card {
        background: rgba(26, 26, 46, 0.8);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #6C63FF;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FAFAFA;
    }
    .kpi-label { color: #8892B0; font-size: 0.85rem; }
    .comparison-bar {
        background: rgba(26, 26, 46, 0.8);
        padding: 16px 24px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(108, 99, 255, 0.3);
        margin: 16px 0;
    }
    .success-text { color: #4CAF50; font-weight: bold; }
    .danger-text { color: #EF5350; font-weight: bold; }
    .gradient-divider {
        height: 2px;
        background: linear-gradient(90deg, #6C63FF, #FF6584, #00D4AA);
        border: none; margin: 24px 0;
    }
    .stButton>button {
        background: linear-gradient(135deg, #EF5350, #D32F2F) !important;
        color: white !important; font-weight: 700 !important;
        border: none !important; border-radius: 8px !important;
        padding: 12px !important; font-size: 1.1rem !important;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #D32F2F, #B71C1C) !important;
        box-shadow: 0 4px 16px rgba(239, 83, 80, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 AI Price Optimizer")
st.markdown("Find the **profit-maximizing price** using machine learning demand prediction and mathematical optimization.")
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Data & Model Loading ─────────────────────────────────────
@st.cache_resource
def load_demand_model():
    model_path = MODELS_DIR / "lgbm_demand_model.pkl"
    if not model_path.exists():
        return None
    return DemandForecaster.load(str(model_path))

@st.cache_data
def load_featured_data():
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

def get_base_features(df_feat, product_id, feature_cols):
    """Extract median features for a product (same logic as main.py)."""
    for col in ["product_category", "season"]:
        if col in df_feat.columns:
            df_feat[col] = df_feat[col].astype("category")

    pipeline = DataPipeline()
    train_df, _, _ = pipeline.split_data(df_feat)

    prod_mask = train_df["product_id"] == product_id if "product_id" in train_df.columns else pd.Series([True] * len(train_df))
    prod_data = train_df[prod_mask]
    if len(prod_data) == 0:
        prod_data = train_df

    base_features = {}
    for col in feature_cols:
        if col in prod_data.columns:
            if prod_data[col].dtype.name == "category":
                mode_vals = prod_data[col].mode()
                base_features[col] = mode_vals.iloc[0] if len(mode_vals) > 0 else prod_data[col].iloc[0]
            else:
                base_features[col] = prod_data[col].median()
    return base_features

# ── Sidebar Controls ─────────────────────────────────────────
st.sidebar.header("⚙️ Optimization Settings")

product_names = {pid: info['name'] for pid, info in PRODUCT_CATALOG.items()}
selected_product = st.sidebar.selectbox(
    "Select Product",
    options=list(product_names.keys()),
    format_func=lambda x: product_names[x]
)

prod_info = PRODUCT_CATALOG[selected_product]

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Price Parameters")
cost_price = st.sidebar.number_input("Cost Price (₹)", min_value=1.0, value=float(prod_info['cost_price']), step=10.0)
current_price = st.sidebar.number_input("Current Price (₹)", min_value=1.0, value=float(prod_info['base_price']), step=10.0)
competitor_price = st.sidebar.number_input("Competitor Price (₹)", min_value=1.0, value=float(prod_info['competitor_base_price']), step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎭 Scenario Overrides")
is_festival = st.sidebar.checkbox("🎉 Festival Season", value=False)
is_weekend = st.sidebar.checkbox("📅 Weekend", value=False)

optimize_btn = st.sidebar.button("🔴 FIND OPTIMAL PRICE", use_container_width=True)

# ── Session State ────────────────────────────────────────────
if optimize_btn:
    st.session_state.optimized = True
    st.session_state.opt_product = selected_product
    st.session_state.opt_cost = cost_price
    st.session_state.opt_current = current_price
    st.session_state.opt_competitor = competitor_price
    st.session_state.opt_festival = is_festival
    st.session_state.opt_weekend = is_weekend

# ── Main Content ─────────────────────────────────────────────
model = load_demand_model()

if model is None:
    st.error("⚠️ **Demand model not found.** Run `python main.py` first to train the model.")
    st.stop()

if not st.session_state.get('optimized', False):
    st.info("👈 Configure settings in the sidebar and click **'FIND OPTIMAL PRICE'** to run the optimizer.")
    st.stop()

# Retrieve session state
prod_id = st.session_state.opt_product
cost = st.session_state.opt_cost
curr_price = st.session_state.opt_current
comp_price = st.session_state.opt_competitor
fest = st.session_state.opt_festival
wknd = st.session_state.opt_weekend

# Load and prepare features
df_feat = load_featured_data()
if df_feat is None:
    st.error("Data not found. Run `python main.py` first.")
    st.stop()

feature_cols = [c for c in ALL_FEATURES if c in df_feat.columns]
base_features = get_base_features(df_feat.copy(), prod_id, feature_cols)

# Apply scenario overrides
base_features['cost_price'] = cost
base_features['competitor_price'] = comp_price
if fest:
    base_features['is_festival'] = 1
if wknd:
    base_features['is_weekend'] = 1

# Setup optimizer
min_price = cost * 1.1
max_price = cost * 5.0
optimizer = PriceOptimizer(model, cost, min_price, max_price)

with st.spinner("🔍 Calculating optimal price..."):
    # Run optimization — returns: optimal_price, predicted_demand, daily_profit,
    # daily_revenue, monthly_profit, margin_pct
    opt_result = optimizer.optimize(base_features, competitor_price=comp_price)

    # Run comparison — returns: current{}, optimal{}, improvement{}
    comparison = optimizer.compare_with_current(curr_price, base_features, competitor_price=comp_price)

    # Generate curves — returns: prices, profits, demands, revenues, margins arrays
    curves = optimizer.generate_profit_curve(base_features, competitor_price=comp_price)

# ── Results Section ──────────────────────────────────────────
st.header("✨ Optimization Results")

# KPI Cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">🎯 Optimal Price</div>
        <div class="kpi-value">{CURRENCY}{opt_result['optimal_price']:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #00D4AA;">
        <div class="kpi-label">📦 Predicted Demand</div>
        <div class="kpi-value">{opt_result['predicted_demand']:.1f} units</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #4CAF50;">
        <div class="kpi-label">💰 Daily Profit</div>
        <div class="kpi-value">{CURRENCY}{opt_result['daily_profit']:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #FFB74D;">
        <div class="kpi-label">📊 Monthly Profit</div>
        <div class="kpi-value">{CURRENCY}{opt_result['monthly_profit']:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Comparison Bar
profit_change_pct = comparison['improvement']['profit_change_pct']
monthly_extra = comparison['improvement']['monthly_extra_profit']
color_class = "success-text" if profit_change_pct > 0 else "danger-text"
sign = "+" if profit_change_pct > 0 else ""

st.markdown(f"""
<div class="comparison-bar">
    <h4 style="color: #FAFAFA; margin-bottom: 8px;">vs Current Price ({CURRENCY}{curr_price:,.0f})</h4>
    <span class="{color_class}" style="font-size: 1.2rem;">
        {sign}{profit_change_pct:.1f}% profit improvement &nbsp;|&nbsp; {sign}{CURRENCY}{monthly_extra:,.0f} extra monthly profit
    </span>
</div>
""", unsafe_allow_html=True)

# Charts
st.subheader("📈 Price vs Profit & Demand")
col_left, col_right = st.columns(2)

with col_left:
    fig_profit = plot_profit_curve(
        curves['prices'], curves['profits'],
        opt_result['optimal_price'], opt_result['daily_profit'],
        current_price=curr_price,
        title="Profit Curve"
    )
    st.plotly_chart(fig_profit, use_container_width=True)

with col_right:
    fig_demand = plot_demand_curve(
        curves['prices'], curves['demands'],
        optimal_price=opt_result['optimal_price'],
        title="Demand Curve"
    )
    st.plotly_chart(fig_demand, use_container_width=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Scenario Analysis ────────────────────────────────────────
st.header("🎭 Scenario Analysis")

scenario_engine = ScenarioEngine(optimizer)

with st.spinner("Running scenarios..."):
    # Reset to neutral for fair comparison
    neutral_features = base_features.copy()
    neutral_features['is_festival'] = 0
    neutral_features['is_weekend'] = 0

    baseline = optimizer.optimize(neutral_features, competitor_price=comp_price)

    fest_result = scenario_engine.festival_scenario(neutral_features)
    wknd_result = scenario_engine.weekend_scenario(neutral_features)

    scenarios = {
        "Normal Day": baseline,
        "Festival": fest_result['festival_scenario'],
        "Weekend": wknd_result['weekend_scenario'],
    }

fig_scenario = plot_scenario_comparison(scenarios, "Scenario Performance Comparison")
st.plotly_chart(fig_scenario, use_container_width=True)

# Sensitivity Analysis
st.subheader("📐 Sensitivity Analysis")
sensitivity_df = scenario_engine.sensitivity_analysis(neutral_features, competitor_price=comp_price)
display_df = sensitivity_df.copy()
display_df['price'] = display_df['price'].apply(lambda x: f"{CURRENCY}{x:.0f}")
display_df['profit'] = display_df['profit'].apply(lambda x: f"{CURRENCY}{x:.0f}")
display_df['demand'] = display_df['demand'].apply(lambda x: f"{x:.1f}")
display_df['pct_from_optimal'] = display_df['pct_from_optimal'].apply(lambda x: f"{x:+.1f}%")
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── What-If Calculator ───────────────────────────────────────
st.header("🧮 What-If Calculator")
st.markdown("Explore how manual price adjustments affect demand and profit.")

price_change_pct = st.slider(
    "What if price changes by X%?",
    min_value=-30.0, max_value=30.0, value=0.0, step=1.0,
    format="%.0f%%"
)

opt_price = opt_result['optimal_price']
sim_price = opt_price * (1 + price_change_pct / 100)
sim_demand = model.predict_at_price(base_features, sim_price, cost, comp_price)
sim_profit = (sim_price - cost) * sim_demand

w1, w2, w3 = st.columns(3)
w1.metric("Simulated Price", f"{CURRENCY}{sim_price:,.0f}", f"{price_change_pct:+.0f}%")

demand_diff = sim_demand - opt_result['predicted_demand']
w2.metric("Simulated Demand", f"{sim_demand:.1f} units", f"{demand_diff:+.1f}")

profit_diff = sim_profit - opt_result['daily_profit']
w3.metric("Simulated Profit", f"{CURRENCY}{sim_profit:,.0f}", f"{CURRENCY}{profit_diff:+,.0f}")
