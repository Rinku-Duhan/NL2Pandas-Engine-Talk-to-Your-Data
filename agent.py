"""
agent.py
CLI entrypoint and interactive loop for the CSV/Excel QA Agent.

Workflow per question:
1. Generate JSON plan from natural language prompt (planner.py).
2. Execute plan deterministically against pandas DataFrame (executor.py).
3. Validate execution & trigger 1-retry if plan/execution fails (validator.py).
4. Synthesize plain-English explanation grounded strictly in calculated evidence.
5. Render PNG chart if result is chart-eligible (charting.py).
6. Print tabular evidence & explanation to CLI console.
7. Append formatted transcript entry to outputs/transcript.md.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

import profiler
import planner
import executor
import validator
import charting


TRANSCRIPT_PATH = os.path.join("outputs", "transcript.md")


def _init_transcript(file_path: str, dataset_name: str, row_count: int, col_count: int) -> None:
    """Initialize transcript file with session header if it doesn't exist."""
    os.makedirs(os.path.dirname(TRANSCRIPT_PATH), exist_ok=True)
    if not os.path.exists(TRANSCRIPT_PATH):
        with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
            f.write("# QA Agent Session Transcript\n\n")
            f.write(f"- **Dataset:** `{dataset_name}`\n")
            f.write(f"- **Rows:** {row_count} | **Columns:** {col_count}\n")
            f.write(f"- **Session Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")


def _log_to_transcript(
    question: str,
    plan: Dict[str, Any],
    exec_res: Dict[str, Any],
    explanation: str,
    chart_path: Optional[str]
) -> None:
    """Append a structured Q&A record to the Markdown transcript log."""
    with open(TRANSCRIPT_PATH, "a", encoding="utf-8") as f:
        f.write(f"### Question: {question}\n\n")
        f.write("**Execution Plan (JSON):**\n```json\n")
        f.write(json.dumps(plan, indent=2))
        f.write("\n```\n\n")

        f.write("**Calculated Evidence Table:**\n")
        if exec_res.get("markdown_table"):
            f.write(f"{exec_res['markdown_table']}\n\n")
        else:
            f.write(f"_No tabular output (Error: {exec_res.get('error')})_\n\n")

        f.write(f"**Explanation:**\n{explanation}\n\n")

        if chart_path:
            f.write(f"**Generated Chart:** `![]({chart_path})`\n\n")

        f.write("---\n\n")


def process_question(
    question: str,
    df,
    profile_str: str,
    interactive: bool = True
) -> Dict[str, Any]:
    """
    Process a single natural language question through the pipeline.
    """
    if interactive:
        print("\n" + "=" * 60)
        print(f" QUESTION: {question}")
        print("=" * 60)
        print(" -> Generating execution plan...")

    # Step 1: Generate initial execution plan
    plan = planner.generate_plan(question, profile_str, retry=True)
    
    # Step 2: Execute plan
    if interactive:
        print(" -> Executing plan against pandas dataset...")
    exec_res = executor.execute_plan(df, plan)

    # Step 3: Validate & 1-Retry logic on execution failure
    is_valid, err_msg = validator.validate_execution(exec_res)
    if not is_valid and plan.get("operation") != "unsupported":
        if interactive:
            print(f" -> Plan execution failed ({err_msg}). Retrying plan generation (1-retry budget)...")
        
        # Re-prompt planner with execution error context
        retry_prompt = f"{question} (Note: Previous attempt failed with error: '{err_msg}'. Adjust column names/filters)."
        plan = planner.generate_plan(retry_prompt, profile_str, retry=False)
        exec_res = executor.execute_plan(df, plan)

    # Step 4: Synthesize Plain-English Explanation
    if interactive:
        print(" -> Synthesizing explanation...")
    explanation = validator.synthesize_explanation(question, plan, exec_res)

    # Step 5: Render PNG Chart if eligible
    chart_path = None
    if exec_res.get("chart_eligible", False):
        if interactive:
            print(" -> Rendering chart visualization...")
        chart_path = charting.generate_chart(exec_res)

    # Step 6: Console Output Display
    if interactive:
        print("\n" + "-" * 40)
        print(" EVIDENCE TABLE:")
        print("-" * 40)
        if exec_res.get("markdown_table"):
            print(exec_res["markdown_table"])
        else:
            print(f"N/A ({exec_res.get('error', 'No table output')})")

        print("\n" + "-" * 40)
        print(" ANSWER / EXPLANATION:")
        print("-" * 40)
        print(explanation)

        if chart_path:
            print(f"\n Chart saved to: {chart_path}")
        print("-" * 40 + "\n")

    # Step 7: Log entry to transcript file
    _log_to_transcript(question, plan, exec_res, explanation, chart_path)

    return {
        "question": question,
        "plan": plan,
        "execution": exec_res,
        "explanation": explanation,
        "chart_path": chart_path
    }


def main():
    parser = argparse.ArgumentParser(
        description="CLI Agent for natural language Q&A on tabular datasets (CSV/Excel)."
    )
    parser.add_argument(
        "--file", "-f", required=True, help="Path to input CSV or Excel file."
    )
    parser.add_argument(
        "--question", "-q", required=False, help="Single question to run non-interactively."
    )

    args = parser.parse_args()

    # Step 0: Load dataset & compute profile
    print(f"\n Loading dataset from '{args.file}'...")
    try:
        df = profiler.load_dataset(args.file)
        profile_dict = profiler.profile_dataset(df)
        profile_str = profiler.format_profile_for_llm(profile_dict)
    except Exception as e:
        print(f"\n Error loading dataset: {e}")
        sys.exit(1)

    dataset_name = os.path.basename(args.file)
    _init_transcript(args.file, dataset_name, profile_dict["row_count"], profile_dict["column_count"])

    print(f" Dataset loaded: {profile_dict['row_count']} rows, {profile_dict['column_count']} columns.")
    print(f" Transcript log initialized at '{TRANSCRIPT_PATH}'.\n")

    # Single-question mode
    if args.question:
        process_question(args.question, df, profile_str, interactive=True)
        sys.exit(0)

    # Interactive CLI Loop mode
    print("=" * 60)
    print(" Interactive CSV QA Agent Ready!")
    print(" Type your question in plain English, or type 'exit' or 'quit' to end.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nQ: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n Exiting QA Agent session. All Q&A logged to transcript. Goodbye!")
                break

            process_question(user_input, df, profile_str, interactive=True)

        except (KeyboardInterrupt, EOFError):
            print("\n Session terminated by user.")
            break


if __name__ == "__main__":
    main()