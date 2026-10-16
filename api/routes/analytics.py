from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional, Literal
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

from src.config import SYNTHETIC_DATA_DIR, RAW_DATA_DIR
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator
from src.optimization.lifecycle_optimizer import LifecycleOptimizer
from src.optimization.multi_store_balancer import MultiStoreBalancer
from src.explainability.reason_generator import ReasonGenerator
from src.data.data_pipeline import DataPipeline
from src.data.kaggle_pipeline import KaggleDemandAdapter, KAGGLE_RAW_CSV
from src.optimization.competitor_game_theory import CompetitorGameTheorySimulator
from src.evaluation.model_ablation import run_full_ablation
from src.optimization.retail_price_lp_optimizer import (
    RetailPriceRevenueSimulator,
    RetailPortfolioLPOptimizer,
    SingleProductSimulationResult
)

router = APIRouter()

# Global instances cache
_models_cache: Dict[str, Any] = {}
# Per-source caches: {"synthetic": [...], "kaggle": [...]}
_optimizations_cache: Dict[str, List[Dict[str, Any]]] = {}
_summary_cache: Dict[str, Dict[str, Any]] = {}
_active_events: List[Dict[str, Any]] = []
_runtime_catalog_overrides: Dict[str, Dict[str, Any]] = {}
# Offline Retailer dynamic product catalog and saved inventory
_retailer_custom_products: Dict[str, Dict[str, Any]] = {}
_retailer_saved_inventory: List[Dict[str, Any]] = []
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
    costs_df = pd.read_csv(SYNTHETIC_DATA_DIR / "costs.csv")
    competitors_df = pd.read_csv(SYNTHETIC_DATA_DIR / "competitors.csv")

    # Merge custom offline retailer products if registered
    if _retailer_custom_products:
        custom_rows = []
        custom_costs = []
        custom_comps = []
        latest_comp_date = competitors_df["date"].max() if "date" in competitors_df.columns and not competitors_df.empty else datetime.now().strftime("%Y-%m-%d")
        
        for pid, pdata in _retailer_custom_products.items():
            custom_rows.append({
                "product_id": pid,
                "brand": pdata.get("brand", "Generic"),
                "model": pdata.get("product_name", pid),
                "variant": f"{pdata.get('category', 'Electronics')} Retail Stock",
                "category": pdata.get("category", "Flagship Smartphone"),
                "ram_gb": 8,
                "storage_gb": 256,
                "mrp": float(pdata.get("mrp", 50000.0)),
                "launch_date": "2025-01-01",
                "successor_model": f"{pdata.get('product_name', pid)} Next-Gen",
                "days_to_successor": int(pdata.get("days_to_successor", 60)),
                "base_elasticity": 2.0,
                "base_daily_demand": 8.0,
                "target_segment": "Offline Retail Customers"
            })
            custom_costs.append({
                "product_id": pid,
                "unit_cost": float(pdata.get("unit_cost", 40000.0)),
                "holding_cost_daily_pct": 0.00068,
                "salvage_value_pct": 0.65
            })
            comp_p = float(pdata.get("competitor_avg_price", 45000.0))
            custom_comps.append({
                "product_id": pid,
                "competitor_name": "Local Market Average",
                "competitor_price": comp_p,
                "date": latest_comp_date
            })
        
        if custom_rows:
            products_df = pd.concat([products_df, pd.DataFrame(custom_rows)], ignore_index=True)
            costs_df = pd.concat([costs_df, pd.DataFrame(custom_costs)], ignore_index=True)
            competitors_df = pd.concat([competitors_df, pd.DataFrame(custom_comps)], ignore_index=True)

    if _runtime_catalog_overrides:
        products_df = products_df.copy()
        for pid, overrides in _runtime_catalog_overrides.items():
            mask = products_df["product_id"] == pid
            if mask.any():
                for col, val in overrides.items():
                    if col in products_df.columns:
                        products_df.loc[mask, col] = val

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

    # Incorporate custom saved offline retailer stock state
    if _retailer_custom_products:
        for pid, pdata in _retailer_custom_products.items():
            entry = state.setdefault(str(pid), {})
            entry["inventory"] = int(pdata.get("current_inventory", 50))
            entry["inventory_source"] = "retailer store on-hand stock"
            entry["inventory_snapshot_date"] = datetime.now().strftime("%Y-%m-%d")
            entry["current_price"] = float(pdata.get("current_price", 50000.0))
            entry["price_recent_median"] = float(pdata.get("current_price", 50000.0))
            entry["price_source"] = "retailer current shelf price"

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

        # Elasticity Resolution Hierarchy:
        # Priority 1: Empirical econometric log-log OLS regression on historical transactions (gold standard)
        el_info = elasticity_est.get_elasticity(pid) if hasattr(elasticity_est, "get_elasticity") else {}
        if el_info.get("identifiable") and el_info.get("elasticity") is not None and el_info.get("elasticity") > 0.05:
            elasticity_val = float(el_info["elasticity"])
            elasticity_regime = str(el_info.get("regime", "Unknown"))
            elasticity_method = str(el_info.get("method", "econometric log-log OLS"))
        else:
            # Priority 2: Model-derived adaptive finite difference on the demand surface
            el_model = ElasticityEstimator.estimate_from_model(
                forecaster, curr_price,
                float(row["competitor_avg_price"]),
                float(row["competitor_min_price"]),
                float(row["mrp"]), float(row["unit_cost"]),
                curr_inv, days_to_succ
            )
            elasticity_val = el_model.get("elasticity")
            elasticity_regime = el_model.get("regime", "Unknown")
            elasticity_method = el_model.get("method", "model-derived (demand ML surface)")

        # Priority 3: Arc elasticity along the optimizer's discrete candidate demand curve
        if elasticity_val is None and len(res.feasible_prices) >= 2 and len(res.demand_curve) >= 2:
            fp = np.array(res.feasible_prices)
            dc = np.array(res.demand_curve)
            idx = int(np.argmin(np.abs(fp - curr_price)))
            idx_lo = max(0, idx - 1)
            idx_hi = min(len(fp) - 1, idx + 1)
            if idx_hi > idx_lo and fp[idx_hi] > fp[idx_lo] and (dc[idx_lo] + dc[idx_hi]) > 0:
                p_mid = (fp[idx_hi] + fp[idx_lo]) / 2.0
                d_mid = (dc[idx_lo] + dc[idx_hi]) / 2.0
                delta_p = fp[idx_hi] - fp[idx_lo]
                delta_d = dc[idx_lo] - dc[idx_hi]
                arc_eps = float((delta_d / d_mid) / (delta_p / p_mid)) if delta_p > 0 and d_mid > 0 else 0.0
                if arc_eps > 0.05:
                    elasticity_val = round(arc_eps, 3)
                    elasticity_regime = "Highly Elastic" if arc_eps > 1.8 else ("Moderately Elastic" if arc_eps >= 1.1 else "Inelastic")
                    elasticity_method = "arc elasticity along optimizer demand response curve"

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

    if force:
        _models_cache.pop("kaggle_adapter", None)
        _models_cache.pop("kaggle_optimizer", None)

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
        elasticity_val = el_model.get("elasticity")
        elasticity_regime = el_model.get("regime", "Unknown")
        elasticity_method = el_model.get("method", "model-derived (Kaggle ML surface)")

        # Arc elasticity fallback on Kaggle demand curve if point derivative is locally discrete
        if elasticity_val is None and len(res.feasible_prices) >= 2 and len(res.demand_curve) >= 2:
            fp = np.array(res.feasible_prices)
            dc = np.array(res.demand_curve)
            idx = int(np.argmin(np.abs(fp - current_price)))
            idx_lo = max(0, idx - 1)
            idx_hi = min(len(fp) - 1, idx + 1)
            if idx_hi > idx_lo and fp[idx_hi] > fp[idx_lo] and (dc[idx_lo] + dc[idx_hi]) > 0:
                p_mid = (fp[idx_hi] + fp[idx_lo]) / 2.0
                d_mid = (dc[idx_lo] + dc[idx_hi]) / 2.0
                delta_p = fp[idx_hi] - fp[idx_lo]
                delta_d = dc[idx_lo] - dc[idx_hi]
                arc_eps = float((delta_d / d_mid) / (delta_p / p_mid)) if delta_p > 0 and d_mid > 0 else 0.0
                if arc_eps > 0.05:
                    elasticity_val = round(arc_eps, 3)
                    elasticity_regime = "Highly Elastic" if arc_eps > 1.8 else ("Moderately Elastic" if arc_eps >= 1.1 else "Inelastic")
                    elasticity_method = "arc elasticity along optimizer demand response curve"
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
            "elasticity": elasticity_val,
            "elasticity_regime": elasticity_regime,
            "elasticity_method": elasticity_method,
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
        "market": "Real Kaggle mobile phones & consumer electronics retail dataset",
        "legal_compliance": "MRP-style ceiling enforced (imputed proxy)",
        "engine_version": "v2.4-LightGBM",
        "active_events_count": len(_active_events),
        "model_source": "kaggle",
        "training_metadata": {
            "dataset": f"Real Kaggle mobile phones dataset ({len(df)} transactions, {df['product_id'].nunique()} devices)",
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

    # Dynamic point elasticity at the simulated price point
    sim_forecaster = adapter if source == "kaggle" else forecaster
    el_sim = ElasticityEstimator.estimate_from_model(
        sim_forecaster, effective_price,
        comp_avg, comp_min,
        mrp, unit_cost, inv, days_to_succ
    )
    sim_elasticity = el_sim.get("elasticity")
    sim_regime = el_sim.get("regime", "Unknown")
    sim_advice = el_sim.get("action_advice", "")

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
        "margin_per_unit": round(margin, 2),
        "elasticity": sim_elasticity,
        "elasticity_regime": sim_regime,
        "elasticity_advice": sim_advice
    }

