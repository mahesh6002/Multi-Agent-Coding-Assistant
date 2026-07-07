import os
import json
import sqlite3
import asyncio
import threading
import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import LangGraph app and settings
from agent_graph.graph import app as graph_app
from agent_graph.config import settings

api_app = FastAPI(title="Multi-Agent Coding Assistant API")

class GenerateRequest(BaseModel):
    spec: str
    thread_id: str
    output_dir: str = "generated_project"

class ResumeRequest(BaseModel):
    thread_id: str
    output_dir: str = "generated_project"

def get_db_threads() -> List[str]:
    """Queries checkpoints.db to list all unique thread IDs."""
    if not os.path.exists(settings.CHECKPOINT_DB_PATH):
        return []
    conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
        return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def run_graph_in_thread(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, spec: str, thread_id: str, output_dir: str):
    """Runs the LangGraph workflow in a background thread, pushing state snapshots into the queue."""
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "spec": spec,
        "architecture": {"files": [], "explanation": ""},
        "files": {},
        "test_files": {},
        "test_results": {},
        "lint_results": {},
        "review_notes": [],
        "iteration_count": {},
        "status": "planning",
        "next_agent": "planner",
        "run_log": []
    }
    
    try:
        # Check for existing checkpoint to support resumption
        existing_state = graph_app.get_state(config)
        state_input = None if (existing_state and existing_state.values) else initial_state
        
        # Stream the graph execution synchronously
        for event in graph_app.stream(state_input, config, stream_mode="values"):
            # Put event into queue in a thread-safe way
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "event", "data": event})
            
        # Get final state to save generated files
        final_state = graph_app.get_state(config).values
        if final_state and final_state.get("status") == "done":
            # Write source/test files to disk
            os.makedirs(output_dir, exist_ok=True)
            for filepath, content in final_state.get("files", {}).items():
                out_path = os.path.join(output_dir, filepath)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
            for filepath, content in final_state.get("test_files", {}).items():
                out_path = os.path.join(output_dir, filepath)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
            # Save run_log trace
            log_path = os.path.join(output_dir, "run_trace.json")
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(final_state.get("run_log", []), f, indent=2)
                
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "done"})
    except Exception as e:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(e)})

async def stream_orchestrator(spec: str, thread_id: str, output_dir: str):
    """Async generator bridging the background thread queue to SSE text/event-stream chunks."""
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    
    # Run LangGraph in a separate background thread to keep FastAPI completely responsive
    t = threading.Thread(
        target=run_graph_in_thread,
        args=(loop, queue, spec, thread_id, output_dir)
    )
    t.daemon = True
    t.start()
    
    try:
        while True:
            item = await queue.get()
            if item["type"] == "done":
                yield f"event: done\ndata: {json.dumps({'message': 'Generation finished successfully'})}\n\n"
                break
            elif item["type"] == "error":
                yield f"event: error\ndata: {json.dumps({'error': item['error']})}\n\n"
                break
            elif item["type"] == "event":
                event = item["data"]
                # Package state payload
                run_log = event.get("run_log", [])
                latest_log = run_log[-1] if run_log else {}
                
                payload = {
                    "status": event.get("status"),
                    "run_log": latest_log,
                    "files": event.get("files", {}),
                    "test_files": event.get("test_files", {}),
                    "review_notes": event.get("review_notes", []),
                    "lint_results": event.get("lint_results", {}),
                    "iteration_count": event.get("iteration_count", {})
                }
                yield f"event: update\ndata: {json.dumps(payload)}\n\n"
    except asyncio.CancelledError:
        # FastAPI triggers this when the client disconnects mid-stream.
        # Since we use SQLite checkpointer, the background thread keeps running to completion
        # and its progress is persisted in checkpoints.db. The user can resume or reconnect anytime.
        print(f"Client disconnected from SSE stream for thread: {thread_id}. Underlying run continues in background.")
        raise

@api_app.get("/api/generate")
async def generate(spec: str, thread_id: str, output_dir: str = "generated_project"):
    """Endpoint starting a new task generation, returning an SSE stream."""
    return StreamingResponse(
        stream_orchestrator(spec, thread_id, output_dir),
        media_type="text/event-stream"
    )

@api_app.get("/api/resume")
async def resume(thread_id: str, output_dir: str = "generated_project"):
    """Endpoint resuming an existing task generation from the last saved state, returning an SSE stream."""
    config = {"configurable": {"thread_id": thread_id}}
    existing_state = graph_app.get_state(config)
    if not existing_state or not existing_state.values:
        raise HTTPException(status_code=404, detail=f"No existing checkpoint found for thread ID: {thread_id}")
        
    spec = existing_state.values.get("spec", "")
    return StreamingResponse(
        stream_orchestrator(spec, thread_id, output_dir),
        media_type="text/event-stream"
    )

@api_app.get("/api/threads")
def list_threads() -> List[Dict[str, Any]]:
    """Returns metadata summaries for all available threads (lazy-loaded)."""
    thread_ids = get_db_threads()
    metadata_list = []
    
    for tid in thread_ids:
        try:
            config = {"configurable": {"thread_id": tid}}
            state = graph_app.get_state(config)
            if state and state.values:
                spec = state.values.get("spec", "No spec")
                status = state.values.get("status", "unknown")
                files = state.values.get("files", {})
                run_log = state.values.get("run_log", [])
                
                # Fetch last updated timestamp
                last_updated = run_log[-1].get("timestamp") if run_log else None
                
                metadata_list.append({
                    "thread_id": tid,
                    "task": spec,
                    "status": status,
                    "file_count": len(files),
                    "last_updated": last_updated
                })
        except Exception:
            pass
            
    # Sort by last updated descending
    metadata_list.sort(key=lambda x: x["last_updated"] or "", reverse=True)
    return metadata_list

@api_app.get("/api/threads/{thread_id}")
def get_thread(thread_id: str) -> Dict[str, Any]:
    """Returns the full detailed state for a specific thread_id (lazy-loaded)."""
    config = {"configurable": {"thread_id": thread_id}}
    state = graph_app.get_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
    return {
        "thread_id": thread_id,
        "spec": state.values.get("spec"),
        "status": state.values.get("status"),
        "files": state.values.get("files", {}),
        "test_files": state.values.get("test_files", {}),
        "test_results": state.values.get("test_results", {}),
        "lint_results": state.values.get("lint_results", {}),
        "review_notes": state.values.get("review_notes", []),
        "run_log": state.values.get("run_log", []),
        "iteration_count": state.values.get("iteration_count", {})
    }

# Mount React static files (only if the built directory exists)
dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_dir):
    api_app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
else:
    @api_app.get("/")
    def index_fallback():
        return {"message": "API is running. Please build the React frontend with 'npm run build' inside 'frontend/' to load the dashboard."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api_app, host="0.0.0.0", port=settings.PORT)
