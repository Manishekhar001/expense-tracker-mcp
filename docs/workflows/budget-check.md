# Workflow: Budget Check

## Purpose

Compares actual spending against budgeted amounts for each category in a given month. The user asks something like *"Show me my budget status"* or *"Am I over budget on food?"* and the agent calls `budget_status` to retrieve the comparison.

## Trigger

User asks a budget-related question in the Streamlit chat, or the LLM invokes the `budget_check` MCP prompt which instructs it to call `budget_status()`.

**Entry point:** `streamlit_app.py:228` → `asyncio.run(run_agent(prompt))`

## Preconditions

- At least one budget must be set (via the `set_budget` tool or direct SQL)
- At least one expense exists in the month being queried (otherwise spent = 0 for all categories)

## Step-by-Step Execution

### Step 1 — LLM decides to call `budget_status`

- **File:** Agent decision
- **What happens:** The LLM recognises the user wants a budget comparison and outputs a call to `budget_status(month, year, api_key)`. If the user doesn't specify a month/year, the LLM passes `None` (the function defaults to the current month).
- **Data out:** Tool call: `budget_status(month="06", year="2026", api_key="...")` or `budget_status(api_key="...")`

### Step 2 — MCP adapter sends to server (same as other workflows)

### Step 3 — FastMCP routes to `budget_status`

- **File:** `main.py:339-380`
- **Function:** `budget_status(month=None, year=None, api_key="")`

### Step 4 — Authentication check

- **File:** `main.py:348`
- **Function:** `authenticated(api_key)`

### Step 5 — Determine the target month

- **File:** `main.py:354-355`
- **What happens:** Defaults to current month/year using `datetime.now()`:
  ```python
  month = month or today.strftime("%m")   # e.g., "06"
  year = year or str(today.year)           # e.g., "2026"
  ```
- **Data out:** `month="06"`, `year="2026"`

### Step 6 — Build date pattern

- **File:** `main.py:357`
- **What happens:** Creates a LIKE pattern to match all dates in the target month:
  ```python
  pattern = f"%/{month}/{year}"   # e.g., "%/06/2026"
  ```
  This matches any date string ending in `/06/2026` — so `15/06/2026`, `01/06/2026`, etc.

### Step 7 — Two parallel database queries

- **File:** `main.py:359-365`
- **Query 1:** Fetch all budgets:
  ```sql
  SELECT * FROM budgets ORDER BY category
  ```
- **Query 2:** Aggregate actual spending by category for the month:
  ```sql
  SELECT category, SUM(amount) AS spent
  FROM expenses WHERE date LIKE ? GROUP BY category
  ```
  Parameter: `("%/06/2026",)`
- **Data out:** Two result sets: all budgets, and aggregated actuals per category

### Step 8 — Compare and compute status

- **File:** `main.py:367-380`
- **What happens:**
  1. Builds a lookup dict `actual_map = {category: spent}` from the actuals for O(1) access
  2. For each budget row: computes `spent = actual_map.get(category, 0)` and `remaining = budget - spent`
  3. Sets `status = "over"` if remaining < 0, `"under"` otherwise
  4. Also adds categories that have spending but no budget set (with `budget: 0` and `status: "over"`)
- **Data out:** List of dicts, e.g.:
  ```json
  [
    {"category": "food", "budget": 5000, "spent": 2450, "remaining": 2550, "status": "under"},
    {"category": "entertainment", "budget": 1000, "spent": 1250, "remaining": -250, "status": "over"},
    {"category": "transport", "budget": 0, "spent": 800, "remaining": -800, "status": "over"}
  ]
  ```

### Step 9 — LLM formats the response

- **What happens:** The LLM receives the comparison data and generates a readable summary:
  *"Here's your budget status for June 2026:\n- ✅ Food: ₹2,450 spent of ₹5,000 (₹2,550 under)\n- ⚠️ Entertainment: ₹1,250 spent of ₹1,000 (₹250 over)\n- ⚠️ Transport: ₹800 spent (no budget set)"*
- **Side effects:** None

## Using the `budget_check` prompt

The MCP prompt `budget_check()` produces a structured instruction template for the LLM:

```
Please check my current budget status.
1. Call budget_status() to see how much I've spent vs my budgeted amounts
2. Summarize:
   - Which categories are over budget (by how much)
   - Which categories are under budget (by how much)
   - Total spent vs total budgeted
   - Any recommendations to get back on track
```

This prompt is registered in the MCP server and can be invoked by clients that support MCP prompts.

## Success Outcome

The user receives a clear breakdown showing which categories are over and under budget, with specific amounts.

## Failure Modes

| Error Condition | How it is handled | What the user sees |
|-----------------|-------------------|--------------------|
| No budgets set | First query returns empty list; second query returns spending | All categories show `budget: 0` and `status: "over"` |
| No expenses in month | Second query returns empty list | All budgeted categories show `spent: 0`, `remaining: budget`, `status: "under"` |
| Invalid month/year | No validation — LIKE pattern returns no matches | Same as "no expenses" case |

## Affected Data Models

- **Reads:** `budgets` (all rows) and `expenses` (aggregated by category for the month)

## Permissions Required

Same as other tools.

## Related Workflows

- [Add Expense](add-expense.md) — creates the spending data this workflow reads
- [Query Spending](query-spending.md) — more detailed spending breakdown
