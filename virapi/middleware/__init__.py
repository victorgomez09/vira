"""
virapi Middleware Package

This package provides the middleware system for virapi applications.
Middleware allows you to process requests and responses in a pipeline fashion.
"""

from .middleware_chain import MiddlewareChain, MiddlewareCallable

__all__ = ["MiddlewareChain", "MiddlewareCallable"]
