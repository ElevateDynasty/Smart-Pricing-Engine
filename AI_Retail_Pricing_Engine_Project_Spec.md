# AI-Powered Dynamic Pricing & Inventory Optimization for Retailers
## Project Master Specification / Agent Handoff Document

**Document purpose:** This file is designed to be given to Codex, another coding agent, or a development team so the project can be understood without needing the previous conversation.

**Current recommended vertical:** Indian offline electronics retail, initially smartphones.

**Recommended project title:**
> **AI-Powered Dynamic Pricing and Inventory Optimization for Electronics Retail**

**Alternative product/startup name:**
> **AI Revenue Optimization Engine for Retailers**

---

# 1. Executive Summary

The project is an AI-powered pricing and inventory optimization system for retailers.

The system does **not** simply predict tomorrow's price and does **not** simply tell a retailer to give a discount.

Its core question is:

> **Given the retailer's current inventory, acquisition cost, current/competitor prices, sales velocity, demand, product lifecycle, and future market conditions, what selling price or pricing strategy maximizes expected total profit while keeping inventory risk under control?**

The first target market should be **offline electronics retailers in India**, especially smartphone retailers.

The initial use case is a retailer holding a large amount of an aging phone model while a successor model or major market event is approaching.

Example (illustrative, not tied to an actual launch date):

- SKU: Smartphone X
- Inventory: 800 units
- Retailer acquisition cost: ₹68,000/unit
- Current selling price: ₹79,999
- Competitor average: ₹77,999
- Expected successor launch: 60 days away
- Current sales velocity: 10/day

The system should estimate the demand curve at multiple feasible prices, estimate the risk/value of holding inventory, then recommend the price that maximizes expected lifecycle profit.

The important concept is:

> **Do not optimize today's unit margin in isolation. Optimize total expected profit over the remaining useful selling life of the inventory.**

---

# 2. The Business Problem

## 2.1 What happens to offline retailers

Offline electronics retailers compete with online marketplaces and other stores that customers can compare instantly.

A customer can physically inspect a smartphone at a shop and then compare the price with online competitors. This creates pricing pressure.

Current Indian smartphone research also shows that offline retail remains a major channel while online channels have substantial influence. Counterpoint's April 2026 online tracker reported a 40% online channel share for that month, while its broader retail audit tracks store-level selling prices, inventory, promotions, footfall and new-launch inquiries at 600+ multi-brand stores across 41 Indian cities. These observations show why a retailer-specific pricing system can use both local sales data and external market signals. [Source: Counterpoint Research, April 2026; Counterpoint Retail Audit, March 2026]

At the same time, electronics retailers can carry expensive inventory. If an older model loses market value after a new generation launches, the retailer has to decide whether to:

- hold price and accept slower sales,
- reduce price,
- run a promotion,
- bundle accessories/services,
- move inventory to another store,
- or take a lower margin to clear stock.

The retailer already knows that "discounting can clear stock." The harder problem is **how much, when, and for which SKU**.

---

# 3. Core Product Proposition

The product should be positioned as:

> **An AI revenue-management platform that helps retailers determine the optimal price for each SKU based on demand, competition, inventory, product lifecycle and business constraints.**

A stronger commercial statement:

> **Compete with online prices without giving away unnecessary margin, while reducing the risk of aging or stranded inventory.**

The system should be able to recommend:

- Increase price
- Keep price unchanged
- Reduce price slightly
- Reduce price aggressively
- Stop discounting
- Run a temporary promotion
- Move inventory to another store
- Prioritize certain SKUs for clearance

The AI must be allowed to conclude **"do not discount"** when that is economically optimal.

---

# 4. Target Market Options

## 4.1 Recommended first vertical: Smartphones

Why smartphones are strong:

- frequent price/promotional changes;
- many direct competitors;
- clear SKU/model structures;
- significant online/offline competition;
- costly inventory;
- strong product lifecycle effects;
- frequent new model launches;
- readily understandable use case;
- retailer POS/billing data can be structured as transactions.

