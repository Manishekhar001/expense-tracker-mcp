import asyncio
import json
import os
import uuid
from datetime import date

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()
MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
TODAY = date.today().strftime("%d/%m/%Y")

# Fallback categories — mirrors categories.json exactly
FALLBACK_CATEGORIES = {
    "food": ["groceries", "fruits_vegetables", "dairy_bakery", "dining_out", "coffee_tea", "snacks", "delivery_fees", "other"],
    "transport": ["fuel", "public_transport", "cab_ride_hailing", "parking", "tolls", "vehicle_service", "other"],
    "housing": ["rent", "maintenance_hoa", "property_tax", "repairs_service", "cleaning", "furnishing", "other"],
    "utilities": ["electricity", "water", "gas", "internet_broadband", "mobile_phone", "tv_dth", "other"],
    "health": ["medicines", "doctor_consultation", "diagnostics_labs", "insurance_health", "fitness_gym", "other"],
    "education": ["books", "courses", "online_subscriptions", "exam_fees", "workshops", "other"],
    "entertainment": ["movies_events", "streaming_subscriptions", "games_apps", "outing", "other"],
    "shopping": ["clothing", "footwear", "accessories", "electronics_gadgets", "appliances", "home_decor", "other"],
    "subscriptions": ["saas_tools", "cloud_ai", "newsletters", "music_video", "storage_backup", "other"],
    "personal_care": ["salon_spa", "grooming", "cosmetics", "hygiene", "other"],
    "travel": ["flights", "hotels", "train_bus", "visa_passport", "local_transport", "food_travel", "other"],
    "investments": ["mutual_funds", "stocks", "fd_rd", "gold", "crypto", "brokerage_fees", "other"],
    "misc": ["uncategorized", "rounding", "other"],
}


async def fetch_categories(client) -> str:
    """Fetch categories from the MCP resource, falling back to hardcoded values."""
    try:
        resources = await client.get_resources(
            server_name="expense_tracker",
            uris="expense://categories",
        )
        if resources:
            blob = resources[0]
            raw = blob.data
            text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2)
    except Exception as e:
        print(f"  [Warning] Could not fetch categories from MCP: {e}")
    return json.dumps(FALLBACK_CATEGORIES, indent=2)


def build_system_message(categories_text: str) -> str:
    """Build the system prompt with category context."""
    return (
        f"You are an expense tracking assistant. Today's date is {TODAY}.\n\n"
        f"Here are the valid expense categories and subcategories:\n"
        f"{categories_text}\n\n"
        f"Rules:\n"
        f"- Always use a category from the list above when calling add_expense.\n"
        f"- Use the 'misc' category if nothing else fits.\n"
        f"- Use DD/MM/YYYY format for all dates.\n"
        f"- Amounts are in Indian Rupees (INR).\n"
        f"- When asked about spending, use the tools available to get real data.\n"
        f"- You have access to tools for budgets and recurring expenses too — use them.\n"
        + (
            f"- Use api_key=\"{MCP_API_KEY}\" with every tool call. Always pass this api_key parameter.\n"
            if MCP_API_KEY
            else ""
        )
    )


async def main():
    print()
    print("  Connecting to MCP server...")

    # ── Connect to MCP ──────────────────────────────────────────────────────
    client = MultiServerMCPClient(
        {
            "expense_tracker": {
                "url": MCP_URL,
                "transport": "streamable_http",
            }
        }
    )

    # ── Discover tools ──────────────────────────────────────────────────────
    tools = await client.get_tools()
    tool_names = [t.name for t in tools]
    print(f"  Tools loaded: {len(tools)} — {', '.join(tool_names)}")

    # ── Wrap tools: stringify results ──────────────────────────────────────
    # The installed langgraph version uses response_format='content_and_artifact',
    # which expects tool outputs as (string_content, raw_artifact).
    # We wrap func/coroutine to return (json_string, original_result).

    def _wrap_coro(fn):
        async def wrapped(*args, **kwargs):
            result = await fn(*args, **kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str), result
        return wrapped

    def _wrap_func(fn):
        def wrapped(*args, **kwargs):
            result = fn(*args, **kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str), result
        return wrapped

    for tool in tools:
        if tool.coroutine is not None:
            tool.coroutine = _wrap_coro(tool.coroutine)
        if tool.func is not None:
            tool.func = _wrap_func(tool.func)

    # ── Discover prompts ────────────────────────────────────────────────────
    try:
        prompts = await client.get_prompts(server_name="expense_tracker")
        prompt_names = [p.name for p in prompts]
        print(f"  Prompts available: {', '.join(prompt_names)}")
    except Exception:
        print("  Prompts: not available in this adapter version")

    # ── Fetch categories ────────────────────────────────────────────────────
    categories_text = await fetch_categories(client)
    print(f"  Categories loaded from MCP resource")

    # ── Build LLM & agent ──────────────────────────────────────────────────
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    system_message = build_system_message(categories_text)

    memory = MemorySaver()
    agent = create_react_agent(llm, tools, checkpointer=memory)
    config = {"configurable": {"thread_id": "expense-tracker-interactive"}}

    # ── Interactive loop ────────────────────────────────────────────────────
    print()
    print("=" * 58)
    print("  Expense Tracker Agent — Interactive Mode")
    print("  Ask me anything about your expenses!")
    print()
    print("  Commands:  /exit  /reset  /help")
    print("=" * 58)

    first_turn = True

    while True:
        try:
            query = input("\n[You] ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query:
            continue

        # ── Built-in commands ──────────────────────────────────────────────
        if query.startswith("/"):
            cmd = query[1:].lower()
            if cmd in ("exit", "quit"):
                print("\n  Goodbye!")
                break
            elif cmd == "reset":
                config = {"configurable": {"thread_id": str(uuid.uuid4())}}
                first_turn = True
                print("  Memory cleared. Starting fresh.")
                continue
            elif cmd == "help":
                print()
                print("  Commands:")
                print("    /exit          - Exit the application")
                print("    /reset         - Clear conversation memory")
                print("    /help          - Show this help")
                print()
                print("  Examples:")
                print('    "Add INR 350 for groceries"')
                print('    "What did I spend last week?"')
                print('    "Show me my budget status"')
                print('    "Search for anything with coffee"')
                print('    "Export my June expenses as CSV"')
                continue
            else:
                print(f"  Unknown command: /{cmd}. Try /help")
                continue

        # ── Send to agent ──────────────────────────────────────────────────
        if first_turn:
            messages = [SystemMessage(content=system_message), ("human", query)]
            first_turn = False
        else:
            messages = [("human", query)]

        print()
        print("[Agent] ", end="", flush=True)

        full_response = ""

        try:
            async for event in agent.astream_events(
                {"messages": messages},
                config,
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        if isinstance(chunk.content, str):
                            print(chunk.content, end="", flush=True)
                            full_response += chunk.content

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    print(f"\n  [Using: {tool_name}]", end="", flush=True)

        except Exception as e:
            print(f"\n  [Error] {e}")

        print("\n")

    print("\n  Session ended. See you next time!")


if __name__ == "__main__":
    asyncio.run(main())
