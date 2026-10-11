"""
Price Elasticity Estimator
Estimates econometric log-log demand functions and price sensitivity coefficients
to identify elastic vs inelastic SKUs across the retail portfolio.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
import statsmodels.api as sm

class ElasticityEstimator:
    def __init__(self):
        self.sku_elasticities: Dict[str, Dict[str, Any]] = {}

    def fit(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Fit econometric relative price elasticity:
        ln(Units + 1) = alpha - beta * ln(Price / Competitor_Price) + gamma * Weekend + eps
        Using relative price ratio avoids multicollinearity and isolates price elasticity cleanly.
        """
        results = {}
        unique_skus = df["product_id"].unique()

        for pid in unique_skus:
            sub = df[df["product_id"] == pid].copy()
            if len(sub) < 30:
                continue

            # Econometric requirement: only evaluate price sensitivity on active, in-stock trading days
            # to avoid confounding stockout periods (opening_inventory == 0) with zero demand
            sub = sub[(sub["selling_price"] > 0) & (sub["competitor_avg_price"] > 0)]
            if "opening_inventory" in sub.columns:
                sub = sub[sub["opening_inventory"] > 0]
            if "units_sold" in sub.columns:
                sub = sub[sub["units_sold"] > 0]

            if len(sub) < 30:
                continue
            
            # Dependent variable: log(units + 1)
            y = np.log(sub["units_sold"] + 1.0)
            
            # Relative price ratio: ln(Selling_Price / Competitor_Avg_Price)
            log_price_ratio = np.log(sub["selling_price"] / sub["competitor_avg_price"])
            weekend = (pd.to_datetime(sub["date"]).dt.dayofweek >= 5).astype(int)

            X = pd.DataFrame({
                "const": 1.0,
                "log_price_ratio": log_price_ratio,
                "weekend": weekend
            })

            try:
                model = sm.OLS(y, X).fit()
                # Beta is negative of coefficient on log_price_ratio
                raw_beta = -float(model.params.get("log_price_ratio", np.nan))
                p_val = float(model.pvalues.get("log_price_ratio", 1.0))
                r2 = float(model.rsquared)

                # Identifiability guard: regressor must exhibit meaningful price variation
                ratio_spread = float(log_price_ratio.std())
                identifiable = bool(ratio_spread > 0.01 and (p_val < 0.05 or raw_beta > 0.5))

                if identifiable and raw_beta > 0:
                    beta = float(np.clip(raw_beta, 0.05, 8.0))
                elif identifiable and raw_beta <= 0:
                    beta = 0.5  # Inelastic / strong pricing power regime
                else:
                    beta = None

                if beta is None:
                    regime = "Not Identifiable"
                    action_advice = ("Insufficient independent price variation in data. "
                                     "Use the model-derived elasticity instead.")
                elif beta > 1.8:
                    regime = "Highly Elastic"
                    action_advice = "Sensitive to pricing. Strategic markdowns yield strong volume lift."
                elif beta >= 1.1:
                    regime = "Moderately Elastic"
                    action_advice = "Standard response. Align with competitor movements."
                else:
                    regime = "Inelastic"
                    action_advice = "Strong pricing power / scarcity. Can hold or increase price without severe volume drop."

                results[pid] = {
                    "product_id": pid,
                    "method": "econometric log-log OLS",
                    "elasticity": round(beta, 3) if beta is not None else None,
                    "raw_beta": round(raw_beta, 3),
                    "r_squared": round(r2, 3),
                    "p_value": round(p_val, 4),
                    "identifiable": identifiable,
                    "ratio_spread": round(ratio_spread, 4),
                    "regime": regime,
                    "action_advice": action_advice,
                    "sample_size": len(sub)
                }
            except Exception as exc:
                # Never fabricate metrics. Report the failure honestly.
                results[pid] = {
                    "product_id": pid,
                    "method": "econometric log-log OLS",
                    "elasticity": None,
                    "raw_beta": None,
                    "r_squared": None,
                    "p_value": None,
                    "identifiable": False,
                    "error": str(exc),
                    "regime": "Not Identifiable",
                    "action_advice": "Regression failed. Use the model-derived elasticity instead.",
                    "sample_size": len(sub)
                }

        self.sku_elasticities = results
        return results

    @staticmethod
    def estimate_from_model(
        forecaster,
        selling_price: float,
        competitor_avg_price: float,
        competitor_min_price: float,
        mrp: float,
        unit_cost: float,
        opening_inventory: int,
        days_to_successor: int = 60,
        eps: float = 1e-3
    ) -> Dict[str, Any]:
        """
        Model-derived price elasticity via central finite differences on the
        trained demand function:

            epsilon = - d(ln D) / d(ln P)

        Always consistent with the demand model that drives the optimizer
        (unlike a separate OLS on possibly degenerate data), and works for any
        forecaster exposing predict_point with the DemandForecaster signature.
        """
        p_hi = selling_price * (1.0 + eps)
        p_lo = selling_price * (1.0 - eps)

        d_hi = float(forecaster.predict_point(
            selling_price=p_hi, mrp=mrp,
            competitor_avg_price=competitor_avg_price,
            competitor_min_price=competitor_min_price,
            unit_cost=unit_cost, opening_inventory=opening_inventory,
            days_to_successor=days_to_successor
        ))
        d_lo = float(forecaster.predict_point(
            selling_price=p_lo, mrp=mrp,
            competitor_avg_price=competitor_avg_price,
            competitor_min_price=competitor_min_price,
            unit_cost=unit_cost, opening_inventory=opening_inventory,
            days_to_successor=days_to_successor
        ))

        denom = np.log((1.0 + eps) / (1.0 - eps))
        numer = np.log(max(d_hi, 1e-6) / max(d_lo, 1e-6))
        epsilon = float(-numer / denom) if denom != 0 else None

        if epsilon is None:
            regime = "Not Identifiable"
            advice = "Demand function flat near current price."
        elif epsilon > 1.8:
            regime = "Highly Elastic"
            advice = "Sensitive to pricing. Strategic markdowns yield strong volume lift."
        elif epsilon >= 1.1:
            regime = "Moderately Elastic"
            advice = "Standard response. Align with competitor movements."
        else:
            regime = "Inelastic"
            advice = "Strong pricing power / scarcity. Can hold or increase price without severe volume drop."

        return {
            "method": "model-derived (central finite difference on demand ML model)",
            "elasticity": round(epsilon, 3) if epsilon is not None else None,
            "regime": regime,
            "action_advice": advice,
            "at_price": float(selling_price),
            "identifiable": epsilon is not None
        }

    def get_elasticity(self, product_id: str) -> Dict[str, Any]:
        """Retrieve estimated elasticity metrics for a specific product."""
        return self.sku_elasticities.get(product_id, {
            "product_id": product_id,
            "method": "econometric log-log OLS",
            "elasticity": None,
            "raw_beta": None,
            "r_squared": None,
            "p_value": None,
            "identifiable": False,
            "regime": "Not Identifiable",
            "action_advice": "No elasticity estimate available for this SKU. Use model-derived elasticity."
        })