Counterpoint's 2026 retail-audit material is particularly relevant because it explicitly tracks store-level selling prices, inventory levels, promotions, footfall, inquiries about new launches and retailer/store characteristics across hundreds of multi-brand outlets in India.

## 4.2 Laptops

Very strong second vertical.

Additional useful features include:

- CPU generation;
- GPU;
- RAM/SSD;
- component cost movements;
- model refreshes;
- student/gaming seasons;
- currency effects.

## 4.3 Fashion

Potentially the strongest non-electronics vertical.

The problem becomes:

> "What markdown path maximizes profit while clearing seasonal/aging inventory?"

Fashion adds:

- seasonality;
- trends;
- size-level demand;
- collection lifecycle;
- end-of-season sales;
- overstock;
- store transfers.

An Indian apparel survey reported that nearly 40% of clothing products sold on discount/EOSS were associated with mismatch between planned inventory and actual sales, and industry commentary described discounting as a significant margin drain. This supports the business case for better inventory and markdown optimization. [Source: Economic Times, Feb 27, 2025; article citing Vector Consulting Group/NielsenIQ]

## 4.4 Fresh fruits and vegetables

Strongest for raw price volatility and perishability.

Useful factors:

- wholesale/mandi prices;
- weather;
- supply/arrivals;
- local demand;
- shelf life;
- quality;
- wastage.

Main difficulty: retailer-level data and quality standardization.

## 4.5 Other possible verticals

- TVs
- Gaming hardware / GPUs
- Audio and wearables
- Air conditioners/refrigerators
- Automobiles
- Furniture
- Beauty/cosmetics
- Short-shelf-life food
- Hotels/travel (dynamic pricing, but less like physical-retail inventory)

---

# 5. Why Electronics vs Fashion

## Electronics

The system primarily solves:

> **Price optimization + product lifecycle + competitive pricing + expensive inventory risk**

Example:

800 phones with a successor model approaching.

## Fashion

The system primarily solves:

> **Markdown optimization + seasonality + size-level inventory + dead stock + store allocation**

Fashion may have a richer inventory problem, but smartphones provide a cleaner first MVP and an easier demo.

## Recommended strategy

Build the underlying engine as **vertical-neutral**, while implementing **smartphone retail first**.

Architecture should use generic fields such as:

- product_id
- category
- cost
- price
- inventory
- competitor_price
- demand
- lifecycle_end
- season_end
- constraints

Then later support fashion without rebuilding the optimization layer.

---

# 6. Offline Retailer Workflow

The system must work for a physical shop even if the retailer has no e-commerce website.

## MVP method

Retailer can provide:

- Excel/CSV upload;
- daily stock;
- daily sales;
- purchase cost;
- current price;
- product/MRP data.

The app calculates recommendations.

## More advanced methods

1. POS/ERP integration
2. Daily CSV import
3. Simple mobile app entry
4. API integration
5. Multi-store inventory integration

The retailer does not need to understand machine learning.

### Retailer-facing output

Example:

**iPhone 17 256GB**

- Inventory: 800
- Cost: ₹68,000
- Current price: ₹79,999
- Competitor average: ₹77,999
- Product lifecycle risk: High
- Expected clearance at current price: 80+ days

**AI recommendation: ₹77,499**

Expected impact:

- increased sales velocity;
- lower inventory exposure;
- better probability of clearing before the relevant lifecycle event;
- total profit estimate;
- confidence/risk score.

All numerical outputs in the example above are illustrative.

---

# 7. Core Input Data

## 7.1 Retailer transaction data

Minimum:

```text
date
store_id
product_id
selling_price
units_sold
inventory_end_of_day
discount
```

Preferred:

```text
customer_segment
payment_method
promotion_id
salesperson
return_flag
stock_in
stock_out
```

