"""Headless live framebuffer scheduling and transport helpers."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
import statistics
import time
from typing import Callable, Protocol

from .graphics_protocol import encode_graphic
from .pixel_model import PixelFrame


class FrameSource(ABC):
    """UI-independent producer for live framebuffer applications.

    Sources own simulation state and produce ``PixelFrame`` objects. They do not
    inherit from Qt classes and can be tested headlessly.
    """

    width: int
    height: int

    def start(self) -> None:
        """Prepare the source for updates."""

    def update(self, delta_seconds: float) -> None:
        """Advance simulation by ``delta_seconds``."""

    def render(self) -> PixelFrame:
        """Render the current simulation state to a framebuffer."""
        raise NotImplementedError

    def handle_input(self, action: str, pressed: bool = True) -> None:
        """Handle a source-specific input action."""

    def reset(self) -> None:
        """Return to the initial source state."""

    def next_frame(self, elapsed_ms: int) -> PixelFrame:
        """Compatibility helper for the original v1.3.0 seam."""
        self.update(max(0, elapsed_ms) / 1000)
        return self.render()


@dataclass
class StaticFrameSource(FrameSource):
    """A simple source useful for tests and static previews."""

    frame: PixelFrame

    @property
    def width(self) -> int:
        return self.frame.width

    @property
    def height(self) -> int:
        return self.frame.height

    def render(self) -> PixelFrame:
        return self.frame.duplicate()


@dataclass
class LiveFramePacket:
    """Encoded frame plus measurement metadata."""

    frame: PixelFrame
    payload: bytes
    encode_seconds: float


class LiveRenderer:
    """Encodes frames for a live transport.

    The Alpha SMALL DOTS path writes sign files. It is deterministic and useful
    for simulation, but it is not marked safe for physical live streaming because
    volatile storage has not been proven for compatible BetaBrite hardware.
    """

    safe_for_physical_streaming = False
    protocol_method = "SMALL DOTS PICTURE file write"

    def __init__(self, *, label: str = "A", clock: Callable[[], float] = time.perf_counter):
        self.label = label
        self.clock = clock

    def encode(self, frame: PixelFrame) -> LiveFramePacket:
        start = self.clock()
        payload = encode_graphic(frame, label=self.label)
        return LiveFramePacket(frame=frame.duplicate(), payload=payload, encode_seconds=self.clock() - start)


class SimulatedLiveRenderer(LiveRenderer):
    """Renderer allowed for simulated transports only."""

    safe_for_physical_streaming = True
    protocol_method = "simulated SMALL DOTS live packets"


class LiveTransport(Protocol):
    """Transport contract for live frame packets."""

    def send_packet(self, packet: LiveFramePacket) -> None:
        """Transmit an encoded packet."""


@dataclass
class SimulatedLiveTransport:
    """In-memory live transport for CI and virtual diagnostics."""

    latency_seconds: float = 0.0
    fail_after: int | None = None
    payloads: list[bytes] = field(default_factory=list)
    packets: list[LiveFramePacket] = field(default_factory=list)

    def send_packet(self, packet: LiveFramePacket) -> None:
        if self.fail_after is not None and len(self.payloads) >= self.fail_after:
            raise RuntimeError("simulated live transport failure")
        if self.latency_seconds > 0:
            time.sleep(self.latency_seconds)
        self.payloads.append(packet.payload)
        self.packets.append(packet)


@dataclass
class LiveStatistics:
    """Runtime counters and latency aggregates for a live session."""

    frames_rendered: int = 0
    frames_transmitted: int = 0
    frames_dropped: int = 0
    frames_coalesced: int = 0
    errors: int = 0
    render_latencies: list[float] = field(default_factory=list)
    encode_latencies: list[float] = field(default_factory=list)
    transport_latencies: list[float] = field(default_factory=list)
    total_latencies: list[float] = field(default_factory=list)
    scheduler_lateness: list[float] = field(default_factory=list)

    @staticmethod
    def _average(values: list[float]) -> float:
        return statistics.fmean(values) if values else 0.0

    @property
    def average_render_ms(self) -> float:
        return self._average(self.render_latencies) * 1000

    @property
    def average_encode_ms(self) -> float:
        return self._average(self.encode_latencies) * 1000

    @property
    def average_transport_ms(self) -> float:
        return self._average(self.transport_latencies) * 1000

    @property
    def latest_transport_ms(self) -> float:
        return self.transport_latencies[-1] * 1000 if self.transport_latencies else 0.0

    @property
    def average_total_ms(self) -> float:
        return self._average(self.total_latencies) * 1000


class LiveScheduler:
    """Monotonic live simulation and transmit scheduler with coalescing."""

    def __init__(
        self,
        source: FrameSource,
        *,
        renderer: LiveRenderer | None = None,
        transport: LiveTransport | None = None,
        preview_fps: float = 30.0,
        target_fps: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
        perf_clock: Callable[[], float] = time.perf_counter,
        max_failures: int = 3,
    ):
        if preview_fps <= 0:
            raise ValueError("preview_fps must be positive")
        if target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if target_fps > 10:
            raise ValueError("target_fps is capped at 10 FPS until hardware is benchmarked")
        self.source = source
        self.renderer = renderer or LiveRenderer()
        self.transport = transport
        self.preview_fps = float(preview_fps)
        self.target_fps = float(target_fps)
        self.clock = clock
        self.perf_clock = perf_clock
        self.max_failures = max_failures
        self.statistics = LiveStatistics()
        self.running = False
        self.paused = False
        self.last_tick: float | None = None
        self.next_preview_time = 0.0
        self.next_transmit_time = 0.0
        self.latest_frame: PixelFrame | None = None
        self.last_error: str | None = None

    @property
    def streaming_to_sign(self) -> bool:
        return self.transport is not None and self.renderer.safe_for_physical_streaming

    def start(self) -> PixelFrame:
        now = self.clock()
        self.statistics = LiveStatistics()
        self.running = True
        self.paused = False
        self.last_tick = now
        self.next_preview_time = now
        self.next_transmit_time = now
        self.last_error = None
        self.source.start()
        self.latest_frame = self._render_frame()
        return self.latest_frame

    def pause(self) -> None:
        if self.running:
            self.paused = True

    def resume(self) -> None:
        if self.running and self.paused:
            now = self.clock()
            self.last_tick = now
            self.next_preview_time = now
            self.next_transmit_time = now
            self.paused = False

    def stop(self) -> None:
        self.running = False
        self.paused = False

    def handle_input(self, action: str, pressed: bool = True) -> None:
        self.source.handle_input(action, pressed=pressed)

    def _render_frame(self) -> PixelFrame:
        start = self.perf_clock()
        frame = self.source.render()
        self.statistics.render_latencies.append(self.perf_clock() - start)
        self.statistics.frames_rendered += 1
        return frame

    def tick(self) -> PixelFrame | None:
        if not self.running:
            return self.latest_frame
        now = self.clock()
        if self.last_tick is None:
            self.last_tick = now
        if self.paused:
            self.last_tick = now
            return self.latest_frame

        delta = max(0.0, now - self.last_tick)
        self.last_tick = now
        self.source.update(delta)

        preview_interval = 1.0 / self.preview_fps
        if now >= self.next_preview_time or self.latest_frame is None:
            if now > self.next_preview_time + preview_interval:
                missed = int((now - self.next_preview_time) // preview_interval)
                self.statistics.frames_dropped += missed
            self.latest_frame = self._render_frame()
            self.next_preview_time = now + preview_interval

        if self.transport is not None:
            self._transmit_if_due(now)
        return self.latest_frame

    def _transmit_if_due(self, now: float) -> None:
        if not self.renderer.safe_for_physical_streaming:
            self.last_error = "No proven volatile BetaBrite live pixel transport is available."
            return
        interval = 1.0 / self.target_fps
        if now < self.next_transmit_time:
            return
        lateness = max(0.0, now - self.next_transmit_time)
        self.statistics.scheduler_lateness.append(lateness)
        if lateness > interval:
            skipped = int(lateness // interval)
            self.statistics.frames_coalesced += skipped
        self.next_transmit_time = now + interval
        if self.latest_frame is None:
            return

        total_start = self.perf_clock()
        try:
            packet = self.renderer.encode(self.latest_frame)
            self.statistics.encode_latencies.append(packet.encode_seconds)
            write_start = self.perf_clock()
            self.transport.send_packet(packet)
            self.statistics.transport_latencies.append(self.perf_clock() - write_start)
            self.statistics.frames_transmitted += 1
            self.statistics.total_latencies.append(self.perf_clock() - total_start)
        except Exception as exc:
            self.statistics.errors += 1
            self.last_error = str(exc)
            if self.statistics.errors >= self.max_failures:
                self.stop()
