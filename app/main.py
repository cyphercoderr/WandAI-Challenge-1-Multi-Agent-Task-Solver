from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
import uuid

from .models import RunRequest, RunResponse
from .orchestrator import Orchestrator
from fastapi.responses import FileResponse

app = FastAPI(title="WandAI Agent Orchestration API", version="0.1.0")

RUNS: Dict[str, Dict[str, Any]] = {}

@app.post("/graph/execute", response_model=RunResponse)
async def execute_graph(req: RunRequest):
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"status": "running", "result": None, "error": None}

    try:
        orchestrator = Orchestrator(concurrency=req.concurrency)
        result = await orchestrator.run_graph(req.graph)
        RUNS[run_id]["status"] = "succeeded"
        RUNS[run_id]["result"] = result
    except Exception as e:
        # catch anything unexpected; ideally should not happen
        RUNS[run_id]["status"] = "failed"
        RUNS[run_id]["error"] = str(e)
    return RunResponse(run_id=run_id, status=RUNS[run_id]["status"], result=RUNS[run_id]["result"], error=RUNS[run_id]["error"])

@app.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(404, "run not found")
    entry = RUNS[run_id]
    return RunResponse(run_id=run_id, status=entry["status"], result=entry["result"], error=entry["error"])

@app.get("/health")
async def health():
    return JSONResponse({"ok": True})


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/favicon.ico")