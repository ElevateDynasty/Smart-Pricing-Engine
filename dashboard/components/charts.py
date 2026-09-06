"""
Interactive Plotly Visualizations for Retail AI Dashboard
Provides sleek, dark-themed charts for demand elasticity, lifecycle inventory trajectories,
competitor price positioning, and store balancing.
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from src.optimization.lifecycle_optimizer import OptimizationResult

# Dark theme palette
PLOTLY_TEMPLATE = "plotly_dark"
COLOR_CYAN = "#38bdf8"
COLOR_EMERALD = "#10b981"
COLOR_ROSE = "#f43f5e"
COLOR_AMBER = "#f59e0b"
COLOR_PURPLE = "#a855f7"
BG_PAPER = "#0b0f19"
BG_PLOT = "#131b2e"

def render_demand_and_profit_curves(result: OptimizationResult) -> go.Figure:
    """
    Creates dual-axis chart:
    - Left Y-axis: Predicted Daily Demand Curve (Emerald)
    - Right Y-axis: Expected Total Lifecycle Profit (Cyan)
    - Vertical lines for Current Price vs Recommended Price
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    prices = result.feasible_prices
    demands = result.demand_curve
    profits = [p / 100000.0 for p in result.profit_curve] # in Lakhs ₹

    # Demand Curve
    fig.add_trace(
        go.Scatter(
            x=prices,
            y=demands,
            name="Daily Demand (Units/Day)",
            line=dict(color=COLOR_EMERALD, width=3),
            mode="lines"
        ),
        secondary_y=False
    )

    # Lifecycle Profit Curve
    fig.add_trace(
        go.Scatter(
            x=prices,
            y=profits,
            name="Expected Lifecycle Profit (₹ Lakhs)",
            line=dict(color=COLOR_CYAN, width=3.5),
            mode="lines"
        ),
        secondary_y=True
    )

    # Marker for Recommended Price
    rec_profit_lakhs = result.expected_lifecycle_profit / 100000.0
    fig.add_trace(
        go.Scatter(
            x=[result.recommended_price],
            y=[rec_profit_lakhs],
            mode="markers+text",
            name="AI Optimal Price",
            text=[f"Optimal: ₹{int(result.recommended_price):,}"],
            textposition="top center",
            marker=dict(color=COLOR_CYAN, size=14, symbol="star", line=dict(color="#ffffff", width=2))
        ),
        secondary_y=True
    )

    # Marker for Current Price
    sq_profit_lakhs = result.status_quo_profit / 100000.0
    fig.add_trace(
        go.Scatter(
            x=[result.current_price],
            y=[sq_profit_lakhs],
            mode="markers+text",
            name="Current Price",
            text=[f"Current: ₹{int(result.current_price):,}"],
            textposition="bottom center",
            marker=dict(color=COLOR_AMBER, size=11, symbol="circle")
        ),
        secondary_y=True
    )

    fig.update_layout(
        title=dict(text="<b>Demand Curve vs Lifecycle Profit Tradeoff</b>", font=dict(size=16)),
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    fig.update_xaxes(title_text="Selling Price (₹)", tickprefix="₹", gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(title_text="Predicted Daily Units Sold", secondary_y=False, gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(title_text="Expected Profit (₹ Lakhs)", secondary_y=True)

    return fig

def render_inventory_trajectory_chart(result: OptimizationResult) -> go.Figure:
    """
    Simulates and plots day-by-day inventory drawdown over the horizon:
    Status Quo vs AI Recommended Pricing.
    """
    horizon = result.days_to_successor
    days = np.arange(0, horizon + 1)
    
    # Status Quo Trajectory
    sq_inv = np.maximum(0, result.current_inventory - (result.status_quo_daily_demand * days))
    
    # AI Recommended Trajectory
    ai_inv = np.maximum(0, result.current_inventory - (result.expected_daily_demand * days))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=days,
        y=sq_inv,
        mode="lines",
        name=f"Status Quo @ ₹{int(result.current_price):,} (Leaves {int(result.status_quo_leftover)} Leftover)",
        line=dict(color=COLOR_ROSE, width=2.5, dash="dash"),
        fill="tozeroy",
        fillcolor="rgba(244, 63, 94, 0.08)"
    ))

    fig.add_trace(go.Scatter(
        x=days,
        y=ai_inv,
        mode="lines",
        name=f"AI Recommended @ ₹{int(result.recommended_price):,} (Clears {result.clearance_probability*100:.0f}%)",
        line=dict(color=COLOR_EMERALD, width=3),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.12)"
    ))

    # Add vertical line for successor deadline
    fig.add_vline(
        x=horizon,
        line_dash="dot",
        line_color=COLOR_AMBER,
        annotation_text=f"Successor Launch ({horizon}d)",
        annotation_position="top right"
    )

    fig.update_layout(
        title=dict(text="<b>60-Day Inventory Drawdown Trajectory</b>", font=dict(size=16)),
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        hovermode="x",
        xaxis=dict(title="Days from Today", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Remaining Inventory (Units)", gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig

def render_competitor_comparison_chart(
    product_name: str,
    current_price: float,
    recommended_price: float,
    mrp: float,
    competitors_dict: Dict[str, float]
) -> go.Figure:
    """Horizontal bar chart comparing channel pricing against legal MRP ceiling."""
    labels = ["Legal Ceiling (MRP)", "Your Current Price", "AI Recommendation"] + list(competitors_dict.keys())
    values = [mrp, current_price, recommended_price] + list(competitors_dict.values())
    
    colors = [
        "rgba(255,255,255,0.3)",
        COLOR_AMBER,
        COLOR_CYAN
    ] + [COLOR_PURPLE if "Amazon" in k or "Flipkart" in k else "rgba(148, 163, 184, 0.7)" for k in competitors_dict.keys()]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=colors),
        text=[f"₹{int(v):,}" for v in values],
        textposition="auto"
    ))

    fig.update_layout(
        title=dict(text=f"<b>Channel Price Positioning: {product_name}</b>", font=dict(size=15)),
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        xaxis=dict(title="Price (₹)", tickprefix="₹", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig

def render_risk_quadrant_chart(portfolio_df: pd.DataFrame) -> go.Figure:
    """
    Scatter chart:
    X: Days to Successor
    Y: Capital at Risk (₹ Lakhs)
    Color: Risk Level
    """
    df = portfolio_df.copy()
    df["capital_lakhs"] = (df["current_inventory"] * df["unit_cost"]) / 100000.0

    color_map = {
        "High Risk": COLOR_ROSE,
        "Medium Risk": COLOR_AMBER,
        "Low Risk": COLOR_EMERALD
    }

    fig = px.scatter(
        df,
        x="days_to_successor",
        y="capital_lakhs",
        size="current_inventory",
        color="inventory_risk_level",
        hover_name="product_name",
        hover_data={"current_price": ":,.0f", "current_inventory": True, "capital_lakhs": ":.1f"},
        color_discrete_map=color_map,
        labels={
            "days_to_successor": "Days Remaining Until Successor Model Launch",
            "capital_lakhs": "Capital at Risk (₹ Lakhs)",
            "inventory_risk_level": "Risk Level"
        }
    )

    fig.update_layout(
        title=dict(text="<b>Portfolio Inventory Risk Matrix</b>", font=dict(size=16)),
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        xaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0.06)"), # shorter horizon on right
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig

def render_store_balancing_sankey(transfers_list: List[Dict[str, Any]]) -> go.Figure:
    """Bar chart visual of inter-store transfer volumes and margin saved."""
    if not transfers_list:
        fig = go.Figure()
        fig.add_annotation(text="All store inventories are currently balanced!", showarrow=False, font=dict(size=16, color=COLOR_EMERALD))
        fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT)
        return fig

    df = pd.DataFrame(transfers_list)
    labels = [f"{r['from_store_name']} ➔ {r['to_store_name']}" for _, r in df.iterrows()]

    fig = go.Figure(data=[
        go.Bar(name="Units Transferred", x=labels, y=df["transfer_units"], marker_color=COLOR_CYAN, yaxis="y"),
        go.Bar(name="Net Margin Saved (₹)", x=labels, y=df["estimated_margin_saved"], marker_color=COLOR_EMERALD, yaxis="y2")
    ])

    fig.update_layout(
        title=dict(text="<b>Recommended Store Transfers & Net Economic Benefit</b>", font=dict(size=15)),
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        yaxis=dict(title="Units Transferred", gridcolor="rgba(255,255,255,0.06)"),
        yaxis2=dict(title="Margin Saved (₹)", overlaying="y", side="right", tickprefix="₹"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group",
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig
