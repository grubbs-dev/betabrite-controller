"""One serial operation at a time, without blocking the Qt event loop."""
import logging
from PySide6.QtCore import QThread
from .connection import BetaBriteTransportError, ConnectionDiagnostic
from .devices import DeviceDiscoveryError


class Operation(QThread):
    def __init__(self, callback, parent):
        super().__init__(parent)
        self.callback = callback
        self.result = None

    def run(self):
        try:
            self.result = self.callback()
        except (BetaBriteTransportError, DeviceDiscoveryError) as exc:
            logging.getLogger(__name__).exception("Device operation failed")
            self.result = ConnectionDiagnostic(
                state=getattr(exc, "state", "not-found"), message=str(exc),
                port=getattr(exc, "port", None),
            )
        except Exception:
            logging.getLogger(__name__).exception("Device operation failed")
            self.result = ConnectionDiagnostic(
                state="open-failed",
                message="The operation failed. Reconnect the adapter and try again. See About / Diagnostics for the log location.",
            )
