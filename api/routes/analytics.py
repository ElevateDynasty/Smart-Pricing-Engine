from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel
from datetime import datetime

from src.config import SYNTHETIC_DATA_DIR, RAW_DATA_DIR
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator
from src.optimization.lifecycle_optimizer import LifecycleOptimizer
from src.optimization.multi_store_balancer import MultiStoreBalancer
from src.explainability.reason_generator import ReasonGenerator
from src.data.data_pipeline import DataPipeline
from src.data.kaggle_pipeline import KaggleDemandAdapter, KAGGLE_RAW_CSV

router = APIRouter()

# Global instances cache
_models_cache: Dict[str, Any] = {}
# Per-source caches: {"synthetic": [...], "kaggle": [...]}
_optimizations_cache: Dict[str, List[Dict[str, Any]]] = {}
_summary_cache: Dict[str, Dict[str, Any]] = {}
_active_events: List[Dict[str, Any]] = []

VALID_MODEL_SOURCES = ("synthetic", "kaggle")

def get_models():
    if "forecaster" not in _models_cache:
        forecaster = DemandForecaster(model_type="lightgbm")
        try:
            forecaster.load()
        except Exception:
            dp = DataPipeline()
            df = dp.build_unified_dataset()
            forecaster.fit(df)
            
        elasticity_est = ElasticityEstimator()
        try:
            dp = DataPipeline()
            df = dp.build_unified_dataset()
            elasticity_est.fit(df)
        except Exception:
            pass
            
        optimizer = LifecycleOptimizer(forecaster)
        _models_cache["forecaster"] = forecaster
        _models_cache["elasticity_est"] = elasticity_est
        _models_cache["optimizer"] = optimizer
        
    return _models_cache["forecaster"], _models_cache["elasticity_est"], _models_cache["optimizer"]

def get_kaggle_engine():
    """Lazily load the real-data Kaggle model and its optimizer."""
    if "kaggle_adapter" not in _models_cache:
        adapter = KaggleDemandAdapter()
        optimizer = LifecycleOptimizer(adapter)
        _models_cache["kaggle_adapter"] = adapter
        _models_cache["kaggle_optimizer"] = optimizer
    return _models_cache["kaggle_adapter"], _models_cache["kaggle_optimizer"]

def get_catalog_and_meta():
    products_df = pd.read_csv(SYNTHETIC_DATA_DIR / "products.csv")
    costs_df = pd.read_csv(SYNTHETIC_DATA_DIR / "costs.csv")
    competitors_df = pd.read_csv(SYNTHETIC_DATA_DIR / "competitors.csv")
    return products_df, costs_df, competitors_df

