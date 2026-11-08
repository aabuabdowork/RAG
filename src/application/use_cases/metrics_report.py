from typing import Any, Dict, List, Optional

from src.domain.interfaces.metrics import IMetrics

FAILED = ("error", "unavailable")
REQUESTS = ("ask", "search", "evaluate")


def percentile(values: List[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round(fraction * (len(ordered) - 1))] if ordered else 0


def percent(part: int, total: int) -> str:
    return f"{part / total:.0%}" if total else "0%"


class MetricsReportUseCase:
    def __init__(self, metrics: IMetrics, primary_model: str) -> None:
        self._metrics = metrics
        self._primary_model = primary_model

    def execute(self, request_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        events = [event for event in self._metrics.events() if request_id in (None, event["request_id"])]
        report = {name: self._requests(events, name) for name in ("ask", "search")}
        asks = report["ask"]["requests"] + sum(event.get("cases", 0) for event in events if event["event"] == "evaluate")
        report["llm"] = self._llm([event for event in events if event["event"] == "llm"], asks)
        report["cache"] = self._cache([event for event in events if event["event"] == "cache"])
        return report

    def history(self, last: int) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for event in self._metrics.events():
            groups.setdefault(event["request_id"], []).append(event)

        rows = []
        for events in groups.values():
            request = next((event for event in events if event["event"] in REQUESTS), None)
            if not request:
                continue
            llm = [event for event in events if event["event"] == "llm" and event["status"] == "ok"]
            cache = [event["hit"] for event in events if event["event"] == "cache"]
            rows.append({
                "time": request["time"][11:19],
                "command": request["event"],
                "channel": request.get("channel", "cli"),
                "status": request["status"],
                "ms": request.get("latency_ms", "-"),
                "in": sum(event["input_tokens"] for event in llm),
                "out": sum(event["output_tokens"] for event in llm),
                "usd": f"{sum(event['cost'] for event in llm):.6f}",
                "cache": f"{sum(cache)} hit / {len(cache) - sum(cache)} miss",
                "query": (request.get("query") or "")[:50],
            })
        return rows[-last:]

    @staticmethod
    def _cache(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        hits = sum(event["hit"] for event in rows)
        return {"lookups": len(rows), "hits": hits, "misses": len(rows) - hits, "hit_rate": percent(hits, len(rows))}

    @staticmethod
    def _requests(events: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
        rows = [event for event in events if event["event"] == name]
        ok = [event for event in rows if event["status"] == "ok"]
        latencies = [event["latency_ms"] for event in ok]
        errors = sum(event["status"] in FAILED for event in rows)
        not_found = sum(not event.get("found", True) for event in ok)
        return {
            "requests": len(rows),
            "errors": f"{errors} ({percent(errors, len(rows))})",
            "rejected": sum(event["status"] == "rejected" for event in rows),
            "not_found": f"{not_found} ({percent(not_found, len(ok))})",
            "p50_ms": percentile(latencies, 0.5),
            "p95_ms": percentile(latencies, 0.95),
        }

    def _llm(self, rows: List[Dict[str, Any]], asks: int) -> Dict[str, Any]:
        ok = [event for event in rows if event["status"] == "ok"]
        cost = sum(event["cost"] for event in ok)
        report = {
            "calls": len(rows),
            "errors": len(rows) - len(ok),
            "fallbacks": sum(event["model"] != self._primary_model for event in ok),
            "tokens_in": sum(event["input_tokens"] for event in ok),
            "tokens_out": sum(event["output_tokens"] for event in ok),
            "cost_usd": f"{cost:.6f}",
        }
        if asks:
            report["per_ask_usd"] = f"{cost / asks:.6f}"
        return report
