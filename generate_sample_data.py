"""
generate_sample_data.py
Script to generate a synthetic Superstore-style sales dataset for testing.
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd

def generate_sales_dataset(num_rows: int = 500, output_path: str = "data/sample_sales.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    random.seed(42)
    regions = ["West", "East", "Central", "South"]
    segments = ["Consumer", "Corporate", "Home Office"]
    
    catalog = {
        "Technology": ["Phones", "Accessories", "Machines", "Copiers"],
        "Furniture": ["Chairs", "Tables", "Bookcases", "Furnishings"],
        "Office Supplies": ["Binders", "Paper", "Storage", "Art", "Appliances"]
    }

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range_days = (end_date - start_date).days

    data = []
    for i in range(1, num_rows + 1):
        cat = random.choice(list(catalog.keys()))
        sub_cat = random.choice(catalog[cat])
        region = random.choice(regions)
        segment = random.choice(segments)
        
        order_date = start_date + timedelta(days=random.randint(0, date_range_days))
        order_id = f"CA-{order_date.year}-{1000 + i}"
        
        quantity = random.randint(1, 10)
        discount = random.choice([0.0, 0.0, 0.0, 0.05, 0.1, 0.15, 0.2])
        
        base_price_map = {
            "Technology": random.uniform(80, 800),
            "Furniture": random.uniform(100, 600),
            "Office Supplies": random.uniform(10, 150)
        }
        
        unit_price = base_price_map[cat]
        sales = round(unit_price * quantity * (1 - discount), 2)
        
        # Profit calculation with occasional negative profit on high discounts
        margin = random.uniform(0.15, 0.35) - (discount * 1.2)
        profit = round(sales * margin, 2)
        
        data.append({
            "Order ID": order_id,
            "Order Date": order_date.strftime("%Y-%m-%d"),
            "Region": region,
            "Category": cat,
            "Sub-Category": sub_cat,
            "Segment": segment,
            "Sales": sales,
            "Quantity": quantity,
            "Discount": discount,
            "Profit": profit
        })

    df = pd.DataFrame(data)
    df = df.sort_values(by="Order Date").reset_index(drop=True)
    df.to_csv(output_path, index=False)
    print(f"Generated dataset with {num_rows} rows saved to '{output_path}'.")

if __name__ == "__main__":
    generate_sales_dataset()