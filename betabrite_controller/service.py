"""Application operations shared with the GUI, using the authoritative controller."""
from .controller import BetaBriteController
from .connection import ConnectionDiagnostic
from .graphics_protocol import (
    DEFAULT_CONFIGURED_GRAPHIC_LABEL,
    BetaBriteGraphicsController,
    GraphicsProtocolError,
    format_memory_config_entries,
    has_compatible_graphics_slot,
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


def inspect_graphics_support(port):
    controller = BetaBriteGraphicsController(port=port)
    try:
        entries = controller.read_memory_config()
    except GraphicsProtocolError as exc:
        return ConnectionDiagnostic(
            state="graphics-config-error",
            port=controller.last_port,
            source="graphics-inspect",
            message=str(exc),
        )
    ready = has_compatible_graphics_slot(entries)
    prefix = "Graphics support is initialized." if ready else "Graphics support is not initialized."
    return ConnectionDiagnostic(
        state="ready",
        port=controller.last_port,
        source="graphics-inspect",
        message=f"{prefix}\n\nCurrent memory directory:\n{format_memory_config_entries(entries)}",
    )


def initialize_graphics_support(port):
    controller = BetaBriteGraphicsController(port=port)
    try:
        entries = controller.initialize_graphics_support()
    except GraphicsProtocolError as exc:
        return ConnectionDiagnostic(
            state="graphics-config-error",
            port=controller.last_port,
            source="graphics-init",
            message=str(exc),
        )
    return ConnectionDiagnostic(
        state="ready",
        port=controller.last_port,
        source="graphics-init",
        message=(
            "Graphics support initialized and verified. "
            "TEXT A/B/C were restored with GREEN OK; DOTS D is ready.\n\n"
            f"Memory directory:\n{format_memory_config_entries(entries)}"
        ),
    )


def return_to_text(port):
    controller = BetaBriteGraphicsController(port=port)
    controller.return_to_text()
    return ConnectionDiagnostic(
        state="ready",
        port=controller.last_port,
        source="graphics-return",
        message="Returned to text. TEXT B was overwritten with GREEN OK; DOTS D and memory configuration were left unchanged.",
    )
