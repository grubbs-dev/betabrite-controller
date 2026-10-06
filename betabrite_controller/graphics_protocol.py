"""Protocol encoder for Alpha/BetaBrite custom SMALL DOTS graphics."""

from __future__ import annotations

from dataclasses import dataclass

from alphasign import Color, DisplayMode, DisplayPosition, Packet, Sign, SignType, WriteText
from alphasign.protocol import EOT, ETX, SOH, STX, SYNC
from alphasign.commands.dots import ReadSmallDots, WriteSmallDots
from alphasign.commands.special import ReadSpecialFunction, WriteSpecialFunction
from alphasign.protocol import DotsColorDepth, FileProtection, FileType, SpecialFunction

from .connection import BetaBriteTransportError, classify_transport_exception
from .devices import AUTO_PORT, resolve_port
from .pixel_model import PixelAnimation, PixelFrame


DEFAULT_GRAPHIC_LABELS = "ABCDEFGHIJKLMNPQRSTUVWXYZ"
CALL_SMALL_DOTS = b"\x14"
DEFAULT_GRAPHIC_TEXT_LABEL = "B"
DEFAULT_CONFIGURED_GRAPHIC_LABEL = "D"
DEFAULT_GRAPHIC_SIZE = (7, 7)
DEFAULT_GRAPHIC_COLOR_STATUS = "2000"
PRIORITY_TEXT_LABEL = "0"
STOP_PRIORITY_TEXT_PACKET = b"\x00\x00\x00\x00\x00\x01Z00\x02A0\x04"
CURRENT_TEXT_FILE_SIZES = {
    "A": 0x7262,
    "B": 0x00AB,
    "C": 0x00AB,
}
APP_MANAGED_TEXT_LABELS = ("A", "B", "C")


class GraphicsProtocolError(ValueError):
    """Raised when custom graphics cannot be encoded for the sign protocol."""


@dataclass(frozen=True, slots=True)
class GraphicSlot:
    label: str = "A"

    def __post_init__(self) -> None:
        validate_graphic_label(self.label)


@dataclass(frozen=True, slots=True)
class MemoryConfigEntry:
    label: str
    file_type: str
    protection: str
    size: str
    suffix: str

    @property
    def raw(self) -> str:
        return f"{self.label}{self.file_type}{self.protection}{self.size}{self.suffix}"

    @property
    def is_text(self) -> bool:
        return self.file_type == FileType.TEXT.value.decode("ascii")

    @property
    def is_dots(self) -> bool:
        return self.file_type == FileType.DOTS.value.decode("ascii")

    @property
    def dots_dimensions(self) -> tuple[int, int] | None:
        if not self.is_dots:
            return None
        return int(self.size[:2], 16), int(self.size[2:], 16)


def validate_graphic_label(label: str) -> None:
    if not isinstance(label, str) or len(label) != 1:
        raise GraphicsProtocolError("Graphic labels must be exactly one character")
    if not label.isalnum():
        raise GraphicsProtocolError("Graphic labels must be alphanumeric")


def validate_display_text_label(label: str) -> None:
    validate_graphic_label(label)
    if label == PRIORITY_TEXT_LABEL:
        raise GraphicsProtocolError(
            "Priority TEXT file 0 is reserved for recovery; use a normal TEXT label for graphics display"
        )


def validate_graphic_memory_labels(*, text_labels: tuple[str, ...], graphic_label: str) -> None:
    validate_graphic_label(graphic_label)
    for label in text_labels:
        validate_display_text_label(label)
    if graphic_label in text_labels:
        raise GraphicsProtocolError("Use a DOTS label that does not collide with configured TEXT labels")


def _text_memory_entry(label: str, size: int) -> dict:
    validate_display_text_label(label)
    return {
        "label": label,
        "type": FileType.TEXT,
        "protection": FileProtection.UNLOCKED,
        "size": size,
        "start_time": 0xFF,
        "stop_time": 0x00,
    }


def _packet_for_memory_entries(entries: list[dict], *, type_code: bytes, address: str) -> bytes:
    command = WriteSpecialFunction.configure_memory(entries)
    return Packet(type_code=type_code, address=address).add(command).to_bytes()


