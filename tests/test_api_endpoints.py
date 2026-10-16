"""
Regression tests for the FastAPI surface (api/routes/analytics.py).

These lock in the fixes made after the backend audit. Every test here failed (or
would have failed) against the pre-fix code:

  * inventory was hardcoded per SKU instead of read from inventory.csv (the old
    code reported 2315 units for a catalog that actually holds 541);
  * current_price was derived as competitor_avg * 1.015, ignoring observed sales;
  * a sold-out SKU still received a "Clearance Markdown" recommendation;
  * risk_counts/action_counts used a different vocabulary from the optimizer, so
    every declared bucket read 0 while the real counts sat in undeclared keys;
  * the kaggle summary served a stale active_events_count;
  * /api/simulate accepted negative prices and prices far above the legal MRP;
  * `req.inventory or 200` turned a legitimate inventory of 0 into 200;
  * the kaggle simulate path fabricated stats for a SKU it had never seen.

The suite deliberately avoids the network: it uses FastAPI's TestClient, which
exercises the same request handlers in-process.
"""
import json
from collections import Counter

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.config import SYNTHETIC_DATA_DIR

client = TestClient(app)


def _latest_inventory_csv() -> pd.Series:
    inv = pd.read_csv(SYNTHETIC_DATA_DIR / "inventory.csv")
    latest = inv[inv["date"] == inv["date"].max()]
    return latest.groupby("product_id")["closing_inventory"].sum()


def _latest_sales_prices() -> dict:
    sales = pd.read_csv(SYNTHETIC_DATA_DIR / "sales.csv")
    last = sales[sales["date"] == sales["date"].max()]
    return last.groupby("product_id")["selling_price"].median().to_dict()


# --------------------------------------------------------------------------
# KPI provenance: numbers must come from the data, not from literals
# --------------------------------------------------------------------------

def test_inventory_is_derived_from_inventory_csv():
    """Headline stock must equal the latest snapshot in inventory.csv."""
    resp = client.get("/api/optimizations")
    assert resp.status_code == 200
    rows = resp.json()["data"]
    csv_stock = _latest_inventory_csv()

    for row in rows:
        assert row["current_inventory"] == int(csv_stock[row["product_id"]]), (
            f"{row['product_id']} inventory {row['current_inventory']} "
            f"!= inventory.csv {csv_stock[row['product_id']]}"
        )

    summary = client.get("/api/summary").json()
    assert summary["total_inventory_units"] == int(csv_stock.sum())


def test_current_price_matches_observed_sales():
    """Shelf price must reflect the most recent real transactions."""
    rows = client.get("/api/optimizations").json()["data"]
    observed = _latest_sales_prices()

    for row in rows:
        pid = row["product_id"]
        if pid in observed:
            assert abs(row["current_price"] - observed[pid]) < 1.0, (
                f"{pid} price {row['current_price']} != observed {observed[pid]}"
            )


def test_sku_rows_report_data_provenance():
    """Each row states where its stock/price came from, so a fallback is visible."""
    for row in client.get("/api/optimizations").json()["data"]:
        assert row.get("inventory_source")
        assert row.get("current_price_source")


# --------------------------------------------------------------------------
# Sold-out SKUs must not receive a pricing recommendation
# --------------------------------------------------------------------------

def test_sold_out_sku_is_labelled_not_priced():
    rows = client.get("/api/optimizations").json()["data"]
    sold_out = [r for r in rows if r["current_inventory"] <= 0]
    assert sold_out, "fixture expectation: the catalog contains a sold-out SKU"

    for row in sold_out:
        assert row["price_action"] == "No Stock"
        assert row["inventory_risk_level"] == "Stockout"
        assert row["recommended_price"] == row["current_price"]
        assert row["profit_lift_amount"] == 0.0

        # The narrative memo must agree with the action. Previously the action was
        # relabelled but the memo still ordered a "clearance markdown" on zero stock,
        # and that text is what the UI renders in the explainability dialog.
        memo = row.get("memo") or {}
        headline = (memo.get("headline") or "").lower()
        rationale = (memo.get("key_rationale") or "").lower()
        assert "markdown" not in headline, f"phantom markdown order in memo: {headline}"
        assert "out of stock" in headline or "no action" in headline, headline
        assert "out of stock" in rationale or "zero units" in rationale, rationale


