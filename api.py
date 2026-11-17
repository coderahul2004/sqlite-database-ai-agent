import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agent import ask_agent
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = (BASE_DIR / "db").resolve()
DB_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("SQLite AI Agent API is ready. Database agents will load on demand.")
    yield
app = FastAPI(
    title="SQLite Database AI Agent",
    description="Ask natural-language questions about uploaded SQLite databases.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    thread_id: str = Field(default="default", min_length=1, max_length=100)
    database_name: str = Field(default="olist.sqlite", min_length=1, max_length=255)
class ChatResponse(BaseModel):
    answer: str
    thread_id: str
    database_name: str
def resolve_database(database_name: str) -> Path:
    safe_name = Path(database_name.replace("\\", "/")).name
    if safe_name != database_name or safe_name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid database name.")
    if Path(safe_name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .db, .sqlite, and .sqlite3 files are supported.")
    path = (DB_DIR / safe_name).resolve()
    try:
        path.relative_to(DB_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid database location.")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Database '{safe_name}' was not found in the db folder.")
    return path
@app.get("/")
async def home():
    return {"status": "online", "message": "SQLite Database AI Agent API is running"}
@app.get("/health")
async def health():
    return {"status": "healthy"}
@app.get("/databases")
async def list_databases():
    databases = []
    for path in sorted(DB_DIR.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES:
            databases.append({"name": path.name, "size_bytes": path.stat().st_size})
    return {"databases": databases}
@app.post("/databases/upload")
async def upload_database(file: UploadFile = File(...)):
    original_name = file.filename or ""
    safe_name = Path(original_name.replace("\\", "/")).name
    if not safe_name or safe_name != original_name or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Please upload a file with a valid filename.")
    if Path(safe_name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Upload a .db, .sqlite, or .sqlite3 file.")
    destination = (DB_DIR / safe_name).resolve()
    if destination.exists():
        raise HTTPException(status_code=409, detail=f"A database named '{safe_name}' already exists. Rename the file or remove the old one first.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Database file is larger than the 100 MB upload limit.")
    if not content.startswith(b"SQLite format 3\x00"):
        raise HTTPException(status_code=400, detail="The uploaded file does not have a valid SQLite database header.")
    temp_path = DB_DIR / f".{uuid.uuid4().hex}.uploading"
    try:
        temp_path.write_bytes(content)
        connection = sqlite3.connect(f"file:{temp_path.as_posix()}?mode=ro", uri=True, timeout=10)
        try:
            check = connection.execute("PRAGMA quick_check").fetchone()
            if not check or check[0] != "ok":
                raise HTTPException(status_code=400, detail="The uploaded SQLite database failed its integrity check.")
        finally:
            connection.close()
        temp_path.replace(destination)
    except HTTPException:
        raise
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=f"Could not read this SQLite database: {exc}")
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
    return {"message": "Database uploaded successfully.", "database": safe_name, "size_bytes": destination.stat().st_size}
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    database_path = resolve_database(request.database_name)
    try:
        answer = await ask_agent(
            request.query.strip(),
            request.thread_id,
            database_path,
        )
        return ChatResponse(
            answer=answer,
            thread_id=request.thread_id,
            database_name=database_path.name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")