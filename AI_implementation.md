# 📊 AI Pricing Engine — Implementation & Training Tracker

> **File Purpose:** Living technical status document tracking all completed system changes, dataset download/ingestion states, model training intervals/runs, validation metrics, and pending roadmap items.

---

## 🚦 1. High-Level Executive Status

| Component | Status | Last Updated | Notes |
| :--- | :---: | :---: | :--- |
| **Synthetic Indian Retail Dataset** | 🟢 Ready / Generated | 2026-09-06 | 9,640 store-SKU daily records generated across 4 metro regions |
| **Kaggle Retail Price Dataset** | 🟢 Downloaded & Verified | 2026-09-06 | `suddharshan/retail-price-optimization` (676 records across 52 SKUs) |
| **Primary Demand Forecaster (LightGBM)**| 🟢 Trained & Saved | 2026-09-06 | Validation $R^2 = 0.932$, $MAE = 0.936$ units |
| **Price Elasticity Estimator** | 🟢 Trained & Computed | 2026-09-06 | Econometric log-log relative regressions fit across catalog |
| **Kaggle Demand Forecaster (LightGBM)** | 🟢 Trained & Saved | 2026-09-06 | Validation $R^2 = 0.456$, $MAE = 8.562$ units |
| **Lifecycle Profit Optimizer** | 🟢 Production Ready | 2026-09-06 | SciPy constrained solver + Legal Metrology MRP enforcement |
| **Multi-Store Inventory Balancer** | 🟢 Production Ready | 2026-09-06 | Transfer matrix evaluates velocity & ₹250 logistics unit cost |
| **Explainable AI (Reasoning Engine)** | 🟢 Production Ready | 2026-09-06 | Generates natural language retailer briefing memos |
| **Streamlit Interactive UI Dashboard** | 🟢 Production Ready | 2026-09-06 | 6 interactive web modules operational on port 8501 |
| **Pytest Automated Test Suite** | 🟢 Passing (12/12) | 2026-09-06 | Covers data pipelines, models, optimizer constraints, & Kaggle |
| **Git Repository & Security Rules** | 🟢 Synchronized | 2026-09-06 | Pushed to GitHub; zero API keys or credentials leaked |

---

## 💾 2. Dataset Ingestion & Preparation Status

| Dataset Name | Source / Slug | Download Status | Local Path | Records & Dimensions | Training Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **Indian Offline Electronics Dataset** | Internal Generator (`generate_synthetic_data.py`) | ✅ Generated | `data/synthetic/*.csv` (6 relational tables) | 9,640 daily store-SKU rows; 6 metro stores; 6 smartphone SKUs | ✅ Trained |
| **Kaggle Retail Price Optimization** | `suddharshan/retail-price-optimization` | ✅ Downloaded | `data/raw/retail_price.csv` | 676 monthly SKU rows; 52 SKUs; 9 product categories | ✅ Trained |
| **Flipkart Smartphones Market Dataset** | Kaggle (`dnyaneshyeole/flipkart-smartphones-dataset`) | ⏳ Pending | `data/raw/flipkart_smartphones.csv` | ~2,400 e-commerce listings with RAM/ROM/MRP attributes | ⏳ Ingestion Required |
| **Real POS / ERP Transaction Feeds** | Retailer ERP / CSV Drops | ⏳ Ready for drop-in | `data/raw/` | Drop CSVs matching schema in `data_pipeline.py` | ⏳ Pending Retailer Feed |

> [!NOTE]
> - `data/raw/` and `data/processed/` are strictly ignored in `.gitignore` to prevent raw data or private customer information from entering version control.
> - Sample synthetic tables remain in `data/synthetic/` so team members can run out-of-the-box demonstrations immediately after cloning.

---

## 🏋️ 3. Model Training Intervals & Execution Log

This log records every training interval, hyperparameter profile, dataset version, and performance evaluation.

