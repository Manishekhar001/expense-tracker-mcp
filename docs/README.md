# Expense Tracker MCP — Documentation

## What is this application?

**Expense Tracker MCP** is a personal expense tracking system that you interact with through a **conversational AI assistant**. You type natural-language questions like *"How much did I spend on food last month?"* or *"Add ₹350 for groceries"*, and an AI agent translates those into structured tool calls against a **Model Context Protocol (MCP)** server backend.

The backend (the MCP server) exposes 12 tools for CRUD operations on expenses, budgets, and recurring expenses, plus 3 read-only resources and 2 prompt templates. The frontend is a Streamlit web application that visualises every tool call in real time, making the MCP architecture visible and demonstrable — ideal for architecture interviews or anyone learning the MCP protocol.

## Who is this documentation for?

- **Developers** joining the project who need to understand the codebase quickly
- **Ops / DevOps** engineers deploying or maintaining the server
- **Interview candidates** studying the MCP architecture implemented here
- **Anyone learning** about MCP, FastMCP, LangChain agents, or Streamlit

## Table of Contents

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture/overview.md) | High-level system design, component diagram, directory map, design decisions |
| [Data Models](architecture/data-models.md) | All database tables, fields, constraints, relationships, and ER diagram |
| [Technology Stack](architecture/tech-stack.md) | Languages, frameworks, libraries, external services, local prerequisites |
| [Workflow: Add Expense](workflows/add-expense.md) | End-to-end flow: user says "add ₹350 for groceries" → tool call → database write → response |
| [Workflow: Query Spending](workflows/query-spending.md) | End-to-end flow: user asks "what did I spend on food?" → summarise → respond |
| [Workflow: Budget Check](workflows/budget-check.md) | End-to-end flow: comparing actual spending against budgeted amounts |
| [Workflow: Application Startup](workflows/application-startup.md) | Server initialisation sequence and client connection flow |
| [API Reference](api-reference.md) | All 12 MCP tools, 3 resources, and 2 prompts with exact signatures and examples |
| [Configuration](configuration.md) | All environment variables, their purposes, and what breaks if missing |
| [Development Guide](development-guide.md) | Local setup, running, testing, coding conventions, and how to extend |
| [Deployment](deployment.md) | Render deployment, build commands, environment setup, health checks |
| [Testing](testing.md) | Current test coverage, how to run tests, and known gaps |

## Quick Start

```bash
# Prerequisites: Python 3.13+ and a free Groq API key

# 1. Clone the repository
git clone <repo-url>
cd expense-tracker-mcp

# 2. Install dependencies (using uv — fast Python package manager)
uv sync

# 3. Create environment file
echo "GROQ_API_KEY=gsk_your_key_here" > .env

# 4. Run the Streamlit demo frontend
uv run streamlit run streamlit_app.py
```

This opens `http://localhost:8501` in your browser. Click **"Connect & Start Demo"** to connect to the live MCP server (or run your own locally with `uv run python main.py`), then ask questions like:

- *"Add INR 350 for groceries"*
- *"How much did I spend on food last week?"*
- *"Show me my budget status"*
- *"Search for anything with coffee"*

## Run the test suite

```bash
uv run pytest
```

> ⚠️ **Note:** No test files currently exist in the repository. See [Testing](testing.md) for details.
