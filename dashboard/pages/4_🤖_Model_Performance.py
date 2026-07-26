"""
4_🤖_Model_Performance.py — Model Performance Dashboard
========================================================
Displays model metrics, actual vs predicted, residuals, feature importance,
and training configuration.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")

from src.utils.config import *
from src.models.demand_forecaster import DemandForecaster
from src.models.model_evaluator import ModelEvaluator
from src.data.data_pipeline import DataPipeline
from src.data.feature_engineering import FeatureEngineer
from src.visualization.plots import plot_actual_vs_predicted, plot_feature_importance, COLORS

st.set_page_config(page_title="Model Performance", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

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
</style>
""", unsafe_allow_html=True)

st.title("🤖 Model Performance Dashboard")
st.markdown("*Evaluate the LightGBM demand forecaster's accuracy and understand which features drive predictions.*")
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Data & Model Loading ─────────────────────────────────────
@st.cache_resource
def load_demand_model():
    model_path = MODELS_DIR / "lgbm_demand_model.pkl"
    if not model_path.exists():
        return None
    return DemandForecaster.load(str(model_path))

@st.cache_data
def load_and_prep_data():
    """Load, clean, feature-engineer, and split data (same as main.py)."""
    data_path = RAW_DATA_DIR / "sales_data.csv"
    if not data_path.exists():
        return None, None, None
    df = pd.read_csv(data_path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])

    pipeline = DataPipeline()
    df_clean = pipeline.clean_data(df)

    engineer = FeatureEngineer()
    df_feat = engineer.create_features(df_clean)

    # Encode categoricals
    for col in ["product_category", "season"]:
        if col in df_feat.columns:
            df_feat[col] = df_feat[col].astype("category")

    train_df, val_df, test_df = pipeline.split_data(df_feat)
    return train_df, val_df, test_df

demand_model = load_demand_model()
split_result = load_and_prep_data()

if demand_model is None or split_result[0] is None:
    st.error("⚠️ **Model or data not found.** Run `python main.py` first to train the model.")
    st.stop()

train_df, val_df, test_df = split_result

# ── Prepare predictions ──────────────────────────────────────
feature_cols = [c for c in ALL_FEATURES if c in test_df.columns]
X_test = test_df[feature_cols]
y_true = test_df[TARGET_COLUMN].values  # TARGET_COLUMN = 'units_sold'
y_pred = demand_model.predict(X_test)

# ── Model Metrics ────────────────────────────────────────────
st.header("📊 Overall Model Metrics")

evaluator = ModelEvaluator()
# evaluate() returns keys: 'RMSE', 'MAE', 'MAPE (%)', 'R²'
metrics = evaluator.evaluate("LightGBM", y_true, y_pred)

c1, c2, c3, c4 = st.columns(4)
c1.metric("RMSE", f"{metrics['RMSE']:.2f}", help="Root Mean Squared Error — lower is better")
c2.metric("MAE", f"{metrics['MAE']:.2f}", help="Mean Absolute Error — lower is better")
c3.metric("MAPE", f"{metrics['MAPE (%)']:.1f}%", help="Mean Absolute Percentage Error — <15% is good")
c4.metric("R² Score", f"{metrics['R²']:.4f}", help="Coefficient of determination — closer to 1.0 is better")

# Interpretation
r2 = metrics['R²']
mape = metrics['MAPE (%)']
if r2 > 0.85:
    st.success(f"✅ **Excellent model fit** — R² = {r2:.3f} means the model explains {r2*100:.1f}% of demand variance.")
elif r2 > 0.7:
    st.info(f"👍 **Good model fit** — R² = {r2:.3f}. Model captures most demand patterns.")
else:
    st.warning(f"⚠️ **Moderate fit** — R² = {r2:.3f}. Consider tuning hyperparameters or adding features.")

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Actual vs Predicted ──────────────────────────────────────
st.header("🎯 Actual vs Predicted Demand")
fig_scatter = plot_actual_vs_predicted(y_true, y_pred, "Actual vs Predicted (Test Set)")
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Residual Analysis ────────────────────────────────────────
st.header("📉 Residual Analysis")
residuals = y_true - y_pred