| Interval # | Date / Timestamp | Model Type | Dataset | Hyperparameters / Setup | Validation MAE | Validation RMSE | Validation $R^2$ | Status | Artifact Location |
| :---: | :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **#1** | 2026-09-06 14:45 | `LGBMRegressor` | Unified Synthetic (13.2k rows) | `n_est=150, lr=0.05, leaves=31` | 0.852 units | 1.141 | 0.892 | ✅ Completed | `models_saved/demand_forecaster_lightgbm.joblib` |
| **#2** | 2026-09-06 15:14 | `LGBMRegressor` | Kaggle `retail_price.csv` (676 rows) | `n_est=160, lr=0.04, leaves=25, min_child=5` | 8.562 units | 12.149 | 0.456 | ✅ Completed | `models_saved/demand_forecaster_kaggle.joblib` |
| **#3** | 2026-09-06 15:15 | `LGBMRegressor` | Unified Synthetic (9.6k rows) | `n_est=150, lr=0.05, leaves=31` | 0.936 units | 2.096 | 0.932 | ✅ Completed | `models_saved/demand_forecaster_lightgbm.joblib` |
| **#4** *(Scheduled)* | *Upcoming* | `LGBMRegressor` + Monotonic | Indian Retail + Festive Flags | Retraining on extended 365-day seasonal cycle | — | — | — | ⏳ Pending | `models_saved/` |

---

## 📈 4. Econometric Price Elasticity Log

Log of price sensitivity estimations fit across catalog SKUs and retail categories:

### A. Indian Smartphone Catalog (Log-Log Relative Regression)
$$\ln(\text{Units} + 1) = \alpha - \beta \ln\left(\frac{P}{P_{\text{comp}}}\right) + \gamma \cdot \text{Weekend} + \epsilon$$

| SKU ID | Product Name | Elasticity ($\beta$) | Regime | $R^2$ Score | Pricing Strategy Guidance |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `SKU_IPHONE_17_256` | iPhone 17 (256GB) | **2.38** | Highly Elastic | 0.870 | High price sensitivity approaching successor; tactical markdown clears stock before obsolescence |
| `SKU_IPHONE_16_128` | iPhone 16 (128GB) | **2.80** | Highly Elastic | 0.966 | End-of-life clearance; aggressive discounting recommended to prevent total write-down |
| `SKU_PIXEL_10_PRO` | Pixel 10 Pro (256GB)| **0.85** | Inelastic | 0.265 | Competitors frequently out of stock; hold price or take +₹1,000 to +₹2,000 margin lift |
| `SKU_GALAXY_S26_256`| Galaxy S26 (256GB) | **1.75** | Moderately Elastic | 0.954 | Standard price responsiveness; maintain parity with Croma / Vijay Sales |
| `SKU_ONEPLUS_13_256`| OnePlus 13 (256GB) | **1.90** | Highly Elastic | 0.936 | Price-sensitive mid-flagship buyers; align with online festive flash sales |

### B. Kaggle Retail Benchmark Categories
| Category | Elasticity ($\beta$) | Regime | $R^2$ Score | Average Price | Strategy Guidance |
| :--- | :---: | :--- | :---: | :---: | :--- |
| `perfumery` | **0.88** | Inelastic | 0.21 | $89.35 | Brand-driven loyalty; maintain prices or test premium pricing |
| `cool_stuff` | **0.54** | Inelastic | 0.05 | $107.86 | Inelastic demand; price increases feasible without demand collapse |
| `garden_tools` | **0.47** | Inelastic | 0.13 | $80.09 | Utility purchasing; steady margins |
| `consoles_games` | **0.20** | Inelastic | 0.15 | $27.03 | Software/accessories driven; bundled pricing recommended |
| `computers_accessories` | **0.20** | Inelastic | 0.06 | $119.48 | Low sensitivity to minor price variance; focus on stock availability |

---

## 🛠️ 5. Inventory of Completed Implementations

