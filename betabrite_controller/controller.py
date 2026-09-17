from alphasign import (
    Sign,
    SignType,
    Packet,
    WriteText,
    DisplayMode,
    DisplayPosition,
    SpecialMode,
    Color,
    color,
    speed,
    CTRL_FLASH_ON,
    CTRL_FLASH_OFF,
    CTRL_WIDE_ON,
    CTRL_WIDE_OFF,
)

from .connection import (
    BetaBriteTransportError,
    classify_transport_exception,
    probe_connection,
)
from .devices import (
    AUTO_PORT,
    DeviceDiscoveryError,
    port_is_available,
    resolve_port,
)


DEFAULT_PORT = AUTO_PORT


COLORS = {
    "auto": Color.AUTO,
    "red": Color.RED,
    "green": Color.GREEN,
    "amber": Color.AMBER,
    "yellow": Color.YELLOW,
    "orange": Color.ORANGE,
    "brown": Color.BROWN,
    "dim-red": Color.DIM_RED,
    "dim-green": Color.DIM_GREEN,
    "rainbow1": Color.RAINBOW1,
    "rainbow2": Color.RAINBOW2,
    "mix": Color.MIX,
}


MODES = {
    "rotate": DisplayMode.ROTATE,
    "hold": DisplayMode.HOLD,
    "scroll": DisplayMode.SCROLL,
    "compressed-rotate": DisplayMode.COMPRESSED_ROTATE,
    "roll-left": DisplayMode.ROLL_LEFT,
    "roll-right": DisplayMode.ROLL_RIGHT,
    "roll-up": DisplayMode.ROLL_UP,
    "roll-down": DisplayMode.ROLL_DOWN,
    "roll-in": DisplayMode.ROLL_IN,
    "roll-out": DisplayMode.ROLL_OUT,
    "wipe-left": DisplayMode.WIPE_LEFT,
    "wipe-right": DisplayMode.WIPE_RIGHT,
    "wipe-up": DisplayMode.WIPE_UP,
    "wipe-down": DisplayMode.WIPE_DOWN,
    "wipe-in": DisplayMode.WIPE_IN,
    "wipe-out": DisplayMode.WIPE_OUT,
    "automode": DisplayMode.AUTOMODE,
    "flash": DisplayMode.FLASH,
}


SPECIALS = {
    "twinkle": SpecialMode.TWINKLE,
    "sparkle": SpecialMode.SPARKLE,
    "snow": SpecialMode.SNOW,
    "interlock": SpecialMode.INTERLOCK,
    "switch": SpecialMode.SWITCH,
    "spray": SpecialMode.SPRAY,
    "starburst": SpecialMode.STARBURST,
    "welcome": SpecialMode.WELCOME,
    "slot-machine": SpecialMode.SLOT_MACHINE,
    "news-flash": SpecialMode.NEWS_FLASH,
    "trumpet": SpecialMode.TRUMPET,
    "cycle-colors": SpecialMode.CYCLE_COLORS,
    "thank-you": SpecialMode.THANK_YOU,
    "no-smoking": SpecialMode.NO_SMOKING,
    "dont-drink-drive": SpecialMode.DONT_DRINK_DRIVE,
    "running-animal": SpecialMode.RUNNING_ANIMAL,
    "fireworks": SpecialMode.FIREWORKS,
    "turbocar": SpecialMode.TURBOCAR,
    "cherry-bomb": SpecialMode.CHERRY_BOMB,
}


class BetaBriteController:
    """Controller for Alpha/BetaBrite serial LED signs."""

    def __init__(
        self,
        port=DEFAULT_PORT,
        address="00",
        type_code=b"Z",
    ):
        self.port = port or DEFAULT_PORT
        self.address = address
        self.type_code = type_code
        self.last_port = None

    @property
    def resolved_port(self):
        """Return the selected serial port, or ``None`` when auto-detection fails."""
        try:
            return resolve_port(self.port)
        except DeviceDiscoveryError:
            return None

    @property
    def connected(self):
        """Return whether the selected serial device is present.

        This is a passive availability check. Use ``check_connection()`` when
        the application needs to verify that the serial port can actually open.
        """
        port = self.resolved_port
        return bool(port and port_is_available(port))

    def check_connection(self):
        """Actively verify that the selected serial transport can be opened."""
        return probe_connection(self.port)

    def build_content(
        self,
        message,
        color_name="auto",
        speed_level=None,
        flash=False,
        wide=False,
    ):
        if color_name not in COLORS:
            raise ValueError(
                f"Unknown color: {color_name}"
            )

        if speed_level is not None:
            if speed_level not in range(1, 6):
                raise ValueError(
                    "Speed must be between 1 and 5"
                )

        content = color(COLORS[color_name])

        if speed_level is not None:
            content += speed(speed_level)

        if wide:
            content += CTRL_WIDE_ON

        if flash:
            content += CTRL_FLASH_ON

        content += message.encode(
            "ascii",
            errors="replace",
        )

        if flash:
            content += CTRL_FLASH_OFF

        if wide:
            content += CTRL_WIDE_OFF

        return content

    def send(
        self,
        message="",
        color_name="auto",
        mode_name="rotate",
        special_name=None,
        speed_level=None,
        flash=False,
        wide=False,
    ):
        if mode_name not in MODES:
            raise ValueError(
                f"Unknown display mode: {mode_name}"
            )

        if special_name is not None:
            if special_name not in SPECIALS:
                raise ValueError(
                    f"Unknown special effect: {special_name}"
                )

        if not message and special_name is None:
            raise ValueError(
                "A message or special effect is required"
            )

        content = self.build_content(
            message=message,
            color_name=color_name,
            speed_level=speed_level,
            flash=flash,
            wide=wide,
        )

        if special_name is not None:
            display_mode = DisplayMode.SPECIAL
            special_mode = SPECIALS[special_name]
        else:
            display_mode = MODES[mode_name]
            special_mode = None

        port = resolve_port(self.port)
        self.last_port = port

        sign = Sign(
            sign_type=SignType.ALL,
            address=self.address,
        )

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

            packet = Packet(
                type_code=self.type_code,
                address=self.address,
            )

            packet.add(
                WriteText(
                    content,
                    label="A",
                    position=DisplayPosition.FILL,
                    mode=display_mode,
                    special_mode=special_mode,
                )
            )

            sign.send(packet)

        except Exception as exc:
            diagnostic = classify_transport_exception(exc, port)
            if diagnostic is not None:
                raise BetaBriteTransportError.from_diagnostic(
                    diagnostic
                ) from exc
            raise

        finally:
            try:
                sign.close()
            except Exception:
                pass