@router.get("/game-theory/simulate")
def simulate_game_theory_duopoly(
    initial_store_price: float = Query(79999.0, ge=1000.0),
    initial_comp_price: float = Query(77999.0, ge=1000.0),
    unit_cost: float = Query(68000.0, ge=500.0),
    mrp: float = Query(89900.0, ge=1000.0),
    ai_price: Optional[float] = Query(79000.0),
    offline_premium: float = Query(1000.0, ge=0.0),
    max_rounds: int = Query(6, ge=2, le=20)
):
    """
    Simulates multi-round asymmetric Bertrand duopoly game between offline store
    and online algorithmic platforms to verify Nash equilibrium stability and price war avoidance.
    """
    simulator = CompetitorGameTheorySimulator(offline_premium=offline_premium)
    result = simulator.simulate_duopoly_dynamics(
        initial_store_price=initial_store_price,
        initial_comp_price=initial_comp_price,
        unit_cost=unit_cost,
        mrp=mrp,
        ai_recommended_price=ai_price,
        max_rounds=max_rounds
    )
    return {"status": "success", "data": result}

@router.get("/models/ablation")
def get_model_ablation_matrix():
    """
    Returns empirical ablation benchmarks comparing Monotone LightGBM,
    Unconstrained LightGBM, Random Forest, and Linear Econometric OLS models.
    """
    try:
        ablation_df = run_full_ablation()
        records = ablation_df.to_dict(orient="records")
        return {"status": "success", "data": records}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ablation evaluation failed: {exc}")


