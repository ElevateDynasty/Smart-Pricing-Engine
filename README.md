# ⚡ AI-Powered Dynamic Pricing & Inventory Optimization for Electronics Retail

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Machine Learning](https://img.shields.io/badge/ML-Monotone%20LightGBM%20%7C%20Scikit--Learn-brightgreen)](https://lightgbm.readthedocs.io/)
[![Optimization](https://img.shields.io/badge/Optimization-SciPy%20%7C%20HiGHS%20Transportation%20LP-orange)](https://scipy.org/)
[![FastAPI Backend](https://img.shields.io/badge/API-FastAPI%20REST-009688)](https://fastapi.tiangolo.com/)
[![Web Dashboards](https://img.shields.io/badge/UI-Streamlit%20%7C%20Next.js%2014%20%7C%20Plotly-red)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-Pytest%20Passing%20(9%20Suites)-brightgreen)](https://pytest.org/)
[![Academic Publication](https://img.shields.io/badge/Report-LaTeX%2040--Page%20Publication-purple)](https://www.latex-project.org/)

An enterprise-grade revenue management engine and mathematical decision-support system designed specifically for **Indian offline multi-brand consumer electronics retailers** (smartphones, personal electronics, and tech hardware).

> **Authors / Project Researchers:**  
> **Gaurav Singh** | **Ritesh Dhange** | **Laksh Jagtap**  
> *Department of Computer Science & Engineering (Academic Session 2025–2026)*

---

## 📑 Table of Contents

- [🎯 Executive Summary & The Retail Dilemma](#-executive-summary--the-retail-dilemma)
- [✨ Core Capabilities & Architectural Features](#-core-capabilities--architectural-features)
- [📐 Mathematical & Econometric Formulations](#-mathematical--econometric-formulations)
- [📱 Flagship Showcase Benchmark (iPhone 17 Scenario)](#-flagship-showcase-benchmark-iphone-17-scenario)
- [🏗️ System Architecture & Data Flow](#️-system-architecture--data-flow)
- [📂 Comprehensive Project File Structure](#-comprehensive-project-file-structure)
- [🔌 REST API Endpoints (FastAPI)](#-rest-api-endpoints-fastapi)
- [💻 User Interfaces & Dashboards](#-user-interfaces--dashboards)
- [🚀 Quickstart & Pipeline Execution](#-quickstart--pipeline-execution)
- [🧪 Automated Testing Suite](#-automated-testing-suite)
- [📄 Academic Report & Presentation Assets](#-academic-report--presentation-assets)

---

## 🎯 Executive Summary & The Retail Dilemma

Traditional retail pricing tools merely predict tomorrow's sales volume or apply rigid markdown rules (e.g., flat 15% discounts, or blind price matching against Amazon/Flipkart flash sales). In consumer electronics retail, this heuristic approach triggers disastrous outcomes:
1. **Severe Margin Destruction:** Blind online price-matching destroys up to 96% of net margin, ignoring offline convenience, instant physical handover, warranty trust, and assisted selling value.
2. **Catastrophic Clearance Losses:** Applying flat ERP discounts drops unit prices below wholesale replacement costs ($P < C_{\text{unit}}$), inflicting multi-lakh rupee losses.
3. **Obsolescence Liquidation Traps:** Failing to accelerate sales before successor device launches strands hundreds of unsold units, triggering 20%–25% post-launch salvage haircut write-downs.

### The Engine's Core Optimization Question:
> *"Given current inventory across stores, wholesale acquisition cost, current and competitor prices, sales velocity, price elasticity, and approaching successor launches, what selling price maximizes expected total lifecycle profit over the remaining selling horizon while strictly adhering to Indian Legal Metrology regulations ($P \le \text{MRP}$), avoiding price wars, and minimizing inventory risk?"*

---

## ✨ Core Capabilities & Architectural Features

### 1. Constrained Lifecycle Profit Optimization
- Evaluates candidate prices across a discrete feasible lattice: $P \in [C_{\text{unit}}, \text{MRP}]$.
- Balances trade-offs across **Gross Margin**, **Daily Inventory Carrying & Working Capital Debt Interest Costs** ($r_{\text{holding}} + r_{\text{finance}}$), and **Post-Successor Terminal Obsolescence Haircut Write-Downs** ($\delta_{\text{deprec}}$).
- Identifies the global profit-maximizing price rather than optimizing a single day's margin in isolation.

### 2. Monotone Gradient-Boosted Demand Forecaster
- Implements **LightGBM** with strict monotonic split constraints:
  $$\frac{\partial \hat{D}(P)}{\partial P} \le 0$$
- Prevents spurious overfitting bumps (where unconstrained tree models erroneously predict higher sales at higher prices, destabilizing discrete optimizers).
- Incorporates calibrated **conformal prediction intervals** ($P_{10} - P_{90}$) to quantify demand and profit uncertainty bounds.

### 3. Dual Dataset Architecture (Synthetic & Real Kaggle)
- **Synthetic Indian Electronics Market:** 800+ realistic daily transactions across 4 multi-tier cities (Mumbai, Pune, Delhi, Bangalore), capturing footfall cycles, payday spikes, festive Diwali promotions, and competitor price scrapes.
- **Real-World Kaggle Benchmark:** Ingests the `retail_price.csv` dataset (676 real transactions across 9 product categories) with leakage-free train/validation splits.

### 4. Spatial Multi-Store Stock Balancing (Transportation LP)
- Formulates multi-branch inventory transfers as a **Linear Programming (LP) Transportation Problem** solved via `scipy.optimize.linprog` with the **HiGHS** solver engine.
- Reallocates stock from sluggish Tier-2 branches with surplus inventory ($>45\text{ days of supply}$) to high-velocity Tier-1 flagship stores ($<12\text{ days of supply}$) whenever the preserved retail margin exceeds inter-city freight transit costs.

### 5. Multi-Round Game-Theoretic Duopoly Simulator
- Simulates an asymmetric Bertrand duopoly game between offline physical retail and online algorithmic scrapers.
- Models differentiated demand with an empirical offline convenience premium ($\Delta_{\text{offline}} \approx \text{Rs.\,}1,000$).
- Validates mathematical convergence to a stable Nash Equilibrium, proving that the engine avoids triggering destructive tit-for-tat price wars.

### 6. Event-Driven Tech Launch Countdown Sensing
- Dynamic RSS/News event listener (`scripts/monitor_tech_launches.py`) that detects breaking tech announcements (e.g., Apple Keynotes, Samsung Unpacked).
- Exposes REST endpoints (`/api/lifecycle-event`) that perform non-destructive, in-memory lifecycle timeline compressions and immediately re-optimizes retail markdowns.

### 7. Explainable AI (XAI) for Store Managers
- Built-in `ReasonGenerator` transforms complex mathematical multi-objective trade-offs into plain-English retail briefings.
- Outlines clear operational headlines, unit-economics trade-offs, and offline conversion justifications.

---

## 📐 Mathematical & Econometric Formulations

### 1. Lifecycle Profit Objective Function
For any candidate retail selling price $P \in [C_{\text{unit}}, \text{MRP}]$ over operational horizon $T$:

$$\max_{P} \; \Pi_{\text{lifecycle}}(P) = \text{Gross Margin}(P) - \text{Carrying Costs}(P) - \text{Depreciation Loss}(P)$$

$$\text{Gross Margin}(P) = \min(I_0, \, \hat{D}(P) \cdot T) \cdot (P - C_{\text{unit}})$$

$$\text{Carrying Costs}(P) = \left( \frac{I_0 + I_{\text{terminal}}(P)}{2} \right) \cdot C_{\text{unit}} \cdot \left( r_{\text{daily\_holding}} + \frac{r_{\text{annual\_finance}}}{365} \right) \cdot T$$

$$\text{Depreciation Loss}(P) = \max(0, \, I_0 - \hat{D}(P) \cdot T) \cdot C_{\text{unit}} \cdot \delta_{\text{post\_successor}}$$

$$\text{Subject to:} \quad C_{\text{unit}} \le P \le \text{MRP}$$

### 2. Relative Price Elasticity Model (Log-Log Econometrics)
Estimated via ordinary least squares (OLS) regression:
$$\ln(\text{Units} + 1) = \alpha - \beta \ln\left( \frac{P}{P_{\text{comp}}} \right) + \gamma \cdot \text{Weekend} + \epsilon$$

### 3. Spatial Inventory Rebalancing Formulation (Transportation LP)
$$\min \sum_{i \in \mathcal{S}} \sum_{j \in \mathcal{D}} c_{ij} \cdot x_{ij} - \sum_{j \in \mathcal{D}} (P_j - C) \cdot \min\left( \Delta D_j, \, \sum_{i} x_{ij} \right)$$
$$\text{Subject to:} \quad \sum_{j \in \mathcal{D}} x_{ij} \le \text{Surplus}_i, \quad x_{ij} \ge 0$$

---

## 📱 Flagship Showcase Benchmark (iPhone 17 Scenario)

A live operational showcase evaluated over a 60-day horizon approaching a successor model launch:
- **Product:** Apple iPhone 17 256GB (Midnight)
- **Starting Inventory ($I_0$):** 800 units across regional stores
- **Wholesale Acquisition Cost ($C_{\text{unit}}$):** Rs. 68,000 / unit
- **Current Selling Price ($P_{\text{current}}$):** Rs. 79,999
- **Competitor Price:** Rs. 77,999 (Lowest: Rs. 76,999)
- **Legal Metrology MRP:** Rs. 89,900
- **Operational Horizon ($T$):** 60 days to successor launch

### 📊 Comparative Benchmark Results

| Pricing Strategy | Selling Price | 60-Day Clearance | Stranded Inventory | Net Lifecycle Profit | Profit Lift vs Status Quo |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline A: Status Quo** | Rs. 79,999 | 76.4% | 188 units | Rs. 18,17,777 | Baseline (Rs. 0) |
| **Baseline B: Match Competitor** | Rs. 76,999 | 76.8% | 185 units | Rs. 72,237 | -Rs. 17,45,540 *(Margin Destroyed)* |
| **Baseline C: Flat 15% Markdown** | Rs. 68,000 | 76.8% | 185 units | -Rs. 54,55,542 | -Rs. 72,73,319 *(Severe Loss)* |
| **⚡ [AI] Optimal Engine** | **Rs. 79,000** | **93.2%** | **54 units** | **Rs. 56,45,631** | **+Rs. 38,27,854 (+210.6%)** |

---

## 🏗️ System Architecture & Data Flow

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           1. INGESTION & DATA LAYER                         │
│  • Synthetic Indian Retail Generator (stores, products, inventory, sales)   │
│  • Kaggle Real-World Retail Dataset Adapter (retail_price.csv)             │
│  • Automated Tech Launch RSS Monitor (Google News tech alerts)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    2. FEATURE PIPELINE & PERSISTENCE                        │
│  • Economic Ratios (P/MRP, P/P_comp) • Lifecycle Urgency (Days to Launch)   │
│  • Velocity Differentials • Day-of-Week / Weekend Multipliers               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌──────────────────────────────────────┐┌─────────────────────────────────────┐
│     3A. DEMAND FORECASTING ENGINE    ││    3B. PRICE ELASTICITY ENGINE      │
│  • LightGBM Monotone Tree Splits     ││  • Econometric Log-Log Regression   │
│  • Non-Monotonicity Guardrails       ││  • Elasticity Regime Categorization │
│  • Conformal Intervals (P10 - P90)   ││  • Cross-Price Sensitivity Vectors  │
└──────────────────┬───────────────────┘└──────────────────┬──────────────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    4. CONSTRAINED OPERATIONS RESEARCH LAYER                 │
│  • Lifecycle Profit Discrete Lattice Grid Optimizer (Gross - Hold - Deprec)│
│  • HiGHS Transportation Linear Program (Spatial Multi-Store Balancing)      │
│  • Asymmetric Bertrand Duopoly Game Simulator (Nash Equilibrium Audit)      │
│  • Multi-Week Stepped Price Glide-Path Generator                            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌──────────────────────────────────────┐┌─────────────────────────────────────┐
│     5A. EXPLAINABLE AI (XAI) LAYER   ││       5B. ENTERPRISE REST API       │
│  • ReasonGenerator Briefing Memos    ││  • FastAPI High-Performance Backend │
│  • Unit-Economics Tradeoff Ledger    ││  • Live Simulations & In-Memory State│
└──────────────────┬───────────────────┘└──────────────────┬──────────────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         6. CLIENT PRESENTATION LAYER                        │
│  • Streamlit Web Dashboard (6 Interactive Analytic Modules)                 │
│  • Next.js 14 / TypeScript Modern Web Application                           │
│  • Fast Static Single-Page App (Mounted directly on FastAPI)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Comprehensive Project File Structure

```text
Technical Seminar project/
│
├── compile_all.py                    # Master pipeline: verifies slides prompt & builds LaTeX report
├── speech.docx                       # Presentation speech script for the technical seminar
│
├── report/                           # Academic Report Master Workspace
│   ├── main.tex                      # 40-page formal IEEE/academic LaTeX master report
│   ├── references.bib                # Formal academic citations and bibliography
│   └── main.pdf                      # Compiled publication-grade PDF report
│
├── presentation/                     # Technical Seminar Presentation Master
│   └── PROJECT_INFO_AND_GEMINI_SLIDES_PROMPT.md  # 15-slide master prompt for Gemini / Google Slides
│
└── AI PRice recomm/                  # Core Revenue Management Engine & Software Application
    │
    ├── main.py                       # CLI entry point: run data generation, training, demo, or Kaggle
    ├── requirements.txt              # Production Python package dependencies
    ├── README.md                     # Comprehensive project documentation (this file)
    ├── AI_implementation.md          # Living technical implementation & ML status tracker
    ├── AI_Retail_Pricing_Engine_Project_Spec.md  # Formal engineering and product requirements
    │
    ├── src/                          # Core Python Engine Architecture
    │   ├── config.py                 # Global financial parameters, holding rates, and paths
    │   │
    │   ├── data/                     # Ingestion & Data Pipeline
    │   │   ├── data_pipeline.py      # Feature engineering and unified dataset assembly
    │   │   ├── feature_engineering.py# Economic ratio and lifecycle feature transformers
    │   │   ├── generate_synthetic_data.py # Indian retail simulation (stores, products, sales)
    │   │   └── kaggle_pipeline.py    # Kaggle retail-price-optimization pipeline & adapter
    │   │
    │   ├── models/                   # Predictive Modeling & Machine Learning
    │   │   ├── demand_forecaster.py  # Monotone LightGBM Demand Forecaster with conformal bounds
    │   │   ├── elasticity_estimator.py # Econometric log-log price elasticity regression
    │   │   └── model_evaluator.py    # Cross-validation and regression evaluation metrics
    │   │
    │   ├── optimization/             # Operations Research & Constrained Solvers
    │   │   ├── lifecycle_optimizer.py# Constrained Lifecycle Profit discrete lattice solver
    │   │   ├── multi_store_balancer.py # Transportation LP solver (scipy / HiGHS)
    │   │   ├── competitor_game_theory.py # Asymmetric Bertrand duopoly game simulator
    │   │   └── price_path_generator.py # Multi-week stepped price glide-path scheduler
    │   │
    │   ├── explainability/           # Explainable AI & Human-in-the-Loop Memos
    │   │   └── reason_generator.py   # Natural language executive briefing generator
    │   │
    │   └── evaluation/               # Benchmarking & Ablation
    │       ├── baseline_benchmarking.py # Head-to-head comparison against retail heuristics
    │       └── model_ablation.py     # Ablation audit (Monotone vs Unconstrained vs RF vs OLS)
    │
    ├── api/                          # FastAPI REST API Backend
    │   ├── main.py                   # FastAPI application initialization & CORS config
    │   └── routes/
    │       └── analytics.py          # REST endpoints for summary, simulation, events, LP & game theory
    │
    ├── dashboard/                    # Streamlit Interactive Web Application
    │   ├── app.py                    # Streamlit multi-page launcher & navigation
    │   ├── style.css                 # Custom CSS stylesheet
    │   └── pages/
    │       ├── 1_Overview.py         # Module 1: Executive KPI overview & pricing action queue
    │       ├── 2_SKU_Pricing.py      # Module 2: SKU pricing deep-dive & dual-axis curves
    │       ├── 3_Price_Simulator.py  # Module 3: Real-time price sandbox & sensitivity sliders
    │       ├── 4_Inventory_Risk.py   # Module 4: Obsolescence risk radar & markdown urgency
    │       ├── 5_Competitor_Monitor.py # Module 5: Online vs offline price intelligence
    │       └── 6_Multi_Store_Balancing.py # Module 6: Inter-store transportation transfer routes
    │
    ├── frontend/                     # Fast Static Single-Page Dashboard (Mounted on FastAPI)
    │   ├── index.html                # Responsive web analytics interface
    │   ├── css/                      # Stylesheets
    │   └── js/                       # Interactive chart scripts
    │
    ├── web-app/                      # Modern Next.js 14 / TypeScript Web Application
    │   ├── package.json              # Next.js dependencies & scripts
    │   ├── tsconfig.json             # TypeScript compiler configuration
    │   ├── next.config.ts            # Next.js server configuration
    │   └── src/                      # React components, pages, and hooks
    │
    ├── scripts/                      # Autonomous Background Daemons
    │   └── monitor_tech_launches.py  # Google News RSS scraper for tech launch countdowns
    │
    ├── tests/                        # Automated Pytest Suite
    │   ├── test_models.py            # Unit tests for Monotone LightGBM & Elasticity
    │   ├── test_optimizer.py         # Unit tests for Lifecycle Optimizer & MRP ceiling
    │   ├── test_data_pipeline.py     # Unit tests for data generation and merging
    │   ├── test_explainability.py    # Unit tests for ReasonGenerator memos
    │   ├── test_api_endpoints.py     # Unit tests for FastAPI HTTP routes
    │   ├── test_kaggle_pipeline.py   # Unit tests for Kaggle dataset ingestion
    │   ├── test_ablation.py          # Unit tests for model ablation sweeps
    │   └── test_game_theory.py       # Unit tests for duopoly simulation convergence
    │
    ├── data/                         # Data Storage
    │   ├── raw/                      # Raw incoming retail feeds
    │   ├── synthetic/                # Generated Indian retail CSVs (products, sales, etc.)
    │   ├── processed/                # Unified preprocessed feature matrices
    │   └── import_templates/         # CSV import templates for retail ERP onboarding
    │
    ├── models_saved/                 # Serialized Model Checkpoints
    │   ├── demand_forecaster_lightgbm.joblib # Trained LightGBM model (synthetic)
    │   └── demand_forecaster_kaggle.joblib   # Trained LightGBM model (Kaggle)
    │
    ├── docs/                         # Retailer Documentation & Guides
    │   ├── Retailer_User_Guide.pdf   # Step-by-step user manual for store managers
    │   └── Real_Data_Import_Templates.zip # Blank ERP ingestion spreadsheets
    │
    ├── report/                       # Mirrored Production LaTeX Report
    │   ├── main.tex                  # Mirrored LaTeX source
    │   ├── references.bib            # Mirrored bibliography
    │   └── main.pdf                  # Mirrored publication PDF
    │
    └── presentation/                 # Mirrored Presentation Prompt
        └── PROJECT_INFO_AND_GEMINI_SLIDES_PROMPT.md
```

---

## 🔌 REST API Endpoints (FastAPI)

When running the FastAPI server (`uvicorn api.main:app --port 8000`), the engine provides the following endpoints:

| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `GET` | `/health` or `/api/health` | Service health check and status confirmation. |
| `GET` | `/api/summary` | Portfolio-level KPIs (valuation, net profit lift, action counts, risk tiers). Accepts `?model_source=synthetic\|kaggle`. |
| `GET` | `/api/optimizations` | Full catalog optimization results including price recommendations, demand curves, and XAI memos. |
| `POST` | `/api/optimizations/refresh` | Forces live in-memory cache refresh and reloads updated retail CSV files. |
| `POST` | `/api/simulate` | Real-time "What-If" sandbox. Evaluates candidate prices, inventory, and competitor shifts with conformal prediction bounds. |
| `POST` | `/api/lifecycle-event` | Ingests breaking tech launch countdowns (e.g. iPhone 18) and immediately triggers in-memory markdown re-optimization. |
| `POST` | `/api/reset-events` | Resets all active lifecycle overrides back to standard baseline schedules. |
| `GET` | `/api/active-events` | Retrieves list of currently active launch countdowns and urgent alerts. |
| `GET` | `/api/transfers` | Solves multi-store transportation LP (HiGHS) and returns inter-store transfer routes. |
| `GET` | `/api/game-theory/simulate` | Simulates multi-round asymmetric Bertrand duopoly game to verify Nash equilibrium stability. |
| `GET` | `/api/models/ablation` | Returns empirical ablation benchmark comparing Monotone LightGBM, Unconstrained, RF, and OLS. |

---

## 💻 User Interfaces & Dashboards

The engine provides three client interfaces:

### 1. Interactive Streamlit Dashboard (`dashboard/app.py`)
Launch with:
```powershell
streamlit run dashboard/app.py
```
Includes 6 interactive analytical modules:
1. **Executive Portfolio Overview:** Portfolio valuation, prioritized pricing queue, and projected financial lift.
2. **SKU Pricing Deep-Dive:** Dual-axis demand & profit curves, inventory drawdown trajectory, and retailer briefing memos.
3. **Price Simulator Sandbox:** Live "What-If" sliders with competitor stockout toggles, footfall modifiers, and profit curves.
4. **Inventory Risk Radar:** Days-to-successor countdown radar, stranded inventory exposure, and markdown urgency matrix.
5. **Competitor Intelligence Monitor:** Online vs offline price dispersion radar, identifying stockout price-hike opportunities.
6. **Multi-Store Balancing:** Store velocity vs stock disbalance matrix, inter-store transfer generator, and phased multi-week schedules.

### 2. Modern Next.js 14 Web Application (`web-app/`)
Built with Next.js 14, TypeScript, and TailwindCSS:
```powershell
cd web-app
npm install
npm run dev
```

### 3. Fast Static Single-Page Dashboard (`frontend/`)
Mounted directly by the FastAPI backend at `http://localhost:8000/`.
- **Light & Dark Mode Support:** Full dual-theme design system with instant switching, `localStorage` persistence, and automatic Chart.js color palette adaptation.
- **One-Click Page Refresh:** Dedicated `Refresh Page` quick-reload button alongside live `Sync Data` recompute triggers.
- **Responsive Command Shell:** Full desktop and mobile-responsive drawer with keyboard navigation (`Ctrl+K` command palette, deep hash links).

---

## 🚀 Quickstart & Pipeline Execution

### 1. Environment Setup
```powershell
# Navigate to the core project directory
cd "AI PRice recomm"

# Install required Python packages
pip install -r requirements.txt
```

### 2. End-to-End Pipeline Execution via CLI
```powershell
# 1. Execute the entire pipeline (Data Generation -> Training -> Showcase Demo)
python main.py --all

# 2. Run only the flagship iPhone 17 showcase demonstration
python main.py --demo

# 3. Generate synthetic Indian retail market datasets
python main.py --generate-data

# 4. Train Monotone LightGBM demand forecaster and price elasticity models
python main.py --train

# 5. Download and execute Kaggle real-world dataset pipeline
python main.py --kaggle
```

### 3. Launching the Backend API & Web Dashboards
```powershell
# Start FastAPI backend server (API available at http://localhost:8000/docs)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# In a separate terminal, launch the Streamlit dashboard
streamlit run dashboard/app.py
```

### 4. Running the Autonomous Tech Launch Monitor
```powershell
python scripts/monitor_tech_launches.py
```

---

## 🧪 Automated Testing Suite

The repository includes 9 unit and integration test suites covering the entire mathematical and operational pipeline:

```powershell
pytest tests/ -v
```

### Test Coverage Highlights:
- **`test_models.py`:** Validates LightGBM monotonic constraint satisfaction ($\frac{\partial \hat{D}}{\partial P} \le 0$) across the price grid.
- **`test_optimizer.py`:** Verifies strict MRP boundary adherence ($P \le \text{MRP}$) and positive profit lift generation.
- **`test_api_endpoints.py`:** Validates FastAPI route integrity, HTTP responses, and payload schemas.
- **`test_game_theory.py`:** Tests duopoly simulation round iterations and Nash equilibrium stability.
- **`test_kaggle_pipeline.py`:** Tests real-data adapter, leakage-free cross-validation, and metric computation.
- **`test_ablation.py`:** Tests model ablation matrix generation and monotonicity audit flags.

---

## 📄 Academic Report & Presentation Assets

The project includes formal academic deliverables:

1. **40-Page LaTeX Technical Seminar Report:**
   - **Source:** [`report/main.tex`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/report/main.tex)
   - **Compiled Publication PDF:** [`report/main.pdf`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/report/main.pdf)
   - Features 14 formal academic tables, 9 native TikZ/PGFPlots vector diagrams, zero text clipping, and publication styling.
2. **Automated Report Build Pipeline:**
   - Run from the root directory:
     ```powershell
     python compile_all.py
     ```
3. **Master Presentation Asset:**
   - **File:** [`presentation/PROJECT_INFO_AND_GEMINI_SLIDES_PROMPT.md`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/presentation/PROJECT_INFO_AND_GEMINI_SLIDES_PROMPT.md)
   - A complete 15-slide master prompt formatted for direct execution in Google Gemini to generate presentation slide decks.
4. **Presentation Speech Script:**
   - **File:** [`speech.docx`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/speech.docx)

---

## 👥 Authors & Academic Credit

This project was developed by:

- **Gaurav Singh**
- **Ritesh Dhange**
- **Laksh Jagtap**

*Bachelor of Technology in Computer Science & Engineering*  
*Academic Session 2025–2026*  
*Specialization: Constrained Revenue Management, Operations Research & Applied Machine Learning*
