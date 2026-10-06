"""Application operations shared with the GUI, using the authoritative controller."""
from .controller import BetaBriteController
from .connection import ConnectionDiagnostic
from .graphics_protocol import (
    DEFAULT_CONFIGURED_GRAPHIC_LABEL,
    BetaBriteGraphicsController,
    GraphicsProtocolError,
)


def transmit(port, draft):
    controller = BetaBriteController(port=port)
    controller.send(**draft.send_kwargs())
    return ConnectionDiagnostic(
        state="ready", port=controller.last_port, source="transmit",
        message="Message sent. The serial write completed; the sign does not acknowledge display updates.",
    )


def clear_sign(port):
    controller = BetaBriteController(port=port)
    controller.send(message=" ", mode_name="hold", color_name="auto")
    return ConnectionDiagnostic(
        state="ready",
        port=controller.last_port,
        source="clear",
        message="Sign cleared. The serial write completed; the sign does not acknowledge display updates.",
    )


def transmit_graphic(port, frame, *, label=DEFAULT_CONFIGURED_GRAPHIC_LABEL):
    controller = BetaBriteGraphicsController(port=port)
    try:
        controller.send_static_graphic(frame, graphic_label=label)
    except GraphicsProtocolError as exc:
        return ConnectionDiagnostic(
            state="graphics-not-initialized",
            port=controller.last_port,
            source="graphics",
            message=str(exc),
        )
    return ConnectionDiagnostic(
        state="ready",
        port=controller.last_port,
        source="graphics",
        message="Graphic sent. The serial write completed; the sign does not acknowledge display updates.",
    )