def compute_optimizations(force: bool = False, model_source: str = "synthetic") -> List[Dict[str, Any]]:
    global _optimizations_cache, _summary_cache
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"

    if model_source == "kaggle":
        return compute_kaggle_optimizations(force)

    if not force and "synthetic" in _optimizations_cache:
        return _optimizations_cache["synthetic"]

    forecaster, elasticity_est, optimizer = get_models()
    products_df, costs_df, competitors_df = get_catalog_and_meta()
    
    latest_date = competitors_df["date"].max()
    latest_comp = competitors_df[competitors_df["date"] == latest_date].groupby("product_id").agg(
        competitor_avg_price=("competitor_price", "mean"),
        competitor_min_price=("competitor_price", "min"),
        competitor_stockouts=("availability", lambda s: (s == "Out of Stock").sum())
    ).reset_index()

    merged = products_df.merge(costs_df, on="product_id", how="left")
    merged = merged.merge(latest_comp, on="product_id", how="left")

    results: List[Dict[str, Any]] = []
    total_inv_units = 0
    total_inv_value = 0.0
    total_status_quo_profit = 0.0
    total_opt_profit = 0.0
    total_profit_lift = 0.0
    action_counts = {"Increase Price": 0, "Hold Price": 0, "Slight Reduction": 0, "Clearance Markdown": 0}
    risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}

    for _, row in merged.iterrows():
        pid = row["product_id"]
        if pid == "SKU_IPHONE_17_256":
            curr_inv, curr_price = 800, 79999.0
        elif pid == "SKU_IPHONE_16_128":
            curr_inv, curr_price = 320, 62999.0
        elif pid == "SKU_PIXEL_10_PRO":
            curr_inv, curr_price = 95, 104999.0
        else:
            curr_inv = 220
            curr_price = float(round(row["competitor_avg_price"] * 1.015, -2))

        stockout_flag = 1 if row["competitor_stockouts"] > 0 else 0
        product_title = f"{row['brand']} {row['model']} ({row['variant']})"
        days_to_succ = int(row["days_to_successor"])

        res = optimizer.optimize_sku(
            product_id=pid,
            product_name=product_title,
            current_price=curr_price,
            mrp=float(row["mrp"]),
            unit_cost=float(row["unit_cost"]),
            current_inventory=curr_inv,
            competitor_avg_price=float(row["competitor_avg_price"]),
            competitor_min_price=float(row["competitor_min_price"]),
            days_to_successor=days_to_succ,
            competitor_stockout_flag=stockout_flag
        )
        
        # Retailer explanation memo
        memo = ReasonGenerator.generate_retailer_memo(res)

        # XAI: native TreeSHAP explanation of the demand model at the recommended price
        xai = forecaster.explain_point(
            selling_price=float(res.recommended_price),
            mrp=float(row["mrp"]),
            competitor_avg_price=float(row["competitor_avg_price"]),
            competitor_min_price=float(row["competitor_min_price"]),
            unit_cost=float(row["unit_cost"]),
            opening_inventory=curr_inv,
            days_to_successor=days_to_succ
        )

        # Elasticity: model-derived (primary — always consistent with the demand
        # model that drives the optimizer), econometric OLS as fallback diagnostic.
        el_model = ElasticityEstimator.estimate_from_model(
            forecaster, curr_price,
            float(row["competitor_avg_price"]),
            float(row["competitor_min_price"]),
            float(row["mrp"]), float(row["unit_cost"]),
            curr_inv, days_to_succ
        )
        elasticity_val = el_model.get("elasticity")
        elasticity_regime = el_model.get("regime", "Unknown")
        elasticity_method = el_model.get("method", "")
        if elasticity_val is None:
            el_info = elasticity_est.get_elasticity(pid) if hasattr(elasticity_est, "get_elasticity") else {}
            elasticity_val = el_info.get("elasticity") if isinstance(el_info, dict) else None
            elasticity_regime = el_info.get("regime", "Unknown") if isinstance(el_info, dict) else "Unknown"
            elasticity_method = el_info.get("method", "econometric log-log OLS") if isinstance(el_info, dict) else "econometric log-log OLS"

        # Check if there is an active tech announcement for this product
        active_event_for_sku = next((e for e in _active_events if e.get("product_id") == pid), None)

        # Update totals
        total_inv_units += curr_inv
        total_inv_value += curr_inv * curr_price
        total_status_quo_profit += res.status_quo_profit
        total_opt_profit += res.expected_lifecycle_profit
        total_profit_lift += res.profit_lift_amount
        action_counts[res.price_action] = action_counts.get(res.price_action, 0) + 1
        risk_counts[res.inventory_risk_level] = risk_counts.get(res.inventory_risk_level, 0) + 1

        # Build comprehensive SKU payload
        results.append({
            "product_id": res.product_id,
            "product_name": res.product_name,
            "brand": str(row.get("brand", "")),
            "model": str(row.get("model", "")),
            "successor_model": str(row.get("successor_model", "")),
            "category": str(row.get("category", "Smartphones")),
            "current_price": float(curr_price),
            "recommended_price": float(res.recommended_price),
            "optimal_price": float(res.recommended_price),  # Compatibility alias
            "price_action": res.price_action,
            "price_change": float(res.price_change),
            "price_change_pct": float(res.price_change_pct),
            "mrp": float(row["mrp"]),
            "unit_cost": float(row["unit_cost"]),
            "current_inventory": int(curr_inv),
            "days_to_successor": days_to_succ,
            "expected_daily_demand": round(float(res.expected_daily_demand), 2),
            "expected_sales_horizon": round(float(res.expected_sales_horizon), 1),
            "expected_volume": round(float(res.expected_sales_horizon), 1),  # Compatibility alias
            "expected_leftover_inventory": round(float(res.expected_leftover_inventory), 1),
            "projected_clearance_days": round(float(res.projected_clearance_days), 1),
            "clearance_probability": round(float(res.clearance_probability), 3),
            "expected_lifecycle_profit": round(float(res.expected_lifecycle_profit), 2),
            "expected_profit": round(float(res.expected_lifecycle_profit), 2),  # Compatibility alias
            "expected_revenue": round(float(res.expected_revenue), 2),
            "holding_and_finance_cost": round(float(res.holding_and_finance_cost), 2),
            "depreciation_loss": round(float(res.depreciation_loss), 2),
            "status_quo_daily_demand": round(float(res.status_quo_daily_demand), 2),
            "status_quo_clearance_days": round(float(res.status_quo_clearance_days), 1),
            "status_quo_leftover": round(float(res.status_quo_leftover), 1),
            "status_quo_profit": round(float(res.status_quo_profit), 2),
            "profit_lift_amount": round(float(res.profit_lift_amount), 2),
            "profit_lift_pct": round(float(res.profit_lift_pct), 2),
            "inventory_risk_level": res.inventory_risk_level,
            "business_reason": res.business_reason,
            "competitor_avg_price": round(float(row["competitor_avg_price"]), 2),
            "competitor_min_price": round(float(row["competitor_min_price"]), 2),
            "memo": memo,
            "xai": xai,
            "elasticity": elasticity_val,
            "elasticity_regime": elasticity_regime,
            "elasticity_method": elasticity_method,
            "optimization_method": "constrained lifecycle-profit grid search on the ML demand surface",
            "data_source": "synthetic-simulation",
            "active_event": active_event_for_sku,
            "feasible_prices": [round(float(p), 2) for p in res.feasible_prices],
            "profit_curve": [round(float(pr), 2) for pr in res.profit_curve],
            "demand_curve": [round(float(d), 2) for d in res.demand_curve]
        })

    avg_lift_pct = round((total_profit_lift / (total_status_quo_profit + 1e-5)) * 100, 2)
    
    _optimizations_cache["synthetic"] = results
    _summary_cache["synthetic"] = {
        "total_skus": len(results),
        "total_inventory_units": total_inv_units,
        "total_inventory_value": round(total_inv_value, 2),
        "total_status_quo_profit": round(total_status_quo_profit, 2),
        "total_optimized_profit": round(total_opt_profit, 2),
        "total_profit_lift": round(total_profit_lift, 2),
        "avg_profit_lift_pct": avg_lift_pct,
        "action_counts": action_counts,
        "risk_counts": risk_counts,
        "market": "Indian Consumer Electronics Retail",
        "legal_compliance": "Legal Metrology MRP Enforced",
        "engine_version": "v2.4-LightGBM",
        "active_events_count": len(_active_events),
        "model_source": "synthetic",
        "training_metadata": {
            "dataset": "Synthetic Indian electronics retail simulation (8 SKUs x 5 stores, 240 days)",
            "model": "LightGBM gradient-boosted demand forecaster",
            "split_strategy": forecaster.metrics.get("split_strategy", "unknown"),
            "leakage_free": bool(forecaster.metrics.get("leakage_free", False)),
            "val_metrics": {k: forecaster.metrics.get(k) for k in ("mae", "rmse", "r2", "train_samples", "val_samples")}
        }
    }

    return _optimizations_cache["synthetic"]

