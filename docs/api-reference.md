# API Reference

## Transport and Base URL

The MCP server communicates over HTTP using the **streamable-http** transport. All requests are HTTP POST to the `/mcp` endpoint.

| Environment | Base URL |
|-------------|----------|
| Production (Render) | `https://expense-tracker-mcp.onrender.com/mcp` |
| Local | `http://localhost:8000/mcp` |

## Authentication

Authentication is **optional** and controlled by the `MCP_API_KEY` environment variable on the server.

**If `MCP_API_KEY` is set:**
Every tool call must include an `api_key` parameter with the correct value. If missing or incorrect, the tool returns:
```json
{"status": "error", "message": "Invalid or missing API key. Provide the correct api_key parameter."}
```

**If `MCP_API_KEY` is not set (local development):**
All tool calls succeed regardless of the `api_key` value. Authentication is completely disabled.

> ⚠️ **Design note:** Authentication is passed as a tool parameter (not an HTTP header) because the LLM only sees function parameters. The system prompt instructs the LLM to include `api_key` with every call.

## Wire Protocol

MCP uses **JSON-RPC 2.0** as its message format. All requests and responses are JSON objects. Key methods:

- `tools/list` — discover all available tools
- `tools/call` — invoke a specific tool
- `resources/read` — read a resource by URI
- `prompts/get` — retrieve a prompt template

---

## Tools (12 total)

All tools follow the same calling convention:
- Parameters are passed as key-value pairs
- Return values are JSON strings (auto-serialised by `@json_response` decorator)
- On success: returns data or `{"status": "success", ...}`
- On error: returns `{"status": "error", "message": "..."}`

---

### `add_expense`

**Auth required:** Yes (if MCP_API_KEY is set)
**Description:** Add a new expense record.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `date` | string | yes | — | Date in DD/MM/YYYY format (e.g., `"11/06/2026"`) |
| `amount` | float | yes | — | Amount in Indian Rupees (e.g., `350.0`) |
| `category` | string | yes | — | Must match a key in `categories.json` (e.g., `"food"`) |
| `subcategory` | string | no | `""` | Optional subcategory (e.g., `"groceries"`) |
| `note` | string | no | `""` | Optional free-text note |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{"status": "success", "id": 7}
```

#### Error Responses

| Condition | Response |
|-----------|----------|
| Auth failure | `{"status": "error", "message": "Invalid or missing API key..."}` |
| Database error | Exception propagates (not caught in tool) |

---

### `get_expense`

**Auth required:** Yes
**Description:** Fetch a single expense by its ID.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `expense_id` | integer | yes | — | The numeric ID of the expense |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{
  "id": 7,
  "date": "11/06/2026",
  "amount": 350.0,
  "category": "food",
  "subcategory": "groceries",
  "note": "Weekly shopping"
}
```

#### Error Responses

| Condition | Response |
|-----------|----------|
| Not found | `{"status": "error", "message": "No expense found with id 999"}` |
| Auth failure | `{"status": "error", "message": "..."}` |

---

### `update_expense`

**Auth required:** Yes
**Description:** Update one or more fields of an existing expense. Omitted fields retain their current values.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `expense_id` | integer | yes | — | The ID of the expense to update |
| `date` | string | no | `None` | New date (DD/MM/YYYY) |
| `amount` | float | no | `None` | New amount |
| `category` | string | no | `None` | New category |
| `subcategory` | string | no | `None` | New subcategory |
| `note` | string | no | `None` | New note |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{
  "status": "success",
  "updated_id": 7,
  "changed_fields": ["amount", "note"]
}
```

#### Error Responses

| Condition | Response |
|-----------|----------|
| No fields provided | `{"status": "error", "message": "No fields to update"}` |
| Expense not found | `{"status": "error", "message": "No expense found with id 999"}` |
| Auth failure | `{"status": "error", "message": "..."}` |

---

### `delete_expense`

**Auth required:** Yes
**Description:** Delete an expense by its ID.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `expense_id` | integer | yes | — | The ID of the expense to delete |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{"status": "success", "deleted_id": 7}
```

#### Error Responses

| Condition | Response |
|-----------|----------|
| Not found | `{"status": "error", "message": "No expense found with id 999"}` |
| Auth failure | `{"status": "error", "message": "..."}` |

---

### `search_expenses`

**Auth required:** Yes
**Description:** Search expenses by keyword across notes, categories, and subcategories (case-insensitive via SQL LIKE/ILIKE).

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keyword` | string | yes | — | Text to search for (e.g., `"coffee"`) |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
[
  {
    "id": 3,
    "date": "10/06/2026",
    "amount": 45.0,
    "category": "food",
    "subcategory": "coffee_tea",
    "note": "Morning coffee"
  }
]
```

Returns an empty list `[]` if no matches are found.

---

### `list_expenses`

**Auth required:** Yes
**Description:** Fetch all expenses between two dates (inclusive), ordered by ID ascending.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | yes | — | Start date in DD/MM/YYYY format |
| `end_date` | string | yes | — | End date in DD/MM/YYYY format |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
[
  {"id": 1, "date": "01/06/2026", "amount": 500.0, "category": "food", ...},
  {"id": 2, "date": "02/06/2026", "amount": 200.0, "category": "transport", ...}
]
```

---

### `summarize`

**Auth required:** Yes
**Description:** Summarise total spending grouped by category within a date range. Optionally filter to a single category.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | yes | — | Start date in DD/MM/YYYY format |
| `end_date` | string | yes | — | End date in DD/MM/YYYY format |
| `category` | string | no | `None` | Filter to a single category (optional) |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
[
  {"category": "food", "total_amount": 2450.0},
  {"category": "transport", "total_amount": 1200.0}
]
```

