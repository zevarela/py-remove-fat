"""Terminal color detection and ANSI formatting helpers."""

from __future__ import annotations

import os
import sys


class C:
    """ANSI color codes. Empty until init_colors() runs on a capable TTY."""

    RESET = ""
    BOLD = ""
    DIM = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    CYAN = ""
    WHITE = ""
    BLUE = ""
    MAGENTA = ""
    BOLD_CYAN = ""
    BOLD_GREEN = ""
    BOLD_YELLOW = ""
    BOLD_BLUE = ""
    BOLD_MAGENTA = ""
    BOLD_WHITE = ""


def init_colors() -> None:
    if os.environ.get("NO_COLOR"):
        return
    if not sys.stdout.isatty():
        return
    if sys.platform == "win32":
        try:
            import ctypes  # noqa: PLC0415

            enable_vtp = 0x0004
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return
            kernel32.SetConsoleMode(handle, mode.value | enable_vtp)
        except Exception:
            return
    C.RESET = "\033[0m"
    C.BOLD = "\033[1m"
    C.DIM = "\033[2m"
    C.RED = "\033[31m"
    C.GREEN = "\033[32m"
    C.YELLOW = "\033[33m"
    C.CYAN = "\033[36m"
    C.WHITE = "\033[37m"
    C.BLUE = "\033[34m"
    C.MAGENTA = "\033[35m"
    C.BOLD_CYAN = "\033[1;36m"
    C.BOLD_GREEN = "\033[1;32m"
    C.BOLD_YELLOW = "\033[1;33m"
    C.BOLD_BLUE = "\033[1;34m"
    C.BOLD_MAGENTA = "\033[1;35m"
    C.BOLD_WHITE = "\033[1;37m"


init_colors()


def clabel(text: str, width: int, color: str) -> str:
    if color:
        return color + text + C.RESET + " " * max(0, width - len(text))
    return f"{text:<{width}}"


def ccol(text: str, width: int, color: str) -> str:
    if color:
        return " " * max(0, width - len(text)) + color + text + C.RESET
    return f"{text:>{width}}"


def summary_data_column_colors(
    num_bytes: int,
    *,
    footer_row: bool,
) -> tuple[str, str, str, str]:
    if footer_row:
        return (
            C.BOLD_GREEN if num_bytes > 0 else C.DIM,
            C.BOLD_YELLOW,
            C.BOLD_BLUE,
            C.BOLD_MAGENTA,
        )
    return (
        C.GREEN if num_bytes > 0 else C.DIM,
        C.YELLOW,
        C.BLUE,
        C.MAGENTA,
    )
