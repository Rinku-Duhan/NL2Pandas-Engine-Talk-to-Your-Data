# NL2Pandas Engine: Talk to Your Data

An easy-to-use, secure tool that lets you ask questions about your data in plain English and get instant, accurate answers with tables and charts.

Instead of guessing or doing math in the background, this tool translates your question into a clear action plan and lets **Pandas** handle all calculations. This guarantees **100% accurate math with zero AI hallucinations**.

---

## 🌟 Introduction

Analyzing spreadsheets usually requires writing complex Excel formulas or Python code. While AI models are great at understanding plain English, they are notoriously bad at doing exact math on huge datasets—often making up numbers or hallucinating totals.

**NL2Pandas Engine** solves this problem by splitting the job into two roles:

1. **The Planner (LLM):** Understands what you are asking and picks the right steps.
2. **The Worker (Pandas):** Runs the actual code and calculates the numbers on your computer.

Whether you are looking at sales reports, employee records, or inventory lists, you can just ask questions in normal language and get verified answers.

---
> **Agent Capability Statement:**  
> My agent takes a **natural language question and a CSV/Excel dataset** and produces a **verified numerical answer, evidence table, and chart visualization using deterministic Pandas execution.**


## 💡 Key Design Decisions: Why We Built It This Way

When designing this system, specific technical choices is made to ensure safety, speed, and accuracy:

* **Why use Pandas for math instead of the LLM?**
AI models predict text—they don't "calculate." Asking an AI to sum 10,000 rows leads to wrong numbers. Passing the data to Pandas ensures exact, mathematical precision every single time.
* **Why use structured JSON plans instead of generating raw Python code (`eval()`)?**
Allowing an AI to generate and execute freeform Python code on your machine is a massive security risk (it could delete files or run malicious commands). Using a fixed list of allowed operations (like `sum`, `mean`, `group_by`) keeps execution completely safe.
* **Why send a "Dataset Profile" instead of the whole spreadsheet to the AI?**
Sending thousands of rows to an AI API is expensive, slow, and breaches data privacy. We only send column names, data types, and brief summary statistics. Your actual data rows stay private on your local machine.

---

## 🔄 How It Works

Here is what happens under the hood when you ask a question:

```
 ┌────────────────┐     ┌─────────────────┐     ┌────────────────┐
 │ 1. Load Data   ├────>│ 2. Build Schema ├────>│ 3. User Asks   │
 │   (CSV/Excel)  │     │    Profile      │     │    Question    │
 └────────────────┘     └─────────────────┘     └───────┬────────┘
                                                        │
 ┌────────────────┐     ┌─────────────────┐             ▼
 │ 6. Answer &    │<────┤ 5. Pandas Runs  │<────┌────────────────┐
 │   Chart Output │     │    Calculations │     │ 4. LLM Creates │
 └────────────────┘     └─────────────────┘     │    JSON Plan   │
                                                └────────────────┘

```

1. **Profiling:** The engine looks at your spreadsheet to learn column names and types.
2. **Planning:** The AI translates your question into a structured JSON plan (e.g., "Filter by Region = West, calculate sum of Sales").
3. **Execution:** Pandas runs the exact calculation on your computer and creates an evidence table.
4. **Explanation:** The AI writes a friendly, plain-English summary using *only* the numbers from the evidence table.
5. **Visualization:** If the answer involves trends or groups, a chart image (`.png`) is saved automatically.

---

## ⚙️ Getting Started

### 1. Prerequisites