### A. Core Architecture & Pipeline
- [x] **Relational Schema**: Generated 6 core relational CSV tables simulating Indian retail realities (`products`, `stores`, `costs`, `competitors`, `sales`, `inventory`).
- [x] **Data Pipeline** ([`src/data/data_pipeline.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/data/data_pipeline.py)): Automated merging and validation into `unified_retail_daily.parquet`.
- [x] **Feature Engineering** ([`src/data/feature_engineering.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/data/feature_engineering.py)): MRP ratios, competitor price deltas, days-to-successor countdowns, footfall index, and Indian festive seasonality (Diwali / Republic Day).
- [x] **Kaggle Pipeline** ([`src/data/kaggle_pipeline.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/data/kaggle_pipeline.py)): Automated Kaggle dataset downloader, cross-competitor aggregator, and LightGBM model trainer.

### B. Machine Learning & Econometrics
- [x] **LightGBM Demand Forecaster** ([`src/models/demand_forecaster.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/models/demand_forecaster.py)): Trained gradient-boosted demand predictor with monotonic price constraints and `.predict_point()` / `.predict_curve()` methods.
- [x] **Price Elasticity Estimator** ([`src/models/elasticity_estimator.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/models/elasticity_estimator.py)): Econometric relative log-log demand function solver.

### C. Optimization & Multi-Store Balancing
- [x] **Lifecycle Optimizer** ([`src/optimization/lifecycle_optimizer.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/optimization/lifecycle_optimizer.py)): Total lifecycle net profit objective solver accounting for carrying cost, finance rate, and post-successor depreciation penalties.
- [x] **Legal Metrology Constraint**: Strict mathematical upper bound $\text{Selling Price} \le \text{MRP}$ enforced at optimization boundary.
- [x] **Multi-Store Balancer** ([`src/optimization/multi_store_balancer.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/optimization/multi_store_balancer.py)): Generates inter-store branch inventory transfers whenever preserved margin exceeds the ₹250/unit physical logistics transfer cost.

### D. Explainability & Web UI Dashboard
- [x] **Reasoning Engine** ([`src/explainability/reason_generator.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/explainability/reason_generator.py)): Human-readable retailer briefings explaining unit economics trade-offs.
- [x] **Heuristic Benchmarker** ([`src/evaluation/baseline_benchmarking.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/evaluation/baseline_benchmarking.py)): Head-to-head comparison against Status Quo, Match Competitor, and 15% Markdown.
- [x] **Streamlit Web Dashboard** ([`dashboard/app.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/dashboard/app.py)): 6 interactive modules with dark theme CSS, Plotly charts, and real-time simulator sandboxes.

### E. Quality & Security
- [x] **Automated Testing** ([`tests/`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/tests)): 12/12 unit tests passing in pytest.
- [x] **Git & Credential Security** ([`.gitignore`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/.gitignore)): Total protection against leaked API tokens, `.env`, credentials, raw CSVs, and model binaries.
- [x] **Remote Repository**: Synchronized with `https://github.com/ElevateDynasty/Smart-Pricing-Engine`.

---

## 📋 6. Pending Requirements & Future Roadmap

| Priority | Feature / Work Item | Description | Prerequisites / Dependencies |
| :---: | :--- | :--- | :--- |
| **P1** | **Automated Retraining Scheduler** | Cron job or scheduled task to retrain LightGBM every 7 days as new POS data accumulates | Task scheduler or cron integration |
| **P1** | **E-Commerce Real-Time Scraper Adapter** | Lawful API connectors / scheduled price check for Amazon India & Flipkart competitor listings | Rotating IP / API keys (kept in `.env`) |
| **P2** | **Cross-SKU Cannibalization Matrix** | Estimate cross-price elasticity between memory variants (e.g., 128GB vs 256GB) to prevent internal margin dilution | Extended multi-product transaction dataset |
| **P2** | **Kaggle Flipkart Smartphone Pipeline** | Download and map `dnyaneshyeole/flipkart-smartphones-dataset` into Indian market reference catalog | Run `kaggle datasets download` |
| **P3** | **ERP / POS Connectors (Tally / Zoho)** | Direct database / REST API ingestion adapter for physical store billing software | POS database credentials / API endpoint |
| **P3** | **A/B Testing & Price Experimentation** | Dynamic price test harness allocating random traffic fractions across offline stores | Multi-store POS deployment |

---

## 🔄 7. Developer Guide: How to Update This File

Whenever you perform data generation, dataset downloads, or model training intervals:

1. **When downloading a new dataset**:
   - Update **Section 2 (Dataset Ingestion Status)**.
   - Record the source, download status, file location, and record count.
   - Set "Training Status" to `⏳ Training Required`.

2. **When running a model training interval**:
   - Run training via `python main.py --train` or `python main.py --kaggle`.
   - Update **Section 3 (Model Training Intervals & Execution Log)**:
     - Increment Interval number (`#4`, `#5`, etc.).
     - Record timestamp, dataset, hyperparameters, and achieved metrics ($MAE, RMSE, R^2$).
     - Update the status from `⏳ Pending` to `✅ Completed`.

3. **When implementing a roadmap item**:
   - Move the item from **Section 6 (Pending Requirements)** to **Section 5 (Completed Implementations)**.
   - Run `pytest tests/ -v` to ensure all tests pass.
   - Commit and push changes.