def compute_kaggle_optimizations(force: bool = False) -> List[Dict[str, Any]]:
    """
    Runs the SAME constrained lifecycle optimizer on products from the real
    Kaggle retail dataset, using the real-data LightGBM demand model.

    Documented economic assumptions (the real dataset carries no MRP/cost/
    inventory/lifecycle fields):
      - unit_cost = 72% of current unit price (retail gross-margin assumption)
      - mrp       = 1.05 x max observed unit price (legal-ceiling proxy)
      - inventory = 20 days of median observed daily qty
      - days_to_successor = 90 (no successor metadata in source data)
    """
    global _optimizations_cache, _summary_cache
    if not force and "kaggle" in _optimizations_cache:
        return _optimizations_cache["kaggle"]

    adapter, optimizer = get_kaggle_engine()
    df = pd.read_csv(KAGGLE_RAW_CSV)
    df = df.sort_values(["year", "month"]).reset_index(drop=True)

    top_products = (
        df.groupby("product_id")["qty"].sum()
        .sort_values(ascending=False).head(8).index.tolist()
    )

    results: List[Dict[str, Any]] = []
    total_inv_units, total_inv_value = 0, 0.0
    total_sq_profit, total_opt_profit, total_lift = 0.0, 0.0, 0.0
    action_counts = {"Increase Price": 0, "Hold Price": 0, "Slight Reduction": 0, "Clearance Markdown": 0}
    risk_counts = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}

    for pid in top_products:
        sub = df[df["product_id"] == pid]
        last = sub.iloc[-1]
        stats = adapter.product_stats.get(pid, adapter.default_stats)

        current_price = float(last["unit_price"])
        comp_vals = [float(last.get(c)) for c in ("comp_1", "comp_2", "comp_3") if pd.notna(last.get(c))]
        comp_avg = float(np.mean(comp_vals)) if comp_vals else current_price
        comp_min = float(min(comp_vals)) if comp_vals else current_price

        mrp = max(float(stats["max_unit_price"]) * 1.05, current_price * 1.05)
        unit_cost = round(current_price * 0.72, 2)
        current_inventory = max(10, int(round(stats["median_qty"] * 20)))
        days_to_succ = 90

        adapter.current_product_id = pid
        res = optimizer.optimize_sku(
            product_id=pid,
            product_name=f"{stats['category']} · {pid}",
            current_price=current_price,
            mrp=mrp,
            unit_cost=unit_cost,
            current_inventory=current_inventory,
            competitor_avg_price=comp_avg,
            competitor_min_price=comp_min,
            days_to_successor=days_to_succ
        )

        memo = ReasonGenerator.generate_retailer_memo(res)
        el_model = ElasticityEstimator.estimate_from_model(
            adapter, current_price, comp_avg, comp_min,
            mrp, unit_cost, current_inventory, days_to_succ
        )
        xai = adapter.explain_point(float(res.recommended_price), comp_avg, comp_min)

        total_inv_units += current_inventory
        total_inv_value += current_inventory * current_price
        total_sq_profit += res.status_quo_profit
        total_opt_profit += res.expected_lifecycle_profit
        total_lift += res.profit_lift_amount
        action_counts[res.price_action] = action_counts.get(res.price_action, 0) + 1
        risk_counts[res.inventory_risk_level] = risk_counts.get(res.inventory_risk_level, 0) + 1

        results.append({
            "product_id": pid,
            "product_name": f"{stats['category']} · {pid}",
            "brand": stats["category"],
            "model": pid,
            "successor_model": None,
            "category": stats["category"],
            "current_price": round(current_price, 2),
            "recommended_price": float(res.recommended_price),
            "optimal_price": float(res.recommended_price),
            "price_action": res.price_action,
            "price_change": float(res.price_change),
            "price_change_pct": float(res.price_change_pct),
            "mrp": round(mrp, 2),
            "unit_cost": unit_cost,
            "current_inventory": current_inventory,
            "days_to_successor": days_to_succ,
            "expected_daily_demand": round(float(res.expected_daily_demand), 2),
            "expected_sales_horizon": round(float(res.expected_sales_horizon), 1),
            "expected_volume": round(float(res.expected_sales_horizon), 1),
            "expected_leftover_inventory": round(float(res.expected_leftover_inventory), 1),
            "projected_clearance_days": round(float(res.projected_clearance_days), 1),
            "clearance_probability": round(float(res.clearance_probability), 3),
            "expected_lifecycle_profit": round(float(res.expected_lifecycle_profit), 2),
            "expected_profit": round(float(res.expected_lifecycle_profit), 2),
            "expected_revenue": round(float(res.expected_revenue), 2),
            "holding_and_finance_cost": round(float(res.holding_and_finance_cost), 2),
            "depreciation_loss": round(float(res.depreciation_loss), 2),
            "status_quo_daily_demand": round(float(res.status_quo_daily_demand), 2),
            "status_quo_clearance_days": round(float(res.status_quo_clearance_days), 1),
            "status_quo_leftover": round(float(res.status_quo_leftover), 1),
            "status_quo_profit": round(float(res.status_quo_profit), 2),
            "profit_lift_amount": round(float(res.profit_lift_amount), 2),
            "profit_lift_pct": round(float(res.profit_lift_pct), 2),
            "inventory_risk_level": res.inventory_risk_level,
            "business_reason": res.business_reason,
            "competitor_avg_price": round(comp_avg, 2),
            "competitor_min_price": round(comp_min, 2),
            "memo": memo,
            "xai": xai,
            "elasticity": el_model.get("elasticity"),
            "elasticity_regime": el_model.get("regime", "Unknown"),
            "elasticity_method": el_model.get("method", ""),
            "optimization_method": "constrained lifecycle-profit grid search on the real-data ML demand surface",
            "data_source": "kaggle-real",
            "active_event": None,
            "feasible_prices": [round(float(p), 2) for p in res.feasible_prices],
            "profit_curve": [round(float(pr), 2) for pr in res.profit_curve],
            "demand_curve": [round(float(d), 2) for d in res.demand_curve]
        })

    avg_lift_pct = round((total_lift / (total_sq_profit + 1e-5)) * 100, 2)
    _optimizations_cache["kaggle"] = results
    _summary_cache["kaggle"] = {
        "total_skus": len(results),
        "total_inventory_units": total_inv_units,
        "total_inventory_value": round(total_inv_value, 2),
        "total_status_quo_profit": round(total_sq_profit, 2),
        "total_optimized_profit": round(total_opt_profit, 2),
        "total_profit_lift": round(total_lift, 2),
        "avg_profit_lift_pct": avg_lift_pct,
        "action_counts": action_counts,
        "risk_counts": risk_counts,
        "market": "Real Kaggle retail dataset (suddharshan/retail-price-optimization)",
        "legal_compliance": "MRP-style ceiling enforced (imputed proxy)",
        "engine_version": "v2.4-LightGBM",
        "active_events_count": len(_active_events),
        "model_source": "kaggle",
        "training_metadata": {
            "dataset": "Real Kaggle retail_price.csv (676 rows, " + str(df["product_id"].nunique()) + " products)",
            "model": "LightGBM gradient-boosted demand forecaster (real data)",
            "split_strategy": adapter.metrics.get("split_strategy", "unknown"),
            "leakage_free": bool(adapter.metrics.get("leakage_free", False)),
            "val_metrics": {k: adapter.metrics.get(k) for k in ("mae", "rmse", "r2", "train_samples", "val_samples")},
            "economic_assumptions": {
                "unit_cost_pct": 0.72,
                "mrp_factor": 1.05,
                "inventory_days": 20,
                "days_to_successor": 90
            }
        }
    }

    return _optimizations_cache["kaggle"]

