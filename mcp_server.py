
import os
import re
import json
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("sqlite-database-agent")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "db/olist.sqlite"))

if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH

DB_PATH = DB_PATH.resolve()


def get_connection():
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"SQLite database not found: {DB_PATH}")

    connection = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro",
        uri=True,
        timeout=10
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")

    return connection


@mcp.tool()
def list_tables() -> str:
    """List all tables in the SQLite database."""

    connection = get_connection()

    try:
        cursor = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        tables = [row["name"] for row in cursor.fetchall()]

        return json.dumps(tables)

    finally:
        connection.close()


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Get the columns and data types of a SQLite table."""

    connection = get_connection()

    try:
        exists = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,)
        ).fetchone()

        if not exists:
            return f"Table '{table_name}' does not exist."

        safe_name = table_name.replace('"', '""')

        cursor = connection.execute(
            f'PRAGMA table_info("{safe_name}")'
        )

        return json.dumps(
            [dict(row) for row in cursor.fetchall()],
            default=str
        )

    finally:
        connection.close()


@mcp.tool()
def run_readonly_query(sql_query: str) -> str:
    """Execute a read-only SELECT query against SQLite."""

    query = sql_query.strip().rstrip(";").strip()

    if not query:
        return "Query cannot be empty."

    if not re.match(r"^(SELECT|WITH)\b", query, re.IGNORECASE):
        return "Only SELECT queries are allowed."

    blocked = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|"
        r"ATTACH|DETACH|VACUUM|REINDEX|PRAGMA)\b",
        re.IGNORECASE
    )

    if blocked.search(query):
        return "Write and administrative SQL operations are blocked."

    if not re.search(r"\bLIMIT\b", query, re.IGNORECASE):
        query += " LIMIT 200"

    connection = get_connection()

    try:
        allowed_actions = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
        }

        if hasattr(sqlite3, "SQLITE_RECURSIVE"):
            allowed_actions.add(sqlite3.SQLITE_RECURSIVE)

        def authorize(action, arg1, arg2, database, trigger):
            if action in allowed_actions:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)

        cursor = connection.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]

        return json.dumps({
            "row_count": len(rows),
            "rows": rows
        }, default=str)

    except sqlite3.Error as error:
        return f"SQLite query error: {error}"

    finally:
        connection.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
