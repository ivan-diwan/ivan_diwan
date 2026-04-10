from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def managed_test_paths(*paths: str | Path) -> Iterator[tuple[Path, ...]]:
    resolved_paths = tuple(_resolve_test_path(path) for path in paths)
    try:
        yield resolved_paths
    finally:
        for path in resolved_paths:
            if path.exists():
                path.unlink()


def _resolve_test_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return candidate