* Python 3.10 or higher
* A free Groq API Key ([Get a Groq API key here](https://console.groq.com/))

### 2. Installation

Open your terminal or command prompt and run:

```bash
# Clone the repository and go to the project folder
git clone https://github.com/Rinku-Duhan/NL2Pandas-Engine-Talk-to-Your-Data
cd NL2Pandas-Engine-Talk-to-Your-Data

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Mac / Linux:
source .venv/bin/activate

# Install required packages
#This command updates Python's core package installer and build tools (`pip`, `setuptools`, and `wheel`) to their latest versions to ensure smooth, error-free package installations.
python -m pip install --upgrade pip setuptools wheel

pip install -r requirements.txt

```

### 3. Set Up Your API Key

Create a file named `.env` in the project root folder and add your Groq key:

```env
GROQ_API_KEY=your_actual_groq_api_key_here

```

---

## 📁 Preparing Your Data

* **Option A: Use Your Own Data**
Simply copy your `.csv` or `.xlsx` file into the `data/` folder (e.g., `data/my_company_sales.csv`).
* **Option B: Generate Sample Data**
If you want to test the system right away, run either of the built-in dataset generators:
```bash
# Generate sample sales data (sample_sales.csv)
python generate_sample_sales.py

# Generate sample HR employee data (sample_hr.csv)
python generate_sample_hr.py

```



---

## 💬 How to Ask Questions (CLI Syntax)

You interact with the system using a simple command structure in your terminal:

```bash
python agent.py --file <PATH_TO_YOUR_FILE> --question "<YOUR_QUESTION_IN_QUOTES>"

```

### Example Commands

#### Simple Totals & Aggregations

```bash
python agent.py --file data/sample_sales.csv --question "What is the total sales amount?"
python agent.py --file data/sample_hr.csv --question "How many distinct job titles exist in the company?"

```

#### Grouped Breakdowns

```bash
python agent.py --file data/sample_hr.csv --question "What is the average salary by department?"
python agent.py --file data/sample_hr.csv --question "What is the average performance rating broken down by department and gender?"

```

#### Filtered Top-N Rankings

```bash
python agent.py --file data/sample_sales.csv --question "What are the top 3 sub-categories by profit in the Technology category?"

```

#### Time Trends

```bash
python agent.py --file data/sample_sales.csv --question "What is the monthly sales trend for the West region?"

```

---

## 🔒 Security, Safety & Data Prevention

To make this engine safe for business data, we built in strict security boundaries:

* **No Code Injection (`eval()` Prevention):** The system never converts AI output into executable Python code strings. Operations are limited to pre-defined function blocks in `executor.py`.
* **Privacy Isolation:** No customer rows or personal information (PII) are ever sent to external LLM APIs. Only structural metadata (column headers and data types) is transmitted.
* **Schema Validation:** Before executing anything, the engine verifies that requested columns actually exist in your spreadsheet, preventing crashes or improper access.
* **Type Safeguards:** If an LLM accidentally attempts string concatenation on a numeric field, the engine catches the mismatch, sanitizes the plan, and safely falls back to valid numeric aggregates.

---

## ⚠️ Current Limitations

While the engine handles standard queries effortlessly, it has specific design boundaries:

1. **Dynamic Subqueries:** Questions requiring individual row comparisons against group averages (e.g., *"Which employees earn more than their department's average?"*) are flagged as `unsupported` rather than returning inaccurate single-pass results.
2. **Sequential `AND` vs. Complex `OR` Filters:** Currently, multiple filters are applied step-by-step using `AND` logic. Cross-column `OR` queries (e.g., *"Technology in West OR Furniture in East"*) require multi-pass handling.

---

## 🧪 Benchmark Test Results

Here is how the engine performs across 10 common analytical test cases:

| # | Question | Dataset | Operation | Status | Result / Output Summary |
| --- | --- | --- | --- | --- | --- |
| **1** | *"What is the total sales amount?"* | Sales | `sum` | **PASS** | Exact total ($682,928) calculated. |
| **2** | *"How many unique sub-categories are sold?"* | Sales | `nunique` | **PASS** | Identified 13 unique sub-categories. |
| **3** | *"What are the total sales by category?"* | Sales | `group_aggregate` | **PASS** | Tech ($351k), Furniture ($251k), Office ($79.5k) + Bar Chart. |
| **4** | *"What are the top 3 sub-categories by profit in Tech?"* | Sales | `top_n` + Filter | **PASS** | Copiers ($19.1k), Phones ($16.2k), Machines ($14.1k) + Bar Chart. |
| **5** | *"What is the monthly sales trend for the West region?"* | Sales | `time_series` | **PASS** | 23 months resampled ($413 min to $19.6k max) + Line Chart. |
| **6** | *"How many distinct job titles exist in the company?"* | HR | `nunique` | **PASS** | 18 unique titles counted. |
| **7** | *"What is the average salary by department?"* | HR | `group_aggregate` | **PASS** | Finance ($121.5k) down to Marketing ($89k) + Bar Chart. |
| **8** | *"Average performance rating by department & gender?"* | HR | Multi Group-By | **PASS** | Calculated 12 subgroup averages accurately. |
| **9** | *"Median rating for employees with >5 years experience?"* | HR | Filter + `median` | **PASS** | Filter applied (`Years > 5`), Median = 3.0. |
| **10** | *"Who earns more than the Engineering average salary?"* | HR | Guardrail Check | **PASS** | Safely rejected unsupported dynamic subquery. |

---

## 📂 Output Logs & Visual Artifacts

Every query generates auditable records on your computer:

* **Audit Transcript:** All JSON plans, raw Pandas evidence tables, execution timing, and synthesis summaries are logged in `outputs/transcript.md`.
* **Chart Images:** Automatically created charts are saved in `outputs/charts/` as high-resolution PNG images.

## 💡 Example Input & Output
Command (Input)
```Bash 

python agent.py --file data/sample_sales.csv --question "What are the top 3 sub-categories by profit in the Technology category?" 
```
Terminal Response (Output)
```Bash 
Plaintext
----------------------------------------
 EVIDENCE TABLE:
----------------------------------------
| Sub-Category   | Sum of Profit |
|:---------------|--------------:|
| Copiers        |       19092.6 |
| Phones         |       16184.9 |
| Machines       |       14120.8 |

----------------------------------------
 ANSWER / EXPLANATION:
----------------------------------------
The top 3 sub-categories by profit in the Technology category are Copiers ($19,092.60), 
Phones ($16,184.90), and Machines ($14,120.80). These figures represent the total profit 
calculated directly from the provided dataset.

 Chart saved to: outputs/charts/top_3_sum_of_profit.png
----------------------------------------
```