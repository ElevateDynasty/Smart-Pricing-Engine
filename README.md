# ⚡ AI-Powered Dynamic Pricing and Inventory Optimization for Electronics Retail

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Machine Learning](https://img.shields.io/badge/ML-LightGBM%20%7C%20Scikit--Learn-brightgreen)](https://lightgbm.readthedocs.io/)
[![Optimization](https://img.shields.io/badge/Optimization-SciPy%20%7C%20Constrained%20Lifecycle-orange)](https://scipy.org/)
[![UI Dashboard](https://img.shields.io/badge/Dashboard-Streamlit%20%7C%20Plotly-red)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-Pytest%20Passing-brightgreen)](https://pytest.org/)

An enterprise-grade AI revenue management engine designed for **Indian offline multi-brand consumer electronics retailers** (smartphones and tech hardware), built strictly according to [`AI_Retail_Pricing_Engine_Project_Spec.md`](./AI_Retail_Pricing_Engine_Project_Spec.md).

---

## 🎯 Executive Summary & Core Question

Traditional pricing software merely predicts tomorrow's market price or applies simplistic discount heuristics. This engine solves the true economic retail dilemma:

> **"Given current inventory, acquisition cost, current and competitor prices, sales velocity, demand elasticity, product lifecycle, and approaching successor launches, what selling price or pricing strategy maximizes expected total profit over the remaining selling horizon while keeping inventory risk under control?"**

### 🌟 Core Differentiators
1. **Lifecycle Profit Over Today's Margin:** Does not optimize a single day's margin in isolation. Evaluates daily carrying cost, financing charges, and post-successor depreciation penalties over a 60–180 day horizon.
2. **Indian Legal Metrology Compliance:** Strict mathematical enforcement of the Legal Metrology Rules (Packaged Commodities): **Selling Price ≤ MRP**.
3. **Intelligent Non-Discounting & Price Increases:** Capable of recommending **holding or increasing prices** when demand is inelastic, replacement costs inflate (e.g. memory-cost inflation), or competitors are out of stock. Competitor prices serve as informational signals, not automatic matching targets.
4. **Multi-Store Inventory Balancing:** Identifies velocity mismatches across physical retail branches (e.g., Mumbai Palladium vs Pune FC Road) and generates profitable inter-store transfers where margin preserved exceeds logistics transfer costs.
5. **Explainable AI for Retailers:** Generates natural language briefings detailing the exact unit-economics tradeoff behind every recommendation.

---

## 📐 Mathematical Formulation

### 1. Expected Total Lifecycle Profit Objective
For any candidate selling price $P \in [\text{Cost}, \text{MRP}]$ over remaining horizon $T$:

$$\max_{P} \; \Pi_{\text{lifecycle}}(P) = \text{Gross Margin}(P) - \text{Carrying Costs}(P) - \text{Depreciation Loss}(P)$$

Where:
- $\text{Gross Margin}(P) = \min(I_0, D(P) \times T) \times (P - C_{\text{unit}})$
- $\text{Carrying Costs}(P) = \bar{I}(P) \times C_{\text{unit}} \times \left( r_{\text{daily\_holding}} + \frac{r_{\text{annual\_finance}}}{365} \right) \times T$
- $\text{Depreciation Loss}(P) = \max(0, I_0 - D(P) \times T) \times C_{\text{unit}} \times \delta_{\text{post\_successor}}$
- Subject to:
  $$C_{\text{unit}} \le P \le \text{MRP}$$

### 2. Relative Price Elasticity Model
Estimated via econometric log-log regression:
$$\ln(\text{Units} + 1) = \alpha - \beta \ln\left(\frac{P}{P_{\text{comp}}}\right) + \gamma \cdot \text{Weekend} + \epsilon$$

---

## 🏗️ System Architecture

```text
               RETAILER TRANSACTION & INVENTORY DATA
                                |
             +------------------+------------------+
             |                                     |
       POS / ERP Feeds                        Daily CSV / Manual
             |                                     |
             +------------------+------------------+
                                |
                        DATA PIPELINE
             (Validation, Merging, SQL Persistence)
                                |
                       FEATURE ENGINEERING
           (MRP Ratios, Competitor Gaps, Lifecycle Urgency)
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
     DEMAND FORECASTER                    PRICE ELASTICITY
   (LightGBM / Monotonic)               (Log-Log Econometrics)
             |                                     |
             +------------------+------------------+
                                |
                  CONSTRAINED LIFECYCLE OPTIMIZER
             (MRP Ceiling, Carrying Costs, Depreciation)
                                |
             +------------------+------------------+
             |                  |                  |
      RECOMMENDED PRICE    REASONING ENGINE   MULTI-STORE BALANCER
      (Stepped Roadmap)    (Plain Language)   (Branch Transfers)
             |                  |                  |
             +------------------+------------------+
                                |
                   STREAMLIT WEB DASHBOARD
              (6 Dedicated Interactive Modules)
```

---

## 📱 The Flagship Showcase Demonstration

Directly illustrates **Spec Section 1 & Section 27**:
- **SKU:** iPhone 17 256GB (Midnight)
- **Current Inventory:** 800 units across stores
- **Acquisition Cost:** ₹68,000 / unit
- **Current Selling Price:** ₹79,999
- **Competitor Average:** ₹77,999 (Lowest: ₹76,999)
- **Successor Launch:** 60 days away
- **Status Quo Velocity:** 10.2 units/day (clears only 611 units; leaves **188 units stranded**, risking ₹38.3 Lakhs in depreciation write-downs)

### 📊 Benchmark Comparison
| Strategy | Selling Price | Clearance % | Stranded Units | Expected Net Profit | Profit Lift vs Status Quo |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline A: Status Quo** | ₹79,999 | 76.4% | 188 units | ₹18,17,777 | ₹0 |
| **Baseline B: Match Competitor** | ₹76,999 | 76.8% | 185 units | ₹72,237 | -₹17,45,540 *(Destroyed Margin)* |
| **Baseline C: Fixed 15% Markdown** | ₹68,000 | 76.8% | 185 units | -₹54,55,542 | -₹72,73,319 *(Severe Loss)* |
| **⚡ AI Pricing Engine** | **₹79,000** | **93.2%** | **54 units** | **₹56,45,631** | **+₹38,27,854 (+210.6%)** |

---

## 💻 Web Dashboard Modules (Streamlit)

Launch the interactive dashboard:
```powershell
streamlit run dashboard/app.py
```

1. **📊 1. Executive Overview:** Total portfolio valuation (₹ Cr), morning prioritized pricing queue, portfolio clearance rate, and profit lift.
2. **🏷️ 2. SKU Pricing Deep-Dive:** Interactive SKU explorer with dual-axis demand & profit curves, day-by-day inventory drawdown trajectory, and retailer briefing memos.
3. **🎛️ 3. Price Simulator Sandbox:** Real-time "What-If" sandbox with price sliders, competitor stockout toggles, footfall modifiers, and live sensitivity plots.
4. **⚠️ 4. Inventory Risk Radar:** Days-to-successor countdown radar, stranded capital exposure, and depreciation write-down mitigation matrix.
5. **🌐 5. Competitor Intelligence:** Online (Amazon, Flipkart) vs offline (Croma, Vijay Sales) price gaps and stockout opportunity detector.
6. **🔄 6. Multi-Store Balancing:** Store velocity vs stock disbalance matrix, inter-store transfer generator, and phased multi-week pricing schedules.

---

## 🛠️ CLI Quickstart & Pipeline Execution

```powershell
# Run the complete end-to-end pipeline (Data Generation -> Model Training -> Showcase Demo)
python main.py --all

# Run only the showcase demonstration
python main.py --demo

# Re-generate synthetic Indian retail datasets
python main.py --generate-data

# Re-train LightGBM demand forecaster & price elasticity models
python main.py --train
```

---

## 🧪 Automated Testing

Run the full pytest suite (9 unit tests covering data pipeline, feature engineering, models, constraints, and optimization):
```powershell
pytest tests/ -v
```

---

## 📁 Project Folder Renaming Guide

To rename the root workspace folder from `AI PRice recomm` to the theme name **`AI-Retail-Pricing-Engine`**:
1. Close Antigravity IDE / VS Code.
2. In PowerShell or Command Prompt, run:
   ```powershell
   Rename-Item -Path "c:\Users\gaura\OneDrive\Desktop\Technical Seminar project\AI PRice recomm" -NewName "AI-Retail-Pricing-Engine"
   ```
3. Re-open the folder `c:\Users\gaura\OneDrive\Desktop\Technical Seminar project\AI-Retail-Pricing-Engine` in the IDE.
