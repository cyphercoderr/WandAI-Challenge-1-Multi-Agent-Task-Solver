from typing import Any, Dict, List, Union
from .tools import BaseTool, DataFetcher, ChartGenerator


TOOL_REGISTRY = {
    DataFetcher.name: DataFetcher,
    ChartGenerator.name: ChartGenerator,
}


class BaseAgent:
    name = "base"

    def __init__(self, params: Dict[str, Any] | None = None, tools: List[BaseTool] | None = None):
        self.params = params or {}
        self.tools = tools or []

    def get_tool(self, name: str) -> BaseTool | None:
        for t in self.tools:
            if getattr(t, "name", None) == name:
                return t
        return None

    async def run(self, **inputs) -> Dict[str, Any]:
        raise NotImplementedError


class EchoAgent(BaseAgent):
    name = "echo"
    async def run(self, **inputs):
        try:
            return {"echo": inputs or {}, "params": self.params}
        except Exception as e:
            return {"error": f"EchoAgent failed: {repr(e)}"}


class SumAgent(BaseAgent):
    name = "sum"
    async def run(self, numbers: Union[List[int], List[float]] = None):
        try:
            if not numbers:
                return {"error": "no numbers provided"}
            total = sum(numbers)
            return {"sum": total, "params": self.params}
        except Exception as e:
            return {"error": f"SumAgent failed: {repr(e)}"}


class HttpGetAgent(BaseAgent):
    name = "http_get"
    async def run(self, url: str):
        try:
            fetcher = self.get_tool("data_fetcher")
            if not fetcher:
                return {"error": "data_fetcher tool not configured"}

            resp = await fetcher(url=url)
            if not isinstance(resp, dict):
                return {"error": "invalid fetcher response", "raw": str(resp)}

            return {
                "status": resp.get("status"),
                "length": len(resp.get("text") or ""),
                "headers": resp.get("headers", {}),
            }
        except Exception as e:
            return {"error": f"HttpGetAgent failed: {repr(e)}"}


AGENT_REGISTRY = {
    EchoAgent.name: EchoAgent,
    SumAgent.name: SumAgent,
    HttpGetAgent.name: HttpGetAgent,
}
