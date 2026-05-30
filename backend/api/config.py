"""Config API — ui/ uses this to read/write app settings."""
from backend.utils.config import get_output_root, set_output_root

__all__ = ["get_output_root", "set_output_root"]
