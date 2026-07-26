import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Setup project root and imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import *
from src.visualization.plots import *

st.set_page_config(
    page_title="Product Analysis | AI Smart Pricing Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme glassmorphism cards
st.markdown("""
<style>
    .metric-card {
        background-color: #1A1A2E;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .metric-title {
        color: #A0AEC0;
        font-size: 0.9rem;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #FFFFFF;
        font-size: 1.5rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_sales_data():
    data_path = RAW_DATA_DIR / "sales_data.csv"
    if not data_path.exists():
        return None
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    return df

st.title("📈 Product Analysis")

# Load data
df = load_sales_data()

if df is None:
    st.warning("⚠️ Sales data not found. Please ensure the data pipeline has run and generated 'sales_data.csv' in the data/raw directory.")
    st.stop()

# Sidebar Product Selector
st.sidebar.header("Product Selection")
product_options = {pid: p['name'] for pid, p in PRODUCT_CATALOG.items()}
selected_product_id = st.sidebar.selectbox(
    "Select Product",
    options=list(product_options.keys()),
    format_func=lambda x: product_options[x]
)

# Filter data for selected product
product_df = df[df['product_id'] == selected_product_id].copy()

if product_df.empty:
    st.warning(f"No sales data found for {product_options[selected_product_id]}.")
    st.stop()

# Product Info Card
prod_info = PRODUCT_CATALOG[selected_product_id]

st.markdown("### Product Profile")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Category", prod_info.get('category', 'N/A'))
with col2:
    st.metric("Base Price", f"{CURRENCY}{prod_info.get('base_price', 0):.2f}")
with col3:
    st.metric("Cost Price", f"{CURRENCY}{prod_info.get('cost_price', 0):.2f}")
with col4:
    st.metric("Competitor Price", f"{CURRENCY}{prod_info.get('competitor_base_price', 0):.2f}")
with col5:
    st.metric("Rating", f"{prod_info.get('rating_mean', 0):.1f} ⭐")

st.divider()

# Sales History & Competitor Analysis
col_main1, col_main2 = st.columns(2)

with col_main1:
    st.markdown("### Sales History")
    fig_sales = plot_sales_timeseries(df, selected_product_id, f"Sales History - {prod_info['name']}")
    st.plotly_chart(fig_sales, use_container_width=True)

with col_main2:
    st.markdown("### Competitor Price Analysis")
    fig_comp = plot_competitor_analysis(df, selected_product_id, f"Price vs Competitor - {prod_info['name']}")
    st.plotly_chart(fig_comp, use_container_width=True)

# Price vs Demand Scatter
st.markdown("### Price Elasticity & Demand Pattern")
fig_scatter = plot_price_vs_demand_scatter(df, selected_product_id, f"Price vs Demand - {prod_info['name']}")
st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# Temporal Patterns
st.markdown("### Temporal Patterns")
col_temp1, col_temp2 = st.columns(2)

with col_temp1:
    st.markdown("#### Day-of-Week Distribution")
    product_df['day_of_week'] = product_df['date'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    fig_dow = px.box(
        product_df, 
        x='day_of_week', 
        y='units_sold',
        category_orders={"day_of_week": day_order},
        color_discrete_sequence=[COLORS['primary']],
        template='plotly_dark'
    )
    fig_dow.update_layout(
        paper_bgcolor=COLORS['bg_dark'],
        plot_bgcolor=COLORS['bg_dark'],
        xaxis_title="Day of Week",
        yaxis_title="Units Sold",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig_dow, use_container_width=True)

with col_temp2:
    st.markdown("#### Seasonal Patterns")
    fig_seasonal = plot_seasonal_patterns(product_df, "Monthly Seasonal Patterns")
    st.plotly_chart(fig_seasonal, use_container_width=True)

st.divider()

# Festival Impact
st.markdown("### Festival Impact Analysis")
fig_festival = plot_festival_impact(product_df, "Impact of Festivals on Sales")
st.plotly_chart(fig_festival, use_container_width=True)

st.divider()

# Key Stats Summary
st.markdown("### Key Statistics Summary")
stat1, stat2, stat3, stat4 = st.columns(4)

avg_daily_sales = product_df['units_sold'].mean()
max_price = product_df['selling_price'].max()
min_price = product_df['selling_price'].min()
price_volatility = product_df['selling_price'].std()
best_day = product_df.groupby('day_of_week')['units_sold'].mean().idxmax()

with stat1:
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Avg Daily Sales</div>
            <div class="metric-value">{avg_daily_sales:.0f} units</div>
        </div>
    ''', unsafe_allow_html=True)

with stat2:
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Price Range</div>
            <div class="metric-value">{CURRENCY}{min_price:.0f} - {CURRENCY}{max_price:.0f}</div>
        </div>
    ''', unsafe_allow_html=True)

with stat3:
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Price Volatility (Std Dev)</div>
            <div class="metric-value">{CURRENCY}{price_volatility:.2f}</div>
        </div>
    ''', unsafe_allow_html=True)

with stat4:
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Best Selling Day</div>
            <div class="metric-value">{best_day}</div>
        </div>
    ''', unsafe_allow_html=True)