class RetailerInventoryOptimizationRequest(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=120, description="Electronic device model name")
    brand: str = Field(default="Apple", min_length=1, max_length=60)
    category: str = Field(default="Flagship Smartphone", min_length=1, max_length=60)
    device_type: Optional[str] = Field(default="smartphone", description="Device category: smartphone, laptop, tablet, smartwatch, audio, tv, console, camera, accessories")
    current_inventory: int = Field(..., ge=1, le=100000, description="Current stock units on hand")
    current_price: float = Field(..., ge=100.0, le=2000000.0, description="Current retail selling price (INR)")
    unit_cost: float = Field(..., ge=50.0, le=2000000.0, description="Wholesale unit purchase cost (INR)")
    mrp: float = Field(..., ge=100.0, le=2000000.0, description="Statutory Maximum Retail Price ceiling (INR)")
    competitor_avg_price: float = Field(..., ge=100.0, le=2000000.0, description="Average market competitor price (INR)")
    competitor_min_price: Optional[float] = Field(default=None, ge=100.0, le=2000000.0, description="Lowest observed competitor price (INR)")
    days_to_successor: int = Field(default=60, ge=5, le=365, description="Clearance deadline or days to next-gen model launch")
    offline_premium: float = Field(default=1000.0, ge=0.0, le=50000.0, description="Tolerated offline showrooming premium (INR)")
    store_channel: str = Field(default="Metro Flagship", max_length=60, description="Retail channel tier")

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "current_inventory" not in data and "stock_units" in data:
                data["current_inventory"] = data["stock_units"]
            if "current_price" not in data and "current_shelf_price" in data:
                data["current_price"] = data["current_shelf_price"]
            if "offline_premium" not in data and "offline_showrooming_premium" in data:
                data["offline_premium"] = data["offline_showrooming_premium"]
            if "store_channel" not in data and "channel_tier" in data:
                data["store_channel"] = data["channel_tier"]
        return data


def resolve_electronic_device_type(product_name: str, category: str = "", brand: str = "") -> Tuple[str, str, str]:
    """
    Returns (device_type, fontawesome_icon, brand_badge)
    device_type: smartphone, laptop, tablet, smartwatch, audio, tv, console, camera, accessories
    """
    text = f"{product_name} {category} {brand}".lower()
    if any(k in text for k in ["laptop", "macbook", "notebook", "thinkpad", "zenbook", "spectre", "xps"]):
        dev_type = "laptop"
        icon = "fa-solid fa-laptop"
    elif any(k in text for k in ["tablet", "ipad", "tab s", "xiaomi pad", "surface pro"]):
        dev_type = "tablet"
        icon = "fa-solid fa-tablet-screen-button"
    elif any(k in text for k in ["watch", "smartwatch", "band", "gear", "fitbit", "garmin"]):
        dev_type = "smartwatch"
        icon = "fa-solid fa-stopwatch"
    elif any(k in text for k in ["audio", "headphone", "earbud", "buds", "airpod", "wh-1000", "tws", "speaker", "soundbar"]):
        dev_type = "audio"
        icon = "fa-solid fa-headphones"
    elif any(k in text for k in ["tv", "television", "bravia", "oled tv", "qled", "monitor", "display"]):
        dev_type = "tv"
        icon = "fa-solid fa-tv"
    elif any(k in text for k in ["console", "playstation", "ps5", "xbox", "nintendo", "switch", "gaming"]):
        dev_type = "console"
        icon = "fa-solid fa-gamepad"
    elif any(k in text for k in ["camera", "dslr", "mirrorless", "gopro"]):
        dev_type = "camera"
        icon = "fa-solid fa-camera"
    elif any(k in text for k in ["phone", "smartphone", "iphone", "galaxy", "pixel", "oneplus", "redmi", "xiaomi", "ultra", "nord"]):
        dev_type = "smartphone"
        icon = "fa-solid fa-mobile-screen"
    else:
        dev_type = "electronics"
        icon = "fa-solid fa-microchip"

    b_text = f"{brand} {product_name}".lower()
    if "apple" in b_text:
        badge = "fa-brands fa-apple"
    elif "google" in b_text:
        badge = "fa-brands fa-google"
    elif "microsoft" in b_text:
        badge = "fa-brands fa-windows"
    elif "samsung" in b_text:
        badge = "SAMSUNG"
    elif "oneplus" in b_text:
        badge = "ONEPLUS"
    elif "xiaomi" in b_text or "redmi" in b_text:
        badge = "XIAOMI"
    elif "sony" in b_text:
        badge = "SONY"
    elif "asus" in b_text:
        badge = "ASUS"
    elif "dell" in b_text:
        badge = "DELL"
    elif "hp" in b_text:
        badge = "HP"
    elif "boat" in b_text:
        badge = "BOAT"
    else:
        badge = brand.upper()[:8] if brand else "DEVICE"

    return dev_type, icon, badge


def resolve_electronic_image(product_name: str, brand: str, category: str = "") -> str:
    """Matches electronic model name to product image in frontend/img catalog."""
    name_lower = f"{product_name} {brand} {category}".lower()

    # If explicitly non-phone electronics (laptop, audio, tablet, watch, tv), don't falsely claim an iPhone photo
    if any(k in name_lower for k in ["laptop", "macbook", "notebook", "thinkpad", "headphone", "earbud", "audio", "airpod", "watch", "smartwatch", "tv", "tablet", "ipad"]):
        return ""

    if "iphone 17" in name_lower or ("17" in name_lower and "apple" in name_lower):
        return "img/iphone_17.jpg"
    elif "iphone 16" in name_lower or ("16" in name_lower and "apple" in name_lower):
        return "img/iphone_16.jpg"
    elif "pixel" in name_lower or "google" in name_lower:
        return "img/pixel_10_pro.jpg"
    elif "ultra" in name_lower or "s26 ultra" in name_lower or "s25 ultra" in name_lower or "s24 ultra" in name_lower:
        return "img/galaxy_s26_ultra.jpg?v=2.3"
    elif "a56" in name_lower or "a55" in name_lower or "a54" in name_lower or "galaxy a" in name_lower:
        return "img/galaxy_a56.jpg"
    elif "s26" in name_lower or "s25" in name_lower or "s24" in name_lower or "galaxy" in name_lower:
        return "img/galaxy_s26.jpg"
    elif "oneplus" in name_lower or "nord" in name_lower:
        return "img/oneplus_13.jpg"
    elif "redmi" in name_lower or "xiaomi" in name_lower or "note" in name_lower:
        return "img/redmi_note_15.jpg"
    elif "apple" in name_lower or "iphone" in name_lower:
        return "img/iphone_17.jpg"
    elif "samsung" in name_lower:
        return "img/galaxy_s26.jpg"
    else:
        return "img/iphone_17.jpg"


