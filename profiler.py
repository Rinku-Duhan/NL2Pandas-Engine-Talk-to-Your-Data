"""
profiler.py

Responsible for:
1. Loading a CSV or Excel file into a pandas DataFrame.
2. Inferring column types (numeric / categorical / datetime).
3. Producing a structured profile (dict) used programmatically by the executor
   for column-existence checks.
4. Producing a compact, human-readable schema summary string that gets injected
   into the LLM planner prompt, so the planner can generalize to ANY dataset
   (not just the sample sales.csv) without hardcoding column names anywhere.

Design note: type inference is intentionally simple (pandas dtypes + a datetime
parse attempt) rather than a full statistical profiler. This keeps the profiler
fast and predictable for the 15-hour scope; see README tradeoffs section.
"""

import os
import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_dataset(file_path: str) -> pd.DataFrame:
    """
    Load a CSV or Excel file into a DataFrame.

    Raises:
        FileNotFoundError: if the path doesn't exist.
        ValueError: if the extension isn't supported or the file is empty/unreadable.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"Could not read '{file_path}': {e}")

    if df.empty:
        raise ValueError(f"'{file_path}' loaded but contains no rows.")

    # Best-effort cleanup: strip whitespace from column names.
    df.columns = [str(c).strip() for c in df.columns]

    return df


def _try_parse_datetime(series: pd.Series) -> bool:
    """
    Heuristic: treat a column as a datetime column if pandas can parse a
    sample of non-null values without a majority of failures, AND the column
    isn't already numeric (avoids misclassifying plain numbers like '2024' as dates).
    """
    if pd.api.types.is_numeric_dtype(series):
        return False
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    sample = series.dropna().astype(str).head(50)
    if sample.empty:
        return False

    try:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    except Exception:
        return False

    success_rate = parsed.notna().mean()
    return success_rate >= 0.8


def infer_column_types(df: pd.DataFrame) -> dict:
    """
    Classify every column as one of: 'numeric', 'datetime', 'categorical'.

    Returns:
        dict[str, str] mapping column name -> type label.
    """
    column_types = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            column_types[col] = "numeric"
        elif _try_parse_datetime(series):
            column_types[col] = "datetime"
        else:
            column_types[col] = "categorical"
    return column_types


def profile_dataset(df: pd.DataFrame) -> dict:
    """
    Build a structured profile of the dataset.

    Returns a dict with:
        - row_count, column_count
        - columns: {name: type}
        - null_counts: {name: count}
        - numeric_stats: {name: {min, max, mean}} for numeric columns
        - datetime_range: {name: {min, max}} for datetime columns
        - categorical_samples: {name: [top distinct values]} for categorical columns
        - sample_rows: list of first 3 rows as dicts
    """
    column_types = infer_column_types(df)

    numeric_stats = {}
    datetime_range = {}
    categorical_samples = {}

    for col, ctype in column_types.items():
        if ctype == "numeric":
            series = df[col].dropna()
            if not series.empty:
                numeric_stats[col] = {
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "mean": round(float(series.mean()), 2),
                }
        elif ctype == "datetime":
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed").dropna()
            if not parsed.empty:
                datetime_range[col] = {
                    "min": str(parsed.min().date()),
                    "max": str(parsed.max().date()),
                }
        else:  # categorical
            top_values = df[col].dropna().astype(str).value_counts().head(8).index.tolist()
            categorical_samples[col] = top_values

    profile = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": column_types,
        "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
        "numeric_stats": numeric_stats,
        "datetime_range": datetime_range,
        "categorical_samples": categorical_samples,
        "sample_rows": df.head(3).astype(str).to_dict(orient="records"),
    }
    return profile


def format_profile_for_llm(profile: dict) -> str:
    """
    Turn the structured profile into a compact text block to inject into the
    planner's system prompt. Kept concise (not the full dataset) to control
    token usage and keep the planner focused on schema, not raw data.
    """
    lines = []
    lines.append(f"Rows: {profile['row_count']}, Columns: {profile['column_count']}")
    lines.append("\nColumns and types:")
    for col, ctype in profile["columns"].items():
        nulls = profile["null_counts"].get(col, 0)
        line = f"  - {col} ({ctype}, {nulls} nulls)"

        if ctype == "numeric" and col in profile["numeric_stats"]:
            stats = profile["numeric_stats"][col]
            line += f" — range [{stats['min']}, {stats['max']}], mean {stats['mean']}"
        elif ctype == "datetime" and col in profile["datetime_range"]:
            dr = profile["datetime_range"][col]
            line += f" — range [{dr['min']} to {dr['max']}]"
        elif ctype == "categorical" and col in profile["categorical_samples"]:
            values = profile["categorical_samples"][col]
            line += f" — sample values: {values}"

        lines.append(line)

    lines.append("\nSample rows:")
    for row in profile["sample_rows"]:
        lines.append(f"  {row}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick manual check: `python profiler.py path/to/file.csv`
    import sys

    if len(sys.argv) != 2:
        print("Usage: python profiler.py <path_to_csv_or_excel>")
        sys.exit(1)

    df = load_dataset(sys.argv[1])
    profile = profile_dataset(df)
    print(format_profile_for_llm(profile))