# 📊 AI Pricing Engine — Implementation & Training Tracker

> **File Purpose:** Living technical status document tracking all completed system capabilities, dataset states, model training runs, validation metrics, and future research roadmap items.

---

## 🚦 1. High-Level Executive Status

| Component | Status | Last Updated | Notes |
| :--- | :---: | :---: | :--- |
| **Synthetic Indian Retail Dataset** | 🟢 Ready / Generated | 2026-10-15 | 9,640 store-SKU daily records generated across 4 metro regions |
| **Kaggle Retail Price Dataset** | 🟢 Downloaded & Verified | 2026-10-15 | `suddharshan/retail-price-optimization` (676 records across 52 SKUs) |
| **Primary Demand Forecaster (LightGBM)**| 🟢 Trained & Saved | 2026-10-15 | Monotone Law of Demand ($\partial \hat{D}/\partial P \le 0$), Conformal Bounds ($P_{10} - P_{90}$) |
| **Price Elasticity Estimator** | 🟢 Trained & Computed | 2026-10-15 | Econometric log-log relative regressions fit across catalog |
| **Kaggle Demand Forecaster (LightGBM)** | 🟢 Trained & Saved | 2026-10-15 | Validation $R^2 = 0.456$, $MAE = 8.562$ units (`demand_forecaster_kaggle.joblib`) |
| **Lifecycle Profit Optimizer** | 🟢 Production Ready | 2026-10-15 | SciPy constrained discrete lattice solver + Legal Metrology Rule 18(2) MRP cap |
| **Multi-Store Inventory Balancer** | 🟢 Production Ready | 2026-10-15 | Transportation LP transfer matrix evaluates store inventory velocities |
| **Explainable AI (Reasoning Engine)** | 🟢 Production Ready | 2026-10-15 | TreeSHAP feature contributions & natural language retailer briefing memos |
| **Competitor Game Theory Simulator** | 🟢 Production Ready | 2026-10-15 | Asymmetric Bertrand duopoly multi-round dynamics & price war avoidance |
| **Model Ablation Study Suite** | 🟢 Production Ready | 2026-10-15 | Benchmarks Monotone LightGBM, Unconstrained, RF, and OLS |
| **Causal 2SLS Elasticity Model** | 🟢 Production Ready | 2026-10-15 | Solves endogeneity via wholesale cost instrumental variables ($C_{\text{unit}}$) |
| **Downside Risk (VaR/CVaR-95)** | 🟢 Production Ready | 2026-10-15 | Quantifies 95% confidence downside revenue and profit risk |
| **Offline Retailer Hub & Onboarding Studio** | 🟢 Production Ready | 2026-10-15 | Custom SKU onboarding, ML optimization, live store ledger & portfolio KPIs |
| **Electronic Hardware Iconography Taxonomy** | 🟢 Production Ready | 2026-10-15 | Specialized vector hardware iconography & brand badges (zero emojis) |
| **Google Colab Training Pipeline** | 🟢 Production Ready | 2026-10-15 | Cloud training script (`scripts/train_colab.py`) & guide (`docs/google_colab_training_guide.md`) |
| **Streamlit Interactive UI Dashboard** | 🟢 Production Ready | 2026-10-15 | 6 interactive web modules operational on port 8501 |
| **FastAPI REST Delivery & Web UI** | 🟢 Production Ready | 2026-10-16 | Full REST API (`/api/*`), dark/light themes, live Chart.js response curves, dynamic elasticity telemetry |
| **Pytest Automated Test Suite** | 🟢 Passing (53/53) | 2026-10-16 | 100% test pass rate across data pipelines, models, optimizer, game theory, retailer API, and end-to-end dynamic elasticity |
| **Academic LaTeX Report & Deck** | 🟢 Compiled (40p PDF) | 2026-10-15 | Publication-grade report (`report/main.pdf`) & Gemini slides prompt |

---

## 💾 2. Dataset Ingestion & Preparation Status

| Dataset Name | Source / Slug | Download Status | Local Path | Records & Dimensions | Training Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **Indian Offline Electronics Dataset** | Internal Generator (`generate_synthetic_data.py`) | ✅ Generated | `data/synthetic/*.csv` (6 relational tables) | 9,640 daily store-SKU rows; 6 metro stores; 6 smartphone SKUs | ✅ Trained |
| **Kaggle Retail Price Optimization** | `suddharshan/retail-price-optimization` | ✅ Downloaded | `data/raw/retail_price.csv` | 676 monthly SKU rows; 52 SKUs; 9 product categories | ✅ Trained |
| **Real Retailer Store Ledger Feeds** | Retailer Hub Onboarding (`/api/retailer/*`) | ✅ Live Runtime | Memory / In-Memory State & CSV Drops | Custom SKU specs, stock units, shelf prices, competitor benchmarks | ✅ Active |