def parse_memory_config_payload(payload: bytes | str) -> list[MemoryConfigEntry]:
    """Parse an ``E$`` memory-configuration payload into 11-byte entries."""
    data = payload.encode("ascii") if isinstance(payload, str) else payload
    if data.startswith(b"E$"):
        data = data[2:]
    if len(data) % 11 != 0:
        raise GraphicsProtocolError("Memory configuration payload must contain 11-byte entries")
    entries = []
    for index in range(0, len(data), 11):
        entry = data[index : index + 11].decode("ascii")
        entries.append(
            MemoryConfigEntry(
                label=entry[0],
                file_type=entry[1],
                protection=entry[2],
                size=entry[3:7],
                suffix=entry[7:11],
            )
        )
    return entries


def parse_sign_response_payload(response: bytes, *, expected_command: bytes | None = None) -> tuple[bytes, str, str]:
    """Return ``(payload, received_checksum, calculated_checksum)`` from a sign response."""
    try:
        soh_index = response.index(SOH)
        stx_index = response.index(STX, soh_index)
        etx_index = response.index(ETX, stx_index)
    except ValueError as exc:
        raise GraphicsProtocolError("Sign response is missing protocol framing") from exc
    payload = response[stx_index + 1 : etx_index]
    received = response[etx_index + 1 : etx_index + 5].decode("ascii")
    calculated = f"{sum(response[stx_index:etx_index + 1]) % 65536:04X}"
    if received != calculated:
        raise GraphicsProtocolError(
            f"Sign response checksum mismatch: received {received}, calculated {calculated}"
        )
    if expected_command is not None and not payload.startswith(expected_command):
        raise GraphicsProtocolError(f"Unexpected sign response payload: {payload!r}")
    return payload, received, calculated


def parse_memory_config_response(response: bytes) -> list[MemoryConfigEntry]:
    payload, _received, _calculated = parse_sign_response_payload(response, expected_command=b"E$")
    return parse_memory_config_payload(payload)


def has_compatible_graphics_slot(
    entries: list[MemoryConfigEntry],
    *,
    graphic_label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL,
    size: tuple[int, int] = DEFAULT_GRAPHIC_SIZE,
    color_status: str = DEFAULT_GRAPHIC_COLOR_STATUS,
) -> bool:
    """Return whether memory config contains the expected dedicated DOTS slot."""
    validate_graphic_memory_labels(text_labels=("A", DEFAULT_GRAPHIC_TEXT_LABEL, "C"), graphic_label=graphic_label)
    for entry in entries:
        if entry.label == graphic_label and entry.is_dots:
            return entry.dots_dimensions == size and entry.suffix == color_status
    return False


def format_memory_config_entries(entries: list[MemoryConfigEntry]) -> str:
    """Return a compact user-facing memory directory summary."""
    if not entries:
        return "No configured files reported."
    lines = []
    for entry in entries:
        if entry.is_text:
            lines.append(f"{entry.label}: TEXT size {entry.size}, timing {entry.suffix}")
        elif entry.is_dots:
            rows, cols = entry.dots_dimensions or (0, 0)
            lines.append(f"{entry.label}: DOTS {rows:02X}x{cols:02X}, color {entry.suffix}")
        else:
            lines.append(f"{entry.label}: type {entry.file_type}, size {entry.size}, suffix {entry.suffix}")
    return "\n".join(lines)


def encode_read_memory_config(*, type_code: bytes = b"Z", address: str = "00") -> Packet:
    """Build the documented read-only ``F$`` memory-directory query."""
    return Packet(type_code=type_code, address=address).add(
        ReadSpecialFunction(SpecialFunction.MEMORY_CONFIG),
        checksum=False,
    )


def encode_read_small_dots(
    *,
    label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL,
    type_code: bytes = b"Z",
    address: str = "00",
) -> Packet:
    """Build the documented read-only SMALL DOTS query for diagnostics."""
    validate_graphic_label(label)
    return Packet(type_code=type_code, address=address).add(ReadSmallDots(label), checksum=False)


def encode_stop_priority_text(*, type_code: bytes = b"Z", address: str = "00") -> bytes:
    """Encode the documented command that disables Priority TEXT file 0."""
    if type_code == b"Z" and address == "00":
        return STOP_PRIORITY_TEXT_PACKET
    return SYNC + SOH + type_code + address.encode() + STX + b"A0" + EOT


