"""Private, bounded diagnostic logs; no message content or telemetry."""
import logging
from logging.handlers import RotatingFileHandler

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
