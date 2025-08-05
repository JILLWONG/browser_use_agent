"""API routes for the search service."""

from .browser_pool import browser_semaphore
from .browser_fastapi import browser_router

__all__ = ["browser_semaphore", "browser_router"]