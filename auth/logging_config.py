import logging
import json


class ExtraFormatter(logging.Formatter):
    """Formatter that appends the extra dict to every log message.

    Python's logging.Formatter stores ``extra={...}`` on the LogRecord but
    never includes it in the formatted output.  This subclass detects custom
    attributes injected via ``extra=`` and serialises them as JSON after the
    message, producing lines like::

        2026-07-16 12:52:36 [INFO] server: Tool called: some_tool
            | {"address_number": 1234, "fields": "summary"}
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in logging.LogRecord.__dict__
            and k
            not in (
                "args",
                "msg",
                "name",
                "levelno",
                "levelname",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "process",
                "processName",
            )
        }
        if extras:
            base += " | " + json.dumps(extras, default=str)
        return base


def configure_logging(level: int = logging.DEBUG) -> None:
    """Install a DEBUG-level handler on the root logger with ``ExtraFormatter``.

    Call this once at application startup, **before** any module creates its
    logger, so that all subsequent ``logger.info(…, extra=…)`` calls render
    the extra dictionary in the output.

    Parameters
    ----------
    level : int
        Logging threshold (e.g. ``logging.DEBUG``, ``logging.INFO``).
    """
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        ExtraFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)