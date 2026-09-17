"""Active serial-transport checks and customer-friendly connection errors."""

from __future__ import annotations

from dataclasses import dataclass
import errno

import serial

from .devices import (
    AUTO_PORT,
    DeviceNotFoundError,
    DeviceSelectionError,
    resolve_device,
)
from .settings import AppSettings


@dataclass(frozen=True, slots=True)
class ConnectionDiagnostic:
    """Result of an active serial-port readiness check."""

    state: str
    message: str
    port: str | None = None
    source: str | None = None

    @property
    def ready(self) -> bool:
        return self.state == "ready"


class BetaBriteTransportError(RuntimeError):
    """Customer-facing serial transport failure with a stable state code."""

    def __init__(
        self,
        state: str,
        message: str,
        *,
        port: str | None = None,
    ):
        super().__init__(message)
        self.state = state
        self.port = port

    @classmethod
    def from_diagnostic(
        cls,
        diagnostic: ConnectionDiagnostic,
    ) -> "BetaBriteTransportError":
        return cls(
            diagnostic.state,
            diagnostic.message,
            port=diagnostic.port,
        )


def classify_transport_exception(
    exc: BaseException,
    port: str,
    *,
    source: str | None = None,
) -> ConnectionDiagnostic | None:
    """Translate common serial/OS failures into stable customer-facing states."""
    text = str(exc).casefold()
    error_number = getattr(exc, "errno", None)

    if (
        isinstance(exc, FileNotFoundError)
        or error_number in {errno.ENOENT, errno.ENODEV}
        or "no such file or directory" in text
        or "cannot find the file" in text
        or "the system cannot find" in text
    ):
        return ConnectionDiagnostic(
            state="port-not-found",
            message=(
                f"The selected serial port {port} is no longer available. "
                "Reconnect the USB adapter and try again."
            ),
            port=port,
            source=source,
        )

    if (
        "device or resource busy" in text
        or "resource busy" in text
        or "port is busy" in text
        or "access is denied" in text
        or "permissionerror(13, 'access is denied')" in text
    ):
        return ConnectionDiagnostic(
            state="port-busy",
            message=(
                f"{port} is currently unavailable. Another application may be "
                "using the serial adapter. Close other serial or sign-control "
                "programs and try again."
            ),
            port=port,
            source=source,
        )

    if (
        isinstance(exc, PermissionError)
        or error_number in {errno.EACCES, errno.EPERM}
        or "permission denied" in text
        or "operation not permitted" in text
    ):
        return ConnectionDiagnostic(
            state="permission-denied",
            message=(
                f"BetaBrite Controller does not have permission to open {port}. "
                "Check serial-device permissions, then reconnect the adapter "
                "and try again."
            ),
            port=port,
            source=source,
        )

    if isinstance(exc, (serial.SerialException, OSError)):
        detail = str(exc).strip()
        suffix = f" ({detail})" if detail else ""
        return ConnectionDiagnostic(
            state="open-failed",
            message=f"Could not open serial port {port}{suffix}.",
            port=port,
            source=source,
        )

    return None


def _configure_serial(handle, port: str) -> None:
    handle.port = port
    handle.baudrate = 9600
    handle.bytesize = serial.SEVENBITS
    handle.parity = serial.PARITY_EVEN
    handle.stopbits = serial.STOPBITS_ONE
    handle.timeout = 1
    handle.write_timeout = 1
    handle.dtr = False


def probe_connection(
    port: str | None = AUTO_PORT,
    *,
    settings: AppSettings | None = None,
) -> ConnectionDiagnostic:
    """Actively verify that the selected serial transport can be opened.

    This confirms computer-to-adapter readiness. It does not claim that the
    BetaBrite display acknowledged a message because this controller path does
    not have a reliable application-level ACK to inspect.
    """
    try:
        selection = resolve_device(port, settings=settings)
    except DeviceNotFoundError as exc:
        return ConnectionDiagnostic(
            state="no-adapter",
            message=str(exc),
        )
    except DeviceSelectionError as exc:
        return ConnectionDiagnostic(
            state="selection-required",
            message=str(exc),
        )

    handle = serial.Serial()
    try:
        _configure_serial(handle, selection.port)
        handle.open()
    except Exception as exc:
        diagnostic = classify_transport_exception(
            exc,
            selection.port,
            source=selection.source,
        )
        if diagnostic is not None:
            return diagnostic
        raise
    finally:
        try:
            if getattr(handle, "is_open", False):
                handle.close()
        except Exception:
            pass

    return ConnectionDiagnostic(
        state="ready",
        message=(
            f"Serial port {selection.port} opened successfully. "
            "The computer-to-adapter connection is ready."
        ),
        port=selection.port,
        source=selection.source,
    )
