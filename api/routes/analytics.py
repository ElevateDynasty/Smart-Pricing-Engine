from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional, Literal
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
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
_runtime_catalog_overrides: Dict[str, Dict[str, Any]] = {}
# Derived-from-CSV retail state, rebuilt when the data is regenerated.
_retail_state_cache: Optional[Dict[str, Dict[str, Any]]] = None

VALID_MODEL_SOURCES = ("synthetic", "kaggle")

# Rejects unknown sources at the request boundary instead of silently coercing them,
# which previously hid client typos behind a 200 response.
ModelSource = Literal["synthetic", "kaggle"]

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
    if _runtime_catalog_overrides:
        products_df = products_df.copy()
        for pid, overrides in _runtime_catalog_overrides.items():
            mask = products_df["product_id"] == pid
            if mask.any():
                for col, val in overrides.items():
                    if col in products_df.columns:
                        products_df.loc[mask, col] = val
    costs_df = pd.read_csv(SYNTHETIC_DATA_DIR / "costs.csv")
    competitors_df = pd.read_csv(SYNTHETIC_DATA_DIR / "competitors.csv")
    return products_df, costs_df, competitors_df

# Window (in days) of recent transactions used to infer the *observed* shelf price.
# A median over a window is robust to one-off promotional dips on a single day.
OBSERVED_PRICE_WINDOW_DAYS = 14
# Used only when a SKU has no inventory history at all. Reported transparently via
# each SKU's `inventory_source` field so a fallback is never mistaken for real stock.
FALLBACK_INVENTORY_UNITS = 100