col_r1, col_r2 = st.columns(2)
with col_r1:
    fig_hist = px.histogram(
        x=residuals,
        nbins=50,
        title="Residuals Distribution",
        labels={'x': 'Residual Error (Actual - Predicted)'},
        color_discrete_sequence=[COLORS['primary']]
    )
    fig_hist.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['bg_dark'],
        plot_bgcolor=COLORS['bg_dark'],
        font=dict(color=COLORS['text']),
        showlegend=False
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_r2:
    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(
        x=y_pred, y=residuals,
        mode='markers',
        marker=dict(color=COLORS['secondary'], opacity=0.5, size=6),
        name='Residuals'
    ))
    fig_res.add_hline(y=0, line_dash="dash", line_color=COLORS['accent'], line_width=2)
    fig_res.update_layout(
        title="Residuals vs Predicted",
        xaxis_title="Predicted Demand",
        yaxis_title="Residual Error",
        template='plotly_dark',
        paper_bgcolor=COLORS['bg_dark'],
        plot_bgcolor=COLORS['bg_dark'],
        font=dict(color=COLORS['text']),
    )
    fig_res.update_xaxes(showgrid=True, gridcolor=COLORS['grid'])
    fig_res.update_yaxes(showgrid=True, gridcolor=COLORS['grid'])
    st.plotly_chart(fig_res, use_container_width=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Feature Importance ───────────────────────────────────────
st.header("🔑 Feature Importance")
try:
    importance_df = demand_model.get_feature_importance()
    if not importance_df.empty:
        fig_imp = plot_feature_importance(importance_df, top_n=15, title="Top 15 Features Driving Demand Predictions")
        st.plotly_chart(fig_imp, use_container_width=True)

        # Top Features Interpretation
        st.subheader("📖 Top Features Interpretation")
        top_5 = importance_df.head(5)

        feature_explanations = {
            'selling_price': '💰 The product price — the most direct lever for demand. Higher price typically reduces demand.',
            'price_to_cost_ratio': '📊 Markup ratio — indicates how much margin is built into the price.',
            'price_vs_competitor': '🏷️ Relative pricing — how our price compares to competitors. Critical for price-sensitive products.',
            'competitor_price': '🔍 Competitor pricing — what similar products sell for. Drives customer comparison behavior.',
            'sales_rolling_7d_mean': '📈 7-day moving average — captures recent sales momentum and trends.',
            'sales_rolling_14d_mean': '📈 14-day moving average — medium-term demand pattern.',
            'sales_rolling_30d_mean': '📈 30-day moving average — monthly demand baseline.',
            'sales_lag_7d': '⏮️ Weekly lag — what sold last week at similar conditions.',
            'sales_lag_14d': '⏮️ Bi-weekly lag — captures fortnightly buying patterns.',
            'sales_lag_30d': '⏮️ Monthly lag — month-ago performance baseline.',
            'rating': '⭐ Product rating — higher ratings boost buyer confidence and demand.',
            'num_reviews': '💬 Review count — social proof drives purchase decisions.',
            'ad_spend': '📣 Advertising spend — higher ad spend increases product visibility.',
            'discount_pct': '🏷️ Discount percentage — larger discounts drive more volume.',
            'days_to_next_festival': '🎉 Festival proximity — demand rises as festivals approach.',
            'is_festival': '🎊 Festival flag — massive demand spike during festivals (Diwali, etc.).',
            'is_weekend': '📅 Weekend indicator — weekend shopping patterns differ from weekdays.',
            'day_of_week': '📅 Day of week — certain days see consistently higher demand.',
            'month': '📆 Month — seasonal patterns across the year.',
            'season': '🌤️ Season — monsoon, festival season, etc. affect buying behavior.',
            'price_rolling_7d_mean': '💰 7-day price trend — recent price movement direction.',
            'cost_price': '🏭 Cost price — baseline for pricing decisions.',
        }

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        for i, (_, row) in enumerate(top_5.iterrows(), 1):
            feat = row['feature']
            explanation = feature_explanations.get(feat, f'Feature used by the model for demand prediction.')
            st.markdown(f"**{i}. `{feat}`** — {explanation}")
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Feature importance unavailable: {e}")

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

# ── Training Configuration ───────────────────────────────────
st.header("⚙️ Model Training Configuration")

c_left, c_right = st.columns(2)
with c_left:
    with st.expander("🔧 LightGBM Hyperparameters"):
        st.json(LGBM_PARAMS)

with c_right:
    with st.expander("📋 Dataset Info"):
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | **Train set** | {len(train_df):,} rows |
        | **Validation set** | {len(val_df):,} rows |
        | **Test set** | {len(test_df):,} rows |
        | **Features** | {len(feature_cols)} |
        | **Target** | `{TARGET_COLUMN}` |
        """)