@router.get("/summary")
def get_portfolio_summary(model_source: str = Query("synthetic")):
    """Returns top-level KPIs for the portfolio (cached for speed)."""
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"
    compute_optimizations(force=False, model_source=model_source)
    return _summary_cache[model_source]

@router.get("/optimizations")
def get_sku_optimizations(model_source: str = Query("synthetic")):
    """Computes and returns optimization for all SKUs (cached per data source)."""
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"
    data = compute_optimizations(force=False, model_source=model_source)
    return {"status": "success", "data": data, "active_events": _active_events, "model_source": model_source}

@router.get("/optimizations/refresh")
@router.post("/optimizations/refresh")
def refresh_sku_optimizations(model_source: str = Query("synthetic")):
    """Forces recalculation of the optimization cache for the given data source."""
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"
    data = compute_optimizations(force=True, model_source=model_source)
    return {"status": "success", "message": "Cache refreshed", "data": data, "active_events": _active_events, "model_source": model_source}

@router.get("/active-events")
def get_active_events():
    """Returns list of currently active tech launch announcements & alerts"""
    return {"status": "success", "events": _active_events}

class LifecycleEventRequest(BaseModel):
    product_id: str
    successor_name: str
    announcement_headline: str
    days_to_successor: int = 14
    competitor_price_drop_pct: Optional[float] = 0.04