# --------------------------------------------------------------------------
# Summary aggregates must agree with the rows they summarise
# --------------------------------------------------------------------------

def test_summary_counts_match_sku_rows():
    rows = client.get("/api/optimizations").json()["data"]
    summary = client.get("/api/summary").json()

    assert summary["risk_counts"] == dict(Counter(r["inventory_risk_level"] for r in rows))
    assert summary["action_counts"] == dict(Counter(r["price_action"] for r in rows))
    assert sum(summary["risk_counts"].values()) == len(rows)


def test_profit_lift_pct_is_guarded_not_inverted():
    """A non-positive status-quo baseline must not yield a sign-flipped ratio."""
    summary = client.get("/api/summary").json()
    sq = summary["total_status_quo_profit"]
    pct = summary["avg_profit_lift_pct"]

    if sq > 0:
        assert pct is not None
        assert (pct > 0) == (summary["total_profit_lift"] > 0)
    else:
        assert pct is None


# --------------------------------------------------------------------------
# Lifecycle events: live state, both model sources, no disk writes
# --------------------------------------------------------------------------

def test_event_state_is_consistent_across_sources_and_csves_untouched():
    products_csv = SYNTHETIC_DATA_DIR / "products.csv"
    mtime_before = products_csv.stat().st_mtime_ns

    evt = client.post("/api/lifecycle-event", json={
        "product_id": "SKU_IPHONE_17_256",
        "successor_name": "Apple iPhone 18",
        "announcement_headline": "Apple Announces iPhone 18",
        "days_to_successor": 14,
    })
    assert evt.status_code == 200
    assert evt.json()["optimized_sku"]["days_to_successor"] == 14

    syn = client.get("/api/summary?model_source=synthetic").json()
    kag = client.get("/api/summary?model_source=kaggle").json()
    assert syn["active_events_count"] == 1
    # The kaggle summary used to serve a stale count after an event.
    assert kag["active_events_count"] == syn["active_events_count"]

    reset = client.post("/api/reset-events")
    assert reset.status_code == 200

    after = client.get("/api/summary").json()
    assert after["active_events_count"] == 0
    sku = next(r for r in client.get("/api/optimizations").json()["data"]
               if r["product_id"] == "SKU_IPHONE_17_256")
    assert sku["days_to_successor"] == 60, "reset must restore the baseline horizon"

    assert products_csv.stat().st_mtime_ns == mtime_before, \
        "no endpoint may ever write products.csv"


# --------------------------------------------------------------------------
# Request validation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad_body,label", [
    ({"product_id": "SKU_IPHONE_17_256", "price": -5000.0}, "negative price"),
    ({"product_id": "SKU_IPHONE_17_256", "price": 0.0}, "zero price"),
    ({"product_id": "SKU_IPHONE_17_256", "price": 79999.0, "inventory": -50}, "negative inventory"),
    ({"product_id": "SKU_IPHONE_17_256", "price": 79999.0, "days_to_successor": -10}, "negative horizon"),
    ({"product_id": "SKU_IPHONE_17_256", "price": 79999.0, "model_source": "garbage"}, "unknown source"),
])
def test_simulate_rejects_impossible_input(bad_body, label):
    assert client.post("/api/simulate", json=bad_body).status_code == 422, label


@pytest.mark.parametrize("days", [0, -5, 99999])
def test_lifecycle_event_rejects_impossible_horizon(days):
    resp = client.post("/api/lifecycle-event", json={
        "product_id": "SKU_IPHONE_17_256",
        "successor_name": "X",
        "announcement_headline": "Y",
        "days_to_successor": days,
    })
    assert resp.status_code == 422


