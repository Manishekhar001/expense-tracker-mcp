# Technology Stack

## Runtime

| Component | Version | Source |
|-----------|---------|--------|
| Python | 3.13 | `.python-version`, `pyproject.toml` (`requires-python = ">=3.13"`) |

## Core dependencies (from `pyproject.toml`)

### MCP Server framework

| Package | Version | Purpose |
|---------|---------|---------|
| `fastmcp` | >=3.2.0 | MCP server framework (like FastAPI but for MCP). Handles JSON-RPC parsing, tool registration, resource routing, prompt generation, and HTTP transport. |

### AI Agent framework

| Package | Version | Purpose |
|---------|---------|---------|
| `langchain` | >=1.3.7 | Core LangChain library. Provides message types (`SystemMessage`), LLM interface (`ChatGroq`), and tool abstraction. |
| `langchain-groq` | >=1.1.3 | LangChain integration for Groq's API. Enables using LLaMA 3.1 models through LangChain's standard interface. |
| `langchain-mcp-adapters` | >=0.3.0 | Bridges LangChain agents with MCP servers. `MultiServerMCPClient` connects to MCP servers, discovers tools via `tools/list`, and wraps each as a LangChain `BaseTool`. |
| `langgraph` | >=1.2.4 | LangChain's graph-based agent framework. `create_react_agent` builds a ReAct (Reasoning + Acting) loop agent. `MemorySaver` persists conversation history by `thread_id`. |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | >=1.43.0 | Web UI framework. Renders the chat interface, sidebar tool-call log, and custom CSS dark theme. |

### Database

| Package | Version | Purpose |
|---------|---------|---------|
| `psycopg2-binary` | >=2.9.12 | PostgreSQL adapter for Python. Used when `DATABASE_URL` is set (production on Render). Falls back to built-in `sqlite3` when not installed. |

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `python-dotenv` | >=1.2.2 | Reads `.env` file into `os.environ`. Used by `streamlit_app.py` to load `GROQ_API_KEY`. |
| `uvicorn` | >=0.29.0 | ASGI server. Likely used internally by FastMCP to serve HTTP. |

## Database

| Environment | Database | Driver | Connection |
|-------------|----------|--------|------------|
| Local development | SQLite (file-based) | `sqlite3` (stdlib) | `sqlite3.connect("expense_tracker.db")` |
| Production (Render) | PostgreSQL (Render Managed) | `psycopg2` | `psycopg2.connect(DATABASE_URL)` |

## External services

| Service | Purpose | What breaks without it |
|---------|---------|----------------------|
| **Groq API** (`console.groq.com`) | LLM inference — runs the LLaMA 3.1 model for the LangChain agent | The Streamlit frontend cannot process any user questions. The agent requires a `GROQ_API_KEY`. |
| **Render** (optional for local dev) | Hosts the MCP server and PostgreSQL database | Local development does not require Render. The server runs fine with SQLite. The hardcoded `MCP_URL` in `streamlit_app.py` points to Render — to use a local server, this URL must be changed. |

## Testing

| Tool | Purpose |
|------|---------|
| No test framework installed | No tests exist in the repository (see [Testing](../testing.md)) |

## Local development prerequisites

- **Python 3.13+** — the project uses `requires-python = ">=3.13"`
- **uv** (recommended) or **pip** — Python package manager
- **A Groq API key** — [free to obtain](https://console.groq.com/keys), required to run the Streamlit frontend
- **No PostgreSQL required locally** — SQLite is the default for development

## CI/CD and infrastructure hints

- **Procfile** declares `web: python main.py` — this is Render's process format
- **No Dockerfile** exists — deployment to Render uses the Procfile directly
- **No CI config** (no `.github/workflows/`, `.gitlab-ci.yml`, etc.) — there is no automated test or build pipeline