@router.post("/lifecycle-event")
def trigger_lifecycle_event(ev: LifecycleEventRequest):
    """
    Ingests a breaking tech launch announcement (e.g. iPhone 18 announced).
    Updates days_to_successor in products.csv, simulates competitor reaction,
    forces model re-optimization, and returns the immediate actionable pricing recommendation.
    """
    global _active_events
    products_file = SYNTHETIC_DATA_DIR / "products.csv"
    df = pd.read_csv(products_file)
    mask = df["product_id"] == ev.product_id

    if not mask.any():
        raise HTTPException(status_code=404, detail=f"Product {ev.product_id} not found")

    old_days = int(df.loc[mask, "days_to_successor"].values[0])
    product_name = f"{df.loc[mask, 'brand'].values[0]} {df.loc[mask, 'model'].values[0]}"

    # Update days_to_successor in catalog
    df.loc[mask, "days_to_successor"] = ev.days_to_successor
    df.to_csv(products_file, index=False)

    # Record event in active alerts
    event_entry = {
        "event_id": f"EVT_{ev.product_id}_{int(datetime.now().timestamp())}",
        "product_id": ev.product_id,
        "product_name": product_name,
        "successor_name": ev.successor_name,
        "headline": ev.announcement_headline,
        "days_to_successor": ev.days_to_successor,
        "old_days": old_days,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "ACTIVE_URGENT"
    }

    # Filter out previous event for this same SKU if exists
    _active_events = [e for e in _active_events if e["product_id"] != ev.product_id]
    _active_events.insert(0, event_entry)

    # Force re-optimization across the catalog
    updated_skus = compute_optimizations(force=True)
    target_sku = next((s for s in updated_skus if s["product_id"] == ev.product_id), None)

    return {
        "status": "success",
        "message": f"Successfully processed {ev.successor_name} announcement. Days to successor shifted from {old_days} to {ev.days_to_successor} days.",
        "event": event_entry,
        "optimized_sku": target_sku,
        "active_events": _active_events
    }

