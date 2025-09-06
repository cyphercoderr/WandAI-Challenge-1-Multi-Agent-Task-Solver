# app/tools.py
import aiohttp
from typing import Any, Dict

class BaseTool:
    name = "base"
    def __init__(self, **config):
        self.config = config
    async def __call__(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

class DataFetcher(BaseTool):
    name = "data_fetcher"

    async def __call__(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """
        Always return a dict. Never raise. In case of network errors,
        return {'status': None, 'text': '', 'headers': {}, 'error': str(e)}.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 10))
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, **kwargs) as resp:
                    # read text defensively
                    try:
                        text = await resp.text()
                    except Exception:
                        # fallback to read bytes and decode safely
                        try:
                            b = await resp.read()
                            text = b.decode('utf-8', errors='ignore')
                        except Exception:
                            text = ""
                    return {
                        "status": getattr(resp, "status", None),
                        "text": text or "",
                        "headers": dict(getattr(resp, "headers", {}) or {}),
                    }
        except Exception as e:
            # Swallow exceptions — always return a dict
            return {"status": None, "text": "", "headers": {}, "error": str(e)}

class ChartGenerator(BaseTool):
    name = "chart_generator"
    async def __call__(self, data, **kwargs):
        # Placeholder implementation
        return {"chart_url": "https://example.com/chart/placeholder", "points": data}
