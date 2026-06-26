# Configuration

## Environment Variables

| Variable | Required | Default | Description | Used In |
|----------|----------|---------|-------------|---------|
| `DATABASE_URL` | no | `""` (empty) | PostgreSQL connection string. If set, the server uses PostgreSQL. If empty/unset, falls back to local SQLite (`expense_tracker.db`). | `main.py` |
| `MCP_API_KEY` | no | `""` (empty) | API key required for all MCP tool calls. If empty/unset, authentication is disabled (local dev). If set, every tool call must include `api_key` parameter with this value. | `main.py`, `streamlit_app.py` |
| `GROQ_API_KEY` | yes (for frontend) | — | Groq API key for LLM inference. Obtain a free key at [console.groq.com/keys](https://console.groq.com/keys). The Streamlit frontend shows a warning if this is missing. | `streamlit_app.py` |
| `PORT` | no | `8000` | HTTP port for the MCP server. Render sets this automatically. | `main.py` |

## Grouped by Concern

### Database

| Variable | Required | What breaks if missing |
|----------|----------|----------------------|
| `DATABASE_URL` | No | Server uses SQLite instead of PostgreSQL. If neither is accessible, the server crashes on startup. |

### Authentication

| Variable | Required | What breaks if missing |
|----------|----------|----------------------|
| `MCP_API_KEY` | No | Authentication is disabled. The server accepts all tool calls without verification. In production, this means anyone who can reach the endpoint can read/write expense data. |

### LLM / AI

| Variable | Required | What breaks if missing |
|----------|----------|----------------------|
| `GROQ_API_KEY` | Yes (for Streamlit frontend) | The LangChain agent cannot initialise `ChatGroq`. The Streamlit app displays a warning and the chat input is disabled. |

### Server

| Variable | Required | What breaks if missing |
|----------|----------|----------------------|
| `PORT` | No | Server defaults to port 8000. On Render, this must be set by the platform (Render's runtime injects `PORT` automatically). |

## Minimum Viable `.env` for Local Development

```bash
# Required to run the Streamlit frontend
GROQ_API_KEY=gsk_your_key_here

# Optional: enable MCP server authentication
# MCP_API_KEY=your-secret-key

# Optional: use PostgreSQL instead of SQLite
# DATABASE_URL=postgresql://user:pass@host:5432/expense_tracker
```

## What catastrophically breaks

| Missing variable | Failure mode |
|-----------------|--------------|
| `GROQ_API_KEY` | Streamlit frontend shows a warning. The agent agent cannot be created. User cannot ask any questions. |
| `DATABASE_URL` (in production) | Server falls back to SQLite. On Render's ephemeral filesystem, the SQLite file is lost on every restart. All data is effectively wiped on redeploy. |
| `MCP_API_KEY` (in production) | Server has no authentication. Anyone who discovers the Render URL can add, read, update, or delete expenses without restriction. |
| `PORT` (on Render) | Render requires this variable to route traffic to the correct process port. Without it, the server starts on 8000 but Render expects whatever `PORT` is set to — traffic is not routed correctly. |