@router.post("/reset-events")
def reset_lifecycle_events():
    """Resets all products back to standard baseline lifecycle schedules."""
    global _active_events
    products_file = SYNTHETIC_DATA_DIR / "products.csv"
    df = pd.read_csv(products_file)

    # Default baseline days_to_successor
    default_schedules = {
        "SKU_IPHONE_17_256": 60,
        "SKU_IPHONE_16_128": 15,
        "SKU_PIXEL_10_PRO": 270,
        "SKU_GALAXY_S26_256": 180,
        "SKU_ONEPLUS_13_256": 220,
        "SKU_REDMI_NOTE_15_PRO": 160,
        "SKU_GALAXY_A56_128": 210,
        "SKU_S26_ULTRA_512": 180
    }

    for pid, days in default_schedules.items():
        mask = df["product_id"] == pid
        if mask.any():
            df.loc[mask, "days_to_successor"] = days

    df.to_csv(products_file, index=False)
    _active_events.clear()

    # Recompute
    data = compute_optimizations(force=True)
    return {
        "status": "success",
        "message": "All product lifecycles reset to baseline schedules.",
        "active_events": [],
        "data": data
    }

@router.get("/transfers")
def get_store_transfers():
    """
    Multi-store balancing: solves the inter-store transfer transportation LP
    (scipy linprog / HiGHS) for every SKU.

    Snapshot selection: the most recent date at which at least one SKU has a
    store with surplus (>45 days of supply) AND a store with a deficit
    (<12 days) — i.e., a date where the transfer problem is actually
    well-posed. (At the very end of the simulation, replenishment stops and
    every store is stockout-imminent, so no profitable transfer exists.)
    Velocity is the 14-day average ending at the snapshot date.
    """
    try:
        inv = pd.read_csv(SYNTHETIC_DATA_DIR / "inventory.csv")
        stores = pd.read_csv(SYNTHETIC_DATA_DIR / "stores.csv")
        products = pd.read_csv(SYNTHETIC_DATA_DIR / "products.csv")
        costs = pd.read_csv(SYNTHETIC_DATA_DIR / "costs.csv")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Store data unavailable: {exc}")

    inv["date"] = pd.to_datetime(inv["date"])

    def build_state(snapshot_date):
        window_start = snapshot_date - pd.Timedelta(days=13)
        recent = inv[inv["date"] >= window_start]
        velocity = recent.groupby(["store_id", "product_id"])["units_sold"].mean().reset_index()
        velocity = velocity.rename(columns={"units_sold": "daily_sales_velocity"})
        latest_inv = inv[inv["date"] == snapshot_date][
            ["store_id", "product_id", "closing_inventory"]
        ].rename(columns={"closing_inventory": "current_inventory"})
        state = latest_inv.merge(velocity, on=["store_id", "product_id"], how="left")
        state = state.merge(stores[["store_id", "store_name", "city"]], on="store_id", how="left")
        state = state.merge(products[["product_id", "brand", "model", "variant", "mrp"]], on="product_id", how="left")
        state = state.merge(costs[["product_id", "unit_cost"]], on="product_id", how="left")
        state["daily_sales_velocity"] = state["daily_sales_velocity"].fillna(0.2)
        return state

    def imbalance_score(state):
        # A date is useful if some SKU has BOTH a surplus store and a deficit store
        score = 0
        for _, sub in state.groupby("product_id"):
            dos = sub["current_inventory"] / sub["daily_sales_velocity"].clip(lower=0.2)
            if (dos > 45).any() and (dos < 12).any():
                score += 1
        return score

    # Walk backwards from the latest date to find the most recent well-posed snapshot
    candidate_dates = sorted(inv["date"].unique(), reverse=True)
    snapshot_date = candidate_dates[0]
    chosen_state = None
    for d in candidate_dates:
        st = build_state(d)
        if imbalance_score(st) > 0:
            snapshot_date, chosen_state = d, st
            break
    if chosen_state is None:
        chosen_state = build_state(snapshot_date)

    balancer = MultiStoreBalancer()
    results = []
    for pid, sub in chosen_state.groupby("product_id"):
        prod = sub.iloc[0]
        store_data = sub[[
            "store_id", "store_name", "city",
            "current_inventory", "daily_sales_velocity"
        ]].to_dict("records")
        out = balancer.analyze_sku_across_stores(
            product_id=pid,
            product_name=f"{prod['brand']} {prod['model']} ({prod['variant']})",
            unit_cost=float(prod["unit_cost"]),
            mrp=float(prod["mrp"]),
            store_data=store_data
        )
        results.append(out)

    return {
        "status": "success",
        "method": "transportation LP (scipy.optimize.linprog / HiGHS)",
        "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
        "data": results
    }

