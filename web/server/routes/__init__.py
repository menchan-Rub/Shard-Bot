"""
ShardBot Dashboard API - Routes
"""

from web.server.routes.settings import router as settings_router
from web.server.routes.logs import router as logs_router
from web.server.routes.users import router as users_router
from web.server.routes.roles import router as roles_router
from web.server.routes.channels import router as channels_router

__all__ = [
    'settings_router',
    'logs_router',
    'users_router',
    'roles_router',
    'channels_router',
] 