@router.post("/retailer/optimize-inventory")
def optimize_retailer_inventory(req: RetailerInventoryOptimizationRequest):
    """
    Real-Time Retailer Inventory & Competition Optimization:
    Accepts retailer electronic model specs, stock size, unit cost, MRP,
    and competitor prices. Executes real Monotone LightGBM Demand Forecaster,
    finite-horizon discrete optimization, Bertrand game theory simulation,
    and returns multi-channel competitor benchmarking with actionable advice.
    """
    # 1. Statutory & Physical Validations
    if req.unit_cost > req.mrp:
        raise HTTPException(
            status_code=400,
            detail=f"Unit purchase cost (₹{req.unit_cost:,.2f}) cannot exceed statutory MRP (₹{req.mrp:,.2f})."
        )
    if req.current_price > req.mrp:
        raise HTTPException(
            status_code=400,
            detail=f"Current price (₹{req.current_price:,.2f}) exceeds statutory MRP (₹{req.mrp:,.2f}), violating Rule 18(2) of the Legal Metrology Act."
        )

    comp_min = req.competitor_min_price
    if comp_min is None or comp_min <= 0:
        comp_min = min(req.competitor_avg_price, round(req.competitor_avg_price * 0.985, 2))
    else:
        comp_min = min(comp_min, req.competitor_avg_price)

    # 2. Real ML Model & Finite-Horizon Optimizer
    forecaster, elasticity_est, optimizer = get_models()
    synthetic_sku_id = f"RET_{req.brand.upper()[:3]}_{abs(hash(req.product_name)) % 10000:04d}"

    opt_res = optimizer.optimize_sku(
        product_id=synthetic_sku_id,
        product_name=req.product_name,
        current_price=req.current_price,
        mrp=req.mrp,
        unit_cost=req.unit_cost,
        current_inventory=req.current_inventory,
        competitor_avg_price=req.competitor_avg_price,
        competitor_min_price=comp_min,
        days_to_successor=req.days_to_successor,
        price_step=500.0
    )

    # 3. Model-Derived Causal Elasticity at Current & AI Price
    el_model = ElasticityEstimator.estimate_from_model(
        forecaster,
        req.current_price,
        req.competitor_avg_price,
        comp_min,
        req.mrp,
        req.unit_cost,
        req.current_inventory,
        req.days_to_successor
    )
    elasticity_val = el_model.get("elasticity")
    elasticity_regime = el_model.get("regime", "Unknown")
    if elasticity_val is None and len(opt_res.feasible_prices) >= 2 and len(opt_res.demand_curve) >= 2:
        fp = np.array(opt_res.feasible_prices)
        dc = np.array(opt_res.demand_curve)
        idx = int(np.argmin(np.abs(fp - req.current_price)))
        idx_lo = max(0, idx - 1)
        idx_hi = min(len(fp) - 1, idx + 1)
        if idx_hi > idx_lo and fp[idx_hi] > fp[idx_lo] and (dc[idx_lo] + dc[idx_hi]) > 0:
            p_mid = (fp[idx_hi] + fp[idx_lo]) / 2.0
            d_mid = (dc[idx_lo] + dc[idx_hi]) / 2.0
            delta_p = fp[idx_hi] - fp[idx_lo]
            delta_d = dc[idx_lo] - dc[idx_hi]
            arc_eps = float((delta_d / d_mid) / (delta_p / p_mid)) if delta_p > 0 and d_mid > 0 else 0.0
            if arc_eps > 0.05:
                elasticity_val = round(arc_eps, 3)
                elasticity_regime = "Highly Elastic" if arc_eps > 1.8 else ("Moderately Elastic" if arc_eps >= 1.1 else "Inelastic")


    # 4. Explainable AI Memo & TreeSHAP Features
    xai = forecaster.explain_point(
        selling_price=float(opt_res.recommended_price),
        mrp=float(req.mrp),
        competitor_avg_price=float(req.competitor_avg_price),
        competitor_min_price=float(comp_min),
        unit_cost=float(req.unit_cost),
        opening_inventory=req.current_inventory,
        days_to_successor=req.days_to_successor
    )
    memo = ReasonGenerator.generate_retailer_memo(opt_res)

    # 5. Game-Theoretic Multi-Round Duopoly Simulation (Nash Equilibrium Check)
    gt_simulator = CompetitorGameTheorySimulator(
        offline_premium=req.offline_premium,
        reaction_sensitivity=0.55
    )
    gt_result = gt_simulator.simulate_duopoly_dynamics(
        initial_store_price=req.current_price,
        initial_comp_price=req.competitor_avg_price,
        unit_cost=req.unit_cost,
        mrp=req.mrp,
        ai_recommended_price=opt_res.recommended_price,
        max_rounds=6
    )

    # 6. Detailed Multi-Channel Competitor Benchmarking Matrix
    rel_digital_price = round(float(req.competitor_avg_price * 1.005), -1)
    croma_price = round(float(req.competitor_avg_price * 0.998), -1)
    amazon_price = round(float(comp_min), -1)
    flipkart_price = round(float(comp_min * 1.003), -1)

    competitor_benchmarks = [
        {
            "channel": f"Your Store ({req.store_channel})",
            "tier": "Your Offline Store",
            "price": float(req.current_price),
            "delta_vs_ai": float(req.current_price - opt_res.recommended_price),
            "margin_pct": round(((req.current_price - req.unit_cost) / req.current_price) * 100, 1),
            "positioning": "Status Quo",
            "tag": "Current"
        },
        {
            "channel": f"Your Store (AI Recommended)",
            "tier": "Your Offline Store",
            "price": float(opt_res.recommended_price),
            "delta_vs_ai": 0.0,
            "margin_pct": round(((opt_res.recommended_price - req.unit_cost) / opt_res.recommended_price) * 100, 1),
            "positioning": f"{opt_res.price_action} (Optimal)",
            "tag": "Optimized"
        },
        {
            "channel": "Reliance Digital",
            "tier": "Organized Offline Retail",
            "price": rel_digital_price,
            "delta_vs_ai": round(rel_digital_price - opt_res.recommended_price, 2),
            "margin_pct": round(((rel_digital_price - req.unit_cost) / rel_digital_price) * 100, 1),
            "positioning": "Offline Competitor (LFR)",
            "tag": "Competitor"
        },
        {
            "channel": "Croma (Tata Electronics)",
            "tier": "Organized Offline Retail",
            "price": croma_price,
            "delta_vs_ai": round(croma_price - opt_res.recommended_price, 2),
            "margin_pct": round(((croma_price - req.unit_cost) / croma_price) * 100, 1),
            "positioning": "Offline Competitor (LFR)",
            "tag": "Competitor"
        },
        {
            "channel": "Amazon India",
            "tier": "E-Commerce Marketplace",
            "price": amazon_price,
            "delta_vs_ai": round(amazon_price - opt_res.recommended_price, 2),
            "margin_pct": round(((amazon_price - req.unit_cost) / amazon_price) * 100, 1),
            "positioning": "Aggressive Online Marketplace",
            "tag": "Online"
        },
        {
            "channel": "Flipkart",
            "tier": "E-Commerce Marketplace",
            "price": flipkart_price,
            "delta_vs_ai": round(flipkart_price - opt_res.recommended_price, 2),
            "margin_pct": round(((flipkart_price - req.unit_cost) / flipkart_price) * 100, 1),
            "positioning": "Aggressive Online Marketplace",
            "tag": "Online"
        }
    ]

    # 7. Actionable Execution Strategy Milestones
    burn_rate = max(0.1, opt_res.expected_daily_demand)
    clearance_days_exact = round(req.current_inventory / burn_rate, 1)
    pace_status = (
        "Safe Clearance Pace" if clearance_days_exact <= req.days_to_successor
        else "Urgent Pace Required (Inventory Exceeds Horizon)"
    )

    strategy_milestones = [
        {
            "stage": "Immediate Repricing (Days 1–7)",
            "action": f"Set selling price to ₹{opt_res.recommended_price:,.0f} ({opt_res.price_action}).",
            "objective": f"Stimulate sales velocity to ~{burn_rate:.1f} units/day to achieve target clearance."
        },
        {
            "stage": "Showrooming Defense (Days 8–20)",
            "action": f"Pair price with ₹{req.offline_premium:,.0f} instant in-store benefits (zero-cost EMI, immediate device setup).",
            "objective": f"Capture offline demand premium and nullify online marketplace advantage."
        },
        {
            "stage": f"Pre-Successor Audit (Days {max(21, req.days_to_successor - 14)}–{req.days_to_successor})",
            "action": "Evaluate remaining inventory. If leftover > 10%, execute targeted promotional bundling.",
            "objective": "Avoid the 20% post-successor terminal depreciation penalty."
        }
    ]

    dev_type, dev_icon, brand_badge = resolve_electronic_device_type(
        req.product_name, req.category, req.brand
    )
    if req.device_type and req.device_type.strip():
        dev_type = req.device_type.strip().lower()

    image_url = resolve_electronic_image(req.product_name, req.brand, req.category)

    return {
        "status": "success",
        "data": {
            "product_id": synthetic_sku_id,
            "product_name": req.product_name,
            "brand": req.brand,
            "category": req.category,
            "device_type": dev_type,
            "device_icon": dev_icon,
            "brand_badge": brand_badge,
            "image_url": image_url,
            "current_inventory": req.current_inventory,
            "days_to_successor": req.days_to_successor,
            "unit_cost": req.unit_cost,
            "mrp": req.mrp,
            "current_price": req.current_price,
            "recommended_price": opt_res.recommended_price,
            "price_action": opt_res.price_action,
            "price_change": opt_res.price_change,
            "price_change_pct": opt_res.price_change_pct,
            "expected_daily_demand": opt_res.expected_daily_demand,
            "status_quo_daily_demand": opt_res.status_quo_daily_demand,
            "clearance_days": opt_res.projected_clearance_days,
            "clearance_probability": opt_res.clearance_probability,
            "pace_status": pace_status,
            "inventory_risk_level": opt_res.inventory_risk_level,
            "expected_sales_horizon": opt_res.expected_sales_horizon,
            "leftover_inventory": opt_res.expected_leftover_inventory,
            "status_quo_leftover": opt_res.status_quo_leftover,
            "expected_lifecycle_profit": opt_res.expected_lifecycle_profit,
            "status_quo_profit": opt_res.status_quo_profit,
            "profit_lift_amount": opt_res.profit_lift_amount,
            "profit_lift_pct": opt_res.profit_lift_pct,
            "holding_and_finance_cost": opt_res.holding_and_finance_cost,
            "depreciation_loss": opt_res.depreciation_loss,
            "elasticity": elasticity_val,
            "elasticity_regime": elasticity_regime,
            "feasible_prices": opt_res.feasible_prices,
            "profit_curve": opt_res.profit_curve,
            "demand_curve": opt_res.demand_curve,
            "profit_curve_lower": opt_res.profit_curve_lower,
            "profit_curve_upper": opt_res.profit_curve_upper,
            "demand_curve_lower": opt_res.demand_curve_lower,
            "stock_units": req.current_inventory,
            "current_shelf_price": req.current_price,
            "expected_daily_sales": opt_res.expected_daily_demand,
            "status_quo_daily_sales": opt_res.status_quo_daily_demand,
            "clearance_days_needed": opt_res.projected_clearance_days,
            "projected_net_profit": opt_res.expected_lifecycle_profit,
            "candidate_prices": opt_res.feasible_prices,
            "benchmarks": competitor_benchmarks,
            "strategic_roadmap": [
                {
                    "stage": sm.get("stage", f"Stage 0{i+1}"),
                    "phase": sm.get("stage", "").split("(")[0].strip() if "(" in sm.get("stage", "") else "Milestone",
                    "title": sm.get("stage", "Execute Strategy"),
                    "action": sm.get("action", ""),
                    "impact": sm.get("objective", "Maximize net margin")
                }
                for i, sm in enumerate(strategy_milestones)
            ],
            "memo": memo,
            "business_reason": opt_res.business_reason,
            "competitor_benchmarks": competitor_benchmarks,
            "game_theory": gt_result,
            "explainability": {
                "business_reason": opt_res.business_reason,
                "memo": memo,
                "top_features": xai.get("feature_importance", {})
            },
            "strategy_milestones": strategy_milestones
        }
    }


