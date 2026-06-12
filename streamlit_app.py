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

# ── CUSTOM CSS ────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Global ─────────────────────────────────────── */
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
        color: #e0e0e0;
    }
    .stApp {
        background: transparent;
    }
    h1, h2, h3, h4 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    p, li, .stMarkdown {
        color: #c0c0d0;
    }

    /* ── Header banner ──────────────────────────────── */
    .header-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.8rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.25);
    }
    .header-banner h1 {
        color: #fff !important;
        font-size: 1.8rem;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-banner p {
        color: rgba(255,255,255,0.85) !important;
        font-size: 0.95rem;
        margin: 0.3rem 0 0 0;
    }

    /* ── Status badges ──────────────────────────────── */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .badge-green {
        background: rgba(76, 175, 80, 0.15);
        color: #81c784;
        border: 1px solid rgba(76, 175, 80, 0.3);
    }
    .badge-amber {
        background: rgba(255, 152, 0, 0.15);
        color: #ffb74d;
        border: 1px solid rgba(255, 152, 0, 0.3);
    }
    .badge-gray {
        background: rgba(255, 255, 255, 0.05);
        color: #a0a0b0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* ── Tool call cards ────────────────────────────── */
    .tool-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.6rem;
        transition: all 0.2s ease;
    }
    .tool-card:hover {
        background: rgba(255, 255, 255, 0.07);
        border-color: rgba(255, 255, 255, 0.15);
    }
    .tool-card .name {
        font-weight: 600;
        font-size: 0.9rem;
        color: #e0e0f0;
    }
    .tool-card .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .tool-card .status-dot.done { background: #4caf50; }
    .tool-card .status-dot.running { background: #ff9800; animation: pulse 1s infinite; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .tool-card .param-row {
        display: flex;
        gap: 6px;
        font-size: 0.8rem;
        color: #9090a8;
        margin: 2px 0;
    }
    .tool-card .param-row .key { color: #7c8cf0; min-width: 80px; }
    .tool-card .param-row .val { color: #c0c0d0; word-break: break-all; }

    /* ── Chat styling ───────────────────────────────── */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        padding: 0.8rem 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: rgba(102, 126, 234, 0.08) !important;
        border-color: rgba(102, 126, 234, 0.2) !important;
    }
    [data-testid="stChatMessageContent"] p {
        color: #e0e0f0 !important;
        font-size: 0.92rem;
        line-height: 1.6;
    }

    /* ── Sidebar ────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #c0c0d0;
    }

    /* ── Buttons ────────────────────────────────────── */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[data-kind="primary"] {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: #fff !important;
        border: none !important;
    }
    .stButton > button[data-kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
    }

    /* ── Example chips ──────────────────────────────── */
    [data-testid="column"] button {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #c0c0d0 !important;
        font-size: 0.8rem !important;
        padding: 4px 8px !important;
        border-radius: 20px !important;
    }
    [data-testid="column"] button:hover {
        background: rgba(102, 126, 234, 0.15) !important;
        border-color: rgba(102, 126, 234, 0.3) !important;
        color: #fff !important;
    }

    /* ── Metrics ────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
    }
    [data-testid="metric-container"] label {
        color: #9090a8 !important;
        font-size: 0.75rem !important;
    }
    [data-testid="metric-container"] [data-testid="metric-value"] {
        color: #e0e0f0 !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }

    /* ── Input ──────────────────────────────────────── */
    .stChatInputContainer {
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.04) !important;
    }
    .stChatInputContainer:focus-within {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
    }

    /* ── Status / spinner ───────────────────────────── */
    .stStatus {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
    }

    /* ── Footer link ────────────────────────────────── */
    .footer-link {
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        font-size: 0.75rem;
        color: #606078;
    }
    .footer-link a {
        color: #7c8cf0;
        text-decoration: none;
    }
    .footer-link a:hover { text-decoration: underline; }

    /* ── Divider ────────────────────────────────────── */
    hr {
        border-color: rgba(255, 255, 255, 0.06) !important;
        margin: 1rem 0 !important;
    }

    /* ── Code blocks in tool cards ──────────────────── */
    .stJson {
        background: rgba(0,0,0,0.3) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
    }
</style>
""", unsafe_allow_html=True)

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
    st.markdown("### 💰 **MCP Demo**")
    st.markdown("<span style='color:#9090a8;font-size:0.8rem;'>Expense Tracker · LangChain + MCP</span>",
                unsafe_allow_html=True)

    st.divider()

    # ── Connection status ──────────────────────────────────────────────
    if st.session_state.connected:
        st.markdown(
            "<span class='badge badge-green'>● Connected  ·  Render MCP</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='badge badge-amber'>● Disconnected</span>",
            unsafe_allow_html=True,
        )

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
                    async def _test():
                        client = MultiServerMCPClient({
                            "expense_tracker": {"url": MCP_URL, "transport": "streamable_http"},
                        })
                        tools = await client.get_tools()
                        return len(tools)
                    n_tools = asyncio.run(_test())
                    st.session_state.connected = True
                    st.success(f"✅ {n_tools} MCP tools available")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")

    st.divider()

    # ── Tool Call Log ───────────────────────────────────────────────────
    st.markdown("### 🔧 Tool Calls")

    if not st.session_state.tool_calls:
        st.markdown(
            "<span style='color:#606078;font-size:0.85rem;'>"
            "Ask a question to see MCP tools in action →</span>",
            unsafe_allow_html=True,
        )
    else:
        for tc in st.session_state.tool_calls:
            is_done = tc["status"] == "done"
            dot_class = "done" if is_done else "running"
            status_icon = "✅" if is_done else "⏳"

            html = f"""
            <div class="tool-card">
                <div>
                    <span class="status-dot {dot_class}"></span>
                    <span class="name">{status_icon} {tc['name']}</span>
                </div>
            """
            # Params
            params = tc.get("params", {})
            if isinstance(params, dict):
                for k, v in params.items():
                    v_str = (str(v)[:55] + "…") if len(str(v)) > 58 else str(v)
                    html += f'<div class="param-row"><span class="key">{k}</span><span class="val">{v_str}</span></div>'

            # Result snippet
            if tc.get("result") is not None:
                result = tc["result"]
                try:
                    parsed = json.loads(result) if isinstance(result, str) else result
                    snippet = json.dumps(parsed, indent=2)[:120]
                except (json.JSONDecodeError, TypeError):
                    snippet = str(result)[:120]
                html += f'<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06);font-size:0.75rem;color:#707090;">{snippet}</div>'

            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

    st.divider()

    # ── Stats ───────────────────────────────────────────────────────────
    st.markdown("### 📊 Stats")
    c1, c2, c3 = st.columns(3)
    c1.metric("Calls", len(st.session_state.tool_calls))
    c2.metric("Done", sum(1 for t in st.session_state.tool_calls if t["status"] == "done"))
    c3.metric("Unique", len({t["name"] for t in st.session_state.tool_calls}))

    st.divider()

    if st.button("🗑️ Clear All", use_container_width=True):
        for k in ["messages", "tool_calls", "client", "agent", "first_turn", "current_tool_calls"]:
            st.session_state.pop(k, None)
        st.session_state.connected = True
        st.rerun()

    st.markdown(
        f"<div style='font-size:0.7rem;color:#505068;margin-top:0.5rem;'>"
        f"MCP Server: {MCP_URL}</div>",
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN CHAT AREA
# ═══════════════════════════════════════════════════════════════════════════

# ── Header banner ─────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="header-banner">
        <h1>💬 Expense Tracker Assistant</h1>
        <p>Ask questions in natural language · The agent calls <strong>MCP tools</strong> on a remote server — watch them appear in the sidebar</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Quick example chips ───────────────────────────────────────────────────
clicked = None
if st.session_state.connected:
    cols = st.columns(len(BUILT_IN_EXAMPLES))
    for i, ex in enumerate(BUILT_IN_EXAMPLES):
        if cols[i].button(ex, use_container_width=True, key=f"ex_{i}"):
            clicked = ex

# ── Welcome message for new users ─────────────────────────────────────────
if not st.session_state.messages and st.session_state.connected:
    with st.chat_message("assistant"):
        st.markdown(
            "👋 **Hello! I'm your expense tracking assistant.**\n\n"
            "I can help you:\n"
            "- **Track spending** — *\"How much did I spend on food last month?\"*\n"
            "- **Add expenses** — *\"Add INR 350 for groceries\"*\n"
            "- **Check budgets** — *\"Show me my budget status\"*\n"
            "- **Search** — *\"Find all coffee expenses\"*\n\n"
            "Try one of the examples above or type your own question!"
        )

# ── Chat history ──────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────
prompt = st.chat_input(
    "Ask about your expenses...",
    disabled=not st.session_state.connected,
)
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
        with st.status("🤖 **Thinking...**", expanded=True) as status:
            try:
                response = asyncio.run(run_agent(prompt))
                n = len(st.session_state.current_tool_calls)
                tool_word = "tool call" if n == 1 else "tool calls"
                status.update(
                    label=f"✅ **Done — {n} {tool_word}**" if n > 0 else "✅ **Done**",
                    state="complete",
                )
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

    st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="footer-link">
        Built with <a href="https://fastmcp.com">FastMCP</a> ·
        <a href="https://langchain.com">LangChain</a> ·
        <a href="https://streamlit.io">Streamlit</a> ·
        <a href="https://groq.com">Groq</a>
    </div>
    """,
    unsafe_allow_html=True,
)
