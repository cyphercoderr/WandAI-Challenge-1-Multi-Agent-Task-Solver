from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal

class ToolConfig(BaseModel):
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)

class AgentConfig(BaseModel):
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    tools: List[ToolConfig] = Field(default_factory=list)

class NodeSpec(BaseModel):
    id: str
    agent: AgentConfig
    inputs: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 20
    max_retries: int = 2

class EdgeSpec(BaseModel):
    source: str
    target: str

class GraphSpec(BaseModel):
    nodes: List[NodeSpec]
    edges: List[EdgeSpec] = Field(default_factory=list)

class RunRequest(BaseModel):
    graph: GraphSpec
    concurrency: int = 4

class RunResponse(BaseModel):
    run_id: str
    status: Literal["running", "succeeded", "failed"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