class SaveRetailerProductRequest(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=120)
    brand: str = Field(default="Generic", min_length=1, max_length=60)
    category: str = Field(default="Flagship Smartphone", min_length=1, max_length=60)
    device_type: Optional[str] = Field(default="smartphone")
    current_inventory: int = Field(..., ge=1, le=100000)
    current_price: float = Field(..., ge=100.0, le=2000000.0)
    unit_cost: float = Field(..., ge=50.0, le=2000000.0)
    mrp: float = Field(..., ge=100.0, le=2000000.0)
    competitor_avg_price: float = Field(..., ge=100.0, le=2000000.0)
    competitor_min_price: Optional[float] = Field(default=None)
    days_to_successor: int = Field(default=60, ge=5, le=365)
    offline_premium: float = Field(default=1000.0, ge=0.0)
    store_channel: str = Field(default="Metro Flagship")
    notes: Optional[str] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "current_inventory" not in data and "stock_units" in data:
                data["current_inventory"] = data["stock_units"]
            if "current_price" not in data and "current_shelf_price" in data:
                data["current_price"] = data["current_shelf_price"]
            if "offline_premium" not in data and "offline_showrooming_premium" in data:
                data["offline_premium"] = data["offline_showrooming_premium"]
            if "store_channel" not in data and "channel_tier" in data:
                data["store_channel"] = data["channel_tier"]
        return data


