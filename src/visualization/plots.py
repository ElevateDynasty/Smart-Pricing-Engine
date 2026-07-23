import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.utils.config import *

pio.templates.default = 'plotly_dark'

COLORS = {
    'primary': '#6C63FF',      # Purple
    'secondary': '#FF6584',    # Pink/coral
    'accent': '#00D4AA',       # Teal/green  
    'warning': '#FFB74D',      # Amber
    'success': '#4CAF50',      # Green
    'danger': '#EF5350',       # Red
    'bg_dark': '#0E1117',      # Dark background
    'bg_card': '#1A1A2E',      # Card background
    'text': '#FAFAFA',         # White text
    'text_muted': '#8892B0',   # Muted text
    'grid': '#233554',         # Grid lines
}

def _apply_layout(fig, title):
    fig.update_layout(
        title=title,
        template='plotly_dark',
        paper_bgcolor=COLORS['bg_dark'],
        plot_bgcolor=COLORS['bg_dark'],
        font=dict(family='Inter, sans-serif', color=COLORS['text']),
        hoverlabel=dict(bgcolor=COLORS['bg_card'], font_size=14, font_family='Inter, sans-serif')
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=COLORS['grid'])
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=COLORS['grid'])
    return fig

def plot_profit_curve(prices, profits, optimal_price, optimal_profit, current_price=None, title="Profit Curve"):
    """Interactive profit curve with optimal price marked.
    Show gradient fill under curve. Mark optimal with vertical dashed line and annotation.
    If current_price provided, mark it too for comparison."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=prices, y=profits,
        mode='lines',
        name='Profit',
        line=dict(color=COLORS['primary'], width=3),
        fill='tozeroy',
        fillcolor='rgba(108, 99, 255, 0.2)'
    ))
    
    fig.add_vline(x=optimal_price, line_dash="dash", line_color=COLORS['accent'], 
                  annotation_text="Optimal Price", annotation_position="top right")
                  
    if current_price is not None:
        fig.add_vline(x=current_price, line_dash="dash", line_color=COLORS['warning'], 
                      annotation_text="Current Price", annotation_position="top left")
                      
    fig.update_layout(xaxis_title="Price", yaxis_title="Profit")
    return _apply_layout(fig, title)

def plot_demand_curve(prices, demands, optimal_price=None, title="Demand Curve"):
    """Demand vs Price curve showing the inverse relationship."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=prices, y=demands,
        mode='lines',
        name='Demand',
        line=dict(color=COLORS['secondary'], width=3)
    ))
    
    if optimal_price is not None:
        fig.add_vline(x=optimal_price, line_dash="dash", line_color=COLORS['accent'], 
                      annotation_text="Optimal Price", annotation_position="top right")
                      
    fig.update_layout(xaxis_title="Price", yaxis_title="Predicted Demand (Units)")
    return _apply_layout(fig, title)

def plot_price_vs_demand_scatter(df, product_id=None, title="Price vs Demand Scatter"):
    """Scatter plot of historical selling_price vs units_sold.
    Color by product_category. Add trendline."""
    if product_id is not None:
        df = df[df['product_id'] == product_id]
        
    fig = px.scatter(
        df, x="selling_price", y="units_sold", 
        color="product_category" if "product_category" in df.columns else None,
        trendline="ols",
        color_discrete_sequence=[COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['warning']]
    )
    
    fig.update_layout(xaxis_title="Selling Price", yaxis_title="Units Sold")
    return _apply_layout(fig, title)

def plot_sales_timeseries(df, product_id=None, title="Sales and Price over Time"):
    """Time series of daily sales with price overlay on secondary y-axis.
    Use two y-axes: left=units_sold, right=selling_price."""
    from plotly.subplots import make_subplots
    
    if product_id is not None:
        df = df[df['product_id'] == product_id]
        
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['units_sold'],
        mode='lines', name='Units Sold',
        line=dict(color=COLORS['primary'])
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['selling_price'],
        mode='lines', name='Selling Price',
        line=dict(color=COLORS['secondary'], dash='dot')
    ), secondary_y=True)
    
    fig.update_layout(xaxis_title="Date")
    fig.update_yaxes(title_text="Units Sold", secondary_y=False)
    fig.update_yaxes(title_text="Selling Price", secondary_y=True)
    return _apply_layout(fig, title)

def plot_elasticity_comparison(elasticities_dict, title="Price Elasticity by Category"):
    """Horizontal bar chart comparing elasticity across categories.
    Color code: elastic (>1) in red/coral, inelastic (<1) in green."""
    categories = list(elasticities_dict.keys())
    values = list(elasticities_dict.values())
    
    colors = [COLORS['danger'] if abs(v) > 1 else COLORS['success'] for v in values]
    
    fig = go.Figure(go.Bar(
        x=values,
        y=categories,
        orientation='h',
        marker_color=colors
    ))
    
    fig.update_layout(xaxis_title="Elasticity", yaxis_title="Category")
    return _apply_layout(fig, title)

def plot_feature_importance(importance_df, top_n=15, title="Feature Importance"):
    """Horizontal bar chart of top N feature importances."""
    df_sorted = importance_df.sort_values(by="importance", ascending=True).tail(top_n)
    
    fig = go.Figure(go.Bar(
        x=df_sorted['importance'],
        y=df_sorted['feature'],
        orientation='h',
        marker_color=COLORS['primary']
    ))
    
    fig.update_layout(xaxis_title="Importance Score", yaxis_title="Feature")
    return _apply_layout(fig, title)

