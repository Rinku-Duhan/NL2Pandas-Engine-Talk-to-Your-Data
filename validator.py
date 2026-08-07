"""
validator.py
Responsible for:
1. Validating execution results returned by executor.py.
2. Synthesizing a clear, natural language explanation of the results using the Groq API.
3. Enforcing anti-hallucination guardrails so explanations strictly reflect calculated data.
"""

import os
import json
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

EXPLANATION_PROMPT = """You are a grounded Data Analysis Synthesizer. Your task is to explain the pandas execution results in clear, concise natural language strictly based on the provided Evidence Table and Execution Plan.

USER QUESTION: {question}

EXECUTION PLAN:
{plan_json}

EVIDENCE TABLE / RESULT DATA:
{result_table}

STRICT GROUNDING RULES:
1. Grounding: Answer ONLY using the numbers and facts present in the Evidence Table. Do not invent or assume figures outside the provided data.
2. Direct Answer: State the core numerical finding in the very first sentence.
3. Clarity & Formatting: Present numerical values clearly (e.g., format currency like $12,345.50 if applicable).
4. Unanswered/Unsupported: If the Evidence Table shows "No rows matched" or N/A, explain clearly that no matching data was found or the condition could not be calculated based on the dataset.
5. Context Check: If the evidence table contains only raw counts or basic totals without showing the specific comparative sub-condition asked in the question, state that the specific condition could not be calculated rather than assuming all rows met the criteria.
"""


def validate_execution(execution_result: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Validate whether the pandas execution succeeded or produced a recoverable error.
    Defensively guards against None or non-dictionary result objects.
    """
    if execution_result is None or not isinstance(execution_result, dict):
        return False, "Execution failed: executor returned empty or invalid result object."

    if not execution_result.get("success", False):
        error_msg = execution_result.get("error", "Unknown execution error.")
        return False, f"Execution failed: {error_msg}"

    res_data = execution_result.get("result_data")
    if res_data is None:
        return False, "Execution succeeded but produced empty result data."

    return True, "Execution valid."


def synthesize_explanation(
    question: str,
    plan: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]],
    model_name: str = "llama-3.3-70b-versatile"
) -> str:
    """
    Synthesize a natural language explanation from execution results using Groq API.
    Includes defensive checks for NoneType or failed execution results.
    """
    # Defensive guard for None or non-dictionary execution results
    if execution_result is None or not isinstance(execution_result, dict):
        return "Cannot answer question: Plan execution failed to return a valid result object."

    if not execution_result.get("success", False):
        error_msg = execution_result.get("error", "Unknown execution error.")
        return f"Cannot answer question: {error_msg}"

    table_str = execution_result.get("markdown_table")
    if not table_str or str(table_str).strip() == "":
        table_str = f"Result Value: {execution_result.get('result_data', 'N/A')}"

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fallback to pure markdown table if API key is missing
        return f"Calculated Result:\n\n{table_str}"

    client = Groq(api_key=api_key)

    formatted_prompt = EXPLANATION_PROMPT.format(
        question=question,
        plan_json=json.dumps(plan, indent=2),
        result_table=table_str
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You synthesize accurate data explanations strictly based on provided evidence tables."},
                {"role": "user", "content": formatted_prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        # Retry with smaller model if primary fails
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You synthesize accurate data explanations strictly based on provided evidence tables."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Calculated Result:\n\n{table_str}"