---

### `set_budget`

**Auth required:** Yes
**Description:** Set or update a budget for a specific category. If a budget already exists for that category, it is updated. Otherwise, a new budget is created.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `category` | string | yes | — | Expense category (must match categories.json keys) |
| `amount` | float | yes | — | Budget amount in Rupees |
| `period` | string | no | `"monthly"` | Budget period — `"monthly"` or `"weekly"` |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{"status": "success", "category": "food", "amount": 5000.0, "period": "monthly"}
```

---

### `budget_status`

**Auth required:** Yes
**Description:** Compare actual spending against budgets for each category in a given month.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `month` | string | no | current | Two-digit month (e.g., `"06"`) |
| `year` | string | no | current | Four-digit year (e.g., `"2026"`) |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
[
  {
    "category": "food",
    "budget": 5000.0,
    "spent": 2450.0,
    "remaining": 2550.0,
    "status": "under"
  },
  {
    "category": "entertainment",
    "budget": 1000.0,
    "spent": 1250.0,
    "remaining": -250.0,
    "status": "over"
  }
]
```

---

### `export_csv`

**Auth required:** Yes
**Description:** Export expenses in CSV format (ready to open in Excel or Google Sheets). Returns the CSV content as a string inside a JSON envelope.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | yes | — | Start date in DD/MM/YYYY format |
| `end_date` | string | yes | — | End date in DD/MM/YYYY format |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{
  "status": "success",
  "csv": "id,date,amount,category,subcategory,note\n7,11/06/2026,350.0,food,groceries,Weekly shopping\n",
  "row_count": 1,
  "filename": "expenses_11-06-2026_to_11-06-2026.csv"
}
```

#### Error Responses

| Condition | Response |
|-----------|----------|
| No expenses found | `{"status": "error", "message": "No expenses found in that date range"}` |

---

### `add_recurring_expense`

**Auth required:** Yes
**Description:** Register a recurring (monthly) expense such as a subscription or EMI.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `description` | string | yes | — | Name (e.g., `"Netflix subscription"`) |
| `amount` | float | yes | — | Monthly amount in Rupees |
| `category` | string | yes | — | Expense category |
| `subcategory` | string | no | `""` | Optional subcategory |
| `day_of_month` | integer | no | `1` | Day of month (1–31) |
| `start_date` | string | no | today | First occurrence date in DD/MM/YYYY |
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
{
  "status": "success",
  "id": 1,
  "description": "Netflix subscription",
  "day_of_month": 15
}
```

---

### `list_recurring_expenses`

**Auth required:** Yes
**Description:** List all active recurring expenses (where `active = 1`), ordered by day_of_month ascending.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | string | no | `""` | Required if server has MCP_API_KEY set |

#### Success Response

```json
[
  {
    "id": 1,
    "description": "Netflix subscription",
    "amount": 499.0,
    "category": "subscriptions",
    "subcategory": "streaming",
    "day_of_month": 15,
    "start_date": "15/01/2026",
    "active": 1
  }
]
```

---

## Resources (3 total)

Resources are read-only data endpoints addressed by URI. They have no side effects.

### `expense://categories`

**MIME type:** `application/json`
**Description:** Returns the full category/subcategory list from `categories.json`. Re-reads from disk on every call.

#### Example response

```json
{
  "food": ["groceries", "fruits_vegetables", "dairy_bakery", "dining_out", "coffee_tea", "snacks", "delivery_fees", "other"],
  "transport": ["fuel", "public_transport", "cab_ride_hailing", "parking", "tolls", "vehicle_service", "other"],
  ...
}
```

### `expense://stats`

**MIME type:** `application/json`
**Description:** Overall spending statistics — total count, total amount, top category.

#### Example response

```json
{
  "total_expenses": 42,
  "total_amount": 12500.0,
  "top_category": "food",
  "top_category_amount": 4500.0
}
```

### `expense://monthly/{month}/{year}`

**MIME type:** `application/json`
**Description:** Spending breakdown by category for a specific month and year. URI takes path parameters: `month` (two digits, e.g., `06`) and `year` (four digits, e.g., `2026`).

#### Example: `expense://monthly/06/2026`

```json
{
  "month": "06",
  "year": "2026",
  "total_spent": 12500.0,
  "categories": [
    {"category": "food", "total": 4500.0, "count": 15},
    {"category": "transport", "total": 2000.0, "count": 8}
  ]
}
```

---

## Prompts (2 total)

Prompts are reusable instruction templates that guide the LLM through multi-step tasks. They produce instruction text, not function calls.

### `monthly_review(month, year)`

**Parameters:**
- `month` (string): two-digit month (e.g., `"06"`)
- `year` (string): four-digit year (e.g., `"2026"`)

**Generates:** A structured instruction template telling the LLM to:
1. Fetch the monthly breakdown from `expense://monthly/{month}/{year}`
2. Call `budget_status(month, year)` to compare against budgets
3. Summarise total spending, top categories, over/under budget items, and an actionable saving insight

### `budget_check()`

**Parameters:** None

**Generates:** A structured instruction template telling the LLM to:
1. Call `budget_status()` to get current spending vs budgeted amounts
2. Summarise which categories are over/under budget, total spent vs total budgeted, and recommendations