def test_zero_inventory_is_respected_in_simulate():
    """`req.inventory or 200` silently turned a valid 0 into 200."""
    resp = client.post("/api/simulate", json={
        "product_id": "SKU_IPHONE_17_256", "price": 79999.0, "inventory": 0,
    })
    assert resp.status_code == 200
    assert resp.json()["expected_sales"] == 0


def test_simulate_clamps_to_the_legal_mrp_ceiling():
    """Selling above MRP is not a legal scenario, so it must not be priced as one."""
    resp = client.post("/api/simulate", json={
        "product_id": "SKU_IPHONE_17_256", "price": 999999.0,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["simulated_price"] <= body["mrp"]
    assert body["price_clamped_to_mrp"] is True


def test_kaggle_simulate_does_not_fabricate_unknown_sku():
    resp = client.post("/api/simulate", json={
        "product_id": "SKU_IPHONE_17_256", "price": 79999.0, "model_source": "kaggle",
    })
    assert resp.status_code == 404


# --------------------------------------------------------------------------
# Economic invariants must survive every recompute
# --------------------------------------------------------------------------

def test_economic_invariants_hold():
    rows = client.get("/api/optimizations").json()["data"]
    assert rows, "no SKU rows returned"

    for row in rows:
        prices, demand, profit = row["feasible_prices"], row["demand_curve"], row["profit_curve"]
        assert len(prices) == len(demand) == len(profit), f"{row['product_id']} curve length mismatch"

        # Law of Demand: demand must never rise as price rises.
        for i in range(1, len(demand)):
            assert demand[i] <= demand[i - 1] + 1e-9, f"{row['product_id']} non-monotonic at {i}"

        # The headline recommendation must be the argmax of the published curve.
        # NOTE: this assertion deliberately applies to EVERY row including sold-out ones.
        # An earlier version skipped "No Stock" rows, which hid the one row that violated
        # the invariant - the test passed while the claim was false.
        best = max(range(len(profit)), key=lambda i: profit[i])
        assert abs(prices[best] - row["recommended_price"]) < 1.0, (
            f"{row['product_id']}: argmax {prices[best]} != recommended {row['recommended_price']}"
        )

        # Cost floor and legal MRP ceiling apply to any actionable recommendation.
        if row["price_action"] != "No Stock":
            assert row["recommended_price"] >= row["unit_cost"] - 1e-6, f"{row['product_id']} below cost"
            assert row["recommended_price"] <= row["mrp"] + 1e-6, f"{row['product_id']} above MRP"


def test_query_param_model_source_is_validated():
    """GET endpoints must reject an unknown source, not silently coerce it."""
    for path in ("/api/summary", "/api/optimizations", "/api/optimizations/refresh"):
        assert client.get(f"{path}?model_source=garbage").status_code == 422, path
        assert client.get(f"{path}?model_source=kaggle").status_code == 200, path


def test_event_and_reset_paths_refresh_retail_state():
    """Event/reset must not serve a stale snapshot of the CSVs."""
    evt = client.post("/api/lifecycle-event", json={
        "product_id": "SKU_IPHONE_17_256",
        "successor_name": "Apple iPhone 18",
        "announcement_headline": "Apple Announces iPhone 18",
        "days_to_successor": 14,
    })
    assert evt.status_code == 200
    optimized = evt.json()["optimized_sku"]
    # Provenance fields are only present when retail state was freshly derived.
    assert "inventory_source" in optimized
    assert optimized["days_to_successor"] == 14

    reset = client.post("/api/reset-events")
    assert reset.status_code == 200
    restored = next(r for r in reset.json()["data"] if r["product_id"] == "SKU_IPHONE_17_256")
    assert restored["days_to_successor"] == 60


def test_only_one_simulation_request_schema_exists():
    """A duplicate class definition once shadowed the validated schema."""
    import api.routes.analytics as analytics
    import inspect
    src = inspect.getsource(analytics)
    assert src.count("class SimulationRequest") == 1
    assert src.count("class LifecycleEventRequest") == 1


def test_all_endpoints_respond():
    for method, path in [
        ("get", "/api/summary"),
        ("get", "/api/optimizations"),
        ("get", "/api/active-events"),
        ("get", "/api/transfers"),
        ("get", "/api/optimizations/refresh"),
        ("get", "/api/game-theory/simulate"),
        ("get", "/api/models/ablation"),
        ("post", "/api/reset-events"),
    ]:
        resp = getattr(client, method)(path)
        assert resp.status_code == 200, f"{method.upper()} {path} -> {resp.status_code}"


def test_game_theory_endpoint():
    resp = client.get("/api/game-theory/simulate?initial_store_price=79999&initial_comp_price=77999&unit_cost=68000&mrp=89900")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["is_converged"] is True
    assert data["stability_score"] >= 70.0
    assert "nash_store_price" in data


def test_models_ablation_endpoint():
    resp = client.get("/api/models/ablation")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 4
    architectures = [r["Model Architecture"] for r in data]
    assert any("Monotone" in a for a in architectures)


def test_retailer_inventory_optimization_endpoint():
    payload = {
        "product_name": "Apple iPhone 17 (256GB Midnight)",
        "brand": "Apple",
        "category": "Flagship Smartphone",
        "current_inventory": 800,
        "current_price": 79999.0,
        "unit_cost": 68000.0,
        "mrp": 89900.0,
        "competitor_avg_price": 77999.0,
        "competitor_min_price": 76999.0,
        "days_to_successor": 60,
        "offline_premium": 1000.0,
        "store_channel": "Metro Flagship Store"
    }
    resp = client.post("/api/retailer/optimize-inventory", json=payload)
    assert resp.status_code == 200, f"Error: {resp.text}"
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]

    # Verify real ML optimization outputs
    assert data["recommended_price"] <= 89900.0, "MRP ceiling must be respected"
    assert data["recommended_price"] >= 68000.0, "Must not sell below cost"
    assert data["profit_lift_amount"] >= 0, "AI optimization should achieve >= status quo"
    assert "image_url" in data and data["image_url"] == "img/iphone_17.jpg"
    assert len(data["competitor_benchmarks"]) == 6
    assert data["game_theory"]["is_converged"] is True
    assert len(data["strategy_milestones"]) == 3


def test_retailer_inventory_optimization_rejects_illegal_prices():
    # Cost > MRP
    bad_cost = {
        "product_name": "Test Device",
        "brand": "Generic",
        "current_inventory": 100,
        "current_price": 80000.0,
        "unit_cost": 95000.0,
        "mrp": 90000.0,
        "competitor_avg_price": 85000.0
    }
    resp = client.post("/api/retailer/optimize-inventory", json=bad_cost)
    assert resp.status_code == 400

    # Price > MRP
    bad_price = {
        "product_name": "Test Device",
        "brand": "Generic",
        "current_inventory": 100,
        "current_price": 95000.0,
        "unit_cost": 70000.0,
        "mrp": 90000.0,
        "competitor_avg_price": 85000.0
    }
    resp = client.post("/api/retailer/optimize-inventory", json=bad_price)
    assert resp.status_code == 400


def test_retailer_device_type_and_icons():
    # Test Laptop device classification
    laptop_payload = {
        "product_name": "Apple MacBook Air M3 (16GB 512GB)",
        "brand": "Apple",
        "category": "Ultrabook Laptop",
        "device_type": "laptop",
        "current_inventory": 30,
        "current_price": 124900.0,
        "unit_cost": 105000.0,
        "mrp": 134900.0,
        "competitor_avg_price": 121990.0
    }
    resp = client.post("/api/retailer/optimize-inventory", json=laptop_payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["device_type"] == "laptop"
    assert data["device_icon"] == "fa-solid fa-laptop"
    # Laptops shouldn't return smartphone phone images
    assert data["image_url"] == ""


def test_retailer_inventory_persistence_and_management():
    # 1. Fetch initial inventory (seeded items)
    get_resp = client.get("/api/retailer/inventory")
    assert get_resp.status_code == 200
    init_data = get_resp.json()["data"]
    assert "items" in init_data
    assert init_data["total_skus"] >= 1
    assert init_data["total_inventory_units"] > 0

    # 2. Save a new custom retailer SKU
    custom_product = {
        "product_name": "Sony WH-1000XM5 Wireless Headphones",
        "brand": "Sony",
        "category": "Audio / TWS",
        "device_type": "audio",
        "current_inventory": 45,
        "current_price": 28990.0,
        "unit_cost": 21000.0,
        "mrp": 34990.0,
        "competitor_avg_price": 27490.0,
        "days_to_successor": 90,
        "notes": "Premium noise cancelling inventory"
    }
    save_resp = client.post("/api/retailer/save-inventory-product", json=custom_product)
    assert save_resp.status_code == 200
    saved_item = save_resp.json()["data"]
    sku_id = saved_item["product_id"]
    assert sku_id.startswith("RET_")
    assert saved_item["device_type"] == "audio"
    assert saved_item["device_icon"] == "fa-solid fa-headphones"
    assert saved_item["recommended_price"] <= 34990.0
    assert saved_item["recommended_price"] >= 21000.0

    # 3. Verify it is present in GET /api/retailer/inventory
    list_resp = client.get("/api/retailer/inventory")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    matching = [it for it in items if it["product_id"] == sku_id]
    assert len(matching) == 1

    # 4. Verify delete
    del_resp = client.delete(f"/api/retailer/inventory/{sku_id}")
    assert del_resp.status_code == 200
    after_list = client.get("/api/retailer/inventory").json()["data"]["items"]
    assert not any(it["product_id"] == sku_id for it in after_list)


# --------------------------------------------------------------------------
# End-to-end Dynamic Elasticity Tests (Zero Static / Non-Zero / Identifiable)
# --------------------------------------------------------------------------

def test_end_to_end_elasticity_resolution_is_non_static_and_positive():
    """Verify that all portfolio SKUs serve genuine, non-zero, positive elasticity values."""
    resp = client.get("/api/optimizations/refresh")
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert len(rows) > 0

    valid_regimes = {"Highly Elastic", "Moderately Elastic", "Inelastic"}

    for r in rows:
        pid = r["product_id"]
        el = r.get("elasticity")
        regime = r.get("elasticity_regime")
        method = r.get("elasticity_method")

        assert el is not None, f"SKU {pid} has null elasticity"
        assert el > 0.05, f"SKU {pid} has static/zero/negative elasticity: {el}"
        assert str(el) != "-0.0", f"SKU {pid} returned -0.0"
        assert regime in valid_regimes, f"SKU {pid} has unrecognized regime: {regime}"
        assert method, f"SKU {pid} missing elasticity_method metadata"


def test_simulate_endpoint_computes_dynamic_point_elasticity():
    """Verify that /api/simulate dynamically calculates point elasticity across prices."""
    sim_lo = client.post("/api/simulate", json={
        "product_id": "SKU_IPHONE_17_256",
        "price": 74000.0
    }).json()

    sim_hi = client.post("/api/simulate", json={
        "product_id": "SKU_IPHONE_17_256",
        "price": 82000.0
    }).json()

    assert sim_lo.get("elasticity") is not None
    assert sim_hi.get("elasticity") is not None
    assert sim_lo["elasticity"] > 0.05
    assert sim_hi["elasticity"] > 0.05
    assert sim_lo["elasticity_regime"] in {"Highly Elastic", "Moderately Elastic", "Inelastic"}
    assert sim_hi["elasticity_regime"] in {"Highly Elastic", "Moderately Elastic", "Inelastic"}




