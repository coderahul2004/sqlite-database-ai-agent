import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage

load_dotenv()

SYSTEM_PROMPT = """
You are MySQL Database Assistant, an AI agent that answers questions using the
configured MySQL database.

Rules:
1. Only answer questions about the database and its data.
2. Use list_tables to discover available tables when needed.
3. Use describe_table before querying an unfamiliar table.
4. Use run_readonly_query for data retrieval.
5. Never invent table names, columns, values, or query results.
6. Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or other write operations.
7. Explain results clearly. Include the SQL query used when it helps the user.
8. If a question is unrelated to the database, politely ask for a database-related question.
9. If a tool reports an error, explain it honestly instead of guessing.
"""

checkpointer = InMemorySaver()
mcp_client = None
agent_cache = {}

async def get_agent():
    global mcp_client

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")

    if "default" in agent_cache:
        return agent_cache["default"]

    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

    mcp_config = {
        "mysql": {
            "transport": "stdio",
            "command": os.sys.executable,
            "args": [server_path],
        }
    }

    mcp_client = MultiServerMCPClient(mcp_config)
    tools = await mcp_client.get_tools()

    model = ChatGroq(
        model=os.getenv("GROQ_MODEL"),
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
    agent_cache["default"] = agent
    print("MCP tools loaded:", [tool.name for tool in tools])
    return agent

async def ask_agent(question: str, thread_id: str = "default") -> str:
    agent = await get_agent()
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=question)]},
        config=config,
    )
    messages = result.get("messages", [])
    if not messages:
        return "The agent did not return a response."
    return str(messages[-1].content)