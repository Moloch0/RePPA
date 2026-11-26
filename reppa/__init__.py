from __future__ import annotations

from pathlib import Path

from ._core import partition_csr

__version__ = "0.2.0"


def get_include() -> str:
    """Return the directory containing the public C++ headers."""
    return str(Path(__file__).resolve().parent / "include")


def get_sources() -> tuple[str, str]:
    """Return the native implementation sources for extension consumers."""
    source = Path(__file__).resolve().parent / "src"
    return str(source / "problem.cpp"), str(source / "rpr.cpp")


__all__ = ["__version__", "get_include", "get_sources", "partition_csr"]
