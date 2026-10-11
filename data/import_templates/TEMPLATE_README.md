# Real-Data Import Templates for ApexPricing

Drop your own POS / ERP data into these 6 CSV files to run the AI pricing
engine on YOUR catalog instead of the demo simulation.

## How to plug in your data

1. Fill the 6 CSVs in this folder with your real data (same column names,
   same formats — see the guide below).
2. Copy the filled files over the demo files:
   `data/synthetic/products.csv`, `stores.csv`, `costs.csv`,
   `competitors.csv`, `sales.csv`, `inventory.csv`
   (or point `src/config.py` `SYNTHETIC_DATA_DIR` at this folder).
3. Retrain the demand model on your history:
   `python main.py --train`
4. Refresh the dashboard at `http://localhost:8000` and click
   **Recalculate Engine** — recommendations now come from your data.

## Column guide

### products.csv (one row per SKU)
- `product_id` — unique code, e.g. `SKU_IPHONE_17_256`
- `brand, model, variant` — display names
- `category, ram_gb, storage_gb, target_segment` — merchandising tags
- `mrp` — printed Maximum Retail Price (legal ceiling, hard-enforced)
- `launch_date` — YYYY-MM-DD the SKU went on sale
- `successor_model` — name of the next generation (for lifecycle urgency)
- `days_to_successor` — estimated days until successor launch (180+ if unknown)
- `base_elasticity` — your best guess of price sensitivity (1.0-3.0; refined by ML)
- `base_daily_demand` — typical units/day across all stores

### stores.csv (one row per branch)
- `store_id, store_name, city, state, tier`
- `footfall_index` — walk-in traffic vs average store (1.0 = average)
- `store_type` — free text

### costs.csv (one row per SKU)
- `unit_cost` — purchase price per unit (inclusive of taxes)
- `landed_cost` — unit_cost + freight + handling
- `daily_holding_cost_rate` — daily storage/insurance cost as fraction of unit value (0.0005 = 0.05%/day)
- `annual_financing_rate` — annual working-capital interest (0.12 = 12%)
- `post_successor_depreciation_rate` — value lost if stuck after successor launch (0.3 = 30%)

### competitors.csv (one row per competitor observation per day)
- `date` — YYYY-MM-DD
- `competitor` — e.g. "Amazon India", "Flipkart", "Croma"
- `competitor_price` — their selling price that day
- `availability` — "In Stock" or "Out of Stock" (drives stockout signal)
- `promotion_tag` — free text (e.g. "Deal of the Day")

### sales.csv (one row per transaction, or per store-SKU-day aggregate)
- `transaction_id` — unique; use a synthetic id for aggregates
- `date, store_id, product_id`
- `selling_price` — actual price charged per unit
- `units_sold` — quantity in this transaction
- `total_revenue` — selling_price x units_sold
- `discount_amount` — total discount given on this line
- `customer_segment, payment_method` — optional free text

### inventory.csv (one row per store-SKU per day — the engine's fuel)
- `date, store_id, product_id`
- `opening_inventory` — units at start of day
- `units_sold` — units sold that day
- `stock_in` — units received from supplier that day
- `closing_inventory` — opening - units_sold + stock_in
- `inventory_age_days` — days since this SKU arrived at the store

## Minimum data requirement
The demand model needs at least ~60 days of history. The more price
variation you have (markdowns, promos, price increases), the better the
model learns real price sensitivity — a flat price history cannot identify
elasticity (the engine will honestly say "Not Identifiable").
