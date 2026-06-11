import asyncio
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

        # Get all tools the MCP server exposes
        tools = client.get_tools()
        print(f"🛠️  Tools loaded: {[t.name for t in tools]}\n")

        # The LLM that will decide which tools to call
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

        # create_react_agent builds a ReAct loop:
        # Think → pick a tool → call it → observe result → think again → answer
        agent = create_react_agent(llm, tools)

        # ── Demo Queries ──────────────────────────────────────────────
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
