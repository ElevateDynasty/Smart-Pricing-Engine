"""
Retailer Reason Generator
Translates complex mathematical optimization outputs into transparent, business-friendly
explanations tailored for offline electronics retailers.
"""
from typing import Dict, Any
from src.optimization.lifecycle_optimizer import OptimizationResult

class ReasonGenerator:
    @staticmethod
    def generate_retailer_memo(result: OptimizationResult) -> Dict[str, str]:
        """
        Creates a structured, easy-to-read executive briefing for the store manager.
        """
        pid = result.product_name
        rec_price = int(result.recommended_price)
        curr_price = int(result.current_price)
        diff = rec_price - curr_price

        # Headline
        if result.price_action == "No Stock":
            # There are zero units on hand, so there is nothing to mark down, hold or
            # raise. Falling through to the clearance branch would issue a markdown
            # order for stock that does not exist.
            headline = f"No action: {pid} is out of stock at every store"
            key_rationale = (
                "Zero units remain on hand as of the latest inventory snapshot, so no pricing "
                "decision applies: there is no stock to discount, hold or reprice. Replenish or "
                "re-assort this SKU before applying any price change."
            )
            offline_advantage = (
                "If the product is still in its selling window, securing fresh allocation at the "
                "current price avoids both a lost sale and an unnecessary margin giveaway."
            )
        elif result.price_action == "Increase Price":
            headline = f"Opportunity: Raise {pid} by ₹{diff:,} to capture higher margin"
            key_rationale = (
                f"Competitors have limited stock or out-of-stock notices, and consumer demand is relatively "
                f"inelastic. Raising price to ₹{rec_price:,} captures an extra ₹{int(result.profit_lift_amount):,} "
                f"in profit without jeopardizing inventory clearance."
            )
            offline_advantage = (
                "Customers in your store value immediate device setup and hands-on inspection over "
                "waiting for online delivery."
            )
        elif result.price_action == "Hold Price":
            headline = f"Optimal: Maintain current price of ₹{curr_price:,} for {pid}"
            key_rationale = (
                f"At ₹{curr_price:,}, your current sales velocity of {result.expected_daily_demand:.1f} units/day "
                f"is perfectly paced to clear your {result.current_inventory} units in {result.projected_clearance_days:.0f} days, "
                f"well ahead of the {result.days_to_successor}-day lifecycle deadline."
            )
            offline_advantage = (
                "Do not match minor online discounts; maintaining price preserves healthy dealer margins."
            )
        elif result.price_action == "Slight Reduction":
            headline = f"Action: Adjust {pid} price down by ₹{abs(diff):,} to ₹{rec_price:,}"
            key_rationale = (
                f"Current sales velocity is {result.status_quo_daily_demand:.1f} units/day, which would leave "
                f"approximately {int(result.status_quo_leftover)} units unsold when the successor model launches. "
                f"Adjusting price to ₹{rec_price:,} accelerates daily sales to {result.expected_daily_demand:.1f} units/day, "
                f"yielding an additional +₹{int(result.profit_lift_amount):,} in total profit."
            )
            offline_advantage = (
                f"A slight price reduction keeps you competitive with online marketplaces while preserving "
                f"a ₹{int(rec_price - result.unit_cost):,} gross margin per unit."
            )
        else:
            headline = f"Urgent: Implement ₹{abs(diff):,} clearance markdown on {pid}"
            key_rationale = (
                f"High inventory risk! With only {result.days_to_successor} days until the successor model launches, "
                f"holding price at ₹{curr_price:,} will leave {int(result.status_quo_leftover)} units stranded. "
                f"Post-launch depreciation write-downs would cost ₹{int(result.depreciation_loss):,}. "
                f"A decisive markdown to ₹{rec_price:,} secures {result.clearance_probability*100:.0f}% clearance probability."
            )
            offline_advantage = (
                "Liquidating stock now frees working capital for purchasing high-margin initial allocations of the next generation model."
            )

        return {
            "headline": headline,
            "key_rationale": key_rationale,
            "offline_advantage": offline_advantage,
            "financial_summary": (
                f"Expected Revenue: ₹{int(result.expected_revenue):,} | "
                f"Expected Total Profit: ₹{int(result.expected_lifecycle_profit):,} | "
                f"Clearance Window: {result.projected_clearance_days:.0f} days"
            )
        }
