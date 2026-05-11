"""
logging_config.py
-----------------
Centralised logging setup for the glacier-snow-analysis package.

Call ``setup_logging()`` once at the entry point (CLI or script).
All modules obtain a logger via ``logging.getLogger(__name__)``.
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
) -> None:
    """
    Configure root logger with a consistent format.

    Parameters
    ----------
    level : str
        Logging level name ("DEBUG", "INFO", "WARNING", "ERROR").
    log_file : str | Path | None
        If provided, logs are also written to this file (in addition to
        stdout).
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file is not None:
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,   # override any previously set handlers
    )
