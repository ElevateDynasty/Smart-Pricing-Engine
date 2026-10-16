# 📚 GitHub References & Upstream Projects

This directory maintains mirrors and documentation of open-source GitHub projects referenced in the research, design, and mathematical formulation of the **Smart Pricing Engine**.

---

## 📂 Referenced Projects

### 1. [`Retail_Price_Revenue_Optimisation`](./Retail_Price_Revenue_Optimisation/)
- **Upstream Repository:** [https://github.com/ozzienobayrak/Retail_Price_Revenue_Optimisation](https://github.com/ozzienobayrak/Retail_Price_Revenue_Optimisation)
- **Author:** Özlem Albayrak (Data Scientist / Economist)
- **Core Architecture:**
  - **Demand Forecasting:** LightGBM regressor predicting retail demand with lagged sales, rolling sales, price ratios, price percent changes, and calendar features.
  - **Price Simulation Engine:** Discrete price candidate evaluation ($P \in [0.8 P_0, 1.2 P_0]$) to generate price-sales and price-revenue curves.
  - **Inventory Feasibility Scenarios:** Demand capping based on baseline supply tiers:
    - *Low Supply:* $80\%$ of baseline sales velocity
    - *Medium Supply:* $100\%$ of baseline sales velocity
    - *High Supply:* $120\%$ of baseline sales velocity
    - Feasible Quantity: $Q_{\text{feasible}}(P) = \min(\hat{Q}(P), \text{Stock})$
    - Predicted Revenue: $R(P) = P \times Q_{\text{feasible}}(P)$
  - **Point Price Elasticity:** Finite difference sensitivity using a $5\%$ price perturbation ($\delta = 0.05$):
    $$\epsilon = \frac{(Q(P \cdot 1.05) - Q(P)) / Q(P)}{0.05}$$

---

## 🔗 Implementation & Integration in this Engine

Our production engine integrates and elevates the concepts from `Retail_Price_Revenue_Optimisation`:

| Feature | Reference Project (`ozzienobayrak`) | Our Smart Pricing Engine (`ElevateDynasty`) |
| :--- | :--- | :--- |
| **Model Type** | Unconstrained LightGBM | Monotone LightGBM ($\partial \hat{D}/\partial P \le 0$) + Conformal Bounds |
| **Elasticity** | Finite Difference ($\delta = 5\%$) | Dual Econometric Log-Log OLS + 2SLS IV + Central Finite Difference |
| **Price Search** | Single-item 1D grid search | Constrained Multi-Item Mixed-Integer Linear Program (MILP/LP) |
| **Supply Constraints** | Fixed item-level caps (80/100/120%) | Dynamic multi-store inventory balancing + shared warehouse LP constraints |
| **Multi-Store Arbitrage**| None (isolated store view) | Spatial transportation linear program via HiGHS LP solver |
| **Portfolio Bounds** | None | Global margin floor, inventory capacity cap, max price inflation drift |
