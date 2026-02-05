"""
Logging configuration for Code-2-Doc.
"""

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(level: str = "INFO", rich_output: bool = True) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        rich_output: Use rich handler for formatted output
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Remove existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler: logging.Handler
    if rich_output:
        # Use Rich handler for beautiful console output
        console = Console(stderr=True)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # Standard stream handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Set specific loggers
    logging.getLogger("code2doc").setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name. If None, returns the root code2doc logger.

    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("code2doc")
    return logging.getLogger(f"code2doc.{name}")
