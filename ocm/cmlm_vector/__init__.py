"""cmlm-vector: the CMLM memory with vector generalization and a learned law, as an installable package."""
__version__ = "0.2.0"

from .memory import Memory  # noqa: E402

__all__ = ["Memory", "__version__"]
