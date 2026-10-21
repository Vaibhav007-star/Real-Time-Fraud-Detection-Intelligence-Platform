import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List


class OperationalMetricsMonitor:
    """Tracks real-time processing throughput (TPS), latency percentiles, queue lag, and recent operational errors."""

    def __init__(self) -> None:
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.start_monotonic = time.monotonic()
        self.processed_timestamps: Deque[float] = deque(maxlen=1000)
        self.latencies_ms: Deque[float] = deque(maxlen=500)
        self.recent_errors: Deque[Dict[str, str]] = deque(maxlen=50)
        self.duplicate_events_count: int = 0
        self.late_events_count: int = 0

    def record_processed(self, latency_ms: float, is_late: bool = False) -> None:
        now_m = time.monotonic()
        self.processed_timestamps.append(now_m)
        self.latencies_ms.append(float(latency_ms))
        if is_late:
            self.late_events_count += 1

    def record_duplicate(self) -> None:
        self.duplicate_events_count += 1

    def record_error(self, source: str, message: str) -> None:
        self.recent_errors.appendleft(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "message": str(message)[:300],
            }
        )

    def current_tps(self, window_seconds: float = 10.0) -> float:
        now_m = time.monotonic()
        recent = [t for t in self.processed_timestamps if (now_m - t) <= window_seconds]
        if not recent:
            return 0.0
        span = max(1.0, min(window_seconds, now_m - recent[0] + 0.2))
        return round(len(recent) / span, 2)

    def snapshot(self) -> Dict[str, Any]:
        lats = sorted(self.latencies_ms)
        avg_lat = sum(lats) / len(lats) if lats else 0.0
        p95_lat = lats[int(len(lats) * 0.95)] if lats else 0.0
        return {
            "started_at": self.started_at,
            "uptime_seconds": round(time.monotonic() - self.start_monotonic, 1),
            "current_tps": self.current_tps(),
            "avg_scoring_latency_ms": round(avg_lat, 2),
            "p95_scoring_latency_ms": round(p95_lat, 2),
            "duplicate_events_handled": self.duplicate_events_count,
            "late_events_handled": self.late_events_count,
            "recent_errors": list(self.recent_errors)[:15],
        }
