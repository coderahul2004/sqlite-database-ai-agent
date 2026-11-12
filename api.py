from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agent import ask_agent

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the agent and verify that MCP tools can be loaded at startup.
    from agent import get_agent
    await get_agent()
    print("MySQL AI Agent API is ready.")
    yield

app = FastAPI(
    title="MySQL Database AI Agent",
    description="Ask natural-language questions about your MySQL database.",
    version="1.0.0",
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

class ChatResponse(BaseModel):
    answer: str
    thread_id: str

@app.get("/")
async def home():
    return {"status": "online", "message": "MySQL Database AI Agent API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        answer = await ask_agent(request.query.strip(), request.thread_id)
        return ChatResponse(answer=answer, thread_id=request.thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")