# Deployment

## Deployment Target

The application is deployed on **Render** as two separate services:

1. **MCP Server** — a web service running `main.py` via the `Procfile`
2. **Streamlit Frontend** — a web service running `streamlit_app.py` (the live demo)

There is no Dockerfile. Render runs the process declared in `Procfile` directly.

## Build Command

Render automatically detects the Python runtime. No custom build command is needed — Render runs `pip install -r requirements.txt` by default for Python services.

> ⚠️ **Note:** The project uses `uv` locally but `requirements.txt` mirrors the dependencies in `pyproject.toml`. Render uses `requirements.txt` by default, not `pyproject.toml`. If Render fails to install dependencies, ensure `requirements.txt` is up to date with `pyproject.toml`.

## MCP Server Deployment

### Required environment variables (Production)

| Variable | Required | Source |
|----------|----------|--------|
| `DATABASE_URL` | Yes | Render's PostgreSQL dashboard — the connection string for the managed Postgres instance |
| `MCP_API_KEY` | Yes | Generate a strong random key (e.g., `openssl rand -hex 32`) |
| `PORT` | Yes | Render sets this automatically |

### Procfile

```
web: python main.py
```

This tells Render to run `python main.py` as the web process. The server listens on `0.0.0.0:$PORT` with `transport="streamable-http"`.

### Database migration strategy

There is no migration system. Tables are created via `CREATE TABLE IF NOT EXISTS` in `init_db()`, which runs every time the server starts.

- **Before deploy:** No action needed — tables are created automatically
- **Schema change:** Requires manual `ALTER TABLE` via `psql` or deleting and recreating the database
- ⚠️ **On Render's ephemeral filesystem:** If using SQLite (no `DATABASE_URL` set), the database file is lost on every restart. You must use PostgreSQL in production.

### Health check

The MCP server **does not have a dedicated health check endpoint**. However, you can verify it is running by sending a `tools/list` request:

```bash
curl -X POST https://expense-tracker-mcp.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "health-1"}'
```

A healthy server responds with the list of 12 tools.

### Rollback

Render supports rolling back to a previous deployment from the Render dashboard:

1. Go to the service's "Deploys" tab
2. Find the last known-good deployment
3. Click "Rollback"

Because `init_db()` uses `CREATE TABLE IF NOT EXISTS`, rollbacks are safe — the schema is not modified. However, any schema changes or data migrations performed after the rolled-back deployment must be reversed manually.

## Streamlit Frontend Deployment

The live Streamlit demo is deployed at: **https://expense-tracker-streamlit-brjt.onrender.com/**

### Required environment variables (Production)

| Variable | Required | Source |
|----------|----------|--------|
| `GROQ_API_KEY` | Yes | [console.groq.com/keys](https://console.groq.com/keys) |
| `MCP_API_KEY` | Yes | Must match the key set on the MCP server |

### Start command

```
streamlit run streamlit_app.py
```

Set this as the Start Command in Render's Streamlit service settings (or use the Render Blueprint / dashboard).

### Important note about `MCP_URL`

The `MCP_URL` is **hardcoded** in `streamlit_app.py:24`:

```python
MCP_URL = "https://expense-tracker-mcp.onrender.com/mcp"
```

This means the frontend always talks to the Render MCP server. If you deploy your own MCP server at a different URL, you must update this constant before deploying the frontend.

## CI/CD Pipeline

**No CI/CD pipeline exists.** There are no configuration files for GitHub Actions, GitLab CI, or any other CI provider.

To set up continuous deployment on Render:

1. Connect your GitHub repository to Render
2. Enable "Auto-Deploy" for the `main` branch
3. Every push to `main` triggers a new deployment

## Production Checklist

Before deploying to production, ensure:

- [ ] `DATABASE_URL` points to a managed PostgreSQL instance (Render PostgreSQL or equivalent)
- [ ] `MCP_API_KEY` is set to a strong random value
- [ ] `GROQ_API_KEY` is set (for the Streamlit frontend)
- [ ] `requirements.txt` is in sync with `pyproject.toml`
- [ ] The hardcoded `MCP_URL` in `streamlit_app.py` points to the correct MCP server URL
- [ ] Render's PostgreSQL IP allowlist is configured (if needed)
