"""
AI-Powered Dynamic Pricing and Inventory Optimization for Electronics Retail
Main Streamlit Application
"""
import streamlit as st
from pathlib import Path
import sys

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.config import PROJECT_NAME, CURRENCY_SYMBOL
from dashboard.components.data_loader import load_models_and_pipeline

st.set_page_config(
    page_title="AI Dynamic Pricing & Inventory Optimization",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Glassmorphic CSS
css_file = Path(__file__).resolve().parent / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚡ AI Retail Pricing Engine")
    st.markdown("**Vertical:** Indian Offline Electronics")
    st.markdown("**Target:** Multi-Brand Smartphone Retail")
    st.markdown("---")
    st.markdown("#### 🎯 Navigation")
    st.info(
        """
        Use the sidebar pages to explore:
        - **1 Overview:** Portfolio KPIs & Today's Actions
        - **2 SKU Pricing:** Deep-Dive & Recommendation Card
        - **3 Price Simulator:** Interactive What-If Sandbox
        - **4 Inventory Risk:** Aging Stock & Successor Countdown
        - **5 Competitor Monitor:** Online vs Offline Price Gap
        - **6 Store Balancing:** Inter-Store Stock Transfers
        """
    )
    st.markdown("---")
    st.caption("Engine Version: v1.0.0 | ML Engine: LightGBM")

# Header Hero
st.markdown(
    """
    <div style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(99, 102, 241, 0.08)); 
                border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 16px; padding: 2rem; margin-bottom: 2rem;">
        <span class="badge-action badge-hold">Indian Consumer Electronics Retail Edition</span>
        <h1 style="color: #f8fafc; margin-top: 0.5rem; font-size: 2.3rem; font-weight: 800;">
            AI-Powered Dynamic Pricing & Lifecycle Inventory Optimization
        </h1>
        <p style="color: #94a3b8; font-size: 1.1rem; max-width: 900px; margin-bottom: 0;">
            Solves the fundamental retail challenge: <i>Given current inventory, acquisition cost, competitor signals, 
            sales velocity, product lifecycle, and future successor launches, what price maximizes total expected profit 
            while avoiding stranded inventory?</i>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# System Health & Models
forecaster, elasticity_est, optimizer = load_models_and_pipeline()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-label">Target Market</div>
            <div class="metric-value">India Retail</div>
            <div class="metric-delta-pos">Smartphones & Laptops</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-label">Legal Metrology</div>
            <div class="metric-value">MRP Enforced</div>
            <div class="metric-delta-pos">100% Legal Compliance</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col3:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-label">ML Model Accuracy</div>
            <div class="metric-value">R² 0.932</div>
            <div class="metric-delta-pos">MAE: 0.94 units/day</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col4:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-label">Stores Tracked</div>
            <div class="metric-value">5 Flagships</div>
            <div class="metric-delta-pos">Mumbai, Delhi, BLR, HYD, PUN</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Three Core Differentiators
col_d1, col_d2, col_d3 = st.columns(3)

with col_d1:
    st.markdown(
        """
        <div class="briefing-card">
            <h4 style="color: #38bdf8; margin-bottom: 0.4rem;">1. Lifecycle Profit Optimization</h4>
            <p style="color: #cbd5e1; font-size: 0.95rem;">
                Does not blindly optimize today's unit margin in isolation. Evaluates carrying cost, 
                depreciation loss post-successor launch, and total clearance probability over 60–180 days.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_d2:
    st.markdown(
        """
        <div class="briefing-card" style="border-left-color: #10b981;">
            <h4 style="color: #34d399; margin-bottom: 0.4rem;">2. Intelligent Non-Discounting</h4>
            <p style="color: #cbd5e1; font-size: 0.95rem;">
                AI concludes <b>"Do Not Discount"</b> or <b>"Increase Price"</b> when competitor stockouts occur 
                or demand is inelastic. Competitor price is an informational signal, not an automatic price-cut target.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_d3:
    st.markdown(
        """
        <div class="briefing-card" style="border-left-color: #a855f7;">
            <h4 style="color: #c084fc; margin-bottom: 0.4rem;">3. Multi-Store Rebalancing</h4>
            <p style="color: #cbd5e1; font-size: 0.95rem;">
                Pricing is combined with physical inventory allocation. Transfers surplus units from slow-moving stores 
                to high-velocity stores when margin gain exceeds logistics transfer costs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")
st.markdown("### 🚀 Jump Directly into Specific Modules")
c_p1, c_p2, c_p3 = st.columns(3)
with c_p1:
    st.markdown("#### 📊 [1. Executive Overview](./Overview)")
    st.write("Review entire portfolio inventory valuation, morning pricing queue, and profit lift.")
    st.markdown("#### 🔍 [2. SKU Pricing Deep-Dive](./SKU_Pricing)")
    st.write("Inspect individual smartphone models including the flagship iPhone 17 800-unit clearance showcase.")

with c_p2:
    st.markdown("#### 🎛️ [3. Price Simulator Sandbox](./Price_Simulator)")
    st.write("Interact with dynamic sliders to test any custom price point and observe real-time profit curves.")
    st.markdown("#### ⚠️ [4. Inventory Risk Radar](./Inventory_Risk)")
    st.write("Identify aging stock, calculate capital at risk, and track successor launch deadlines.")

with c_p3:
    st.markdown("#### 🌐 [5. Competitor Intelligence](./Competitor_Monitor)")
    st.write("Track price gaps against Amazon and Flipkart, and exploit online stockout opportunities.")
    st.markdown("#### 🔄 [6. Multi-Store Balancing](./Multi_Store_Balancing)")
    st.write("View inter-store stock transfers and phased multi-week dynamic pricing roadmaps.")
