"""
ShardBot Dashboard API - Routes
"""

from .settings import router as settings_router
from .logs import router as logs_router
from .users import router as users_router
from .roles import router as roles_router
from .channels import router as channels_router

__all__ = [
    'settings_router',
    'logs_router',
    'users_router',
    'roles_router',
    'channels_router',
] 