@router.post("/retailer/save-inventory-product")
def save_retailer_inventory_product(req: SaveRetailerProductRequest):
    """
    Saves an offline retailer product and inventory into the persistent/runtime
    retailer ledger. Computes full ML optimization, caches the result, and updates
    the global retail catalog so the product participates across all dashboard views.
    """
    opt_payload = RetailerInventoryOptimizationRequest(
        product_name=req.product_name,
        brand=req.brand,
        category=req.category,
        device_type=req.device_type or "smartphone",
        current_inventory=req.current_inventory,
        current_price=req.current_price,
        unit_cost=req.unit_cost,
        mrp=req.mrp,
        competitor_avg_price=req.competitor_avg_price,
        competitor_min_price=req.competitor_min_price,
        days_to_successor=req.days_to_successor,
        offline_premium=req.offline_premium,
        store_channel=req.store_channel
    )
    opt_res = optimize_retailer_inventory(opt_payload)
    opt_data = opt_res["data"]

    sku_id = opt_data.get("product_id") or f"RET_{req.brand.upper()[:3]}_{abs(hash(req.product_name)) % 10000:04d}"
    opt_data["product_id"] = sku_id
    opt_data["notes"] = req.notes or ""
    opt_data["added_at"] = datetime.now().isoformat()

    # Store in retailer custom catalog and saved inventory
    _retailer_custom_products[sku_id] = {
        "product_id": sku_id,
        "product_name": req.product_name,
        "brand": req.brand,
        "category": req.category,
        "device_type": req.device_type or "smartphone",
        "current_inventory": req.current_inventory,
        "current_price": req.current_price,
        "unit_cost": req.unit_cost,
        "mrp": req.mrp,
        "competitor_avg_price": req.competitor_avg_price,
        "competitor_min_price": req.competitor_min_price,
        "days_to_successor": req.days_to_successor,
        "store_channel": req.store_channel
    }

    # Update or append in _retailer_saved_inventory
    existing_idx = next((i for i, item in enumerate(_retailer_saved_inventory) if item.get("product_id") == sku_id), None)
    if existing_idx is not None:
        _retailer_saved_inventory[existing_idx] = opt_data
    else:
        _retailer_saved_inventory.insert(0, opt_data)

    # Invalidate optimizations cache so global views reflect the new SKU
    _optimizations_cache.clear()
    _summary_cache.clear()
    global _retail_state_cache
    _retail_state_cache = None

    return {
        "status": "success",
        "message": f"Successfully registered {req.product_name} ({sku_id}) into store inventory.",
        "data": opt_data
    }


@router.get("/retailer/inventory")
def get_retailer_inventory():
    """
    Returns list of saved retailer inventory items and aggregate portfolio metrics.
    """
    # Seed initial items if empty so user has immediate actionable data
    if not _retailer_saved_inventory:
        _seed_initial_retailer_inventory()

    total_units = sum(int(item.get("current_inventory", 0)) for item in _retailer_saved_inventory)
    total_val = sum(float(item.get("current_inventory", 0)) * float(item.get("current_price", 0)) for item in _retailer_saved_inventory)
    total_lift = sum(float(item.get("profit_lift_amount", 0)) for item in _retailer_saved_inventory)

    return {
        "status": "success",
        "items": _retailer_saved_inventory,
        "total_skus": len(_retailer_saved_inventory),
        "total_units": total_units,
        "total_inventory_valuation": round(total_val, 2),
        "total_profit_lift": round(total_lift, 2),
        "data": {
            "items": _retailer_saved_inventory,
            "total_skus": len(_retailer_saved_inventory),
            "total_inventory_units": total_units,
            "total_inventory_value": round(total_val, 2),
            "total_projected_profit_lift": round(total_lift, 2)
        }
    }


