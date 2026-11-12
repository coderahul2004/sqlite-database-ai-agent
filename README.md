# MySQL Database AI Agent

A portfolio project that lets users ask natural-language questions about a MySQL database. It uses a Groq-powered LangChain agent, MCP tools, FastAPI and Streamlit.

## Architecture

- `app.py`: Streamlit chat interface.
- `api.py`: FastAPI endpoints.
- `agent.py`: Groq LLM, LangChain agent, MCP client and conversation memory.
- `mcp_server.py`: MCP tools for MySQL table discovery, schema inspection and read-only SQL queries.

## 1. Requirements

- Python 3.10+
- MySQL server and a database
- Groq API key

## 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```env
GROQ_API_KEY=your_real_groq_key
GROQ_MODEL=openai/gpt-oss-120b
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ecommerce
MYSQL_SSL=false
```

Never upload `.env` or expose your API key on GitHub.

For a hosted MySQL provider, use the host, port, username, password and SSL requirements provided by that provider.

## 5. Prepare the database

Your uploaded notebook describes migrating the Olist SQLite dataset into a MySQL database named `ecommerce`. Run that migration first, or configure the project to point to an existing MySQL database.

The MySQL user should have only the permissions needed to read the target database. The MCP server also blocks common write operations.

## 6. Run the project

Open two terminals from the project directory.

Terminal 1, start FastAPI:

```powershell
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Open API documentation at `http://127.0.0.1:8000/docs`.

Terminal 2, start Streamlit:

```powershell
streamlit run app.py
```

Open the Streamlit URL shown in the terminal, usually `http://localhost:8501`.

## 7. Test questions

- List all tables.
- Describe the orders table.
- Count the number of customers.
- Show the top 10 orders.
- Group orders by status and count them.
- What are the top 5 product categories by number of orders?

Use table and column names that actually exist in your database.

## Security notes

- The MCP query tool accepts only one read-only `SELECT` or `WITH` query.
- It blocks common data modification and administrative SQL keywords.
- It applies a default result limit of 200 rows when no `LIMIT` is supplied.
- Use a dedicated, least-privilege MySQL account. SQL text checks are defense-in-depth, not a replacement for database permissions or a production SQL parser.
- The in-memory LangGraph checkpointer is for local development. It does not persist memory after an API restart and is not a production multi-worker store.

## GitHub checklist

- Add screenshots of the Streamlit interface and API docs.
- Add an architecture diagram.
- Document setup steps and example questions.
- Keep `.env` out of Git.
- Add tests for the SQL safety checks and API endpoints before calling this production-ready.
