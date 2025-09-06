# Wand AI – Challenge 1: Multi-Agent Task Solver

A minimal, production-lean prototype of an **agent orchestration layer** built with  
**Python + FastAPI + asyncio**.

---

## Note
The agents provided here (Echo, Sum, HttpGet) are **hardcoded sample agents** to mimic real-time conversation behavior. They demonstrate orchestration mechanics, not domain logic.

---

## Why Challenge 1?
This aligns directly with Wand AI’s mission of operating and connecting **agent ecosystems**.  
The prototype demonstrates:

- **Dynamic agent creation** and a **DAG execution graph**
- **Concurrency**, **retries**, and **timeouts**
- **Pluggable tools** (e.g., HTTP data fetcher, chart generator)
- A clean **HTTP API** ready for frontend consumption

---

## Architecture
- **FastAPI** → API layer  
- **Orchestrator** → DAG executor (via `networkx`) with concurrency  
- **Retries** → with exponential backoff (`tenacity`)  
- **Timeouts** → via `asyncio.wait_for`  
- **Pluggable agents/tools** → registered in simple registries  
- **In-memory run store** → for simplicity (can be swapped with Redis/Postgres)
```
app/
agents.py # BaseAgent + sample agents (Echo, Sum, HttpGet)
tools.py # BaseTool + sample tools (DataFetcher, ChartGenerator)
orchestrator.py # DAG builder + concurrent executor, retries/timeouts
models.py # Pydantic models for API contracts
main.py # FastAPI app (execute graph, get run)
```

---

## How It Works

1. **User submits a graph** via `POST /graph/execute`  
   - Nodes = agents with configs & inputs  
   - Edges = dependencies between nodes  

2. **The Orchestrator**:  
   - Builds the DAG and validates it is acyclic  
   - Resolves dependencies (inputs can reference outputs from other nodes)  
   - Runs nodes layer-by-layer with concurrency (using `asyncio.Semaphore`)  
   - Applies **retries** and **timeouts** per node  

3. **Agents**:  
   - Run in isolation and return results  
   - Results are stored in the orchestration context and passed downstream  

4. **Response**:  
   - The API returns a `run_id`, `status`, `result` (node outputs), and any `error`  

---

## Running Locally
**Prereqs:** Python 3.11+

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000/docs
```
## Running with Docker
```
docker build -t wandai-agents .
docker run -p 8000:8000 wandai-agents
# or: docker compose up --build
```
## Example: Execute a 3-node DAG

Here’s a sample request where:
* Node A echoes a message
* Node B sums numbers [1,2,3,4]
* Node C fetches content from https://example.com, depending on A & B

## JSON request (for Swagger /graph/execute)
```json
{
  "concurrency": 4,
  "graph": {
    "nodes": [
      {
        "id": "A",
        "agent": { "name": "echo", "params": {}, "tools": [] },
        "inputs": { "msg": "hello from A" },
        "timeout_seconds": 10,
        "max_retries": 2
      },
      {
        "id": "B",
        "agent": { "name": "sum", "params": {}, "tools": [] },
        "inputs": { "numbers": [1, 2, 3, 4] },
        "timeout_seconds": 10,
        "max_retries": 2
      },
      {
        "id": "C",
        "agent": {
          "name": "http_get",
          "params": {},
          "tools": [
            { "name": "data_fetcher", "config": { "timeout": 5 } }
          ]
        },
        "inputs": { "url": "https://example.com" },
        "timeout_seconds": 10,
        "max_retries": 2
      }
    ],
    "edges": [
      { "source": "A", "target": "C" },
      { "source": "B", "target": "C" }
    ]
  }
}
```
## Example Success Response
```
{
  "run_id": "6d28b11d-1268-4931-9dee-a0f45b5f686e",
  "status": "succeeded",
  "result": {
    "A": { "echo": { "msg": "hello from A" }, "params": {} },
    "B": { "sum": 10, "params": {} },
    "C": {
      "status": 200,
      "length": 1256,
      "headers": {
        "Content-Type": "text/html",
        "Date": "Sat, 06 Sep 2025 08:19:47 GMT"
      }
    }
  },
  "error": null
}
```
## Design Decisions & Trade-offs

* In-memory run store → for speed (swap with Redis/Postgres for prod)
* Simple registries → lightweight, could evolve into plugin system
* Single-process asyncio → sufficient for demo, extend with Celery/RQ for scaling
* No auth → add OAuth/JWT & RBAC for enterprise
* Minimal logging → expand with OpenTelemetry + structured logs

## Extending

* Add new agents by subclassing BaseAgent and registering in AGENT_REGISTRY
* Add tools by subclassing BaseTool and registering in TOOL_REGISTRY
* Support future features: streaming outputs, cancellation, checkpointing

## Demo Script (≤5 min)

* Start API → open /docs swagger.
* Run the example DAG request → see concurrency and results.
* Open agents.py → show how to plug in new agents.
* Explain retries & timeouts → show config per node.
* Close with production hardening roadmap (auth, persistence, observability).

## Tests (Quick Smoke)

You can run the sample JSON (above) in Swagger or test Orchestrator.run_graph directly.
**For example, with pytest:**
```python
import pytest
from app.orchestrator import Orchestrator
from app.models import GraphSpec, NodeSpec, AgentConfig

@pytest.mark.asyncio
async def test_sum_agent():
    graph = GraphSpec(
        nodes=[
            NodeSpec(
                id="B",
                agent=AgentConfig(name="sum", params={}, tools=[]),
                inputs={"numbers": [1, 2, 3]},
            )
        ]
    )
    orch = Orchestrator(concurrency=2)
    result = await orch.run_graph(graph)
    assert result["B"]["sum"] == 6
```

## Author
Challenge completed by Ahmad.