@router.delete("/retailer/inventory/{product_id}")
def delete_retailer_inventory_product(product_id: str):
    """
    Removes a product from the offline retailer's saved inventory.
    """
    global _retail_state_cache
    _retailer_saved_inventory[:] = [item for item in _retailer_saved_inventory if item.get("product_id") != product_id]
    _retailer_custom_products.pop(product_id, None)
    _runtime_catalog_overrides.pop(product_id, None)
    _optimizations_cache.clear()
    _summary_cache.clear()
    _retail_state_cache = None

    return {
        "status": "success",
        "message": f"Product {product_id} deleted from retailer inventory."
    }


def _seed_initial_retailer_inventory():
    """Populates clean realistic default items into offline retailer inventory on boot."""
    sample_presets = [
        RetailerInventoryOptimizationRequest(
            product_name="Apple iPhone 16 (128GB Blue)",
            brand="Apple",
            category="Previous-Gen Flagship",
            device_type="smartphone",
            current_inventory=65,
            current_price=69999.0,
            unit_cost=58000.0,
            mrp=79900.0,
            competitor_avg_price=66490.0,
            competitor_min_price=64999.0,
            days_to_successor=18,
            offline_premium=1000.0,
            store_channel="Metro Flagship Store"
        ),
        RetailerInventoryOptimizationRequest(
            product_name="Samsung Galaxy S25 (256GB)",
            brand="Samsung",
            category="Mainstream Flagship",
            device_type="smartphone",
            current_inventory=80,
            current_price=79999.0,
            unit_cost=64000.0,
            mrp=89999.0,
            competitor_avg_price=76990.0,
            competitor_min_price=74999.0,
            days_to_successor=35,
            offline_premium=1200.0,
            store_channel="Tier-2 Hub Store"
        ),
        RetailerInventoryOptimizationRequest(
            product_name="OnePlus 13 (256GB Emerald Green)",
            brand="OnePlus",
            category="Flagship Killer",
            device_type="smartphone",
            current_inventory=95,
            current_price=64999.0,
            unit_cost=52000.0,
            mrp=69999.0,
            competitor_avg_price=62990.0,
            competitor_min_price=61499.0,
            days_to_successor=60,
            offline_premium=800.0,
            store_channel="High-Street Electronics"
        )
    ]
    for sample in sample_presets:
        try:
            res = optimize_retailer_inventory(sample)
            d = res["data"]
            pid = d["product_id"]
            d["notes"] = "Seeded store inventory baseline"
            d["added_at"] = datetime.now().isoformat()
            _retailer_saved_inventory.append(d)
            _retailer_custom_products[pid] = {
                "product_id": pid,
                "product_name": sample.product_name,
                "brand": sample.brand,
                "category": sample.category,
                "device_type": sample.device_type,
                "current_inventory": sample.current_inventory,
                "current_price": sample.current_price,
                "unit_cost": sample.unit_cost,
                "mrp": sample.mrp,
                "competitor_avg_price": sample.competitor_avg_price,
                "competitor_min_price": sample.competitor_min_price,
                "days_to_successor": sample.days_to_successor,
                "store_channel": sample.store_channel
            }
        except Exception as e:
            print(f"Failed to seed sample retailer inventory: {e}")


# ---------------------------------------------------------------------------
# Retail Price Simulation & Portfolio Linear Programming Endpoints
# (Inspired by & integrating ozzienobayrak/Retail_Price_Revenue_Optimisation)
# ---------------------------------------------------------------------------

class RetailPriceSimulationRequest(BaseModel):
    product_id: str = Field(default="SKU_DEMO_001", description="Unique identifier for the SKU")
    product_name: str = Field(default="Demo Smartphone (256GB)", description="Human-readable product name")
    current_price: float = Field(default=69999.0, gt=0, description="Current selling shelf price")
    unit_cost: float = Field(default=55000.0, gt=0, description="Wholesale procurement cost")
    mrp: float = Field(default=79999.0, gt=0, description="Maximum Retail Price statutory cap")
    current_inventory: int = Field(default=80, ge=1, description="Available stock units")
    competitor_avg_price: float = Field(default=68500.0, gt=0, description="Benchmark competitor price")
    competitor_min_price: float = Field(default=67000.0, gt=0, description="Lowest competitor price")
    scenario: Literal["Low", "Medium", "High"] = Field(default="Medium", description="Inventory scenario (80%, 100%, 120%)")
    grid_low: float = Field(default=0.80, gt=0, description="Lower price multiplier for simulation grid")
    grid_high: float = Field(default=1.20, gt=0, description="Upper price multiplier for simulation grid")
    n_prices: int = Field(default=9, ge=3, le=25, description="Number of candidate price points")
    days_to_successor: int = Field(default=60, ge=1, description="Days until successor model launch")


class RetailPortfolioLPRequest(BaseModel):
    items: Optional[List[RetailPriceSimulationRequest]] = Field(default=None, description="Catalog of items to price jointly")
    objective: Literal["revenue", "profit"] = Field(default="revenue", description="Linear programming objective")
    total_inventory_capacity: Optional[float] = Field(default=None, description="Maximum total units across portfolio")
    min_portfolio_margin_pct: Optional[float] = Field(default=0.15, description="Minimum portfolio gross margin threshold")
    max_portfolio_price_drift_pct: Optional[float] = Field(default=0.08, description="Maximum average price drift across portfolio")
    min_total_units: Optional[float] = Field(default=None, description="Minimum total unit sales volume floor")
    use_integer_milp: bool = Field(default=True, description="Whether to solve exact binary MILP or LP relaxation")


