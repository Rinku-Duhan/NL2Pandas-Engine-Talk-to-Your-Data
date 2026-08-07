"""
executor.py
Responsible for:

Taking a pandas DataFrame and a structured JSON execution plan (from planner.py).
Validating column existence as a safety net.
Executing deterministic pandas calculations corresponding to the JSON plan.
Supporting mathematical primitives: sum, mean, median, std, min, max, count, nunique, pct_share.
Returning a structured result dictionary containing calculation output, markdown tables, and chart metadata.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union


def _validate_columns(df: pd.DataFrame, plan: Dict[str, Any]) -> Optional[str]:
    """Check if all columns referenced in the plan exist in the DataFrame."""
    df_cols = set(df.columns)
    raw_cols = set()

    if plan.get("target_column"):
        raw_cols.add(plan["target_column"])

    group_by = plan.get("group_by")
    if group_by:
        if isinstance(group_by, list):
            raw_cols.update(group_by)
        elif isinstance(group_by, str):
            raw_cols.add(group_by)

    if plan.get("date_column"):
        raw_cols.add(plan["date_column"])

    if plan.get("correlation_columns"):
        raw_cols.update(plan["correlation_columns"])

    for f in plan.get("filters", []):
        if isinstance(f, dict) and "column" in f:
            raw_cols.add(f["column"])

    # Clean set filtering out None or empty values safely
    referenced_cols = {c for c in raw_cols if c and isinstance(c, str)}

    missing = referenced_cols - df_cols
    if missing:
        return f"Columns not found in dataset: {sorted(list(missing))}"
    return None


def _apply_filters(df: pd.DataFrame, filters: list, filter_logic: str = "AND") -> pd.DataFrame:
    if not filters:
        return df.copy()

    if filter_logic == "OR":
        or_masks = []
        for f in filters:
            col, op, val = f.get("column"), f.get("op"), f.get("value")
            if not col or col not in df.columns or val is None:
                continue
            if op == "==":
                or_masks.append(df[col].astype(str).str.lower() == str(val).lower())
            elif op == "in" and isinstance(val, list):
                or_masks.append(df[col].isin(val))

        if or_masks:
            combined_mask = pd.concat(or_masks, axis=1).any(axis=1)
            return df[combined_mask]

    # Default sequential AND filtering
    filtered_df = df.copy()
    for f in filters:
        col, op, val = f.get("column"), f.get("op"), f.get("value")
        if not col or col not in filtered_df.columns or val is None:
            continue
        if op == "==":
            filtered_df = filtered_df[filtered_df[col].astype(str).str.lower() == str(val).lower()]
        elif op == "in" and isinstance(val, list):
            filtered_df = filtered_df[filtered_df[col].isin(val)]

    return filtered_df


def _apply_aggregation(series: pd.Series, agg_func: Optional[str]) -> Union[float, int]:
    """Safely apply mathematical aggregate functions to a pandas series."""
    if series.empty:
        return 0

    if agg_func == "sum":
        return float(series.sum())
    elif agg_func in ["mean", "avg"]:
        return float(series.mean())
    elif agg_func == "median":
        return float(series.median())
    elif agg_func == "count":
        return int(series.count())
    elif agg_func in ["nunique", "distinct", "count_distinct"]:
        return int(series.nunique())
    elif agg_func == "max":
        return float(series.max())
    elif agg_func == "min":
        return float(series.min())
    elif agg_func in ["std", "stddev"]:
        return float(series.std())
    else:
        raise ValueError(f"Unsupported aggregation type: '{agg_func}'")


def execute_plan(df: pd.DataFrame, plan: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a structured JSON plan against a DataFrame."""
    if not isinstance(plan, dict):
        return {
            "success": False,
            "operation": "unknown",
            "result_data": None,
            "markdown_table": None,
            "chart_eligible": False,
            "chart_metadata": None,
            "error": "Plan provided to executor is not a valid JSON dictionary."
        }

    # Sanitize literal string 'null'/'none' values from LLM into Python None
    for k, v in list(plan.items()):
        if isinstance(v, str) and v.lower() in ["null", "none", ""]:
            plan[k] = None
        elif isinstance(v, list):
            plan[k] = [item for item in v if str(item).lower() not in ["null", "none", ""]]

    operation = plan.get("operation")
    # ... rest of execute_plan remains unchanged ...

    if operation == "unsupported":
        return {
            "success": False,
            "operation": operation,
            "result_data": None,
            "markdown_table": None,
            "chart_eligible": False,
            "chart_metadata": None,
            "error": plan.get("reasoning", "Question is unsupported based on dataset schema.")
        }

    try:
        col_error = _validate_columns(df, plan)
        if col_error:
            return {
                "success": False,
                "operation": operation,
                "result_data": None,
                "markdown_table": None,
                "chart_eligible": False,
                "chart_metadata": None,
                "error": col_error
            }

        filters = plan.get("filters", [])
        work_df = _apply_filters(df, filters)
        
        if work_df.empty:
            return {
                "success": True,
                "operation": operation,
                "result_data": 0,
                "markdown_table": "No rows matched the specified filters.",
                "chart_eligible": False,
                "chart_metadata": None,
                "error": None
            }

        target_col = plan.get("target_column")
        agg_type = plan.get("aggregation")
        group_col = plan.get("group_by")
        sort_dir = plan.get("sort", "desc")
        limit = plan.get("limit")

        if isinstance(group_col, list) and len(group_col) == 1:
            group_col = group_col[0]

        # Case A: Scalar Aggregation (Single Number Result)
        if operation in ["aggregate", "filter_aggregate"] and not group_col:
            if not target_col and agg_type in ["nunique", "distinct", "count_distinct"]:
                cat_cols = list(work_df.select_dtypes(include=['object', 'category']).columns)
                target_col = cat_cols[0] if cat_cols else work_df.columns[0]

            if agg_type == "count" and not target_col:
                val = len(work_df)
                res_df = pd.DataFrame([{"Total Rows Count": val}])

            elif agg_type in ["nunique", "distinct", "count_distinct"] and target_col:
                val = int(work_df[target_col].nunique())
                res_df = pd.DataFrame([{f"Unique {target_col} Count": val}])

            elif agg_type == "pct_share" and target_col:
                overall_total = df[target_col].sum() if pd.api.types.is_numeric_dtype(df[target_col]) else len(df)
                filtered_total = work_df[target_col].sum() if pd.api.types.is_numeric_dtype(work_df[target_col]) else len(work_df)
                pct = (filtered_total / overall_total * 100) if overall_total != 0 else 0.0
                
                val = round(pct, 2)
                res_df = pd.DataFrame([{
                    "Filtered Value": round(filtered_total, 2) if isinstance(filtered_total, float) else filtered_total,
                    "Overall Total": round(overall_total, 2) if isinstance(overall_total, float) else overall_total,
                    "Percentage Share (%)": val
                }])

            else:
                val = _apply_aggregation(work_df[target_col], agg_type)
                val_rounded = round(val, 2) if isinstance(val, float) else val
                res_df = pd.DataFrame([{f"{agg_type.capitalize()} of {target_col}": val_rounded}])

            return {
                "success": True,
                "operation": operation,
                "result_data": val,
                "markdown_table": res_df.to_markdown(index=False),
                "chart_eligible": False,
                "chart_metadata": None,
                "error": None
            }

        # Case B: Grouped Aggregation
        elif operation in ["group_aggregate", "filter_aggregate"] or (operation == "aggregate" and group_col):
            agg_col_name = f"{agg_type.capitalize()} of {target_col}" if target_col else "Count"

            if agg_type in ["nunique", "distinct", "count_distinct"] and target_col:
                res_df = work_df.groupby(group_col)[target_col].nunique().reset_index(name=agg_col_name)

            elif agg_type == "count" and not target_col:
                res_df = work_df.groupby(group_col).size().reset_index(name=agg_col_name)

            elif agg_type == "median":
                res_df = work_df.groupby(group_col)[target_col].median().reset_index(name=agg_col_name)

            elif agg_type in ["std", "stddev"]:
                res_df = work_df.groupby(group_col)[target_col].std().reset_index(name=agg_col_name)

            else:
                actual_agg = agg_type if agg_type and agg_type not in ["mean", "avg"] else "mean"
                res_df = work_df.groupby(group_col)[target_col].agg(actual_agg).reset_index(name=agg_col_name)

            if pd.api.types.is_numeric_dtype(res_df[agg_col_name]):
                res_df[agg_col_name] = res_df[agg_col_name].round(2)

            ascending = (sort_dir == "asc")
            res_df = res_df.sort_values(by=agg_col_name, ascending=ascending)

            if limit and isinstance(limit, int):
                res_df = res_df.head(limit)

            chart_eligible = isinstance(group_col, str) and len(res_df) > 1

            return {
                "success": True,
                "operation": operation,
                "result_data": res_df,
                "markdown_table": res_df.to_markdown(index=False),
                "chart_eligible": chart_eligible,
                "chart_metadata": {
                    "chart_type": "bar",
                    "x_col": group_col if isinstance(group_col, str) else group_col[0],
                    "y_col": agg_col_name,
                    "title": f"{agg_col_name} by {group_col if isinstance(group_col, str) else ', '.join(group_col)}"
                } if chart_eligible else None,
                "error": None
            }

        # ---------------------------------------------------------
        # Case C: Top N Rankings
        # ---------------------------------------------------------
        elif operation == "top_n":
            top_limit = limit if limit else 5
            ascending = (sort_dir == "asc")

            # Fallback if target_column is string or identical to group_by
            if group_col and (not target_col or target_col == group_col or not pd.api.types.is_numeric_dtype(work_df[target_col])):
                numeric_cols = list(work_df.select_dtypes(include=[np.number]).columns)
                if numeric_cols:
                    # Prefer Profit or Sales if present
                    if "Profit" in numeric_cols:
                        target_col = "Profit"
                    elif "Sales" in numeric_cols:
                        target_col = "Sales"
                    else:
                        target_col = numeric_cols[0]

            if group_col and target_col:
                agg_type_str = agg_type if agg_type else "sum"
                agg_col_name = f"{agg_type_str.capitalize()} of {target_col}"
                actual_agg = agg_type_str if agg_type_str not in ["mean", "avg"] else "mean"
                
                if agg_type_str in ["nunique", "distinct"]:
                    res_df = work_df.groupby(group_col)[target_col].nunique().reset_index(name=agg_col_name)
                else:
                    res_df = work_df.groupby(group_col)[target_col].agg(actual_agg).reset_index(name=agg_col_name)

                if pd.api.types.is_numeric_dtype(res_df[agg_col_name]):
                    res_df[agg_col_name] = res_df[agg_col_name].round(2)

                res_df = res_df.sort_values(by=agg_col_name, ascending=ascending).head(top_limit)
                x_c = group_col if isinstance(group_col, str) else group_col[0]
                y_c = agg_col_name
            else:
                sort_col = target_col if target_col else work_df.columns[0]
                res_df = work_df.sort_values(by=sort_col, ascending=ascending).head(top_limit)
                x_c = group_col if group_col and isinstance(group_col, str) else res_df.columns[0]
                y_c = sort_col

            return {
                "success": True,
                "operation": operation,
                "result_data": res_df,
                "markdown_table": res_df.to_markdown(index=False),
                "chart_eligible": True,
                "chart_metadata": {
                    "chart_type": "bar",
                    "x_col": x_c,
                    "y_col": y_c,
                    "title": f"Top {top_limit} {y_c}"
                },
                "error": None
            }

        # Case D: Time Series
        elif operation == "time_series":
            date_col = plan.get("date_column")
            granularity = plan.get("time_granularity", "month")
            
            if not date_col or date_col not in work_df.columns:
                datetime_cols = [c for c in work_df.columns if pd.api.types.is_datetime64_any_dtype(work_df[c])]
                if datetime_cols:
                    date_col = datetime_cols[0]
                else:
                    raise ValueError("No valid date_column found for time_series operation.")

            work_df[date_col] = pd.to_datetime(work_df[date_col], errors="coerce")
            work_df = work_df.dropna(subset=[date_col])

            freq_map = {"month": "ME", "quarter": "QE", "year": "YE"}
            freq = freq_map.get(granularity, "ME")

            work_df.set_index(date_col, inplace=True)
            agg_col_name = f"{agg_type.capitalize()} of {target_col}" if target_col else "Count"
            
            if agg_type == "count" or not target_col:
                res_series = work_df.resample(freq).size()
            elif agg_type in ["nunique", "distinct"]:
                res_series = work_df[target_col].resample(freq).nunique()
            else:
                actual_agg = agg_type if agg_type and agg_type not in ["mean", "avg"] else "mean"
                res_series = work_df[target_col].resample(freq).agg(actual_agg)

            res_df = res_series.reset_index()
            res_df.columns = ["Period", agg_col_name]
            
            if granularity == "year":
                res_df["Period"] = res_df["Period"].dt.strftime("%Y")
            else:
                res_df["Period"] = res_df["Period"].dt.strftime("%Y-%m")

            if pd.api.types.is_numeric_dtype(res_df[agg_col_name]):
                res_df[agg_col_name] = res_df[agg_col_name].round(2)

            return {
                "success": True,
                "operation": operation,
                "result_data": res_df,
                "markdown_table": res_df.to_markdown(index=False),
                "chart_eligible": True,
                "chart_metadata": {
                    "chart_type": "line",
                    "x_col": "Period",
                    "y_col": agg_col_name,
                    "title": f"{agg_col_name} Trend over Time ({granularity.capitalize()})"
                },
                "error": None
            }

        # Case E: Correlation
        elif operation == "correlation":
            corr_cols = plan.get("correlation_columns", [])
            if len(corr_cols) < 2:
                numeric_cols = list(work_df.select_dtypes(include=[np.number]).columns)
                if len(numeric_cols) >= 2:
                    corr_cols = numeric_cols[:2]
                else:
                    raise ValueError("Correlation requires at least two valid numeric columns.")

            corr_val = work_df[corr_cols[0]].corr(work_df[corr_cols[1]])
            res_df = pd.DataFrame([{
                "Column 1": corr_cols[0],
                "Column 2": corr_cols[1],
                "Correlation (Pearson)": round(float(corr_val), 4) if not pd.isna(corr_val) else 0.0
            }])

            return {
                "success": True,
                "operation": operation,
                "result_data": corr_val,
                "markdown_table": res_df.to_markdown(index=False),
                "chart_eligible": False,
                "chart_metadata": None,
                "error": None
            }

        else:
            raise ValueError(f"Unknown or missing operation type: '{operation}'")

    except Exception as e:
        return {
            "success": False,
            "operation": operation if 'operation' in locals() else "unknown",
            "result_data": None,
            "markdown_table": None,
            "chart_eligible": False,
            "chart_metadata": None,
            "error": f"Execution error: {str(e)}"
        }