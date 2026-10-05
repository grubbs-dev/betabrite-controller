"""Framebuffer and document model for BetaBrite pixel artwork."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable


DOCUMENT_FORMAT = "betabrite-pixel-document"
DOCUMENT_VERSION = 1
DEFAULT_WIDTH = 90
DEFAULT_HEIGHT = 7
MIN_FRAME_DURATION_MS = 50


class PixelDocumentError(ValueError):
    """Raised when a pixel document cannot be validated or loaded."""


class PixelColor(Enum):
    """Protocol-compatible SMALL DOTS pixel colors."""

    OFF = "0"
    RED = "1"
    GREEN = "2"
    AMBER = "3"
    DIM_RED = "4"
    DIM_GREEN = "5"
    BROWN = "6"
    ORANGE = "7"
    YELLOW = "8"

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def hex_color(self) -> str:
        return {
            PixelColor.OFF: "#111417",
            PixelColor.RED: "#ee3b2f",
            PixelColor.GREEN: "#35b653",
            PixelColor.AMBER: "#f3a21a",
            PixelColor.DIM_RED: "#9d2a24",
            PixelColor.DIM_GREEN: "#247a35",
            PixelColor.BROWN: "#8b5a2b",
            PixelColor.ORANGE: "#e87722",
            PixelColor.YELLOW: "#efc33a",
        }[self]

    @classmethod
    def from_value(cls, value: Any) -> "PixelColor":
        if isinstance(value, PixelColor):
            return value
        try:
            return cls(str(value))
        except ValueError as exc:
            raise PixelDocumentError(f"Unsupported pixel color: {value!r}") from exc


def _validate_dimensions(width: int, height: int) -> None:
    if not isinstance(width, int) or not isinstance(height, int):
        raise PixelDocumentError("Pixel dimensions must be integers")
    if width < 1 or height < 1:
        raise PixelDocumentError("Pixel dimensions must be positive")
    if width > 255:
        raise PixelDocumentError("SMALL DOTS graphics support at most 255 columns")
    if height > 31:
        raise PixelDocumentError("SMALL DOTS graphics support at most 31 rows")


@dataclass
class PixelFrame:
    """One protocol-sized framebuffer."""

    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    pixels: list[list[PixelColor]] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_dimensions(self.width, self.height)
        if not self.pixels:
            self.pixels = [
                [PixelColor.OFF for _x in range(self.width)] for _y in range(self.height)
            ]
        if len(self.pixels) != self.height:
            raise PixelDocumentError("Pixel row count does not match frame height")
        normalized: list[list[PixelColor]] = []
        for row in self.pixels:
            if len(row) != self.width:
                raise PixelDocumentError("Pixel column count does not match frame width")
            normalized.append([PixelColor.from_value(pixel) for pixel in row])
        self.pixels = normalized

    def _check_coordinate(self, x: int, y: int) -> None:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError(f"Pixel coordinate out of bounds: {x},{y}")

    def get_pixel(self, x: int, y: int) -> PixelColor:
        self._check_coordinate(x, y)
        return self.pixels[y][x]

    def set_pixel(self, x: int, y: int, color: PixelColor | str = PixelColor.RED) -> None:
        self._check_coordinate(x, y)
        self.pixels[y][x] = PixelColor.from_value(color)

    def unset_pixel(self, x: int, y: int) -> None:
        self.set_pixel(x, y, PixelColor.OFF)

    def clear(self, color: PixelColor | str = PixelColor.OFF) -> None:
        fill = PixelColor.from_value(color)
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = fill

    def fill(self, color: PixelColor | str) -> None:
        self.clear(color)

    def invert(self, on_color: PixelColor | str = PixelColor.RED) -> None:
        enabled = PixelColor.from_value(on_color)
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = enabled if self.pixels[y][x] is PixelColor.OFF else PixelColor.OFF

    def flip_horizontal(self) -> None:
        for row in self.pixels:
            row.reverse()

    def flip_vertical(self) -> None:
        self.pixels.reverse()

    def duplicate(self) -> "PixelFrame":
        return PixelFrame.from_rows(self.to_rows())

    def to_rows(self) -> list[str]:
        return ["".join(pixel.value for pixel in row) for row in self.pixels]

    def to_protocol_rows(self) -> bytes:
        return b"".join(row.encode("ascii") + b"\r" for row in self.to_rows())

    def to_dict(self) -> dict[str, Any]:
        return {"width": self.width, "height": self.height, "rows": self.to_rows()}

    @classmethod
    def from_rows(cls, rows: Iterable[str]) -> "PixelFrame":
        row_list = [str(row) for row in rows]
        if not row_list:
            raise PixelDocumentError("A frame requires at least one row")
        width = len(row_list[0])
        if width == 0:
            raise PixelDocumentError("Rows cannot be empty")
        pixels = [[PixelColor.from_value(character) for character in row] for row in row_list]
        return cls(width=width, height=len(row_list), pixels=pixels)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PixelFrame":
        if not isinstance(payload, dict):
            raise PixelDocumentError("Frame payload must be an object")
        rows = payload.get("rows")
        if rows is None:
            width = int(payload.get("width", DEFAULT_WIDTH))
            height = int(payload.get("height", DEFAULT_HEIGHT))
            return cls(width=width, height=height)
        frame = cls.from_rows(rows)
        width = int(payload.get("width", frame.width))
        height = int(payload.get("height", frame.height))
        if frame.width != width or frame.height != height:
            raise PixelDocumentError("Serialized frame dimensions do not match row data")
        return frame


@dataclass
class AnimationFrame:
    frame: PixelFrame
    duration_ms: int = 250

    def __post_init__(self) -> None:
        if not isinstance(self.duration_ms, int) or self.duration_ms < MIN_FRAME_DURATION_MS:
            raise PixelDocumentError(f"Frame duration must be at least {MIN_FRAME_DURATION_MS} ms")

    def duplicate(self) -> "AnimationFrame":
        return AnimationFrame(self.frame.duplicate(), self.duration_ms)

    def to_dict(self) -> dict[str, Any]:
        return {"duration_ms": self.duration_ms, "frame": self.frame.to_dict()}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnimationFrame":
        if not isinstance(payload, dict):
            raise PixelDocumentError("Animation frame payload must be an object")
        return cls(
            frame=PixelFrame.from_dict(payload.get("frame", {})),
            duration_ms=int(payload.get("duration_ms", 250)),
        )


@dataclass
class PixelAnimation:
    frames: list[AnimationFrame] = field(default_factory=list)
    loop: bool = True

    def __post_init__(self) -> None:
        if not self.frames:
            self.frames = [AnimationFrame(PixelFrame())]
        self._validate_consistent_dimensions()

    @property
    def width(self) -> int:
        return self.frames[0].frame.width

    @property
    def height(self) -> int:
        return self.frames[0].frame.height

    def _validate_consistent_dimensions(self) -> None:
        width = self.frames[0].frame.width
        height = self.frames[0].frame.height
        for frame in self.frames:
            if frame.frame.width != width or frame.frame.height != height:
                raise PixelDocumentError("All animation frames must have the same dimensions")

    def frame_count(self) -> int:
        return len(self.frames)

    def add_frame(self, frame: PixelFrame | None = None, duration_ms: int = 250) -> int:
        candidate = frame or PixelFrame(width=self.width, height=self.height)
        if candidate.width != self.width or candidate.height != self.height:
            raise PixelDocumentError("New frame dimensions must match the animation")
        self.frames.append(AnimationFrame(candidate, duration_ms))
        return len(self.frames) - 1

    def insert_frame(self, index: int, frame: PixelFrame | None = None, duration_ms: int = 250) -> None:
        candidate = frame or PixelFrame(width=self.width, height=self.height)
        if candidate.width != self.width or candidate.height != self.height:
            raise PixelDocumentError("Inserted frame dimensions must match the animation")
        self.frames.insert(index, AnimationFrame(candidate, duration_ms))

    def duplicate_frame(self, index: int) -> int:
        self.frames.insert(index + 1, self.frames[index].duplicate())
        return index + 1

    def delete_frame(self, index: int) -> None:
        if len(self.frames) == 1:
            raise PixelDocumentError("An animation must contain at least one frame")
        del self.frames[index]

    def move_frame(self, old_index: int, new_index: int) -> None:
        frame = self.frames.pop(old_index)
        self.frames.insert(new_index, frame)

    def next_index(self, index: int) -> int:
        if index + 1 < len(self.frames):
            return index + 1
        return 0 if self.loop else index

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop": self.loop,
            "frames": [frame.to_dict() for frame in self.frames],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PixelAnimation":
        if not isinstance(payload, dict):
            raise PixelDocumentError("Animation payload must be an object")
        frames = [AnimationFrame.from_dict(item) for item in payload.get("frames", [])]
        return cls(frames=frames, loop=bool(payload.get("loop", True)))


@dataclass
class PixelDocument:
    animation: PixelAnimation = field(default_factory=PixelAnimation)
    title: str = "Untitled Pixel Art"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def width(self) -> int:
        return self.animation.width

    @property
    def height(self) -> int:
        return self.animation.height

    @property
    def frames(self) -> list[AnimationFrame]:
        return self.animation.frames

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": DOCUMENT_FORMAT,
            "version": DOCUMENT_VERSION,
            "title": self.title,
            "canvas": {"width": self.width, "height": self.height},
            "animation": self.animation.to_dict(),
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def new(cls, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT, title: str = "Untitled Pixel Art") -> "PixelDocument":
        return cls(animation=PixelAnimation([AnimationFrame(PixelFrame(width=width, height=height))]), title=title)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PixelDocument":
        if not isinstance(payload, dict):
            raise PixelDocumentError("Pixel document must be a JSON object")
        if payload.get("format") != DOCUMENT_FORMAT:
            raise PixelDocumentError("Unsupported pixel document format")
        version = payload.get("version")
        if version != DOCUMENT_VERSION:
            raise PixelDocumentError(f"Unsupported pixel document version: {version!r}")
        animation = PixelAnimation.from_dict(payload.get("animation", {}))
        canvas = payload.get("canvas", {})
        if canvas:
            width = int(canvas.get("width", animation.width))
            height = int(canvas.get("height", animation.height))
            if width != animation.width or height != animation.height:
                raise PixelDocumentError("Document canvas does not match animation dimensions")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return cls(animation=animation, title=str(payload.get("title") or "Untitled Pixel Art"), metadata=metadata)

    @classmethod
    def from_json(cls, text: str) -> "PixelDocument":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PixelDocumentError(f"Malformed pixel document JSON: {exc.msg}") from exc
        return cls.from_dict(payload)

    @classmethod
    def load(cls, path: str | Path) -> "PixelDocument":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

