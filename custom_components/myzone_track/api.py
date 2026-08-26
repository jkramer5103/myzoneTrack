"""Compatibility imports from the standalone myzoneAPI Python module."""

from .myzone_api import MyzoneAuthenticationError, MyzoneClient, MyzoneError

__all__ = ["MyzoneAuthenticationError", "MyzoneClient", "MyzoneError"]
