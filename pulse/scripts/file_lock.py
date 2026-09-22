#!/usr/bin/env python3
"""Shared file locking for concurrent agent access."""

import fcntl
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def file_lock(filepath: Path):
    """Lock file for safe concurrent access across multiple agents."""
    lock_path = Path(str(filepath) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