## 7.2 Product master

```text
product_id
brand
model
variant
storage
ram
color
category
launch_date
successor_model
successor_expected_date
MRP
```

## 7.3 Cost/inventory data

```text
purchase_cost
landed_cost
inventory_quantity
inventory_age
supplier
credit_terms
holding_cost
```

## 7.4 Competitor data

```text
date
product_id
competitor
competitor_price
promotion
availability
```

For a prototype, competitor prices can be manually entered or obtained through lawful data sources/APIs/datasets. Do not assume that unrestricted automated scraping of websites is permitted.

## 7.5 External signals

Possible inputs:

```text
day_of_week
month
festival
holiday
search_interest
new_launch_event
market_price_index
exchange_rate
promotion_period
```

Not every feature is required for MVP.

---

# 8. Important Constraint: MRP and Pricing Rules

For packaged commodities in India, the Department of Consumer Affairs states that a retail dealer cannot sell a packaged commodity above the retail sale price/MRP printed for it under the relevant Legal Metrology rules.

Therefore the engine must not blindly output an arbitrary price.

The optimization layer should use:

> **feasible price range = business constraints + applicable legal/pricing constraints**

For a packaged product, a practical MVP constraint is:

```text
minimum_allowed_price <= recommended_price <= applicable_MRP
```

The exact business/legal treatment can vary by product, packaging, promotions, bundling and channel, so the application should make constraints configurable and should not present itself as legal advice.

Sources:
- Department of Consumer Affairs FAQ on Legal Metrology / packaged commodities.
- Department of Consumer Affairs Consumer Handbook.

---

# 9. ML Problem

Do not build only a "price prediction" model.

The central ML task should be:

> **Predict demand as a function of price and context.**

Formally:

\[
D = f(P, C, I, S, L, T, M)
\]

Where:

- \(D\) = expected units sold
- \(P\) = retailer price
- \(C\) = competitor price/context
- \(I\) = inventory/stock state
- \(S\) = seasonality
- \(L\) = product lifecycle
- \(T\) = temporal factors
- \(M\) = market/promotion factors

---

# 10. Demand Elasticity

A central concept is **price elasticity of demand**.

The engine should learn how quantity changes when price changes.

For example:

| Price | Expected daily demand |
|---:|---:|
| ₹79,999 | 10 |
| ₹78,999 | 12 |
| ₹77,999 | 15 |
| ₹76,999 | 19 |
| ₹75,999 | 23 |

These are example values only.

The model does not need to assume a simple linear relationship.

Recommended initial models:

- Gradient Boosting / XGBoost
- LightGBM
- Random Forest as a baseline
- regularized regression baseline

Deep learning is not necessary for the first version.

---

# 11. Critical ML Warning: Causality

A major challenge is that historical data is observational.

Suppose a retailer sold 20 phones at ₹75,000.

That does not automatically mean:

> lowering price to ₹75,000 caused demand to be 20.

Other factors may have changed:

- festival;
- competitor stockout;
- advertising;
- launch event;
- season;
- local footfall.

Therefore the project should distinguish:

**prediction** from **causal price impact**.

A strong MVP can use historical variation and controlled price experiments to learn local price elasticity.

Later versions can investigate:

- causal inference;
- uplift modelling;
- Bayesian demand models;
- contextual bandits;
- experimentation frameworks.

Do not claim causal effects from a basic tree model without validation.

---

# 12. Profit Objective

The simplest expected profit equation is:

\[
Profit(P) = (P-C)\times D(P)
\]

where:

- \(P\) = selling price
- \(C\) = cost/unit
- \(D(P)\) = expected quantity sold

But this is not enough.

For electronics, add inventory/lifecycle effects:

\[
ExpectedProfit =
Revenue
- Cost
- HoldingCost
- FinancingCost
- ExpectedDepreciationLoss
- PromotionCost
\]

