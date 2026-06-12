"""
Streamlit Frontend — Expense Tracker MCP Demo
==============================================

Connects to Render MCP server and shows tool calls in real-time.
"""

import asyncio
import json
import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# ── Configuration ──────────────────────────────────────────────────────────
load_dotenv()

MCP_URL = "https://expense-tracker-mcp.onrender.com/mcp"
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
TODAY = date.today().strftime("%d/%m/%Y")

BUILT_IN_EXAMPLES = [
    "Add INR 350 for groceries",
    "What did I spend last week?",
    "Show me my budget status",
    "Search for anything with coffee",
]

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  (must be first Streamlit command)
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Expense Tracker · MCP Demo",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API Key check ─────────────────────────────────────────────────────────
if not os.getenv("GROQ_API_KEY"):
    st.warning(
        "⚠️ **GROQ_API_KEY not set.** Add it to your `.env` file. "
        "Get a free key at [console.groq.com](https://console.groq.com/keys)."
    )

# ── Session state defaults ────────────────────────────────────────────────
for key, default in [
    ("messages", []),
    ("tool_calls", []),
    ("connected", False),
    ("first_turn", True),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ═══════════════════════════════════════════════════════════════════════════
#  AGENT LOGIC
# ═══════════════════════════════════════════════════════════════════════════


def build_system_message() -> str:
    """Build the system prompt with category context."""
    return (
        f"You are an expense tracking assistant. Today's date is {TODAY}.\n\n"
        f"Rules:\n"
        f"- Valid categories: food, transport, housing, utilities, health, education,"
        f" entertainment, shopping, subscriptions, personal_care, travel, investments, misc\n"
        f"- Use 'misc' if nothing else fits.\n"
        f"- Use DD/MM/YYYY format for dates.\n"
        f"- Amounts are in Indian Rupees (INR).\n"
        f"- Query data using the tools available.\n"
        + (
            f"- Pass api_key=\"{MCP_API_KEY}\" with every tool call.\n"
            if MCP_API_KEY else ""
        )
    )


async def run_agent(query: str) -> str:
    """Run the LangChain agent, collecting tool events into session state."""

    # ── Lazy init: connect + build agent on first call ──────────────────
    if "agent" not in st.session_state:
        client = MultiServerMCPClient({
            "expense_tracker": {"url": MCP_URL, "transport": "streamable_http"},
        })
        tools = await client.get_tools()

        # Wrap tool outputs for content_and_artifact format
        for tool in tools:
            def _wrap_coro(fn):
                async def wrapped(*args, **kwargs):
                    result = await fn(*args, **kwargs)
                    return (json.dumps(result, default=str), result) if not isinstance(result, str) else result
                return wrapped

            def _wrap_func(fn):
                def wrapped(*args, **kwargs):
                    result = fn(*args, **kwargs)
                    return (json.dumps(result, default=str), result) if not isinstance(result, str) else result
                return wrapped

            if tool.coroutine is not None:
                tool.coroutine = _wrap_coro(tool.coroutine)
            if tool.func is not None:
                tool.func = _wrap_func(tool.func)

        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        memory = MemorySaver()
        agent = create_react_agent(llm, tools, checkpointer=memory)

        st.session_state.client = client
        st.session_state.agent = agent
        st.session_state.connected = True

    agent = st.session_state.agent

    # ── Build messages ──────────────────────────────────────────────────
    if st.session_state.first_turn:
        messages = [SystemMessage(content=build_system_message()), ("human", query)]
        st.session_state.first_turn = False
    else:
        messages = [("human", query)]

    # ── Stream events ───────────────────────────────────────────────────
    st.session_state.current_tool_calls = []
    full_response = ""

    try:
        async for event in agent.astream_events(
            {"messages": messages},
            {"configurable": {"thread_id": "streamlit-demo"}},
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and isinstance(chunk.content, str):
                    full_response += chunk.content

            elif kind == "on_tool_start":
                raw = event["data"].get("input", {})
                st.session_state.current_tool_calls.append({
                    "name": event["name"],
                    "params": raw.get("kwargs", raw),
                    "result": None,
                    "status": "running",
                })

            elif kind == "on_tool_end":
                calls = st.session_state.current_tool_calls
                if calls and calls[-1]["status"] == "running":
                    out = event["data"].get("output", "")
                    if isinstance(out, (list, tuple)) and len(out) == 2:
                        out = out[0]
                    calls[-1]["result"] = out
                    calls[-1]["status"] = "done"

    except Exception as e:
        full_response += f"\n\n⚠️ **Error:** {e}"

    st.session_state.tool_calls.extend(st.session_state.current_tool_calls)
    st.session_state.current_tool_calls = []
    return full_response


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("💰 MCP Demo")

    # ── Connection ──────────────────────────────────────────────────────
    if st.session_state.connected:
        st.success("✅ Connected to MCP Server")
    else:
        st.info("⏳ Not connected")

    if st.session_state.connected:
        if st.button("🔄 Reconnect", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k != "messages":
                    del st.session_state[k]
            st.rerun()
    else:
        if st.button("🚀 Connect & Start Demo", use_container_width=True, type="primary"):
            with st.spinner("Connecting..."):
                try:
                    # Quick connectivity test
                    client = MultiServerMCPClient({
                        "expense_tracker": {"url": MCP_URL, "transport": "streamable_http"},
                    })
                    tools = await client.get_tools()
                    st.session_state.connected = True
                    st.success(f"✅ {len(tools)} MCP tools available")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")

    st.divider()

    # ── Tool Call Log ───────────────────────────────────────────────────
    st.subheader("🔧 Tool Call Log")

    if not st.session_state.tool_calls:
        st.caption("Ask a question to see MCP tool calls →")
    else:
        for tc in st.session_state.tool_calls:
            icon = "✅" if tc["status"] == "done" else "⏳"
            with st.expander(f"{icon} {tc['name']}", expanded=False):
                params = tc.get("params", {})
                if isinstance(params, dict):
                    for k, v in params.items():
                        v_str = (v[:57] + "...") if isinstance(v, str) and len(v) > 60 else v
                        st.markdown(f"**{k}:** `{v_str}`")
                st.markdown("---")
                if tc.get("result") is not None:
                    try:
                        parsed = json.loads(tc["result"]) if isinstance(tc["result"], str) else tc["result"]
                        st.json(parsed)
                    except (json.JSONDecodeError, TypeError):
                        st.code(str(tc["result"]), language="text")

    st.divider()

    # ── Stats ───────────────────────────────────────────────────────────
    st.subheader("📊 Stats")
    c1, c2, c3 = st.columns(3)
    c1.metric("Calls", len(st.session_state.tool_calls))
    c2.metric("Done", sum(1 for t in st.session_state.tool_calls if t["status"] == "done"))
    c3.metric("Unique", len({t["name"] for t in st.session_state.tool_calls}))

    st.divider()
    if st.button("🗑️ Clear", use_container_width=True):
        for k in ["messages", "tool_calls", "client", "agent", "first_turn", "current_tool_calls"]:
            st.session_state.pop(k, None)
        st.session_state.connected = True
        st.rerun()

    st.caption(f"MCP Server: {MCP_URL}")

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN CHAT AREA
# ═══════════════════════════════════════════════════════════════════════════

st.title("💬 Expense Tracker Assistant")
st.markdown("The agent calls **MCP tools** — watch them appear in the sidebar →")

# ── Quick examples ───────────────────────────────────────────────────────
if st.session_state.connected:
    cols = st.columns(len(BUILT_IN_EXAMPLES))
    clicked = None
    for i, ex in enumerate(BUILT_IN_EXAMPLES):
        if cols[i].button(ex, use_container_width=True, key=f"ex_{i}"):
            clicked = ex

# ── Chat history ─────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask about your expenses...", disabled=not st.session_state.connected)
if clicked and not prompt:
    prompt = clicked

# ═══════════════════════════════════════════════════════════════════════════
#  PROCESS QUERY
# ═══════════════════════════════════════════════════════════════════════════

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("🤖 Thinking...", expanded=True) as status:
            try:
                response = asyncio.run(run_agent(prompt))
                n = len(st.session_state.current_tool_calls)
                status.update(label=f"✅ Done — {n} tool call(s)", state="complete")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

    st.rerun()
