"""Small future-facing interfaces for live framebuffer producers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .pixel_model import PixelFrame


class FrameSource(ABC):
    """Produces framebuffer frames over time without depending on Qt widgets."""

    @abstractmethod
    def next_frame(self, elapsed_ms: int) -> PixelFrame:
        """Return the frame that should be rendered after ``elapsed_ms``."""


@dataclass
class StaticFrameSource(FrameSource):
    """A simple frame source useful for tests and static signs."""

    frame: PixelFrame

    def next_frame(self, elapsed_ms: int) -> PixelFrame:
        return self.frame

