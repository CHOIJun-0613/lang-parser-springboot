"""Shared parsing utilities."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Iterable


def read_text(file_path: str, encoding: str = "utf-8") -> str:
    """Read text file with the given encoding."""
    with open(file_path, "r", encoding=encoding) as handle:
        return handle.read()


def file_exists(path: str) -> bool:
    """Return True if the file exists."""
    return os.path.exists(path)


def list_files(directory: str, suffix: str) -> Iterable[str]:
    """Yield files with the given suffix under directory."""
    return (
        os.path.join(directory, entry)
        for entry in os.listdir(directory)
        if entry.endswith(suffix)
    )


def timestamp() -> str:
    """Return a unified timestamp format for parser outputs."""
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]


def collapse_whitespace(text: str) -> str:
    """Normalize whitespace to single spaces and strip ends."""
    return re.sub(r"\s+", " ", text).strip()
