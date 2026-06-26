# Workflow: Add Expense

## Purpose

Allows a user to record a new expense by typing a natural-language instruction like *"Add ₹350 for groceries"* or *"I spent 500 on fuel yesterday"*. The AI agent interprets the intent, extracts the structured fields, and calls the `add_expense` MCP tool to persist the record.

## Trigger

User types an expense-related statement into the Streamlit chat input. The LangChain agent decides to call `add_expense`.

**Entry point:** `streamlit_app.py:228` → `asyncio.run(run_agent(prompt))`

## Preconditions

- Streamlit frontend is connected to the MCP server (sidebar shows green "Connected" badge)
- `GROQ_API_KEY` is set in `.env`
- User message contains an amount and a category (the LLM can infer partial information from context)

## Step-by-Step Execution

### Step 1 — User sends message

- **File:** `streamlit_app.py:228-245`
- **What happens:** The user types a message in the chat input and presses Enter. The message is appended to `st.session_state.messages` and displayed in the chat. Then `asyncio.run(run_agent(prompt))` is called.
- **Data in:** Raw text string (e.g., `"Add INR 350 for groceries"`)
- **Data out:** The prompt string is passed to `run_agent()`
- **Side effects:** None yet

### Step 2 — Agent builds message list

- **File:** `streamlit_app.py:143-146`
- **Function:** Inside `run_agent()`
- **What happens:** On the first turn, a `SystemMessage` with the system prompt (including today's date, valid categories, currency, and API key instructions) is prepended. On subsequent turns, only the `("human", query)` tuple is added.
- **Data in:** The user's query string
- **Data out:** A list `[SystemMessage(...), ("human", prompt)]` or `[("human", prompt)]`
- **Side effects:** None

### Step 3 — LLM decides to call `add_expense`

- **File:** Managed by LangGraph's `create_react_agent` (inside LangGraph library)
- **What happens:** The LLM (Groq LLaMA 3.1) reads the system prompt (which describes all 12 tools) and the user message. It outputs a structured decision to call `add_expense` with inferred parameters. The LangGraph framework detects this is a tool call (not a text response) and routes to the tool execution node.
- **Data in:** Message list with system prompt + user query
- **Data out:** Tool call: `add_expense(date="11/06/2026", amount=350.0, category="food", subcategory="groceries", api_key="...")`
- **Side effects:** None

### Step 4 — MCP adapter wraps and sends

- **File:** `langchain_mcp_adapters` (library code)
- **What happens:** `MultiServerMCPClient` converts the tool call into a JSON-RPC 2.0 `tools/call` request and sends it as an HTTP POST to the MCP server's `/mcp` endpoint.
- **Data in:** `{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "add_expense", "arguments": {...}}, "id": "req-001"}`
- **Data out:** HTTP POST request to `https://expense-tracker-mcp.onrender.com/mcp`
- **Side effects:** Network call

### Step 5 — FastMCP routes to Python function

- **File:** `main.py:173-195`
- **Function:** `add_expense(date, amount, category, subcategory, note, api_key)`
- **What happens:** FastMCP receives the HTTP request, parses the JSON-RPC body, looks up `add_expense` in its internal registry (registered via `@mcp.tool`), and calls the wrapped Python function.
- **Data in:** `date="11/06/2026"`, `amount=350.0`, `category="food"`, `subcategory="groceries"`, `note=""`, `api_key="..."`
- **Data out:** Function is called; execution proceeds

### Step 6 — Authentication check

- **File:** `main.py:187`
- **Function:** `authenticated(api_key)`
- **What happens:** If `MCP_API_KEY` is configured on the server, the provided `api_key` is compared. If it doesn't match, the function returns immediately with `{"status": "error", "message": "Invalid or missing API key."}`.
- **Data in:** The `api_key` string parameter
- **Data out:** Either `None` (pass) or an error string (fail)
- **Side effects:** None

### Step 7 — Database INSERT

- **File:** `main.py:189-194`
- **Function calls:**
  1. `insert("INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)", (date, amount, category, subcategory, note))`
  2. `insert()` calls `get_conn()`, then `_adapt(sql)`, then `cur.execute()`
  3. SQLite: `cur.lastrowid` is returned. PostgreSQL: `RETURNING id` is appended and `cur.fetchone()[0]` is returned.
- **Data in:** `(date, amount, category, subcategory, note)` tuple
- **Data out:** The new row's ID (integer, e.g., `7`)
- **Side effects:** Writes a row to the `expenses` table

### Step 8 — JSON response returned

- **File:** `main.py:195`
- **What happens:** The function returns `{"status": "success", "id": 7}` as a Python dict. The `@json_response` decorator converts it to the JSON string `'{"status": "success", "id": 7}'`.
- **Data in:** `{"status": "success", "id": 7}`
- **Data out:** `'{"status": "success", "id": 7}'` (JSON string)
- **Side effects:** None

### Step 9 — Response flows back through the stack

- **What happens:** FastMCP wraps the JSON string in a JSON-RPC response envelope and sends it as the HTTP response. The MCP adapter unwraps it, creating a `ToolMessage`. The agent feeds this back to the LLM.
- **Data in:** JSON-RPC response `{"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": "{\"status\": \"success\", \"id\": 7}"}]}, "id": "req-001"}`
- **Data out:** Extracted tool result string

### Step 10 — LLM generates natural language response

- **File:** Managed by LangGraph agent
- **What happens:** The LLM reads the tool result `{"status": "success", "id": 7}` and generates a friendly response: *"Done! I've added ₹350 for groceries on 11/06/2026 (expense #7)."*
- **Data in:** Tool result string
- **Data out:** Natural language answer (streamed token by token via `on_chat_model_stream` events)

### Step 11 — Response displayed in Streamlit

- **File:** `streamlit_app.py:234-242`
- **What happens:** The `run_agent()` function returns the full response string. The status widget updates from "Thinking..." to "Done — 1 tool call". The response is rendered in the chat message area and appended to `st.session_state.messages`.
- **Data in:** The full response string
- **Data out:** Rendered HTML in the browser; persisted to session state
- **Side effects:** The sidebar tool-call log is updated with the `add_expense` entry showing params, result, and "✅ done" status

## Success Outcome

The user sees: *"Done! I've added ₹350 for groceries on 11/06/2026 (expense #7)."* in the chat. The sidebar shows one completed tool call for `add_expense` with the parameters and result visible.

## Failure Modes

| Error Condition | How it is handled | What the user sees |
|-----------------|-------------------|--------------------|
| Invalid API key | `authenticated()` returns error message | Tool returns `{"status": "error", "message": "Invalid or missing API key."}`; the LLM reports failure |
| Network error (MCP server down) | `run_agent()` catches `Exception` | `⚠️ Error: [connection error details]` appended to the response |
| LLM misinterprets the intent | The LLM calls the wrong tool or wrong parameters | Incorrect expense recorded; user must correct via another query |
| Empty fields | No validation on the server — all fields accepted | Empty strings stored for optional fields |
| Negative amount | No validation — database accepts negative REAL | Negative expense recorded |

## Affected Data Models

- **Creates:** `expenses` row

## Permissions Required

- If `MCP_API_KEY` is set on the server: the call must include the correct key as the `api_key` parameter
- If `MCP_API_KEY` is not set (local dev): no authentication required

## Related Workflows

- [Query Spending](query-spending.md) — to verify the expense was recorded
- [Budget Check](budget-check.md) — to see how the expense affects budget status
