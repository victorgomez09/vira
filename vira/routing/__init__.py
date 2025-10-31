"""
Routing package for Vira framework.

Provides:
- Route class for individual route definitions
- Router class for managing collections of routes
- APIRouter class for hierarchical API organization
- Decorators for route registration (@get, @post, etc.)
"""

from .route import Route
from .apirouter import APIRouter

__all__ = [
    "Route",
    "APIRouter",
]