> [!NOTE]
> - `data/raw/` and `data/processed/` are strictly ignored in [`.gitignore`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/.gitignore) to prevent raw data or private retailer information from entering version control.
> - Sample synthetic tables remain in `data/synthetic/` so team members can run out-of-the-box demonstrations immediately after cloning.

---

## 🏋️ 3. Model Training Intervals & Execution Log

| Interval # | Date / Timestamp | Model Type | Dataset | Hyperparameters / Setup | Validation MAE | Validation RMSE | Validation $R^2$ | Status | Artifact Location |
| :---: | :---: | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **#1** | 2026-09-06 14:45 | `LGBMRegressor` | Unified Synthetic (13.2k rows) | `n_est=150, lr=0.05, leaves=31` | 0.852 units | 1.141 | 0.892 | ✅ Completed | `models_saved/demand_forecaster_lightgbm.joblib` |
| **#2** | 2026-09-06 15:14 | `LGBMRegressor` | Kaggle `retail_price.csv` (676 rows) | `n_est=160, lr=0.04, leaves=25, min_child=5` | 8.562 units | 12.149 | 0.456 | ✅ Completed | `models_saved/demand_forecaster_kaggle.joblib` |
| **#3** | 2026-09-06 15:15 | `LGBMRegressor` | Unified Synthetic (9.6k rows) | `n_est=150, lr=0.05, leaves=31` | 0.936 units | 2.096 | 0.932 | ✅ Completed | `models_saved/demand_forecaster_lightgbm.joblib` |
| **#4** | 2026-10-15 17:30 | Monotone `LGBMRegressor` + Conformal Bounds | Unified Synthetic (9.6k rows) | `n_est=300, lr=0.04, depth=6, monotone=True` | 0.812 units | 1.145 | 0.892 | ✅ Completed | `models_saved/demand_forecaster_lightgbm.joblib` |

---

## 📈 4. Econometric Price Elasticity Log

Log of price sensitivity estimations fit across catalog SKUs and retail categories:

### A. Indian Electronics Catalog (Log-Log Relative Regression)
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
- [x] **Relational Schema**: 6 core relational CSV tables simulating Indian retail realities (`products`, `stores`, `costs`, `competitors`, `sales`, `inventory`).
- [x] **Data Pipeline** ([`src/data/data_pipeline.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/data/data_pipeline.py)): Automated merging and validation into `unified_retail_daily.parquet`.
- [x] **Feature Engineering** ([`src/data/feature_engineering.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/data/feature_engineering.py)): MRP ratios, competitor price deltas, days-to-successor countdowns, footfall index, and Indian festive seasonality (Diwali / Republic Day).
- [x] **Kaggle Pipeline** ([`src/data/kaggle_pipeline.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/data/kaggle_pipeline.py)): Automated Kaggle dataset downloader, cross-competitor aggregator, and LightGBM model trainer.

### B. Machine Learning, Econometrics & Risk
- [x] **Monotone LightGBM Demand Forecaster** ([`src/models/demand_forecaster.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/models/demand_forecaster.py)): Enforces Law of Demand ($\partial \hat{D}/\partial P \le 0$) with calibrated Conformal Prediction uncertainty intervals ($P_{10} - P_{90}$).
- [x] **Price Elasticity Estimator** ([`src/models/elasticity_estimator.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/models/elasticity_estimator.py)): Dynamic multi-scale econometric log-log demand regression & adaptive finite-difference model-derived point elasticity solver.
- [x] **Two-Stage Least Squares (2SLS) Instrumental Variables**: Resolves simultaneity bias using acquisition cost $C_{\text{unit}}$ as an instrument to prove causal price sensitivity.
- [x] **Model Ablation Study Suite** ([`src/evaluation/model_ablation.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/evaluation/model_ablation.py)): Compares Monotone LightGBM vs Unconstrained LightGBM vs Random Forest vs OLS.
- [x] **Downside Financial Risk (VaR/CVaR-95)**: Incorporates empirical 95% Value-at-Risk and Conditional Value-at-Risk inside lifecycle optimization result objects.

