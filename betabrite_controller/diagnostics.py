"""Private, bounded diagnostic logs and conservative protocol traces."""
from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler

from alphasign.protocol import DELAY

from .settings import config_dir


def log_path():
    return config_dir() / "logs" / "application.log"


def configure_logging():
    logger = logging.getLogger("betabrite_controller")
    if logger.handlers:
        return
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    except OSError:
        logger.addHandler(logging.NullHandler())


@dataclass(frozen=True, slots=True)
class PacketTrace:
    """Human-readable view of the exact encoded packet and serial chunks."""

    encoded: bytes

    @property
    def wire_chunks(self) -> list[bytes]:
        return [chunk for chunk in self.encoded.split(DELAY) if chunk]

    @property
    def encoded_length(self) -> int:
        return len(self.encoded)

    @property
    def wire_length(self) -> int:
        return sum(len(chunk) for chunk in self.wire_chunks)

    @property
    def delay_count(self) -> int:
        return max(0, len(self.encoded.split(DELAY)) - 1)

    def hex_bytes(self) -> str:
        return self.encoded.hex(" ")

    def escaped_ascii(self) -> str:
        return _escaped_ascii(self.encoded)

    def wire_hex_chunks(self) -> list[str]:
        return [chunk.hex(" ") for chunk in self.wire_chunks]

    def wire_escaped_chunks(self) -> list[str]:
        return [_escaped_ascii(chunk) for chunk in self.wire_chunks]


def trace_packet(packet) -> PacketTrace:
    """Trace bytes from the same packet object handed to production Sign.send."""
    return PacketTrace(packet.to_bytes())


def _escaped_ascii(payload: bytes) -> str:
    pieces = []
    for byte in payload:
        if byte == 0x5C:
            pieces.append("\\\\")
        elif 32 <= byte <= 126:
            pieces.append(chr(byte))
        else:
            pieces.append(f"\\x{byte:02x}")
    return "".join(pieces)


def describe_text_trace(trace: PacketTrace) -> list[str]:
    """Return a concise protocol interpretation for a normal text packet."""
    lines = [
        f"encoded length: {trace.encoded_length} bytes",
        f"wire length:    {trace.wire_length} bytes across {len(trace.wire_chunks)} chunks",
        f"delay markers:  {trace.delay_count} x 100 ms pseudo-delay byte(s), not transmitted",
        f"hex:            {trace.hex_bytes()}",
        f"escaped:        {trace.escaped_ascii()}",
    ]
    for index, chunk in enumerate(trace.wire_chunks, start=1):
        lines.append(f"wire chunk {index}: {chunk.hex(' ')}")
    lines.extend(
        [
            "interpretation:",
            "  00 00 00 00 00: wake/sync NUL preamble",
            "  01: SOH",
            "  5a: sign type Z / all signs",
            "  30 30: address 00",
            "  02: STX",
            "  41: WRITE_TEXT command",
            "  41: text file label A",
            "  1b 26: ESC + FILL position",
            "  61/62: display mode, rotate/hold respectively",
            "  1c NN: color control code (43=auto, 31=red, 32=green, 33=amber)",
            "  03: ETX",
            "  final four ASCII hex bytes: checksum",
            "  04: EOT",
        ]
    )
    return lines
