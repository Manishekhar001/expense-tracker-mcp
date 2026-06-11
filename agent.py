import asyncio
import json
import os
from datetime import date

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Load variables from .env file
load_dotenv()

# Where the MCP server is running
# Local:   http://localhost:8000/mcp
# Render:  https://your-app.onrender.com/mcp
MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

# Today's date in the same format the server expects
TODAY = date.today().strftime("%d/%m/%Y")


async def main():
    print(f"\n🔗 Connecting to MCP server at: {MCP_URL}\n")

    # MultiServerMCPClient connects to one or more MCP servers over HTTP.
    # It automatically fetches the tool list from the server.
    async with MultiServerMCPClient(
        {
            "expense_tracker": {
                "url": MCP_URL,
                "transport": "streamable_http",  # must match server transport
            }
        }
    ) as client:

        # ── Step 1: Get the tools ────────────────────────────────────────
        tools = client.get_tools()
        print(f"🛠️  Tools loaded: {[t.name for t in tools]}\n")

        # ── Step 2: Fetch the categories resource from the MCP server ────
        # The server exposes expense://categories which returns categories.json.
        # We pass this to the LLM so it knows valid categories upfront.
        categories_text = ""
        try:
            resources = await client.get_resources(
                server_name="expense_tracker",
                uris="expense://categories",
            )
            if resources:
                blob = resources[0]
                raw = blob.data
                categories_text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                # Pretty-print for readability
                parsed = json.loads(categories_text)
                categories_text = json.dumps(parsed, indent=2)
                print(f"📂 Categories loaded from MCP resource (expense://categories)\n")
        except Exception as e:
            print(f"⚠️  Could not fetch categories from MCP resource: {e}")
            print(f"📂 Using fallback categories\n")
            # Fallback matches the real categories.json exactly
            categories_text = json.dumps({
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
                "misc": ["uncategorized", "rounding", "other"]
            }, indent=2)

        # ── Step 3: Build a system message with categories context ────────
        system_message = (
            f"You are an expense tracking assistant. Today's date is {TODAY}.\n\n"
            f"Here are the valid expense categories and subcategories:\n"
            f"{categories_text}\n\n"
            f"Rules:\n"
            f"- Always use a category from the list above when calling add_expense.\n"
            f"- Use the 'misc' category if nothing else fits.\n"
            f"- Use DD/MM/YYYY format for all dates.\n"
            f"- Amounts are in Indian Rupees (₹)."
        )

        # ── Step 4: Create the agent with categories context ──────────────
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

        # create_react_agent builds a ReAct loop:
        # Think → pick a tool → call it → observe result → think again → answer
        agent = create_react_agent(llm, tools, system_message=system_message)

        # ── Demo Queries ──────────────────────────────────────────────────
        queries = [
            f"Add expense: ₹350 for groceries today ({TODAY}), category food",
            f"Add expense: ₹1200 electricity bill today ({TODAY}), category utilities",
            f"Add expense: ₹220 coffee and snacks today ({TODAY}), category food",
            f"List all my expenses for today ({TODAY})",
            f"Summarize my spending for today ({TODAY}) by category",
        ]

        for query in queries:
            print(f"{'─' * 55}")
            print(f"🙋 You : {query}")
            result = await agent.ainvoke(
                {"messages": [("human", query)]}
            )
            # The last message in the result is the agent's final answer
            answer = result["messages"][-1].content
            print(f"🤖 Agent: {answer}\n")


if __name__ == "__main__":
    asyncio.run(main())
