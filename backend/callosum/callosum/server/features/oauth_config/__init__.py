"""OAuth configuration feature module."""

from callosum.server.features.oauth_config.api import admin_router
from callosum.server.features.oauth_config.api import router

__all__ = ["admin_router", "router"]
