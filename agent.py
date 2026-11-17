import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
MCP_SERVER_PATH = BASE_DIR / "mcp_server.py"
SYSTEM_PROMPT_TEMPLATE = """
You are a SQLite Database Assistant. You answer questions using ONLY the selected SQLite database: {database_name}.
Rules:
1. Only answer questions about the selected database and its data.
2. Use list_tables to discover available tables when needed.
3. Use describe_table before querying an unfamiliar table.
4. Use run_readonly_query for data retrieval. Never pretend a query ran if the tool did not run.
5. Never invent table names, columns, values, or query results.
6. Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, DETACH, PRAGMA, or other write/administrative operations.
7. Answer clearly and include these sections when a SQL query is executed:
   **Answer**: a concise explanation of the result.
   **SQL query**: the exact SELECT/WITH query used, in a SQL code block.
   **Results**: show the returned rows in a readable Markdown table when practical. If there are many rows, summarize and show a useful subset.
   **How the data was obtained**: briefly explain the tables and joins/aggregations used.
8. If the question is unrelated to the selected database, politely ask for a database-related question.
9. If a tool reports an error, explain it honestly instead of guessing.
10. Do not use information from another database or another conversation.
"""
checkpointer = InMemorySaver()
agent_cache = {}
mcp_clients = {}
def _database_path(database_path: str | Path) -> Path:
    """Resolve and validate a database path inside this project's db folder."""
    db_dir = (BASE_DIR / "db").resolve()
    candidate = Path(database_path).resolve()
    try:
        candidate.relative_to(db_dir)
    except ValueError as exc:
        raise ValueError("The selected database must be inside the project's db folder.") from exc

    if candidate.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("Only .db, .sqlite, and .sqlite3 databases are supported.")
    if not candidate.is_file():
        raise FileNotFoundError(f"SQLite database not found: {candidate.name}")
    return candidate
async def get_agent(database_path: str | Path):
    """Return an agent connected to the requested SQLite database."""
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")
    selected_path = _database_path(database_path)
    cache_key = str(selected_path)
    if cache_key in agent_cache:
        return agent_cache[cache_key]
    if not MCP_SERVER_PATH.is_file():
        raise FileNotFoundError(f"MCP server file not found: {MCP_SERVER_PATH}")
    mcp_config = {
        "sqlite": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(MCP_SERVER_PATH)],
            "env": {**os.environ, "SQLITE_DB_PATH": str(selected_path)},
        }
    }
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    model = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT_TEMPLATE.format(database_name=selected_path.name),
        checkpointer=checkpointer,
    )
    mcp_clients[cache_key] = client
    agent_cache[cache_key] = agent
    print(f"MCP tools loaded for {selected_path.name}:", [tool.name for tool in tools])
    return agent
async def ask_agent(question: str, thread_id: str = "default", database_path: str | Path = None) -> str:
    if database_path is None:
        database_path = BASE_DIR / "db" / "olist.sqlite"
    selected_path = _database_path(database_path)
    agent = await get_agent(selected_path)
    scoped_thread_id = f"{selected_path.name}::{thread_id}"
    config = {"configurable": {"thread_id": scoped_thread_id}}
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=question)]},
        config=config,
    )
    messages = result.get("messages", [])
    if not messages:
        return "The agent did not return a response."
    content = messages[-1].content
    if isinstance(content, str):
        return content
    return str(content)