The exact terms should be configurable.

---

# 13. Lifecycle Optimization

This is the project's strongest differentiator.

The objective is not:

> "maximize today's margin."

It is:

> **"maximize expected profit over the product's remaining selling horizon."**

Example:

```text
Inventory = 800
Remaining horizon = 60 days
```

If current price sells 10/day:

```text
60 × 10 = 600 units
```

The retailer could end with ~200 units exposed to future price erosion.

A lower price may increase demand enough to clear the inventory earlier.

The engine should compare complete strategies rather than one day's profit.

---

# 14. Price Optimization

For each feasible price \(P\):

1. Predict demand.
2. Estimate inventory trajectory.
3. Estimate probability of clearance.
4. Estimate future inventory value.
5. Calculate expected profit.
6. Penalize risk/constraint violations.
7. Choose the best feasible price.

Pseudocode:

```python
best_price = None
best_objective = float("-inf")

for price in feasible_prices:
    demand = demand_model.predict(features_at(price))

    inventory_path = forecast_inventory(
        starting_inventory=current_inventory,
        predicted_demand=demand,
        horizon=remaining_horizon,
    )

    expected_profit = calculate_expected_profit(
        price=price,
        cost=unit_cost,
        demand=demand,
        inventory_path=inventory_path,
        lifecycle_risk=lifecycle_risk,
    )

    if expected_profit > best_objective:
        best_objective = expected_profit
        best_price = price
```

This is only the MVP optimizer. More advanced versions can use constrained nonlinear optimization or dynamic programming.

---

# 15. Dynamic Pricing Strategy

Do not restrict the engine to a single current price.

It should eventually generate a **pricing path**.

Illustrative example:

```text
Day 60–45: ₹78,999
Day 44–30: ₹77,999
Day 29–15: ₹75,999
Day 14–7:  ₹73,999
Day 6–0:   ₹70,999
```

These values are not pre-programmed and should not be hard-coded. The model/optimizer should produce them from the data and constraints.

The strategy should change when:

- demand changes;
- inventory falls;
- competitor changes price;
- successor date changes;
- market prices change;
- promotional periods begin.

---

# 16. The AI Should Sometimes Increase Price

This is essential.

A simplistic system might think:

> Old stock = discount.

That is wrong.

Example:

- old inventory;
- competitors out of stock;
- supply costs rise;
- product remains highly demanded;
- no close substitute is available.

The optimal action could be:

> **Keep price unchanged or increase it.**

Real-world Indian smartphone reporting in 2026 even described situations where retailers holding older stock benefited from market-wide price increases caused by memory-cost inflation.

This reinforces why the engine should optimize based on current and expected economics rather than apply a fixed "aging inventory = discount" rule.

---

# 17. Multi-Store Extension

If the retailer has multiple physical stores, pricing alone is not enough.

Example:

```text
Store A: 100 units, 8/day sales
Store B: 200 units, 2/day sales
Store C: 50 units, 10/day sales
```

The system could recommend:

> Transfer 80 units from B to C.

Then use store-specific prices if appropriate.

This creates a broader system:

> **Pricing + Inventory Allocation + Revenue Optimization**

Later optimization target:

\[
maximize\ total\ network\ profit
\]

subject to:

- store inventory;
- transfer capacity;
- transfer cost;
- store demand;
- pricing constraints;
- stock availability.

---

# 18. Online-vs-Offline Competitive Intelligence

One of the strongest use cases is helping offline retailers compete without automatically matching the cheapest online price.

Example:

```text
Amazon: ₹76,999
Flipkart: ₹77,499
Local competitor: ₹78,000
Your current price: ₹79,999
```

A basic price tracker would recommend:

> ₹76,999

The AI should instead ask:

> Does the retailer need to match ₹76,999 to achieve the required demand?

Maybe the retailer can sell at:

> ₹78,499

because of:

