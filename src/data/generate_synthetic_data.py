import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import timedelta, date

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.utils.config import *

class SyntheticDataGenerator:
    """Generates realistic e-commerce sales data."""
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(self.seed)
        
        self.products = {
            "PROD_001": {"name": "Wireless Earbuds", "category": "Electronics", "cost": 400, "base_price": 899, "base_demand": 15, "elasticity": 2.2, "competitor": 799, "rating_mean": 4.5, "review_growth_rate": 0.5},
            "PROD_002": {"name": "Phone Case", "category": "Electronics", "cost": 100, "base_price": 299, "base_demand": 40, "elasticity": 2.5, "competitor": 249, "rating_mean": 4.1, "review_growth_rate": 0.8},
            "PROD_003": {"name": "Cotton T-Shirt", "category": "Apparel", "cost": 200, "base_price": 499, "base_demand": 25, "elasticity": 1.8, "competitor": 449, "rating_mean": 4.3, "review_growth_rate": 0.6},
            "PROD_004": {"name": "Yoga Mat", "category": "Sports", "cost": 350, "base_price": 799, "base_demand": 10, "elasticity": 1.5, "competitor": 749, "rating_mean": 4.6, "review_growth_rate": 0.3},
            "PROD_005": {"name": "Organic Face Wash", "category": "Beauty", "cost": 80, "base_price": 249, "base_demand": 35, "elasticity": 1.2, "competitor": 199, "rating_mean": 4.2, "review_growth_rate": 0.7}
        }
        
    def _get_season(self, dt: date) -> str:
        """Determines the season based on month."""
        month = dt.month
        if month in [3, 4, 5, 6]:
            return "Summer"
        elif month in [7, 8, 9]:
            return "Monsoon"
        elif month in [11, 12, 1, 2]:
            return "Winter"
        return "Other"

    def _get_season_multiplier(self, dt: date) -> float:
        """Returns the multiplier based on the season and month."""
        month = dt.month
        if month in [10, 11]:  # Roughly Festival Season
            return 1.3
        season = self._get_season(dt)
        season_mult = {"Summer": 1.0, "Monsoon": 0.85, "Winter": 1.05, "Other": 1.0}
        return season_mult.get(season, 1.0)
        
    def generate(self, start_date_str: str = "2023-01-01", end_date_str: str = "2024-12-31") -> pd.DataFrame:
        """Generate synthetic sales data."""
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        delta = end_date - start_date
        days = delta.days + 1
        
        # Load festivals
        festivals = {}
        fest_path = Path(__file__).resolve().parent.parent.parent / "data" / "external" / "indian_festivals.json"
        try:
            with open(fest_path, 'r') as f:
                fest_data = json.load(f)
                for item in fest_data:
                    festivals[item['date']] = item
        except FileNotFoundError:
            pass # No festivals found, will proceed without them
            
        data = []
        for day_num in range(days):
            current_date = start_date + timedelta(days=day_num)
            date_str = current_date.isoformat()
            
            day_of_week = current_date.weekday()
            is_weekend = int(day_of_week >= 5)
            weekend_mult = np.random.uniform(1.25, 1.35) if is_weekend else 1.0
            
            fest_info = festivals.get(date_str)
            is_festival = 1 if fest_info else 0
            festival_name = fest_info['name'] if fest_info else None
            festival_mult = fest_info.get('demand_multiplier', 1.0) if fest_info else 1.0
            
            month = current_date.month
            season = self._get_season(current_date)
            season_mult = self._get_season_multiplier(current_date)
            
            trend = 1 + 0.0003 * day_num
            
            for prod_id, prod in self.products.items():
                comp_base = prod["competitor"]
                comp_price = comp_base * (1 + np.random.uniform(-0.15, 0.15))
                
                num_reviews = 50 + prod["review_growth_rate"] * day_num + np.random.normal(0, 2)
                num_reviews = max(0, int(num_reviews))
                
                rating = np.clip(np.random.normal(prod["rating_mean"], 0.2), 1.0, 5.0)
                
                num_prices = np.random.randint(5, 8) # 5-7 prices
                for _ in range(num_prices):
                    selling_price = prod["base_price"] * np.random.uniform(0.8, 1.2)
                    
                    noise = np.random.lognormal(0, 0.15)
                    competitor_effect = (comp_price / selling_price) ** 0.5
                    
                    demand = prod["base_demand"] * ((selling_price / prod["base_price"]) ** -prod["elasticity"]) * \
                             weekend_mult * festival_mult * season_mult * competitor_effect * trend * noise
                             
                    units_sold = int(np.round(max(0, demand)))
                    
                    discount_pct = max(0, 1 - selling_price / prod["base_price"]) * 100
                    ad_spend = np.random.uniform(50, 500)
                    revenue = selling_price * units_sold
                    profit = (selling_price - prod["cost"]) * units_sold
                    
                    data.append({
                        "date": date_str,
                        "product_id": prod_id,
                        "product_name": prod["name"],
                        "product_category": prod["category"],
                        "cost_price": prod["cost"],
                        "selling_price": round(selling_price, 2),
                        "units_sold": units_sold,
                        "competitor_price": round(comp_price, 2),
                        "day_of_week": day_of_week,
                        "is_weekend": is_weekend,
                        "is_festival": is_festival,
                        "festival_name": festival_name,
                        "month": month,
                        "season": season,
                        "discount_pct": round(discount_pct, 2),
                        "rating": round(rating, 2),
                        "num_reviews": num_reviews,
                        "ad_spend": round(ad_spend, 2),
                        "revenue": round(revenue, 2),
                        "profit": round(profit, 2)
                    })
                    
        df = pd.DataFrame(data)
        return df

if __name__ == '__main__':
    generator = SyntheticDataGenerator(seed=42)
    print("Generating synthetic data...")
    df = generator.generate()
    
    output_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sales_data.csv"
    
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} rows of synthetic data and saved to {output_path}")
