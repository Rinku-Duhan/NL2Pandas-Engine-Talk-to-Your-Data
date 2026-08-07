"""
charting.py
Responsible for:

Checking if an execution result is eligible for visualization.
Rendering clean, publication-ready matplotlib bar charts or line plots.
Saving charts as PNG files in the outputs/charts directory.
"""

import os
from typing import Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend suitable for CLI/headless runtimes
import matplotlib.pyplot as plt
import pandas as pd


def generate_chart(
    execution_result: Dict[str, Any],
    output_dir: str = "outputs/charts"
) -> Optional[str]:
    """
    Generate and save a PNG chart if execution result is chart-eligible.
    
    Parameters:
    - execution_result: Dictionary returned by executor.execute_plan.
    - output_dir: Directory path where generated PNG charts will be saved.
    
    Returns:
    - Saved chart file path (str) if successful, or None if not eligible/failed.
    """
    if not execution_result.get("chart_eligible", False):
        return None

    chart_meta = execution_result.get("chart_metadata")
    result_data = execution_result.get("result_data")

    if not chart_meta or not isinstance(result_data, pd.DataFrame) or result_data.empty:
        return None

    os.makedirs(output_dir, exist_ok=True)

    chart_type = chart_meta.get("chart_type", "bar")
    x_col = chart_meta.get("x_col")
    y_col = chart_meta.get("y_col")
    title = chart_meta.get("title", "Data Visualisation")

    if x_col not in result_data.columns or y_col not in result_data.columns:
        return None

    # Set up crisp visualization styling
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    
    try:
        if chart_type == "line":
            ax.plot(
                result_data[x_col].astype(str),
                result_data[y_col],
                marker="o",
                color="#1f77b4",
                linewidth=2,
                markersize=6
            )
            ax.grid(True, linestyle="--", alpha=0.5)
        else:  # bar chart
            bars = ax.bar(
                result_data[x_col].astype(str),
                result_data[y_col],
                color="#2ca02c",
                edgecolor="#1e6b1e",
                alpha=0.85
            )
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            
            # Annotate values above bars if < 12 items
            if len(result_data) <= 12:
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate(
                        f"{height:,.1f}" if isinstance(height, (int, float)) else str(height),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=8
                    )

        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel(x_col, fontsize=10, labelpad=8)
        ax.set_ylabel(y_col, fontsize=10, labelpad=8)

        # Rotate x-axis ticks if labels are long or numerous
        if len(result_data) > 4 or result_data[x_col].astype(str).str.len().max() > 8:
            plt.xticks(rotation=35, ha="right", fontsize=9)

        plt.tight_layout()

        # Generate unique filename based on title
        safe_title = "".join(c if c.isalnum() else "_" for c in title.lower())
        filename = f"{safe_title[:40]}.png"
        filepath = os.path.join(output_dir, filename)

        plt.savefig(filepath, format="png")
        plt.close(fig)

        return filepath

    except Exception as e:
        plt.close(fig)
        return None


if __name__ == "__main__":
    # Quick manual test
    test_df = pd.DataFrame({
        "Category": ["Technology", "Furniture", "Office Supplies"],
        "Sum of Sales": [12000, 8500, 15400]
    })
    
    mock_result = {
        "chart_eligible": True,
        "result_data": test_df,
        "chart_metadata": {
            "chart_type": "bar",
            "x_col": "Category",
            "y_col": "Sum of Sales",
            "title": "Sales by Category"
        }
    }
    
    chart_path = generate_chart(mock_result)
    print(f"Generated chart saved to: {chart_path}")