def encode_minimal_graphics_memory_config(
    *,
    graphic_label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL,
    type_code: bytes = b"Z",
    address: str = "00",
) -> bytes:
    """Encode a conservative memory layout for one 7x7 3-color DOTS file.

    This is intentionally not sent by normal UI paths. Writing memory
    configuration is destructive: the sign's existing file directory is
    replaced and file contents are cleared.
    """
    text_labels = ("A", DEFAULT_GRAPHIC_TEXT_LABEL, "C")
    validate_graphic_memory_labels(text_labels=text_labels, graphic_label=graphic_label)
    entries = [
        _text_memory_entry("A", 0x0100),
        _text_memory_entry(DEFAULT_GRAPHIC_TEXT_LABEL, CURRENT_TEXT_FILE_SIZES["B"]),
        _text_memory_entry("C", CURRENT_TEXT_FILE_SIZES["C"]),
        {
            "label": graphic_label,
            "type": FileType.DOTS,
            "protection": FileProtection.UNLOCKED,
            "size": DEFAULT_GRAPHIC_SIZE,
            "color_depth": DotsColorDepth.THREE_COLOR,
        },
    ]
    return _packet_for_memory_entries(entries, type_code=type_code, address=address)


def encode_current_text_memory_config_rollback(*, type_code: bytes = b"Z", address: str = "00") -> bytes:
    """Encode the exact read-back three-TEXT-file memory directory for rollback.

    This restores layout only. Memory reconfiguration can destroy file contents,
    so TEXT files must be rewritten separately after rollback.
    """
    entries = [
        _text_memory_entry("A", CURRENT_TEXT_FILE_SIZES["A"]),
        _text_memory_entry("B", CURRENT_TEXT_FILE_SIZES["B"]),
        _text_memory_entry("C", CURRENT_TEXT_FILE_SIZES["C"]),
    ]
    return _packet_for_memory_entries(entries, type_code=type_code, address=address)


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
    validate_display_text_label(text_label)
    content = CALL_SMALL_DOTS + graphic_label.encode("ascii")
    command = WriteText(
        content,
        label=text_label,
        position=DisplayPosition.FILL,
        mode=mode,
    )
    return Packet(type_code=type_code, address=address).add(command).to_bytes()


def encode_known_good_text(
    *,
    text_label: str,
    text: str = "GREEN OK",
    type_code: bytes = b"Z",
    address: str = "00",
) -> bytes:
    """Encode a known-good steady green text file."""
    validate_display_text_label(text_label)
    command = WriteText(
        Color.GREEN.value + text.encode("ascii", errors="replace"),
        label=text_label,
        position=DisplayPosition.FILL,
        mode=DisplayMode.HOLD,
    )
    return Packet(type_code=type_code, address=address).add(command).to_bytes()


def encode_graphics_return_to_text(
    *,
    text: str = "GREEN OK",
    text_label: str = DEFAULT_GRAPHIC_TEXT_LABEL,
    type_code: bytes = b"Z",
    address: str = "00",
) -> bytes:
    """Overwrite the normal graphics wrapper TEXT file with harmless text."""
    return encode_known_good_text(text_label=text_label, text=text, type_code=type_code, address=address)


