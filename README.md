# 🎯 AI Smart Pricing Engine

**AI-Powered Dynamic Pricing Engine for Indian E-Commerce Sellers**

> Maximize profit by finding the optimal selling price using Machine Learning demand forecasting, price elasticity estimation, and mathematical optimization.

---

## 📌 Problem

Most small-to-medium Indian e-commerce sellers price products by **gut feeling** or simple cost-plus markup — leaving significant money on the table. Amazon changes prices **2.5 million times per day** using data-driven pricing. This project brings the same intelligence to small sellers.

**Example:** A phone case costing ₹100 —  
| Price | Units/Day | Daily Profit |
|-------|-----------|-------------|
| ₹250 | 20 | ₹3,000 |
| ₹220 | 50 | ₹6,000 |
| **₹199** | **80** | **₹7,920 ← Optimal!** |

## 🧠 How It Works — The 3 Pillars

### 1️⃣ Demand Forecasting
> *"How much will I sell at price X?"*

- **LightGBM** gradient boosting model trained on historical sales data
- Features: price, competitor price, day of week, festivals, weather, ratings, ad spend
- Lag features & rolling averages for temporal patterns

### 2️⃣ Price Elasticity Estimation
> *"If I change price by 10%, how much does demand change?"*

- **Log-log regression** model: `ln(demand) = α - β·ln(price) + γ·X`
- β = price elasticity coefficient (learned per category)
- Electronics (β≈2.2): very price-sensitive | Health (β≈1.2): less sensitive

### 3️⃣ Profit Optimization
> *"What price maximizes (Price - Cost) × Demand?"*

- **SciPy optimizer** finds the profit-maximizing sweet spot
- Supports what-if scenarios: festivals, competitor changes, weekends

### Mathematical Formulation

```
Maximize  Π(p) = (p - c) × D(p)

Subject to:  p ≥ c          (price covers cost)
             p ≤ p_max      (market ceiling)
             D(p) ≥ 0       (non-negative demand)

Where:  D(p) = A · p^(-β) · e^(γ·X)    (constant-elasticity demand model)
```

---

## 🏗️ Project Structure

```
Smart-Pricing-Engine/
│
├── src/
│   ├── data/
│   │   ├── generate_synthetic_data.py   # Realistic sales data generator
│   │   ├── data_pipeline.py             # Data loading & cleaning
│   │   └── feature_engineering.py       # 15+ ML features
│   │
│   ├── models/
│   │   ├── demand_forecaster.py         # LightGBM demand model
│   │   ├── elasticity_estimator.py      # Log-log price elasticity
│   │   └── model_evaluator.py           # RMSE, MAE, MAPE, R²
│   │
│   ├── optimization/
│   │   ├── price_optimizer.py           # SciPy profit maximizer
│   │   └── scenario_engine.py           # What-if analysis
│   │
│   ├── visualization/
│   │   └── plots.py                     # Plotly dark-themed charts
│   │
│   └── utils/
│       ├── config.py                    # Central configuration
│       └── helpers.py                   # Utility functions
│
├── data/external/
│   └── indian_festivals.json            # Festival calendar (2023-2025)
│
├── dashboard/                           # Streamlit web app (coming soon)
├── main.py                              # End-to-end pipeline runner
├── requirements.txt                     # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/ElevateDynasty/Smart-Pricing-Engine.git
cd Smart-Pricing-Engine
pip install -r requirements.txt
```

### 2. Run the Full Pipeline

```bash
python main.py
```

This will:
1. Generate synthetic sales data (~50K rows, 5 products, 2 years)
2. Clean data & engineer 15+ ML features
3. Train LightGBM demand forecaster
4. Estimate price elasticity via log-log regression
5. Find optimal prices for all products
6. Print a complete pricing recommendation report

### 3. Launch Dashboard (coming soon)

```bash
streamlit run dashboard/app.py
```

---

## 📊 Product Catalog

| Product | Category | Cost (₹) | Base Price (₹) | Elasticity (β) |
|---------|----------|----------|---------------|----------------|
| Wireless Earbuds | Electronics | 400 | 899 | 2.2 |
| Phone Case (Premium) | Electronics | 100 | 299 | 2.5 |
| Cotton T-Shirt | Fashion | 200 | 499 | 1.8 |
| Yoga Mat | Home & Fitness | 350 | 799 | 1.5 |
| Organic Face Wash | Health & Beauty | 80 | 249 | 1.2 |

---

## 🔬 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.10+ |
| **ML Models** | LightGBM, Scikit-learn, Statsmodels |
| **Optimization** | SciPy (minimize_scalar, Brent's method) |
| **Visualization** | Plotly (dark theme) |
| **Dashboard** | Streamlit |
| **Data** | Pandas, NumPy |

---

## 📈 Key Features

- **5 diverse product categories** with realistic demand patterns
- **Indian festival calendar** (Diwali 3×, Big Billion Days 2.5× demand spikes)
- **What-if scenario engine** — simulate festivals, competitor price changes, weekends
- **Interactive profit curves** — see exactly where the optimal price lies
- **Category-level elasticity comparison** — which products are most price-sensitive?
- **Model performance dashboard** — RMSE, MAE, MAPE, R², feature importance

---

## 📚 Research Foundation

Built on 20 research papers (2015-2025) including:
- Ban & Keskin (2021) — Dynamic Pricing with ML survey
- Taylor & Letham (2018) — Prophet forecasting at scale
- Cohen et al. (2020) — Feature-based dynamic pricing (MIT)
- Pavlyshenko (2019) — ML methods for demand forecasting
- Sharma & Gupta (2024) — Indian e-commerce pricing strategies

---

## 📋 License

This project is built for academic/educational purposes as a Technical Seminar project.

---

<p align="center">
  <b>Built with ❤️ for Indian e-commerce sellers</b>
</p>
