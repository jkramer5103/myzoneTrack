"""Vendored public myzoneAPI module for self-contained HACS installs."""

from .client import (
    AuthenticationError,
    DashboardQuery,
    MyzoneAuthenticationError,
    MyzoneClient,
    MyzoneError,
)

__all__ = [
    "AuthenticationError",
    "DashboardQuery",
    "MyzoneAuthenticationError",
    "MyzoneClient",
    "MyzoneError",
]