- local convenience;
- immediate availability;
- financing;
- trust;
- service/setup;
- geographic demand;
- customer relationships.

This is why the objective should be **profit optimization**, not "always be cheapest."

---

# 19. Recommended Dashboard

Build with **Streamlit** for MVP.

## Page 1: Overview

Show:

- total inventory value;
- SKUs at risk;
- projected profit;
- projected clearance rate;
- average recommended markdown;
- top pricing actions.

## Page 2: SKU Pricing

Example:

```text
Product: iPhone 17 256GB
Inventory: 800
Current price: ₹79,999
Cost: ₹68,000
Competitor avg: ₹77,999

AI RECOMMENDATION
₹77,499

Expected daily sales: 16
Expected clearance: 50 days
Risk: Medium
Expected profit: ₹...
```

## Page 3: Price Simulator

Retailer selects price.

System shows:

- predicted demand;
- expected revenue;
- expected profit;
- expected remaining inventory;
- clearance probability.

## Page 4: Inventory Risk

Show:

- aging stock;
- slow-moving SKUs;
- lifecycle risk;
- clearance deadline;
- projected leftover inventory.

## Page 5: Competitor Monitor

Show:

- current competitor prices;
- price gap;
- historical changes;
- alerts.

## Page 6: Explanation

AI should explain recommendations in plain language:

> "Your current price is producing too little sales velocity to clear 800 units within the remaining horizon. A ₹2,500 reduction is predicted to increase demand enough to improve total expected lifecycle profit."

---

# 20. Retailer Workflow

## Morning

Retailer opens app.

System displays:

```text
3 actions require attention

1. iPhone 17 → Reduce ₹1,000
2. Galaxy S26 → Maintain
3. Pixel 10 → Increase ₹500
```

## During the day

Data updates as sales happen.

## Evening

System recalculates:

- sales velocity;
- inventory;
- competitor movement;
- projected clearance;
- next recommendation.

## No software/POS integration case

Retailer can simply enter:

```text
Units sold today = 18
```

The MVP updates the forecast.

---

# 21. MVP Architecture

```text
                 RETAILER DATA
                      |
          +-----------+-----------+
          |                       |
        POS/CSV              Manual Entry
          |                       |
          +-----------+-----------+
                      |
                DATA PIPELINE
                      |
              FEATURE ENGINEERING
                      |
          +-----------+-----------+
          |                       |
          v                       v
  DEMAND FORECASTER        INVENTORY FORECAST
          |                       |
          +-----------+-----------+
                      |
               DEMAND CURVE
                      |
              PRICE OPTIMIZER
                      |
          +-----------+-----------+
          |                       |
    Recommended Price       Risk/Explanation
          |                       |
          +-----------+-----------+
                      |
                 WEB DASHBOARD
```

---

# 22. Suggested Tech Stack

## MVP

**Backend / ML**
- Python
- Pandas
- NumPy
- scikit-learn
- XGBoost or LightGBM

**Database**
- PostgreSQL
- SQLite for prototype

**Dashboard**
- Streamlit

**Visualization**
- Plotly
- Matplotlib

**API**
- FastAPI later

## Production direction

```text
React frontend
        |
FastAPI
        |
PostgreSQL
        |
ML service
        |
Scheduled data pipelines
```

Cloud platform can be chosen later.

---

# 23. Suggested Database Tables

## products

```text
product_id
brand
model
variant
category
mrp
launch_date
successor_model
successor_date
```

## stores

```text
store_id
city
state
store_type
```

## inventory

```text
date
store_id
product_id
opening_inventory
stock_in
units_sold
closing_inventory
inventory_age
```

## sales

```text
transaction_id
date
store_id
product_id
selling_price
units
discount
```

## competitors

```text
date
product_id
competitor
price
availability
promotion
```

## costs

```text
product_id
unit_cost
landed_cost
holding_cost
financing_cost
```

## recommendations