### C. Constrained Optimization & Game Theory
- [x] **Lifecycle Optimizer** ([`src/optimization/lifecycle_optimizer.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/optimization/lifecycle_optimizer.py)): Total lifecycle net profit objective solver accounting for carrying cost, finance rate, and post-successor depreciation penalties.
- [x] **Legal Metrology Rule 18(2) Constraint**: Strict mathematical upper bound $\text{Selling Price} \le \text{MRP}$ enforced at optimization boundary.
- [x] **Multi-Store Balancer** ([`src/optimization/multi_store_balancer.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/optimization/multi_store_balancer.py)): Generates inter-store branch inventory transfers whenever preserved margin exceeds the physical logistics transfer cost.
- [x] **Competitor Game Theory Simulator** ([`src/optimization/competitor_game_theory.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/optimization/competitor_game_theory.py)): Asymmetric Bertrand duopoly multi-round reaction dynamics with contraction mapping proof ensuring stable Nash equilibrium.

### D. Offline Retailer Hub & Device Management
- [x] **Offline Retailer Studio & Store Ledger** ([`api/routes/analytics.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/api/routes/analytics.py), [`frontend/index.html`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/frontend/index.html)): Complete portal (`#view-retailer-portal`) allowing store retailers to input custom device models, stock units, wholesale costs, shelf prices, and successor horizons.
- [x] **Multi-Category Hardware Taxonomy**: Specialized iconography for smartphones, laptops, tablets, smartwatches, audio/TWS, smart TVs, gaming consoles, cameras, and peripherals with brand badges (zero generic emojis).
- [x] **Multi-Channel Competitor Benchmarking Matrix**: Comparative positioning matrix benchmarking against local organized retail (Reliance Digital, Croma) and e-commerce platforms (Amazon, Flipkart).
- [x] **3-Stage Actionable Retailer Playbook**: Automated generation of milestone roadmaps (Immediate In-Store Display, Mid-Cycle Velocity Review, Pre-Successor Audit).
- [x] **Live Store Ledger Integration**: Saved products seamlessly participate in the global store catalog, SKU Pricing Matrix, and Demand Simulator.

### E. Cloud Training, Dashboards & Automated Testing
- [x] **Google Colab Cloud Training Pipeline** ([`scripts/train_colab.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/scripts/train_colab.py), [`docs/google_colab_training_guide.md`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/docs/google_colab_training_guide.md)): 1-click cloud execution script and guide for training models in Google Colab and exporting `.joblib` weights.
- [x] **Reasoning Engine (TreeSHAP)** ([`src/explainability/reason_generator.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/src/explainability/reason_generator.py)): Human-readable retailer briefings explaining unit economics trade-offs.
- [x] **FastAPI Web Server & Static UI** ([`api/`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/api), [`frontend/`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/frontend)): Full REST API, dark/light theme engine, live Chart.js response curves, and keyboard navigation (`1-6`).
- [x] **Streamlit Web Dashboard** ([`dashboard/app.py`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/dashboard/app.py)): 6 interactive modules with dark theme CSS, Plotly charts, and real-time simulator sandboxes.
- [x] **Automated Testing Suite** ([`tests/`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/tests)): 53/53 unit and integration tests passing in pytest (100% pass rate).
- [x] **Academic LaTeX Report** ([`report/main.pdf`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/report/main.pdf)): 40-page publication-grade PDF compiled via MiKTeX with native vector TikZ diagrams and IEEEtran bibliography.

---

## 📋 6. Future Research Roadmap

| Priority | Feature / Research Item | Description | Dependencies |
| :---: | :--- | :--- | :--- |
| **P1** | **Automated Retraining Cron Daemon** | Standalone scheduled background cron job to retrain LightGBM every 7 days as new POS records accumulate | System cron / APScheduler |
| **P1** | **E-Commerce Real-Time Scraper Adapter** | Live API / scraping connectors for Amazon India & Flipkart competitor listings with proxy rotation | Scraper API credentials / `.env` |
| **P2** | **Cross-SKU Cannibalization Matrix** | Estimate cross-price substitution elasticity between storage/RAM variants (e.g., 128GB vs 256GB) to prevent internal margin dilution | Extended multi-variant transaction history |
| **P2** | **ERP / POS Connectors (Tally Prime & Zoho)** | Direct database / REST API ingestion bridge for physical store billing software | POS database credentials / API endpoint |
| **P3** | **Multi-Store Dynamic A/B Price Experimentation** | Dynamic price test harness allocating randomized traffic fractions across offline branches | Multi-store POS integration |

---

## 🔄 7. Developer Guide: How to Maintain This Repository

1. **Running Automated Tests:**
   ```powershell
   pytest tests/
   ```
2. **Starting the Production Web Engine:**
   ```powershell
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```
   Open `http://127.0.0.1:8000` to access the full application and Retailer Hub.
3. **Training Models in Google Colab:**
   Refer to [`docs/google_colab_training_guide.md`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/docs/google_colab_training_guide.md) or run:
   ```python
   !python scripts/train_colab.py
   ```