def plot_actual_vs_predicted(y_true, y_pred, title="Actual vs Predicted Demand"):
    """Scatter plot with perfect-prediction diagonal line. Show R²."""
    from sklearn.metrics import r2_score
    import numpy as np
    
    r2 = r2_score(y_true, y_pred)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=y_true, y=y_pred,
        mode='markers',
        marker=dict(color=COLORS['primary'], opacity=0.6, size=8),
        name=f"R² = {r2:.2f}"
    ))
    
    min_val = min(np.min(y_true), np.min(y_pred))
    max_val = max(np.max(y_true), np.max(y_pred))
    
    fig.add_trace(go.Scatter(
        x=[min_val, max_val], y=[min_val, max_val],
        mode='lines', name='Perfect Prediction',
        line=dict(color=COLORS['accent'], dash='dash')
    ))
    
    fig.update_layout(xaxis_title="Actual", yaxis_title="Predicted")
    return _apply_layout(fig, title)

def plot_festival_impact(df, title="Festival Impact on Sales"):
    """Bar chart comparing average sales during festivals vs normal days.
    Grouped by product_category."""
    if 'is_festival' not in df.columns or 'product_category' not in df.columns:
        return go.Figure()
        
    avg_sales = df.groupby(['product_category', 'is_festival'])['units_sold'].mean().reset_index()
    
    fig = px.bar(
        avg_sales, x="product_category", y="units_sold", color="is_festival",
        barmode="group",
        color_discrete_sequence=[COLORS['primary'], COLORS['secondary']]
    )
    
    fig.update_layout(xaxis_title="Category", yaxis_title="Average Units Sold")
    return _apply_layout(fig, title)

def plot_seasonal_patterns(df, title="Seasonal Patterns (Monthly)"):
    """Box plots of units_sold by month or season."""
    if 'date' in df.columns:
        df['month'] = pd.to_datetime(df['date']).dt.month_name()
    elif 'month' not in df.columns:
        return go.Figure()
        
    fig = px.box(
        df, x="month", y="units_sold",
        color_discrete_sequence=[COLORS['primary']]
    )
    
    fig.update_layout(xaxis_title="Month", yaxis_title="Units Sold")
    return _apply_layout(fig, title)

def plot_competitor_analysis(df, product_id, title="Competitor Pricing Analysis"):
    """Dual line chart: our price vs competitor price over time."""
    if product_id is not None:
        df = df[df['product_id'] == product_id]
        
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'] if 'date' in df.columns else df.index, 
        y=df['selling_price'],
        mode='lines', name='Our Price',
        line=dict(color=COLORS['primary'], width=3)
    ))
    
    if 'competitor_price' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'] if 'date' in df.columns else df.index, 
            y=df['competitor_price'],
            mode='lines', name='Competitor Price',
            line=dict(color=COLORS['warning'], dash='dash', width=2)
        ))
        
    fig.update_layout(xaxis_title="Date", yaxis_title="Price")
    return _apply_layout(fig, title)

def plot_scenario_comparison(scenarios_dict, title="Scenario Comparison"):
    """Grouped bar chart comparing profit across different scenarios."""
    scenarios = list(scenarios_dict.keys())
    profits = [s['daily_profit'] if isinstance(s, dict) and 'daily_profit' in s else 0 for s in scenarios_dict.values()]
    
    fig = go.Figure(go.Bar(
        x=scenarios, y=profits,
        marker_color=[COLORS['primary'], COLORS['secondary'], COLORS['accent']]
    ))
    
    fig.update_layout(xaxis_title="Scenario", yaxis_title="Daily Profit")
    return _apply_layout(fig, title)

def plot_optimization_result_card(result_dict):
    """Create a Plotly figure that looks like a dashboard card showing:
    - Optimal Price
    - Predicted Demand
    - Daily Profit
    - Monthly Profit
    Use go.Indicator gauges or number displays."""
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
        mode="number",
        value=result_dict.get('optimal_price', 0),
        title={"text": "Optimal Price"},
        number={'prefix': "$"},
        domain={'row': 0, 'column': 0}
    ))
    
    fig.add_trace(go.Indicator(
        mode="number",
        value=result_dict.get('predicted_demand', 0),
        title={"text": "Predicted Demand (Units)"},
        domain={'row': 0, 'column': 1}
    ))
    
    fig.add_trace(go.Indicator(
        mode="number",
        value=result_dict.get('daily_profit', 0),
        title={"text": "Daily Profit"},
        number={'prefix': "$"},
        domain={'row': 1, 'column': 0}
    ))
    
    fig.add_trace(go.Indicator(
        mode="number",
        value=result_dict.get('monthly_profit', 0),
        title={"text": "Monthly Profit"},
        number={'prefix': "$"},
        domain={'row': 1, 'column': 1}
    ))
    
    fig.update_layout(
        grid={'rows': 2, 'columns': 2, 'pattern': "independent"},
        template='plotly_dark',
        paper_bgcolor=COLORS['bg_card'],
        font=dict(family='Inter, sans-serif', color=COLORS['text'])
    )
    
    return fig
