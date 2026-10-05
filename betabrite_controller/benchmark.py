"""Live Mode benchmark patterns, metrics, and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import platform
import statistics
from pathlib import Path
from typing import Iterable

from . import __version__
from .live import LiveRenderer, SimulatedLiveRenderer, SimulatedLiveTransport
from .pixel_model import DEFAULT_HEIGHT, DEFAULT_WIDTH, PixelColor, PixelFrame


BENCHMARK_RATES = (1, 2, 3, 4, 5, 6, 8, 10)
BENCHMARK_PATTERNS = ("static-repeat", "alternating-frame", "moving-marker")


def percentile(values: Iterable[float], percent: float) -> float:
    items = sorted(values)
    if not items:
        return 0.0
    if len(items) == 1:
        return items[0]
    rank = (len(items) - 1) * (percent / 100)
    lower = int(rank)
    upper = min(lower + 1, len(items) - 1)
    fraction = rank - lower
    return items[lower] + (items[upper] - items[lower]) * fraction


def pattern_frame(pattern: str, index: int, *, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> PixelFrame:
    frame = PixelFrame(width=width, height=height)
    if pattern == "static-repeat":
        for x in range(0, width, 8):
            frame.set_pixel(x, height // 2, PixelColor.AMBER)
    elif pattern == "alternating-frame":
        color = PixelColor.RED if index % 2 == 0 else PixelColor.GREEN
        for x in range(0, width, 4):
            frame.set_pixel(x, 1, color)
            frame.set_pixel(x + 1 if x + 1 < width else x, height - 2, color)
    elif pattern == "moving-marker":
        x = index % max(1, width)
        for dx in range(3):
            if x + dx < width:
                for y in range(1, height - 1):
                    frame.set_pixel(x + dx, y, PixelColor.YELLOW)
    else:
        raise ValueError(f"Unknown benchmark pattern: {pattern}")
    return frame


@dataclass
class BenchmarkResult:
    pattern: str
    target_fps: float
    achieved_fps: float
    bytes_per_frame: int
    protocol_overhead_bytes: int
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float
    dropped_frames: int
    failures: int
    duration_seconds: float
    frames_attempted: int
    frames_sent: int
    status: str = "ok"
    message: str = ""


@dataclass
class BenchmarkReport:
    created_at: str
    app_version: str
    platform: str
    serial_device: str
    baud_rate: int
    sign_address: str
    protocol_method: str
    frame_width: int
    frame_height: int
    results: list[BenchmarkResult] = field(default_factory=list)
    recommended_fps: float = 0.0
    safety_note: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["results"] = [asdict(result) for result in self.results]
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")


def run_virtual_pattern_benchmark(
    pattern: str,
    target_fps: float,
    *,
    duration_seconds: float = 1.0,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> BenchmarkResult:
    if target_fps <= 0:
        raise ValueError("target_fps must be positive")
    renderer = SimulatedLiveRenderer()
    transport = SimulatedLiveTransport()
    frames_attempted = max(1, int(round(target_fps * duration_seconds)))
    latencies: list[float] = []
    failures = 0
    bytes_per_frame = 0
    protocol_overhead = 0
    for index in range(frames_attempted):
        frame = pattern_frame(pattern, index, width=width, height=height)
        try:
            packet = renderer.encode(frame)
            transport.send_packet(packet)
            latency_ms = (packet.encode_seconds + transport.latency_seconds) * 1000
            latencies.append(latency_ms)
            bytes_per_frame = len(packet.payload)
            protocol_overhead = max(0, len(packet.payload) - width * height)
        except Exception:
            failures += 1
    frames_sent = len(transport.payloads)
    achieved = frames_sent / duration_seconds if duration_seconds > 0 else 0.0
    return BenchmarkResult(
        pattern=pattern,
        target_fps=target_fps,
        achieved_fps=achieved,
        bytes_per_frame=bytes_per_frame,
        protocol_overhead_bytes=protocol_overhead,
        average_latency_ms=statistics.fmean(latencies) if latencies else 0.0,
        p50_latency_ms=percentile(latencies, 50),
        p95_latency_ms=percentile(latencies, 95),
        max_latency_ms=max(latencies) if latencies else 0.0,
        dropped_frames=max(0, frames_attempted - frames_sent),
        failures=failures,
        duration_seconds=duration_seconds,
        frames_attempted=frames_attempted,
        frames_sent=frames_sent,
    )


def recommend_fps(results: list[BenchmarkResult]) -> float:
    stable = [
        result.target_fps
        for result in results
        if result.status == "ok"
        and result.failures == 0
        and result.dropped_frames == 0
        and result.achieved_fps >= result.target_fps * 0.95
    ]
    if not stable:
        return 0.0
    return max(1.0, min(stable) if max(stable) <= 2 else max(stable) * 0.75)


def run_virtual_benchmark_suite(
    *,
    rates: Iterable[int] = BENCHMARK_RATES,
    patterns: Iterable[str] = BENCHMARK_PATTERNS,
    duration_seconds: float = 1.0,
) -> BenchmarkReport:
    results = [
        run_virtual_pattern_benchmark(pattern, rate, duration_seconds=duration_seconds)
        for pattern in patterns
        for rate in rates
    ]
    return BenchmarkReport(
        created_at=datetime.now(timezone.utc).isoformat(),
        app_version=__version__,
        platform=platform.platform(),
        serial_device="virtual",
        baud_rate=9600,
        sign_address="00",
        protocol_method=SimulatedLiveRenderer.protocol_method,
        frame_width=DEFAULT_WIDTH,
        frame_height=DEFAULT_HEIGHT,
        results=results,
        recommended_fps=recommend_fps(results),
        safety_note="Virtual benchmark only; no physical sign writes were performed.",
    )


def physical_live_benchmark_blocked_report(serial_device: str = "not connected") -> BenchmarkReport:
    message = (
        "Physical Live Mode benchmarking is blocked because the proven custom "
        "graphics path writes SMALL DOTS files, and volatile sign storage has not "
        "been confirmed. Repeated live writes are disabled to protect sign memory."
    )
    result = BenchmarkResult(
        pattern="physical-live",
        target_fps=0,
        achieved_fps=0,
        bytes_per_frame=0,
        protocol_overhead_bytes=0,
        average_latency_ms=0,
        p50_latency_ms=0,
        p95_latency_ms=0,
        max_latency_ms=0,
        dropped_frames=0,
        failures=0,
        duration_seconds=0,
        frames_attempted=0,
        frames_sent=0,
        status="blocked",
        message=message,
    )
    return BenchmarkReport(
        created_at=datetime.now(timezone.utc).isoformat(),
        app_version=__version__,
        platform=platform.platform(),
        serial_device=serial_device,
        baud_rate=9600,
        sign_address="00",
        protocol_method=LiveRenderer.protocol_method,
        frame_width=DEFAULT_WIDTH,
        frame_height=DEFAULT_HEIGHT,
        results=[result],
        recommended_fps=0,
        safety_note=message,
    )