class SimulationRequest(BaseModel):
    product_id: str
    price: float
    competitor_avg_price: Optional[float] = None
    competitor_min_price: Optional[float] = None
    inventory: Optional[int] = None
    days_to_successor: Optional[int] = None

@router.post("/simulate")
def simulate_price(req: SimulationRequest):
    """Simulates expected daily demand and profitability for an arbitrary price point."""
    forecaster, _, optimizer = get_models()
    products_df, costs_df, competitors_df = get_catalog_and_meta()
    
    p_row = products_df[products_df["product_id"] == req.product_id]
    if p_row.empty:
        raise HTTPException(status_code=404, detail="Product not found")
    
    p_info = p_row.iloc[0]
    c_info = costs_df[costs_df["product_id"] == req.product_id].iloc[0]
    
    latest_date = competitors_df["date"].max()
    comp_row = competitors_df[(competitors_df["date"] == latest_date) & (competitors_df["product_id"] == req.product_id)]
    
    mrp = float(p_info["mrp"])
    unit_cost = float(c_info["unit_cost"])
    comp_avg = float(req.competitor_avg_price or comp_row["competitor_price"].mean())
    comp_min = float(req.competitor_min_price or comp_row["competitor_price"].min())
    inv = int(req.inventory or 200)
    days_to_succ = int(req.days_to_successor or p_info["days_to_successor"])

    # Predict single point demand
    daily_demand = forecaster.predict_point(
        selling_price=req.price,
        mrp=mrp,
        competitor_avg_price=comp_avg,
        competitor_min_price=comp_min,
        unit_cost=unit_cost,
        opening_inventory=inv,
        days_to_successor=days_to_succ
    )

    # 60-day horizon economics
    horizon = min(float(days_to_succ), 60.0)
    expected_sales = min(float(inv), daily_demand * horizon)
    leftover = max(0.0, float(inv) - expected_sales)
    revenue = expected_sales * req.price
    margin = req.price - unit_cost
    gross_profit = expected_sales * margin
    
    # Holding & depreciation cost
    holding_cost = 0.5 * (float(inv) + leftover) * unit_cost * 0.0005 * horizon
    deprec_loss = leftover * unit_cost * 0.25
    net_profit = gross_profit - holding_cost - deprec_loss

    clearance_days = float(inv) / (daily_demand + 1e-5)
    clearance_prob = min(1.0, (daily_demand * float(days_to_succ)) / (float(inv) + 1e-5))

    return {
        "status": "success",
        "product_id": req.product_id,
        "simulated_price": req.price,
        "mrp": mrp,
        "unit_cost": unit_cost,
        "daily_demand": round(daily_demand, 2),
        "expected_sales": round(expected_sales, 1),
        "leftover_inventory": round(leftover, 1),
        "projected_revenue": round(revenue, 2),
        "expected_net_profit": round(net_profit, 2),
        "clearance_days": round(clearance_days, 1),
        "clearance_probability": round(clearance_prob, 3),
        "margin_per_unit": round(margin, 2)
    }
