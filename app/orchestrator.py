import asyncio
import re
import logging
from typing import Any, Dict
import networkx as nx
from tenacity import stop_after_attempt, wait_exponential, retry_if_exception_type, AsyncRetrying

from .models import GraphSpec, NodeSpec
from .agents import AGENT_REGISTRY, TOOL_REGISTRY

try:
    from asyncio import timeout as async_timeout  # Python 3.11+
except ImportError:
    from async_timeout import timeout as async_timeout  # Python < 3.11 (requires pip install async-timeout)

logger = logging.getLogger("orchestrator")
logger.setLevel(logging.INFO)

REF_RE = re.compile(r"\$\{([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)\}")


class Orchestrator:
    def __init__(self, concurrency: int = 4):
        self.sem = asyncio.Semaphore(concurrency)

    def _resolve_inputs(self, node: NodeSpec, context: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Replace ${node.key} references with values from context."""
        def replace_refs(val: str) -> str:
            def _rep(m):
                nid, key = m.group(1), m.group(2)
                if nid not in context:
                    return f"<missing:{nid}>"
                try:
                    return str(context[nid].get(key, f"<missing_key:{key}>"))
                except Exception:
                    return f"<badctx:{nid}>"
            return REF_RE.sub(_rep, val)

        resolved = {}
        for k, v in node.inputs.items():
            if isinstance(v, str):
                resolved[k] = replace_refs(v)
            else:
                resolved[k] = v
        return resolved

    def _build_graph(self, spec: GraphSpec) -> nx.DiGraph:
        g = nx.DiGraph()
        for n in spec.nodes:
            g.add_node(n.id, node=n)
        for e in spec.edges:
            g.add_edge(e.source, e.target)
        if not nx.is_directed_acyclic_graph(g):
            raise ValueError("Execution graph must be a DAG")
        return g

    async def _run_node(self, node: NodeSpec, context: Dict[str, Dict[str, Any]]):
        inputs = self._resolve_inputs(node, context)
        AgentCls = AGENT_REGISTRY.get(node.agent.name)
        if not AgentCls:
            raise ValueError(f"Unknown agent: {node.agent.name}")

        # Build tools
        tools = []
        for t in node.agent.tools:
            ToolCls = TOOL_REGISTRY.get(t.name)
            if not ToolCls:
                raise ValueError(f"Unknown tool: {t.name}")
            tools.append(ToolCls(**t.config))

        agent = AgentCls(params=node.agent.params, tools=tools)

        async def invoke():
            async with async_timeout(node.timeout_seconds):
                return await agent.run(**inputs)

        async with self.sem:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(node.max_retries),
                wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    return node.id, await invoke()

    async def run_graph(self, spec: GraphSpec) -> Dict[str, Dict[str, Any]]:
        g = self._build_graph(spec)
        context: Dict[str, Dict[str, Any]] = {}

        for layer in nx.topological_generations(g):
            tasks = [self._run_node(g.nodes[n]["node"], context) for n in layer]
            for coro in asyncio.as_completed(tasks):
                try:
                    nid, res = await coro
                    context[nid] = res
                except Exception as e:
                    # Store errors at node level
                    context[nid] = {"error": f"node failed after retries: {e}"}

        return context
