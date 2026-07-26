"""
app.py — AI Smart Pricing Engine: Streamlit Dashboard Home
==========================================================
Main entry point for the multi-page Streamlit dashboard.
Displays KPI overview, today's recommendations, and quick summary charts.

Launch:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np

from src.utils.config import *
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator
from src.models.model_evaluator import ModelEvaluator
from src.data.data_pipeline import DataPipeline
from src.data.feature_engineering import FeatureEngineer
from src.optimization.price_optimizer import PriceOptimizer
from src.visualization.plots import (
    plot_sales_timeseries, plot_festival_impact, COLORS
)

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
def load_css():
    css_path = Path(__file__).resolve().parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        .metric-card {
            background: rgba(26, 26, 46, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid rgba(108, 99, 255, 0.2);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(108, 99, 255, 0.15);
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #6C63FF, #00D4AA);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #8892B0;
            margin-bottom: 8px;
        }
        .gradient-divider {
            height: 2px;
            background: linear-gradient(90deg, #6C63FF, #FF6584, #00D4AA);
            border: none;
            margin: 24px 0;
        }
        </style>
    """, unsafe_allow_html=True)

load_css()

# ── Header ───────────────────────────────────────────────────
st.title(DASHBOARD_TITLE)
st.markdown("**AI-Powered Dynamic Pricing for Indian E-Commerce Sellers**")
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Data & Model Loading ─────────────────────────────────────
@st.cache_data
def load_sales_data():
    data_path = RAW_DATA_DIR / "sales_data.csv"
    if not data_path.exists():
        return None
    df = pd.read_csv(data_path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df

@st.cache_resource
def load_demand_model():
    model_path = MODELS_DIR / "lgbm_demand_model.pkl"
    if not model_path.exists():
        return None
    try:
        return DemandForecaster.load(str(model_path))
    except Exception:
        return None

@st.cache_data
def load_featured_data():
    """Load raw data, clean it, and engineer features (same as main.py)."""
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

df = load_sales_data()
demand_model = load_demand_model()

if df is None or demand_model is None:
    st.error("⚠️ **Data or Models not found.** Please run the training pipeline first.")
    st.info("""
    Open a terminal in the project folder and run:
    ```
    python main.py
    ```
    This generates synthetic data, trains the LightGBM model, fits the elasticity estimator,
    and saves everything to disk. Then refresh this page.
    """)
    st.stop()

# ── KPI Dashboard Row ────────────────────────────────────────
st.markdown("### 📊 System Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📦 Total Products</div>
            <div class="metric-value">{len(PRODUCT_CATALOG)}</div>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📋 Sales Records</div>
            <div class="metric-value">{len(df):,}</div>
        </div>
    """, unsafe_allow_html=True)
with col3:
    # Compute actual R² from test data
    df_feat = load_featured_data()
    if df_feat is not None:
        feature_cols = [c for c in ALL_FEATURES if c in df_feat.columns]
        for col in ["product_category", "season"]:
            if col in df_feat.columns:
                df_feat[col] = df_feat[col].astype("category")
        pipeline = DataPipeline()
        _, _, test_df = pipeline.split_data(df_feat)
        X_test = test_df[feature_cols]
        y_test = test_df[TARGET_COLUMN]
        y_pred = demand_model.predict(X_test)
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate("LightGBM", y_test.values, y_pred)
        r2_display = f"{metrics['R²']:.3f}"
    else:
        r2_display = "N/A"

    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🎯 Model R² Score</div>
            <div class="metric-value">{r2_display}</div>
        </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💰 Products Optimized</div>
            <div class="metric-value">{len(PRODUCT_CATALOG)}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Today's Recommendations Table ────────────────────────────
st.markdown("### 🚀 AI Pricing Recommendations")

@st.cache_data
def get_recommendations():
    """Run optimizer for each product (mirrors main.py logic)."""
    df_feat = load_featured_data()
    if df_feat is None:
        return pd.DataFrame()

    feature_cols = [c for c in ALL_FEATURES if c in df_feat.columns]
    for col in ["product_category", "season"]:
        if col in df_feat.columns:
            df_feat[col] = df_feat[col].astype("category")

    pipeline = DataPipeline()
    train_df, _, _ = pipeline.split_data(df_feat)

    recommendations = []
    for prod_id, prod_info in PRODUCT_CATALOG.items():
        cost = prod_info['cost_price']
        current_price = prod_info['base_price']
        competitor = prod_info['competitor_base_price']

        optimizer = PriceOptimizer(
            demand_model=demand_model,
            cost_price=cost,
            min_price=cost * 1.1,
            max_price=cost * 5.0,
        )

        # Get median features for this product
        prod_mask = train_df["product_id"] == prod_id if "product_id" in train_df.columns else pd.Series([True] * len(train_df))
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

        base_features["cost_price"] = cost
        base_features["competitor_price"] = competitor

        try:
            result = optimizer.optimize(base_features, competitor_price=competitor)
            comparison = optimizer.compare_with_current(current_price, base_features, competitor_price=competitor)

            profit_change_pct = comparison['improvement']['profit_change_pct']
            monthly_extra = comparison['improvement']['monthly_extra_profit']

            recommendations.append({
                "Product": prod_info['name'],
                f"Cost ({CURRENCY})": f"{cost:,.0f}",
                f"Current ({CURRENCY})": f"{current_price:,.0f}",
                f"AI Optimal ({CURRENCY})": f"{result['optimal_price']:,.0f}",
                "Demand (units/day)": f"{result['predicted_demand']:.1f}",
                f"Daily Profit ({CURRENCY})": f"{result['daily_profit']:,.0f}",
                f"Monthly Profit ({CURRENCY})": f"{result['monthly_profit']:,.0f}",
                "Profit Change": f"{profit_change_pct:+.1f}%",
            })
        except Exception:
            continue

    return pd.DataFrame(recommendations)

recs_df = get_recommendations()
if not recs_df.empty:
    st.dataframe(recs_df, use_container_width=True, hide_index=True)
else:
    st.info("Run `python main.py` to generate recommendations.")

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Quick Summary Charts ─────────────────────────────────────
st.markdown("### 📈 Quick Summary")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig_sales = plot_sales_timeseries(df, product_id=None, title="📈 Overall Sales & Pricing Trends")
    st.plotly_chart(fig_sales, use_container_width=True)

with col_chart2:
    fig_festival = plot_festival_impact(df, title="🎉 Festival Impact on Sales")
    st.plotly_chart(fig_festival, use_container_width=True)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎯 AI Smart Pricing Engine")
    st.markdown("---")
    st.markdown("""
    **Navigation:**
    - 📈 Product Analysis
    - 🎯 Price Optimizer
    - 📊 Elasticity Analysis
    - 🤖 Model Performance
    """)
    st.markdown("---")
    st.markdown("### ⚙️ Administration")
    if st.button("🔄 Retrain Models", use_container_width=True):
        st.info("Run `python main.py` in your terminal to retrain all models with fresh data.")
    st.markdown("---")
    st.caption("Built with Streamlit • Python • LightGBM")

# ── Footer ───────────────────────────────────────────────────
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: #8892B0; font-size: 0.8rem; padding: 16px;'>"
    "© 2026 AI Smart Pricing Engine — Technical Seminar Project"
    "</div>",
    unsafe_allow_html=True,
)