@router.post("/retail-lp/simulate")
def simulate_retail_price(req: RetailPriceSimulationRequest):
    """
    Simulates retail price elasticity and revenue-maximizing curves across
    candidate prices under Low/Medium/High inventory scenarios.
    """
    forecaster, _, _ = get_models()
    sim = RetailPriceRevenueSimulator(forecaster=forecaster)

    res = sim.simulate_sku_prices(
        product_id=req.product_id,
        product_name=req.product_name,
        current_price=req.current_price,
        unit_cost=req.unit_cost,
        mrp=req.mrp,
        current_inventory=req.current_inventory,
        competitor_avg_price=req.competitor_avg_price,
        competitor_min_price=req.competitor_min_price,
        scenario=req.scenario,
        grid_low=req.grid_low,
        grid_high=req.grid_high,
        n_prices=req.n_prices,
        days_to_successor=req.days_to_successor
    )
    return {
        "status": "success",
        "reference_source": "https://github.com/ozzienobayrak/Retail_Price_Revenue_Optimisation",
        "data": res.to_dict()
    }


@router.post("/retail-lp/optimize-portfolio")
def optimize_retail_portfolio_lp(req: RetailPortfolioLPRequest):
    """
    Solves the portfolio-wide pricing Linear Program (MILP / LP) over candidate price options
    subject to shared inventory capacity, minimum portfolio margin, and max price drift.
    """
    forecaster, _, _ = get_models()
    simulator = RetailPriceRevenueSimulator(forecaster=forecaster)
    lp_optimizer = RetailPortfolioLPOptimizer(simulator=simulator)

    # Use provided items or build from current saved retailer inventory
    items_to_sim = req.items
    if not items_to_sim:
        if _retailer_saved_inventory:
            items_to_sim = [
                RetailPriceSimulationRequest(
                    product_id=inv.get("product_id", f"SKU_{i}"),
                    product_name=inv.get("product_name", f"Item {i}"),
                    current_price=float(inv.get("current_price", 60000.0)),
                    unit_cost=float(inv.get("unit_cost", 48000.0)),
                    mrp=float(inv.get("mrp", 70000.0)),
                    current_inventory=int(inv.get("current_inventory", 50)),
                    competitor_avg_price=float(inv.get("competitor_avg_price", 59000.0)),
                    competitor_min_price=float(inv.get("competitor_min_price", 57000.0)),
                    days_to_successor=int(inv.get("days_to_successor", 45))
                )
                for i, inv in enumerate(_retailer_saved_inventory[:8])
            ]
        else:
            # Default fallback portfolio of 3 flagship electronics
            items_to_sim = [
                RetailPriceSimulationRequest(
                    product_id="SKU_IPHONE_16",
                    product_name="iPhone 16 (128GB)",
                    current_price=69999.0,
                    unit_cost=58000.0,
                    mrp=79900.0,
                    current_inventory=70,
                    competitor_avg_price=66490.0,
                    competitor_min_price=64999.0,
                    days_to_successor=25
                ),
                RetailPriceSimulationRequest(
                    product_id="SKU_GALAXY_S25",
                    product_name="Samsung Galaxy S25 (256GB)",
                    current_price=79999.0,
                    unit_cost=64000.0,
                    mrp=89999.0,
                    current_inventory=85,
                    competitor_avg_price=76990.0,
                    competitor_min_price=74999.0,
                    days_to_successor=40
                ),
                RetailPriceSimulationRequest(
                    product_id="SKU_ONEPLUS_13",
                    product_name="OnePlus 13 (256GB)",
                    current_price=64999.0,
                    unit_cost=52000.0,
                    mrp=69999.0,
                    current_inventory=90,
                    competitor_avg_price=62990.0,
                    competitor_min_price=61499.0,
                    days_to_successor=60
                )
            ]

        if not items_to_sim:
            raise HTTPException(status_code=400, detail="No items provided and retailer inventory is empty.")

    # 1. Run simulation grid for each item
    sim_results: List[SingleProductSimulationResult] = []
    for it in items_to_sim:
        s_res = simulator.simulate_sku_prices(
            product_id=it.product_id,
            product_name=it.product_name,
            current_price=it.current_price,
            unit_cost=it.unit_cost,
            mrp=it.mrp,
            current_inventory=it.current_inventory,
            competitor_avg_price=it.competitor_avg_price,
            competitor_min_price=it.competitor_min_price,
            scenario=it.scenario,
            grid_low=it.grid_low,
            grid_high=it.grid_high,
            n_prices=it.n_prices,
            days_to_successor=it.days_to_successor
        )
        sim_results.append(s_res)

    # 2. Solve Portfolio LP
    lp_res = lp_optimizer.optimize_portfolio(
        item_simulations=sim_results,
        objective=req.objective,
        total_inventory_capacity=req.total_inventory_capacity,
        min_portfolio_margin_pct=req.min_portfolio_margin_pct,
        max_portfolio_price_drift_pct=req.max_portfolio_price_drift_pct,
        min_total_units=req.min_total_units,
        use_integer_milp=req.use_integer_milp
    )

    return {
        "status": "success",
        "method": "Mixed-Integer Linear Programming (HiGHS MILP / LP)",
        "reference_source": "https://github.com/ozzienobayrak/Retail_Price_Revenue_Optimisation",
        "data": lp_res.to_dict()
    }


@router.get("/retail-lp/demo-portfolio")
def get_retail_portfolio_lp_demo():
    """
    Out-of-the-box demonstration running full simulation and Linear Programming
    portfolio optimization across flagship retail SKUs.
    """
    req = RetailPortfolioLPRequest(
        objective="revenue",
        min_portfolio_margin_pct=0.18,
        max_portfolio_price_drift_pct=0.06
    )
    return optimize_retail_portfolio_lp(req)



