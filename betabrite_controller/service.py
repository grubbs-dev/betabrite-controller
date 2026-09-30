"""Application operations shared with the GUI, using the authoritative controller."""
from .controller import BetaBriteController
from .connection import ConnectionDiagnostic


def transmit(port, draft):
    controller = BetaBriteController(port=port)
    controller.send(**draft.send_kwargs())
    return ConnectionDiagnostic(
        state="ready", port=controller.last_port, source="transmit",
        message="Message sent. The serial write completed; the sign does not acknowledge display updates.",
    )