def encode_static_graphic_sequence(
    frame: PixelFrame,
    *,
    graphic_label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL,
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

    def _open_sign(self):
        port = resolve_port(self.port)
        self.last_port = port
        sign = Sign(sign_type=SignType.ALL, address=self.address)
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
        return sign

    def read_memory_config(self) -> list[MemoryConfigEntry]:
        sign = None
        port = resolve_port(self.port)
        self.last_port = port
        try:
            sign = self._open_sign()
            sign.send(encode_read_memory_config(type_code=self.type_code, address=self.address))
            response = sign.read_response(raise_on_timeout=True)
            return parse_memory_config_response(response)
        except Exception as exc:
            diagnostic = classify_transport_exception(exc, port, source="graphics")
            if diagnostic is not None:
                raise BetaBriteTransportError.from_diagnostic(diagnostic) from exc
            raise
        finally:
            if sign is not None:
                try:
                    sign.close()
                except Exception:
                    pass

    def _require_graphics_slot(self, entries: list[MemoryConfigEntry], *, graphic_label: str) -> None:
        if not has_compatible_graphics_slot(entries, graphic_label=graphic_label):
            raise GraphicsProtocolError(
                "Graphics support is not initialized on this sign. "
                "Run Initialize Graphics Support before sending Pixel Studio artwork."
            )

    def initialize_graphics_support(self) -> list[MemoryConfigEntry]:
        """Explicitly configure and verify the A/B/C TEXT + D DOTS layout."""
        sign = None
        port = resolve_port(self.port)
        self.last_port = port
        try:
            sign = self._open_sign()
            sign.send(encode_read_memory_config(type_code=self.type_code, address=self.address))
            current_entries = parse_memory_config_response(sign.read_response(raise_on_timeout=True))
            if not has_compatible_graphics_slot(current_entries):
                sign.send(encode_minimal_graphics_memory_config(type_code=self.type_code, address=self.address))
                sign.send(encode_read_memory_config(type_code=self.type_code, address=self.address))
                current_entries = parse_memory_config_response(sign.read_response(raise_on_timeout=True))
                self._require_graphics_slot(current_entries, graphic_label=DEFAULT_CONFIGURED_GRAPHIC_LABEL)
                for label in APP_MANAGED_TEXT_LABELS:
                    sign.send(encode_known_good_text(text_label=label, type_code=self.type_code, address=self.address))
            return current_entries
        except Exception as exc:
            if isinstance(exc, GraphicsProtocolError):
                raise
            diagnostic = classify_transport_exception(exc, port, source="graphics")
            if diagnostic is not None:
                raise BetaBriteTransportError.from_diagnostic(diagnostic) from exc
            raise
        finally:
            if sign is not None:
                try:
                    sign.close()
                except Exception:
                    pass

    def return_to_text(self) -> None:
        """Replace the graphics TEXT wrapper without touching DOTS or memory config."""
        self._send_packets([encode_graphics_return_to_text(type_code=self.type_code, address=self.address)])

    def write_graphic(self, frame: PixelFrame, *, label: str = "A") -> None:
        self._send_packets([encode_graphic(frame, label=label, type_code=self.type_code, address=self.address)])

    def display_graphic(
        self,
        *,
        graphic_label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL,
        text_label: str = DEFAULT_GRAPHIC_TEXT_LABEL,
    ) -> None:
        self._send_packets([
            encode_display_graphic(
                graphic_label=graphic_label,
                text_label=text_label,
                type_code=self.type_code,
                address=self.address,
            )
        ])

    def send_static_graphic(
        self,
        frame: PixelFrame,
        *,
        graphic_label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL,
        verify_readback: bool = False,
    ) -> None:
        sign = None
        port = resolve_port(self.port)
        self.last_port = port
        try:
            sign = self._open_sign()
            sign.send(encode_read_memory_config(type_code=self.type_code, address=self.address))
            entries = parse_memory_config_response(sign.read_response(raise_on_timeout=True))
            self._require_graphics_slot(entries, graphic_label=graphic_label)
            sign.send(encode_graphic(frame, label=graphic_label, type_code=self.type_code, address=self.address))
            if verify_readback:
                sign.send(encode_read_small_dots(label=graphic_label, type_code=self.type_code, address=self.address))
                parse_sign_response_payload(sign.read_response(raise_on_timeout=True), expected_command=b"I" + graphic_label.encode())
            sign.send(
                encode_display_graphic(
                    graphic_label=graphic_label,
                    text_label=DEFAULT_GRAPHIC_TEXT_LABEL,
                    type_code=self.type_code,
                    address=self.address,
                )
            )
        except Exception as exc:
            if isinstance(exc, GraphicsProtocolError):
                raise
            diagnostic = classify_transport_exception(exc, port, source="graphics")
            if diagnostic is not None:
                raise BetaBriteTransportError.from_diagnostic(diagnostic) from exc
            raise
        finally:
            if sign is not None:
                try:
                    sign.close()
                except Exception:
                    pass


class SimulatedBetaBriteTransport:
    """In-memory transport for hardware-independent integration tests."""

    def __init__(self):
        self.payloads: list[bytes] = []

    def send_static_graphic(self, frame: PixelFrame, *, graphic_label: str = DEFAULT_CONFIGURED_GRAPHIC_LABEL) -> None:
        self.payloads.extend(encode_static_graphic_sequence(frame, graphic_label=graphic_label))
