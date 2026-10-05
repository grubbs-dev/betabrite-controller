"""Protocol encoder for Alpha/BetaBrite custom SMALL DOTS graphics."""

from __future__ import annotations

from dataclasses import dataclass

from alphasign import DisplayMode, DisplayPosition, Packet, Sign, SignType, WriteText
from alphasign.commands.dots import WriteSmallDots

from .connection import BetaBriteTransportError, classify_transport_exception
from .devices import AUTO_PORT, resolve_port
from .pixel_model import PixelAnimation, PixelFrame


DEFAULT_GRAPHIC_LABELS = "ABCDEFGHIJKLMNPQRSTUVWXYZ"
CALL_SMALL_DOTS = b"\x14"
DEFAULT_GRAPHIC_TEXT_LABEL = "0"


class GraphicsProtocolError(ValueError):
    """Raised when custom graphics cannot be encoded for the sign protocol."""


@dataclass(frozen=True, slots=True)
class GraphicSlot:
    label: str = "A"

    def __post_init__(self) -> None:
        validate_graphic_label(self.label)


def validate_graphic_label(label: str) -> None:
    if not isinstance(label, str) or len(label) != 1:
        raise GraphicsProtocolError("Graphic labels must be exactly one character")
    if not label.isalnum():
        raise GraphicsProtocolError("Graphic labels must be alphanumeric")


def encode_graphic(frame: PixelFrame, *, label: str = "A", type_code: bytes = b"Z", address: str = "00") -> bytes:
    """Encode one frame as a Write SMALL DOTS PICTURE packet."""
    validate_graphic_label(label)
    command = WriteSmallDots(
        frame.to_protocol_rows(),
        label=label,
        width=frame.width,
        height=frame.height,
    )
    return Packet(type_code=type_code, address=address).add(command).to_bytes()


def encode_display_graphic(
    *,
    graphic_label: str = "A",
    text_label: str = DEFAULT_GRAPHIC_TEXT_LABEL,
    type_code: bytes = b"Z",
    address: str = "00",
    mode: DisplayMode = DisplayMode.HOLD,
) -> bytes:
    """Encode a TEXT file that calls a stored SMALL DOTS PICTURE file."""
    validate_graphic_label(graphic_label)
    validate_graphic_label(text_label)
    content = CALL_SMALL_DOTS + graphic_label.encode("ascii")
    command = WriteText(
        content,
        label=text_label,
        position=DisplayPosition.FILL,
        mode=mode,
    )
    return Packet(type_code=type_code, address=address).add(command).to_bytes()


def encode_static_graphic_sequence(
    frame: PixelFrame,
    *,
    graphic_label: str = "A",
    text_label: str = DEFAULT_GRAPHIC_TEXT_LABEL,
    type_code: bytes = b"Z",
    address: str = "00",
) -> list[bytes]:
    """Return packets needed to store and display one SMALL DOTS graphic."""
    return [
        encode_graphic(frame, label=graphic_label, type_code=type_code, address=address),
        encode_display_graphic(
            graphic_label=graphic_label,
            text_label=text_label,
            type_code=type_code,
            address=address,
        ),
    ]


def encode_animation_storage_sequence(
    animation: PixelAnimation,
    *,
    labels: str = DEFAULT_GRAPHIC_LABELS,
    type_code: bytes = b"Z",
    address: str = "00",
) -> list[bytes]:
    """Encode frames as separate SMALL DOTS files.

    The classic protocol stores individual DOTS files. A native timed animation
    container has not been proven for the tested one-line BetaBrite path, so the
    caller can store frames and choose a model-specific display strategy later.
    """
    if animation.frame_count() > len(labels):
        raise GraphicsProtocolError("Animation has more frames than available DOTS labels")
    packets: list[bytes] = []
    for index, animation_frame in enumerate(animation.frames):
        packets.append(
            encode_graphic(
                animation_frame.frame,
                label=labels[index],
                type_code=type_code,
                address=address,
            )
        )
    return packets


def delete_graphic(*, label: str = "A") -> None:
    """Placeholder for a protocol-specific delete path.

    The published Alpha protocol documents writing and reading SMALL DOTS files.
    Deletion is normally handled by memory reconfiguration or overwrite, so the
    public controller does not expose an unproven delete command.
    """
    validate_graphic_label(label)
    raise GraphicsProtocolError("Deleting DOTS files requires model-specific memory configuration")


class BetaBriteGraphicsController:
    """Serial transport wrapper for custom graphics packets."""

    def __init__(self, port: str | None = AUTO_PORT, address: str = "00", type_code: bytes = b"Z"):
        self.port = port or AUTO_PORT
        self.address = address
        self.type_code = type_code
        self.last_port: str | None = None

    def _send_packets(self, packets: list[bytes]) -> None:
        port = resolve_port(self.port)
        self.last_port = port
        sign = Sign(sign_type=SignType.ALL, address=self.address)
        try:
            sign.open(
                port,
                baudrate=9600,
                bytesize=7,
                parity="E",
                stopbits=1,
                timeout=1,
                dtr=False,
            )
            sign._ser.write_timeout = 5
            for packet in packets:
                sign.send(packet)
        except Exception as exc:
            diagnostic = classify_transport_exception(exc, port, source="graphics")
            if diagnostic is not None:
                raise BetaBriteTransportError.from_diagnostic(diagnostic) from exc
            raise
        finally:
            try:
                sign.close()
            except Exception:
                pass

    def write_graphic(self, frame: PixelFrame, *, label: str = "A") -> None:
        self._send_packets([encode_graphic(frame, label=label, type_code=self.type_code, address=self.address)])

    def display_graphic(self, *, graphic_label: str = "A", text_label: str = DEFAULT_GRAPHIC_TEXT_LABEL) -> None:
        self._send_packets(
            [
                encode_display_graphic(
                    graphic_label=graphic_label,
                    text_label=text_label,
                    type_code=self.type_code,
                    address=self.address,
                )
            ]
        )

    def send_static_graphic(self, frame: PixelFrame, *, graphic_label: str = "A") -> None:
        self._send_packets(
            encode_static_graphic_sequence(
                frame,
                graphic_label=graphic_label,
                type_code=self.type_code,
                address=self.address,
            )
        )


class SimulatedBetaBriteTransport:
    """In-memory transport for hardware-independent integration tests."""

    def __init__(self):
        self.payloads: list[bytes] = []

    def send_static_graphic(self, frame: PixelFrame, *, graphic_label: str = "A") -> None:
        self.payloads.extend(encode_static_graphic_sequence(frame, graphic_label=graphic_label))