```text
timestamp
store_id
product_id
current_price
recommended_price
expected_demand
expected_profit
clearance_probability
reason
model_version
```

---

# 24. Dataset Strategy

There are three stages.

## Stage 1: Synthetic dataset

Create realistic historical transactions.

Example:

```text
180–365 days
50–200 SKUs
1–10 stores
daily sales
historical prices
competitor prices
inventory
launch dates
promotions
```

This allows the ML pipeline to be developed.

Important: clearly label synthetic data as synthetic.

## Stage 2: Public / lawful market data

Add:

- public price datasets;
- official price indices where relevant;
- publicly available market reports;
- lawful APIs;
- manually collected observations.

## Stage 3: Real retailer data

Partner with one local electronics retailer.

Request:

- daily/weekly sales;
- prices;
- stock;
- cost;
- promotions.

Anonymize all business data.

---

# 25. Model Development Plan

## Phase 1 — Baseline

Implement:

1. Historical moving-average demand.
2. Simple regression.
3. Basic profit calculation.
4. Brute-force price search.

Goal: prove end-to-end pipeline.

## Phase 2 — ML demand model

Use:

- XGBoost/LightGBM.

Features:

- price;
- competitor price;
- price gap;
- inventory;
- day/week/month;
- promotion;
- product age;
- days to successor;
- historical demand;
- store.

## Phase 3 — Lifecycle optimization

Add:

- future value;
- clearance probability;
- inventory risk;
- time horizon.

## Phase 4 — Multi-store optimization

Add:

- store-level demand;
- stock transfers;
- network profit.

## Phase 5 — Experimentation

Add controlled price tests.

---

# 26. Evaluation Metrics

Do not evaluate only with RMSE/MAE.

## Demand model

- MAE
- RMSE
- MAPE where appropriate
- calibration/error by SKU
- error by price range

## Pricing engine

Important business metrics:

- total profit;
- gross margin;
- revenue;
- inventory clearance time;
- leftover inventory;
- markdown percentage;
- stockout rate.

## Decision quality

Compare:

### Baseline A
Keep current price.

### Baseline B
Match lowest competitor.

### Baseline C
Fixed discount rule.

### AI
Optimized price.

The key result:

> **How much more profit / faster clearance / lower inventory risk does AI produce versus simple rules?**

---

# 27. The Best Demo

Use a single case that everyone immediately understands.

## Scenario

```text
Product: Smartphone X
Inventory: 800
Cost: ₹68,000
Current price: ₹79,999
Competitor average: ₹77,999
Sales velocity: 10/day
Relevant lifecycle event: 60 days away
```

The engine tests several prices.

Example output:

```text
₹79,999 → 10/day
₹78,999 → 12/day
₹77,999 → 15/day
₹76,999 → 19/day
₹75,999 → 23/day
```

Then the optimizer chooses the best strategy based on expected profit and inventory/lifecycle risk.

Show two paths:

### Without AI

```text
Keep price
↓
Slow sales
↓
Inventory remains
↓
Lifecycle event
↓
Future markdown / value loss
```

### With AI

```text
Forecast demand
↓
Optimize price
↓
Increase sales velocity
↓
Clear inventory in time
↓
Maximize lifecycle profit
```

The headline should be:

> **"We do not optimize the selling price of a product. We optimize the retailer's expected profit across the product's remaining lifecycle."**

---

# 28. What the Engine Should NOT Do

Do not build a simplistic rule engine such as:

```text
if inventory_high:
    discount = 20%
```

Do not hard-code:

```text
old_product -> discount
competitor_lower -> match_price
```

Do not assume:

```text
lower_price = higher_profit
```

Do not assume:

```text
older_product = less valuable
```

Do not claim that historical correlations automatically prove causal price effects.

Do not expose legal/compliance outputs as legal advice.

---

# 29. Important Business Insight

The retailer's real decision is not:

> "How much discount should I give?"

It is:

