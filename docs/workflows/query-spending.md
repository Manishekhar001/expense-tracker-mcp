# Workflow: Query Spending

## Purpose

Allows a user to ask questions about their spending patterns, such as *"How much did I spend on food last week?"* or *"What did I spend money on in June?"* The AI agent calls the `summarize` tool (and optionally `list_expenses`) to retrieve aggregated data from the database and presents it as a natural-language summary.

## Trigger

User asks a spending-related question in the Streamlit chat. The LLM recognises it needs aggregated data and decides to call `summarize` (and/or `list_expenses`).

**Entry point:** `streamlit_app.py:228` → `asyncio.run(run_agent(prompt))`

## Preconditions

- Streamlit frontend is connected to the MCP server
- At least one expense exists in the date range being queried
- The user's question contains or implies a time range (the LLM defaults to "last week" or similar relative time based on today's date)

## Step-by-Step Execution

### Step 1 — LLM parses the time range and decides to call `summarize`

- **File:** Managed by LangGraph agent (agent decision)
- **What happens:** The LLM reads today's date from the system prompt (`TODAY = date.today().strftime("%d/%m/%Y")`). It computes the relevant date range from the user's query (e.g., "last week" → 7 days ago to today; "last month" → previous month). It outputs a tool call to `summarize(start_date, end_date, category)`.
- **Data in:** User query like *"How much did I spend on food last week?"*
- **Data out:** Tool call: `summarize(start_date="04/06/2026", end_date="11/06/2026", category="food", api_key="...")`
- **Side effects:** None

### Step 2 — MCP adapter sends `summarize` to the server

- **File:** `langchain_mcp_adapters` (library code)
- **What happens:** Identical to Step 4 of the [Add Expense workflow](add-expense.md): JSON-RPC `tools/call` request sent as HTTP POST to `/mcp`.

### Step 3 — FastMCP routes to `summarize`

- **File:** `main.py:298-316`
- **Function:** `summarize(start_date, end_date, category=None, api_key="")`
- **What happens:** FastMCP looks up `summarize` (registered via `@mcp.tool`) and calls the Python function.

### Step 4 — Authentication check

- **File:** `main.py:307`
- **Function:** `authenticated(api_key)`
- **What happens:** Same auth flow as [Add Expense](add-expense.md#step-6--authentication-check).

### Step 5 — Database SELECT with aggregation

- **File:** `main.py:309-316`
- **What happens:** The function builds a dynamic SQL query:
  ```sql
  SELECT category, SUM(amount) AS total_amount
  FROM expenses WHERE date BETWEEN ? AND ?
  ```
  - If `category` is provided, it appends `AND category = ?`
  - Always appends `GROUP BY category ORDER BY category ASC`
- **Data in:** `(start_date="04/06/2026", end_date="11/06/2026", category="food")`
- **Data out:** List of dicts, e.g., `[{"category": "food", "total_amount": 2450.0}]`
- **Side effects:** Database read only

### Step 6 — JSON response returned

- **File:** `main.py:316` (via `@json_response`)
- **Data out:** `'[{"category": "food", "total_amount": 2450.0}]'`

### Step 7 — Response flows back (same as Add Expense Step 9)

### Step 8 — LLM generates a summary

- **File:** Managed by LangGraph agent
- **What happens:** The LLM receives the aggregated data and generates a natural-language response like: *"You spent ₹2,450 on food in the last week (04/06/2026 – 11/06/2026)."*
- **Data in:** `[{"category": "food", "total_amount": 2450.0}]`
- **Data out:** Natural language answer

### Step 9 — Response displayed in Streamlit (same as Add Expense Step 11)

## Multi-tool variant: "What did I spend last week?"

When the user asks a broad question without a specific category, the LLM may call `summarize` without the `category` parameter, returning all categories. The LLM can then optionally call `list_expenses` to get raw transaction details for any category the user asks about.

## Success Outcome

The user receives a natural-language breakdown of their spending, e.g.:
- *"In the last week you spent ₹4,200 total. Your top categories were: food (₹2,450), transport (₹1,200), and entertainment (₹550)."*

## Failure Modes

| Error Condition | How it is handled | What the user sees |
|-----------------|-------------------|--------------------|
| No expenses in date range | SQL returns empty list `[]` | The LLM reports "No expenses found in that period" |
| Category has no matches | SQL with `AND category = ?` returns empty | LLM reports "No expenses found for [category] in that period" |
| Network error | Exception caught in `run_agent()` | `⚠️ Error: ...` appended to response |
| Invalid date format | No server-side validation; SQL BETWEEN fails silently | Empty result; LLM may be confused |

## Affected Data Models

- **Reads:** `expenses` (aggregated with `SUM` and `GROUP BY`)

## Permissions Required

Same as [Add Expense](add-expense.md#permissions-required).

## Related Workflows

- [Add Expense](add-expense.md) — recording the data that this workflow reads
- [Budget Check](budget-check.md) — comparing spending against budgets
