"""
generate_hr_data.py
Generates a synthetic HR dataset for testing dynamic schema generalization.
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd

def generate_hr_dataset(num_rows: int = 500, output_path: str = "data/sample_hr.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    random.seed(42)
    
    first_names_f = ["Sarah", "Emily", "Rachel", "Priya", "Jessica", "Amanda", "Laura", "Megan", "Sophia", "Olivia"]
    first_names_m = ["Michael", "David", "James", "Robert", "Daniel", "Christopher", "Brian", "Alex", "Ethan", "William"]
    last_names = ["Jenkins", "Chang", "Rodriguez", "Kim", "Adams", "Wilson", "Patel", "Taylor", "Brown", "Lee", "Hall", "Allen"]

    dept_title_map = {
        "Engineering": [("Software Engineer", 85000, 120000), ("Senior Software Engineer", 120000, 160000), ("DevOps Engineer", 95000, 140000)],
        "Human Resources": [("Recruiter", 60000, 85000), ("HR Business Partner", 80000, 110000), ("HR Director", 130000, 170000)],
        "Sales": [("Sales Representative", 65000, 90000), ("Account Executive", 90000, 130000), ("Sales Director", 140000, 185000)],
        "Marketing": [("Marketing Specialist", 60000, 80000), ("Marketing Manager", 95000, 130000), ("SEO Analyst", 70000, 95000)],
        "Data Analytics": [("BI Analyst", 75000, 100000), ("Data Scientist", 105000, 150000), ("Data Engineer", 100000, 145000)],
        "Finance": [("Financial Analyst", 75000, 105000), ("Senior Accountant", 85000, 115000), ("Finance Director", 140000, 190000)]
    }

    start_date = datetime(2015, 1, 1)
    end_date = datetime(2024, 12, 31)
    days_range = (end_date - start_date).days

    data = []
    for i in range(1, num_rows + 1):
        gender = random.choice(["Female", "Male"])
        first_name = random.choice(first_names_f if gender == "Female" else first_names_m)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"

        dept = random.choice(list(dept_title_map.keys()))
        title_info = random.choice(dept_title_map[dept])
        title = title_info[0]
        salary = round(random.uniform(title_info[1], title_info[2]), -2)

        hire_date = start_date + timedelta(days=random.randint(0, days_range))
        years_exp = max(1, round((datetime(2025, 1, 1) - hire_date).days / 365.25) + random.randint(0, 5))
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 45, 30, 10])[0]

        data.append({
            "Employee ID": f"EMP-{1000 + i}",
            "Full Name": full_name,
            "Department": dept,
            "Job Title": title,
            "Gender": gender,
            "Hire Date": hire_date.strftime("%Y-%m-%d"),
            "Salary": salary,
            "Performance Rating": rating,
            "Years Experience": years_exp
        })

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Generated {num_rows} HR records saved to '{output_path}'.")

if __name__ == "__main__":
    generate_hr_dataset()