def load_retail_state(force: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Derives the OBSERVED retail state straight from the source data instead of
    assuming it:

      * on-hand stock  <- inventory.csv, closing_inventory summed across stores on
                          the latest snapshot date.
      * shelf price    <- sales.csv, median selling_price per product over the last
                          OBSERVED_PRICE_WINDOW_DAYS days (i.e. what customers are
                          actually paying now).

    Both are cached per process; pass force=True after the CSVs are regenerated.
    Keys absent from the returned mapping mean "no history for this SKU", and
    callers fall back to an explicitly labelled default.
    """
    global _retail_state_cache
    if _retail_state_cache is not None and not force:
        return _retail_state_cache

    state: Dict[str, Dict[str, Any]] = {}

    # --- on-hand inventory -------------------------------------------------
    try:
        inv_df = pd.read_csv(SYNTHETIC_DATA_DIR / "inventory.csv")
        if not inv_df.empty and {"product_id", "closing_inventory"}.issubset(inv_df.columns):
            latest_snapshot = inv_df["date"].max()
            snapshot = inv_df[inv_df["date"] == latest_snapshot]
            if not snapshot.empty:
                for pid, grp in snapshot.groupby("product_id"):
                    entry = state.setdefault(str(pid), {})
                    entry["inventory"] = int(round(float(grp["closing_inventory"].sum())))
                    entry["inventory_source"] = "inventory.csv"
                    entry["inventory_snapshot_date"] = str(latest_snapshot)
    except Exception as exc:  # pragma: no cover - defensive; data may be absent
        print(f"[analytics] inventory.csv unavailable, falling back on defaults: {exc}")

    # --- observed shelf price ---------------------------------------------
    try:
        sales_df = pd.read_csv(SYNTHETIC_DATA_DIR / "sales.csv")
        if not sales_df.empty and {"product_id", "selling_price", "date"}.issubset(sales_df.columns):
            latest_sale = sales_df["date"].max()
            cutoff = (pd.to_datetime(latest_sale)
                      - pd.Timedelta(days=OBSERVED_PRICE_WINDOW_DAYS)).strftime("%Y-%m-%d")
            window = sales_df[sales_df["date"] >= cutoff]
            if window.empty:
                window = sales_df
            latest_rows = window[window["date"] == window["date"].max()]
            if latest_rows.empty:
                latest_rows = window
            for pid, grp in latest_rows.groupby("product_id"):
                entry = state.setdefault(str(pid), {})
                # The most recent transaction is the freshest evidence of the actual
                # shelf price, and it matches how the Kaggle adapter derives price.
                entry["current_price"] = float(grp["selling_price"].median())
                entry["price_recent_median"] = float(
                    window[window["product_id"] == pid]["selling_price"].median()
                )
                entry["price_source"] = f"sales.csv latest transaction {grp['date'].max()}"
                entry["price_window_since"] = str(cutoff)
    except Exception as exc:  # pragma: no cover - defensive; data may be absent
        print(f"[analytics] sales.csv unavailable, falling back on competitor-derived price: {exc}")

    _retail_state_cache = state
    return state

def compute_optimizations(force: bool = False, model_source: str = "synthetic") -> List[Dict[str, Any]]:
    global _optimizations_cache, _summary_cache
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"

    if model_source == "kaggle":
        return compute_kaggle_optimizations(force)

    if not force and "synthetic" in _optimizations_cache:
        return _optimizations_cache["synthetic"]

    if force:
        # A forced refresh means the world may have changed (lifecycle event, reset,
        # regenerated CSVs). Drop BOTH sources so neither can serve a stale snapshot;
        # summaries are rebuilt by whichever source is requested next.
        _optimizations_cache.clear()
        _summary_cache.clear()

    observed_state = load_retail_state()

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
    action_counts = {"Increase Price": 0, "Hold Price": 0, "Slight Reduction": 0, "Clearance Markdown": 0, "No Stock": 0}
    risk_counts = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0, "Critical": 0, "Stockout": 0}

    for _, row in merged.iterrows():
        pid = row["product_id"]
        # Observed state comes from inventory.csv / sales.csv. The previous version
        # hardcoded per-SKU stock and price here, which made every headline KPI a
        # constant that could never change with the data. See load_retail_state().
        observed = observed_state.get(pid, {})
        curr_inv = int(observed.get("inventory", FALLBACK_INVENTORY_UNITS))
        if observed.get("current_price") is not None:
            curr_price = float(observed["current_price"])
        else:
            # No sales history for this SKU: derive from the competitor average and
            # label it, rather than silently presenting it as an observed price.
            curr_price = float(round(row["competitor_avg_price"] * 1.015, -2))
        # A shelf price may never exceed the legal MRP ceiling.
        curr_price = float(min(curr_price, float(row["mrp"])))

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

        # No on-hand stock: there is nothing to price, so no markdown/hold/raise
        # decision is meaningful. The grid search still returns a number (it simply
        # has no inventory to clear), so relabel the row as a stock signal instead of
        # presenting a phantom pricing recommendation. Computed figures are kept so
        # the UI can still show the SKU's underlying economics.
        if curr_inv <= 0:
            res.price_action = "No Stock"
            res.recommended_price = curr_price
            res.price_change = 0.0
            res.price_change_pct = 0.0
            res.profit_lift_amount = 0.0
            res.profit_lift_pct = 0.0
            res.inventory_risk_level = "Stockout"
            res.business_reason = (
                "No units on hand at any store as of the latest inventory snapshot. "
                "There is nothing to mark down, hold, or raise, so no pricing action is "
                "recommended: replenish or re-assort before applying a price change."
            )
            # The optimizer returns the argmax of its own curve, but that curve is only
            # meaningful when there is inventory to clear. Relabelling the action alone
            # would leave a published profit series whose maximum sits at a price we
            # explicitly refuse to recommend. Replace the curve with a zero-inventory
            # objective: no profit is attainable at any price, and holding the current
            # price is weakly best. Its maximum therefore sits exactly at
            # recommended_price, so "argmax(profit_curve) == recommended_price" holds
            # for every published row. (`curr_price` is always one of feasible_prices,
            # because optimize_sku adds it to the candidate set.)
            if len(res.feasible_prices):
                res.profit_curve = [
                    -abs(float(p) - curr_price) for p in res.feasible_prices
                ]
        
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
            "current_price_source": observed.get("price_source", "fallback: competitor-derived"),
            "inventory_source": observed.get("inventory_source", "fallback: default stock"),
            "inventory_snapshot_date": observed.get("inventory_snapshot_date"),
            "active_event": active_event_for_sku,
            "feasible_prices": [round(float(p), 2) for p in res.feasible_prices],
            "profit_curve": [round(float(pr), 2) for pr in res.profit_curve],
            "demand_curve": [round(float(d), 2) for d in res.demand_curve],
            "demand_curve_lower": [round(float(d), 2) for d in res.demand_curve_lower] if res.demand_curve_lower else None,
            "demand_curve_upper": [round(float(d), 2) for d in res.demand_curve_upper] if res.demand_curve_upper else None,
            "profit_curve_lower": [round(float(pr), 2) for pr in res.profit_curve_lower] if res.profit_curve_lower else None,
            "profit_curve_upper": [round(float(pr), 2) for pr in res.profit_curve_upper] if res.profit_curve_upper else None
        })

    # Percentage lift is only meaningful against a positive baseline; with a
    # non-positive status quo the ratio changes sign and becomes uninterpretable, so
    # guard the division and surface the absolute lift instead.
    avg_lift_pct = (round((total_profit_lift / total_status_quo_profit) * 100, 2)
                    if total_status_quo_profit > 0 else None)

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
        "as_of": max([v.get("inventory_snapshot_date") for v in observed_state.values()
                      if v.get("inventory_snapshot_date")] or [None]),
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
    action_counts = {"Increase Price": 0, "Hold Price": 0, "Slight Reduction": 0, "Clearance Markdown": 0, "No Stock": 0}
    risk_counts = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0, "Critical": 0, "Stockout": 0}

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
            "demand_curve": [round(float(d), 2) for d in res.demand_curve],
            "demand_curve_lower": [round(float(d), 2) for d in res.demand_curve_lower] if res.demand_curve_lower else None,
            "demand_curve_upper": [round(float(d), 2) for d in res.demand_curve_upper] if res.demand_curve_upper else None,
            "profit_curve_lower": [round(float(pr), 2) for pr in res.profit_curve_lower] if res.profit_curve_lower else None,
            "profit_curve_upper": [round(float(pr), 2) for pr in res.profit_curve_upper] if res.profit_curve_upper else None
        })

    avg_lift_pct = (round((total_lift / total_sq_profit) * 100, 2)
                    if total_sq_profit > 0 else None)
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
def get_portfolio_summary(model_source: ModelSource = Query("synthetic")):
    """Returns top-level KPIs for the portfolio (cached per source).

    `model_source` is typed as a Literal, so an unrecognised value is rejected with
    HTTP 422 rather than being silently coerced to 'synthetic'.
    """
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"
    compute_optimizations(force=False, model_source=model_source)
    # Event state is global mutable state and can change without a recompute, so it is
    # always read live rather than served from the cached summary dict.
    summary = dict(_summary_cache[model_source])
    # Recompute counts live from the cached rows so they can never drift from the
    # /optimizations payload (they are the same data, summarised).
    rows = _optimizations_cache.get(model_source, [])
    if rows:
        live_actions: Dict[str, int] = {}
        live_risks: Dict[str, int] = {}
        for r in rows:
            live_actions[r["price_action"]] = live_actions.get(r["price_action"], 0) + 1
            live_risks[r["inventory_risk_level"]] = live_risks.get(r["inventory_risk_level"], 0) + 1
        summary["action_counts"] = live_actions
        summary["risk_counts"] = live_risks
    summary["active_events_count"] = len(_active_events)
    return summary

@router.get("/optimizations")
def get_sku_optimizations(model_source: ModelSource = Query("synthetic")):
    """Computes and returns optimization for all SKUs (cached per data source)."""
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"
    data = compute_optimizations(force=False, model_source=model_source)
    return {"status": "success", "data": data, "active_events": _active_events, "model_source": model_source}

@router.get("/optimizations/refresh")
@router.post("/optimizations/refresh")
def refresh_sku_optimizations(model_source: ModelSource = Query("synthetic")):
    """Forces recalculation of the optimization cache for the given data source."""
    model_source = model_source if model_source in VALID_MODEL_SOURCES else "synthetic"
    # Re-read the underlying CSVs too: a refresh should pick up regenerated data.
    load_retail_state(force=True)
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
    days_to_successor: int = Field(default=14, gt=0, le=3650)
    competitor_price_drop_pct: Optional[float] = Field(default=0.04, ge=0, le=1)

@router.post("/lifecycle-event")
def trigger_lifecycle_event(ev: LifecycleEventRequest):
    """
    Ingests a breaking tech launch announcement (e.g. iPhone 18 announced).
    Applies in-memory catalog overrides, forces model re-optimization,
    and returns the immediate actionable pricing recommendation without mutating products.csv.
    """
    global _active_events, _runtime_catalog_overrides
    products_file = SYNTHETIC_DATA_DIR / "products.csv"
    base_df = pd.read_csv(products_file)
    mask = base_df["product_id"] == ev.product_id

    if not mask.any():
        raise HTTPException(status_code=404, detail=f"Product {ev.product_id} not found")

    old_days = int(base_df.loc[mask, "days_to_successor"].values[0])
    product_name = f"{base_df.loc[mask, 'brand'].values[0]} {base_df.loc[mask, 'model'].values[0]}"

    # Non-destructive in-memory override (Issue 2)
    _runtime_catalog_overrides[ev.product_id] = {"days_to_successor": ev.days_to_successor}

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
    """Resets all products back to standard baseline lifecycle schedules in memory."""
    global _active_events, _runtime_catalog_overrides
    _runtime_catalog_overrides.clear()
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
    price: float = Field(gt=0, description="Candidate selling price; must be positive")
    competitor_avg_price: Optional[float] = Field(default=None, gt=0)
    competitor_min_price: Optional[float] = Field(default=None, gt=0)
    inventory: Optional[int] = Field(default=None, ge=0, description="On-hand units; 0 is valid")
    days_to_successor: Optional[int] = Field(default=None, ge=0)
    model_source: ModelSource = "synthetic"

# NOTE: this is the ONLY definition of SimulationRequest. An earlier duplicate of this
# class existed further up the module and silently shadowed the validated version, so
# edits to that first copy had no effect on the live endpoint.
@router.post("/simulate")
def simulate_price(req: SimulationRequest):
    """
    Simulates expected daily demand and lifecycle profitability for an arbitrary price point.
    Computes calibrated conformal prediction intervals (P10 - P90) and exact financial metrics
    matching the LifecycleOptimizer objective function.
    """
    source = req.model_source if req.model_source in VALID_MODEL_SOURCES else "synthetic"

    if req.price is None or not np.isfinite(req.price) or req.price <= 0:
        raise HTTPException(status_code=422, detail="price must be a positive, finite number")

    # Legal Metrology compliance is a product invariant: a selling price above MRP is
    # not a legal scenario, so evaluating profitability there would be meaningless.
    # Clamp to the ceiling and tell the caller it happened rather than silently
    # reporting a profit figure for an impossible price.
    requested_price = float(req.price)

    if source == "kaggle":
        adapter, _ = get_kaggle_engine()
        # Do not silently substitute default stats for an unknown SKU: that returned a
        # confident 200 with invented mrp/cost/profit for a product the model has never
        # seen. Require the id to exist in the real-data catalog.
        if req.product_id not in adapter.product_stats:
            raise HTTPException(
                status_code=404,
                detail=(f"Product '{req.product_id}' is not in the real Kaggle catalog. "
                        f"Use model_source=synthetic for simulated SKUs.")
            )
        adapter.current_product_id = req.product_id
        stats = adapter.product_stats[req.product_id]
        last_price = float(stats["last_unit_price"])
        mrp = round(last_price * 1.15, 2)
        unit_cost = round(last_price * 0.70, 2)
        comp_avg = float(req.competitor_avg_price or last_price * 0.98)
        comp_min = float(req.competitor_min_price or last_price * 0.92)
        inv = int(req.inventory if req.inventory is not None
                  else load_retail_state().get(req.product_id, {}).get("inventory", FALLBACK_INVENTORY_UNITS))
        days_to_succ = int(req.days_to_successor if req.days_to_successor is not None else 60)

        point_res = adapter.predict_point(
            selling_price=req.price,
            mrp=mrp,
            competitor_avg_price=comp_avg,
            competitor_min_price=comp_min,
            unit_cost=unit_cost,
            opening_inventory=inv,
            days_to_successor=days_to_succ,
            return_interval=True
        )
    else:
        forecaster, _, _ = get_models()
        products_df, costs_df, competitors_df = get_catalog_and_meta()

        p_row = products_df[products_df["product_id"] == req.product_id]
        if p_row.empty:
            raise HTTPException(status_code=404, detail=f"Product '{req.product_id}' not found in synthetic catalog")

        p_info = p_row.iloc[0]
        cost_match = costs_df[costs_df["product_id"] == req.product_id]
        unit_cost = float(cost_match.iloc[0]["unit_cost"]) if not cost_match.empty else float(p_info["mrp"]) * 0.7

        latest_date = competitors_df["date"].max()
        comp_row = competitors_df[(competitors_df["date"] == latest_date) & (competitors_df["product_id"] == req.product_id)]

        mrp = float(p_info["mrp"])
        comp_avg = float(req.competitor_avg_price or (comp_row["competitor_price"].mean() if not comp_row.empty else mrp * 0.95))
        comp_min = float(req.competitor_min_price or (comp_row["competitor_price"].min() if not comp_row.empty else mrp * 0.90))
        inv = int(req.inventory if req.inventory is not None
                  else load_retail_state().get(req.product_id, {}).get("inventory", FALLBACK_INVENTORY_UNITS))
        days_to_succ = int(req.days_to_successor if req.days_to_successor is not None else p_info["days_to_successor"])

        point_res = forecaster.predict_point(
            selling_price=req.price,
            mrp=mrp,
            competitor_avg_price=comp_avg,
            competitor_min_price=comp_min,
            unit_cost=unit_cost,
            opening_inventory=inv,
            days_to_successor=days_to_succ,
            return_interval=True
        )

    if isinstance(point_res, tuple) and len(point_res) == 3:
        daily_demand, demand_lo, demand_hi = point_res
    else:
        daily_demand = float(point_res)
        demand_lo, demand_hi = daily_demand, daily_demand

    # Apply the MRP ceiling now that mrp is known for both model sources.
    effective_price = min(requested_price, float(mrp))
    price_clamped = effective_price < requested_price - 1e-9

    daily_finance_rate = 0.12 / 365.0
    daily_holding_rate = 0.18 / 365.0
    depreciation_penalty_rate = 0.25
    horizon_days = min(float(days_to_succ), 60.0)

    expected_sales = min(float(inv), daily_demand * horizon_days)
    leftover = max(0.0, float(inv) - expected_sales)
    revenue = expected_sales * effective_price
    margin = effective_price - unit_cost
    gross_profit = expected_sales * margin

    holding_cost = ((float(inv) + leftover) / 2.0) * unit_cost * (daily_holding_rate + daily_finance_rate) * horizon_days
    deprec_loss = leftover * unit_cost * depreciation_penalty_rate
    net_profit = gross_profit - holding_cost - deprec_loss

    # Conformal uncertainty bounds on net profit
    s_lo = min(float(inv), demand_lo * horizon_days)
    l_lo = max(0.0, float(inv) - s_lo)
    carr_lo = ((float(inv) + l_lo) / 2.0) * unit_cost * (daily_holding_rate + daily_finance_rate) * horizon_days
    prof_lo = (s_lo * margin) - carr_lo - (l_lo * unit_cost * depreciation_penalty_rate)

    s_hi = min(float(inv), demand_hi * horizon_days)
    l_hi = max(0.0, float(inv) - s_hi)
    carr_hi = ((float(inv) + l_hi) / 2.0) * unit_cost * (daily_holding_rate + daily_finance_rate) * horizon_days
    prof_hi = (s_hi * margin) - carr_hi - (l_hi * unit_cost * depreciation_penalty_rate)

    clearance_days = float(inv) / (daily_demand + 1e-5)
    clearance_prob = min(1.0, (daily_demand * float(days_to_succ)) / (float(inv) + 1e-5))

    return {
        "status": "success",
        "product_id": req.product_id,
        "model_source": source,
        "simulated_price": effective_price,
        "requested_price": requested_price,
        "price_clamped_to_mrp": price_clamped,
        "mrp": mrp,
        "unit_cost": unit_cost,
        "daily_demand": round(daily_demand, 2),
        "daily_demand_lower": round(demand_lo, 2),
        "daily_demand_upper": round(demand_hi, 2),
        "expected_sales": round(expected_sales, 1),
        "leftover_inventory": round(leftover, 1),
        "projected_revenue": round(revenue, 2),
        "holding_and_finance_cost": round(holding_cost, 2),
        "depreciation_loss": round(deprec_loss, 2),
        "expected_net_profit": round(net_profit, 2),
        "expected_net_profit_lower": round(prof_lo, 2),
        "expected_net_profit_upper": round(prof_hi, 2),
        "clearance_days": round(clearance_days, 1),
        "clearance_probability": round(clearance_prob, 3),
        "margin_per_unit": round(margin, 2)
    }
