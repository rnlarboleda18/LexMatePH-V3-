from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import signal
from pipeline_manager import PipelineManager
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Bar Review Pipeline Admin")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline_mgr = PipelineManager()

class PipelineConfig(BaseModel):
    targets: Optional[List[str]] = None
    mode: str = "auto" # "auto" or "manual"

class FileContentRequest(BaseModel):
    path: str

class SaveContentRequest(BaseModel):
    path: str
    content: str

@app.get("/")
def read_root():
    return {"status": "Online", "service": "Bar Review Pipeline API"}

@app.get("/api/status")
def get_status():
    return {
        "is_running": pipeline_mgr.is_running(),
        "stage": pipeline_mgr.current_stage
    }

@app.post("/api/pipeline/start")
async def start_pipeline(config: PipelineConfig, background_tasks: BackgroundTasks):
    if pipeline_mgr.is_running():
        raise HTTPException(status_code=400, detail="Pipeline already running")
    
    # Start pipeline with mode
    background_tasks.add_task(pipeline_mgr.start_pipeline, targets=config.targets, mode=config.mode)
    return {"message": f"Pipeline triggered in {config.mode} mode"}

@app.post("/api/pipeline/resume")
async def resume_pipeline(background_tasks: BackgroundTasks):
    """Resumes pipeline (skips scraping/conversion) -> manual ingest trigger"""
    if pipeline_mgr.is_running():
        raise HTTPException(status_code=400, detail="Pipeline already running")
    
    # Run only Ingest and Digest by skipping Scrape and Convert
    background_tasks.add_task(
        pipeline_mgr.start_pipeline, 
        targets=None, 
        mode="auto", 
        skip_scrape=True, 
        skip_convert=True
    )
    return {"message": "Pipeline resumed (Ingest/Digest)"}

@app.post("/api/cases/content")
def get_case_content(req: FileContentRequest):
    # Verify path is safe (simple check)
    if ".." in req.path or not req.path.endswith(".md"):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "lawphil_md", req.path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}

@app.post("/api/cases/save")
def save_case_content(req: SaveContentRequest):
    if ".." in req.path or not req.path.endswith(".md"):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "lawphil_md", req.path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"message": "File saved successfully"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/stop")
def stop_pipeline():
    if not pipeline_mgr.is_running():
        raise HTTPException(status_code=400, detail="Pipeline not running")
    
    pipeline_mgr.stop_pipeline()
    return {"message": "Pipeline stop signal sent"}

@app.websocket("/api/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pipeline_mgr.register_client(websocket)
    try:
        while True:
            # Keep alive check or listen for commands
            await websocket.receive_text()
    except Exception:
        pipeline_mgr.unregister_client(websocket)

@app.get("/api/cases/preview")
def list_converted_cases():
    # List MD files in the data directory
    # Assume relative path structure from project root
    base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "lawphil_md")
    cases = []
    if os.path.exists(base_path):
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".md"):
                    # Extract year folder -> case
                    rel_dir = os.path.relpath(root, base_path)
                    cases.append({
                        "filename": file,
                        "year": rel_dir,
                        "path": os.path.join(rel_dir, file) 
                    })
    return {"cases": cases[:100]} # Limit for now

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
