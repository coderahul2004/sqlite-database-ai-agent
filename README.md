# 🗄️ Database AI Agent

Ask questions about a database in plain English and get answers back.
The AI agent looks at the tables, writes a safe **read-only SQL query**, runs it, and explains the result.

The project uses the **Olist e-commerce dataset** stored in a SQLite file (`olist.sqlite`).

---
**Live app:** https://app-database-ai-agent-escrzhwwrv4hyx6edeq7sc.streamlit.app/

## Features

- Chat with your database in natural language
- Agent can list tables, describe columns, and run SELECT queries
- **Read-only and safe**: write queries (INSERT, UPDATE, DELETE, DROP, etc.) are blocked
- Conversation memory: each chat has its own `thread_id`
- Simple Streamlit chat UI with example questions
- FastAPI backend with `/chat` and `/health` endpoints

---

## Tech Stack

| Part | Tool |
|------|------|
| LLM | Groq (via `langchain-groq`) |
| Agent | LangChain `create_agent` + LangGraph `InMemorySaver` (memory) |
| Tools | MCP server built with `FastMCP` (stdio) |
| MCP connection | `langchain-mcp-adapters` |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Database | SQLite (Olist dataset) |

---

## How It Works

```
Streamlit UI (app.py)
        |
        |  HTTP POST /chat
        v
FastAPI (api.py)
        |
        v
Agent (agent.py)  <---->  Groq LLM
        |
        |  MCP (stdio)
        v
MCP Server (mcp_server.py)
        |
        v
SQLite database (olist.sqlite)
```

1. You type a question in the Streamlit app.
2. `app.py` sends it to the FastAPI backend (`/chat`).
3. `api.py` calls the agent in `agent.py`.
4. The agent decides which tool to use: `list_tables`, `describe_table`, or `run_readonly_query`.
5. The tools run inside `mcp_server.py` and read the SQLite database.
6. The agent explains the result and the answer is shown in the chat.

---

## Project Structure

```
.
├── agent.py           # LangChain agent, Groq model, MCP client, memory
├── api.py             # FastAPI backend (/, /health, /chat)
├── app.py             # Streamlit chat UI
├── mcp_server.py      # MCP server with the 3 database tools
├── requirements.txt   # Python packages
├── README.md
├── .env               # Your secret keys (create this yourself, do not upload to GitHub)
└── db/
    └── olist.sqlite   # Olist database
```

---

## MCP Tools

| Tool | What it does |
|------|--------------|
| `list_tables` | Returns all table names in the database |
| `describe_table` | Returns the columns and data types of one table |
| `run_readonly_query` | Runs a SELECT query and returns the rows (max 200 rows by default) |

---

## Safety

The database is protected in 4 ways:

1. The SQLite file is opened in **read-only mode** (`mode=ro`).
2. `PRAGMA query_only = ON` is set on every connection.
3. Only queries starting with `SELECT` or `WITH` are allowed, and words like `INSERT`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, `PRAGMA` are blocked.
4. A SQLite **authorizer** denies every action except reading data.

If a query has no `LIMIT`, `LIMIT 200` is added automatically.

---

## Setup (Run Locally)

### 1. Clone the project

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

### 3. Install packages

```bash
pip install -r requirements.txt
```

### 4. Add the database

Create a `db` folder and put `olist.sqlite` inside it:

```
db/olist.sqlite
```

> If your file is in the main project folder instead, set `SQLITE_DB_PATH=olist.sqlite` in the `.env` file.

### 5. Create the `.env` file

Create a file named `.env` in the project folder:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
SQLITE_DB_PATH=db/olist.sqlite
```

- Get a free API key from [console.groq.com](https://console.groq.com)
- `GROQ_MODEL` must be a Groq model that supports **tool calling**.

---

## Run the Project

You need **two terminals** (both with the virtual environment activated).

**Terminal 1: start the FastAPI backend**

```bash
uvicorn api:app --reload
```

Wait until you see `MySQL AI Agent API is ready.` The API runs at http://127.0.0.1:8000
(API docs: http://127.0.0.1:8000/docs).

**Terminal 2: start the Streamlit app**

```bash
streamlit run app.py
```

The app opens at http://localhost:8501.

---

## Example Questions

- Show me all tables in the database.
- How many customers are there?
- Show the total number of orders by status.
- Which are the top 10 orders by price?
- Which product categories have the most items sold?

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Check that the API is running |
| GET | `/health` | Health check |
| POST | `/chat` | Send a question to the agent |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How many customers are there?", "thread_id": "test1"}'
```

Example response:

```json
{
  "answer": "There are 99441 customers ...",
  "thread_id": "test1"
}
```

---

## Deploying the Streamlit App (Streamlit Cloud)

Streamlit Cloud only runs `app.py` (the UI). The FastAPI backend must run somewhere else (for example Render or Railway).

1. Deploy the backend (`api.py`, `agent.py`, `mcp_server.py`, `db/olist.sqlite`) and add `GROQ_API_KEY` and `GROQ_MODEL` as environment variables there.
2. Deploy `app.py` on Streamlit Cloud.
3. In the app sidebar, change **FastAPI URL** to your deployed backend URL.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GROQ_API_KEY is missing` | Add the key to your `.env` file |
| Model error or `None` model | Set `GROQ_MODEL` in `.env` |
| `SQLite database not found` | Check the path of `olist.sqlite` and `SQLITE_DB_PATH` |
| `Could not connect to FastAPI` | Start the backend first with `uvicorn api:app --reload` |
| Request timed out | Ask a simpler question or try again |

---

## What I Learned

- Building an AI agent with LangChain and tool calling
- Creating an MCP server and connecting it to an agent
- Making a database agent safe with read-only rules
- Connecting a FastAPI backend with a Streamlit frontend
- Adding conversation memory with thread IDs

---

## Future Improvements

- Show the SQL query in a separate box in the UI
- Show results as tables and charts
- Add user login
- Support other databases (MySQL, PostgreSQL)