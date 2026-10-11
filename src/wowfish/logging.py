"""loguru configuration: stderr for the user, rotating file for debugging."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from wowfish import paths

_STDERR_FORMAT = "<level>{level: <7}</level> {message}"
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {name}:{line} | {message}"


def setup_logging(verbose: bool = False) -> Path:
    """Reset loguru sinks. Returns the log file path."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO", format=_STDERR_FORMAT)
    log_path = paths.log_file()
    logger.add(log_path, level="DEBUG", format=_FILE_FORMAT, rotation="5 MB", retention=3)
    return log_path