> **"What selling price maximizes expected total profit while satisfying inventory and market constraints?"**

A discount is merely one possible result.

The AI should be able to recommend:

- no discount;
- small discount;
- large discount;
- temporary promotion;
- hold price;
- increase price;
- transfer inventory.

---

# 30. Potential Advanced Features

After MVP:

## Demand elasticity by customer/store

Learn that the same product reacts differently in different locations.

## Personalized store-level pricing

Each shop gets its own learned demand curve.

## Multi-product substitution

If two phones are substitutes:

> lowering Phone A may reduce sales of Phone B.

The model should consider portfolio-level profit.

## Bundle optimization

Example:

> phone + case + charger + setup service.

Instead of lowering the phone price too much, the retailer may bundle value.

## Promotion optimization

Choose between:

- direct discount;
- cashback;
- accessory bundle;
- financing;
- loyalty offer.

## Reinforcement learning / contextual bandits

Only after a strong supervised-learning and experimentation foundation exists.

---

# 31. Startup Expansion Vision

Initial product:

> **Smartphone Pricing Copilot for Offline Retailers**

Expansion:

```text
Smartphones
   ↓
Laptops
   ↓
TVs
   ↓
Gaming hardware
   ↓
All consumer electronics
   ↓
Fashion
   ↓
General retail
```

Core platform:

> **Demand forecasting + inventory prediction + price optimization + competitive intelligence**

---

# 32. Proposed User Roles

## Retailer

Needs:

- today's prices;
- stock risk;
- expected profit;
- simple explanations.

## Store Manager

Needs:

- store comparison;
- target inventory;
- transfer recommendations.

## Business Owner

Needs:

- total profit impact;
- inventory turns;
- margin;
- ROI.

## Admin/Analyst

Needs:

- model performance;
- experiments;
- forecasts;
- data quality.

---

# 33. Suggested Project Modules

Recommended repository structure:

```text
ai-pricing-engine/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_demand_model.ipynb
│   ├── 03_elasticity.ipynb
│   └── 04_price_optimizer.ipynb
│
├── src/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── optimization/
│   ├── forecasting/
│   └── evaluation/
│
├── app/
│   ├── dashboard.py
│   └── components/
│
├── tests/
│
├── config/
│
├── docs/
│
├── requirements.txt
├── README.md
└── .env.example
```

---

# 34. First Development Milestone

The first usable version should do exactly this:

### Input

```text
product
inventory
cost
current_price
competitor_price
historical_sales
historical_prices
days_to_lifecycle_event
MRP
```

### Output

```text
recommended_price
expected_daily_demand
expected_revenue
expected_profit
expected_inventory_after_horizon
clearance_probability
explanation
```

### Dashboard

One SKU page is enough for the first working demo.

Do not start with 100 advanced features.

---

# 35. Agent Instructions

Any coding agent working on this project should preserve these principles:

1. **Optimize profit, not merely revenue.**
2. **Do not equate old inventory with automatic discounting.**
3. **Treat competitor price as a signal, not an automatic price target.**
4. **Include inventory and product lifecycle in the decision.**
5. **Keep legal/pricing constraints configurable.**
6. **Separate demand prediction from optimization.**
7. **Separate correlation from causal claims.**
8. **Make recommendations explainable to a retailer.**
9. **Use synthetic data honestly when real retailer data is unavailable.**
10. **Build smartphone retail first, but keep the architecture extensible to other verticals.**
11. **Do not use deep learning or reinforcement learning prematurely.**
12. **Evaluate the business outcome against simple pricing baselines.**

---

# 36. Current Project Definition

## Name

**AI-Powered Dynamic Pricing and Inventory Optimization for Electronics Retail**

## Initial market

**India**

## Initial customer

**Offline multi-brand smartphone/electronics retailer**

## Initial product

**Smartphones**

## Core problem

