"""
Patent Guard v2.0 - FastAPI Backend API
=======================================
Stateless REST API and Streaming SSE endpoint for Patent Analysis.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from src.vector_db import PineconeClient
from src.history_manager import HistoryManager
from src.analysis_logic import run_full_analysis

app = FastAPI(
    title="Short-Cut Patent API",
    description="Stateless Backend API for Patent Guard v2.0",
    version="2.0.0"
)

# CORS middleware for Frontend SPA integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global singleton clients
db_client = None
history_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    global db_client, history_manager
    try:
        db_client = PineconeClient(skip_init_check=True)
    except Exception as e:
        print(f"Failed to load Pinecone DB: {e}")
    
    try:
        history_manager = HistoryManager()
    except Exception as e:
        print(f"Failed to load HistoryManager: {e}")


class AnalyzeRequest(BaseModel):
    user_idea: str
    user_id: str
    use_hybrid: bool = True
    ipc_filters: list[str] = None


@app.post("/api/v1/analyze")
async def analyze_idea_stream(req: AnalyzeRequest):
    """
    Stream patent analysis process to client using Server-Sent Events (SSE).
    """
    if not db_client:
        raise HTTPException(status_code=503, detail="Database client is unavailable.")
        
    async def event_generator():
        try:
            async for event in run_full_analysis(
                user_idea=req.user_idea,
                user_id=req.user_id,
                db_client=db_client,
                history_manager=history_manager,
                use_hybrid=req.use_hybrid,
                ipc_filters=req.ipc_filters
            ):
                # Prepare SSE formatted string
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            # Safe exception handling to stream error state back
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/history/{user_id}")
async def get_history(user_id: str):
    """Get analysis history for a specific user."""
    if not history_manager:
        raise HTTPException(status_code=503, detail="History manager unavailable.")
        
    try:
        history = history_manager.load_recent(user_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    # Local dev runner
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
