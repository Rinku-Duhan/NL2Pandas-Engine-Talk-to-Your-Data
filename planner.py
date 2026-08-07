"""
planner.py
Responsible for generating a structured JSON plan using the Groq API.
"""

import json
import os
import re
from typing import Any, Dict
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

SYSTEM_PROMPT = """You are a deterministic SQL-style Query Planner for a pandas data analysis engine.
Your sole job is to translate a user's Natural Language Question into a structured JSON execution plan based strictly on the provided Dataset Profile.

DATASET PROFILE:
{profile_text}

JSON PLAN SCHEMA:
Return ONLY a single valid JSON object with the following keys and exact structure:

{{
  "operation": "aggregate" | "group_aggregate" | "filter_aggregate" | "top_n" | "correlation" | "time_series" | "unsupported",
  "target_column": "exact_column_name_or_null",
  "filters": [
    {{
      "column": "exact_column_name",
      "op": "==" | "!=" | ">" | "<" | ">=" | "<=" | "in" | "contains",
      "value": "filter_value_or_list"
    }}
  ],
  "group_by": "exact_column_name" | ["col1", "col2"] | null,
  "aggregation": "sum" | "mean" | "median" | "count" | "nunique" | "max" | "min" | "std" | "pct_share" | "null",
  "sort": "desc" | "asc" | "null",
  "limit": number_or_null,
  "date_column": "exact_column_name_or_null",
  "time_granularity": "month" | "quarter" | "year" | "null",
  "correlation_columns": ["col1", "col2"] | null,
  "reasoning": "short 1-sentence justification of the plan",
  "confidence": "high" | "low" | "unsupported"
}}

RULES FOR PLAN GENERATION:
1. TARGET COLUMN REQUIREMENT:
   - When a question asks about a specific entity or column (e.g., "how many regions/departments/categories are there?"), you MUST set "target_column" to that exact column name (e.g., "Region"). Do NOT set "target_column" to null.
   - Set "aggregation" to "nunique" when counting distinct entities.

2. MULTI-COLUMN GROUP BY:
   - For queries asking to group or break down by multiple attributes (e.g., "by department AND gender"), set "group_by" to a list of exact column names: ["Department", "Gender"].

3. AGGREGATION MAPPING RULES:
   - "nunique": Questions asking how many UNIQUE, DISTINCT, or DIFFERENT items exist.
   - "count": Total number of rows/records matching criteria.
   - "median": Questions asking for median, typical, or 50th percentile values.
   - "std": Questions asking for standard deviation, volatility, or variation.
   - "pct_share": Questions asking for proportion, share, or percentage of total.

4. COLUMN NAMES:
   - Must MATCH EXACTLY as spelled in the Dataset Profile (case-sensitive).

5. UNSUPPORTED PATTERNS:
   - If a question asks to compare individual row values against group-level statistics (e.g., "earns more than department average", "above team median"), set "operation" to "unsupported".

6. TOP_N RANKING RULES:
   - For queries asking for "top N [category] by [metric]" (e.g., "top 3 sub-categories by profit"):
     - "group_by": set to the category entity (e.g., "Sub-Category")
     - "target_column": set to the numeric metric column (e.g., "Profit" or "Sales")
     - "aggregation": "sum" or "mean"
     - "limit": N (e.g., 3)
   
   """


def generate_plan(
    question: str,
    profile_text: str,
    model_name: str = "llama-3.3-70b-versatile",
    retry: bool = True
) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables or .env file.")

    client = Groq(api_key=api_key)
    formatted_prompt = SYSTEM_PROMPT.format(profile_text=profile_text)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": f"USER QUESTION: {question}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        plan_raw = response.choices[0].message.content
        return json.loads(plan_raw)

    except Exception as e:
        if retry:
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": formatted_prompt},
                        {"role": "user", "content": f"USER QUESTION: {question}\n\nPrevious JSON error: {str(e)}. Return valid JSON ONLY."}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception:
                pass

        return {
            "operation": "unsupported",
            "target_column": None,
            "filters": [],
            "group_by": None,
            "aggregation": None,
            "sort": None,
            "limit": None,
            "date_column": None,
            "time_granularity": None,
            "correlation_columns": None,
            "reasoning": f"Groq Plan Generation Error: {str(e)}",
            "confidence": "unsupported"
        }