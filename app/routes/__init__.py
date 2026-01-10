"""Routes module for Entity Service API.

Routes are organized by concern:
- entity_type_routes: DDL operations for entity types
- dynamic_routes: DML operations for dynamic entities
- discovery_routes: Service discovery and schema endpoints
"""

from app.routes.entity_type_routes import entity_type_router
from app.routes.dynamic_routes import get_dynamic_router
from app.routes.discovery_routes import discovery_router
from app.routes.routes import entity_router

__all__ = [
    "entity_type_router",
    "get_dynamic_router",
    "discovery_router",
    "entity_router",
]