Offline retailers face online price competition and expensive inventory. They need to determine the best feasible selling price while considering current demand, competitor prices, inventory, product lifecycle and future value.

## Core AI capability

**Demand forecasting + price elasticity + constrained profit optimization**

## Primary output

**Recommended selling price**

## Secondary outputs

- expected demand;
- expected profit;
- expected inventory clearance;
- risk score;
- explanation;
- recommended future price path.

## Future expansion

- laptops;
- TVs;
- gaming hardware;
- other electronics;
- fashion;
- broader retail.

---

# 37. Recommended Final Pitch

> **"Offline retailers often know that they need to discount slow-moving electronics, but they don't know exactly when to discount, how much to discount, or whether discounting is even the most profitable decision. Our AI pricing engine combines demand forecasting, competitor pricing, inventory levels and product lifecycle risk to determine the optimal selling price for each SKU. Instead of simply maximizing today's margin or blindly matching online prices, it optimizes expected total profit while reducing the risk of inventory becoming difficult to sell."**

---

# 38. Evidence / Current Market Context

These sources were checked while preparing this specification. Because market conditions, channel shares and pricing conditions change, agents should re-check current figures before using them in a final presentation.

### Counterpoint Research — India Smartphone Bi-monthly Retail Audit, March 2026
Tracks sales data from 600+ multi-brand outlets in 41 Indian cities and includes store/model selling prices, inventory, promotions, footfall, launch inquiries and margins.

https://counterpointresearch.com/en/reports/India-Smartphone-Bi-monthly-Retail-Audit-Study-March-2026

### Counterpoint Research — India Online Smartphone Tracker, April 2026
Reported 40% online channel share for April 2026 and described price hikes, soft demand, promotions and pre-sale stocking.

https://counterpointresearch.com/en/reports/india-monthly-smartphone-model-tracker-online-channels-april-2026

### Counterpoint Research — India Smartphone Market Share, Q2 2026
Provides recent Indian smartphone market/channel context and notes the effect of memory-cost-driven price increases on demand.

https://counterpointresearch.com/en/insights/india-smartphone-share

### Economic Times — Smartphone inventory / discounts, 2025
Reported excess inventory concerns and stronger discount/incentive activity to move products.

https://economictimes.indiatimes.com/industry/cons-products/electronics/smartphone-companies-dial-up-discounts-new-models-to-boost-festive-sales/articleshow/123510829.cms

### Economic Times — Old smartphone stock and 2026 price increases
Described a 2026 situation where older smartphone inventory could benefit when broader market prices increased.

https://economictimes.indiatimes.com/industry/cons-products/electronics/old-stock-turns-gold-for-retailers-as-smartphone-prices-rise-amid-memory-cost-inflation/articleshow/131023396.cms

### Economic Times — Apparel inventory mismatch and discounting, 2025
Discussed inventory mismatch, forced apparel discounting, seasonal demand uncertainty and manual/reactive inventory adjustment.

https://economictimes.indiatimes.com/industry/cons-products/garments-/-textiles/apparel-discounts-are-often-forced-not-custom-made/articleshow/118586142.cms

### Department of Consumer Affairs — Legal Metrology FAQ
States that a packaged commodity cannot be sold above its stated retail sale price/MRP under the relevant rules.

https://consumeraffairs.nic.in/sites/default/files/file-uploads/latestnews/LM_FAQs.pdf

### Department of Consumer Affairs — Consumer Handbook
Provides the consumer-facing MRP explanation and states that retailers/dealers cannot sell packaged commodities above MRP.

https://consumeraffairs.nic.in/sites/default/files/file-uploads/consumer_information/Consumer%20Handbook.pdf

---

# 39. One-Sentence Mental Model for Future Agents

> **Build an explainable AI system that learns how price affects demand, forecasts how inventory will evolve, accounts for competitor pricing and product lifecycle, and chooses the feasible price strategy that maximizes the retailer's expected total profit.**
