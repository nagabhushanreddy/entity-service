"""Database module for Entity Service.

Includes:
- Models: SQLAlchemy ORM models (EntityTypeDefinition, Entity, dynamic entities)
- Repository: Data access layer for entity types
- DynamicRepository: Data access layer for dynamic entities
- Dependencies: FastAPI dependency injection for database sessions
"""

from app.database.database import (
    Base,
    Entity,
    EntityTypeDefinition,
    create_dynamic_entity_model,
    _dynamic_models,
)
from app.database.repository import EntityRepository
from app.database.dynamic_repository import DynamicEntityRepository
from app.database.dependencies import (
    get_session,
    init_session_maker,
)

__all__ = [
    "Base",
    "Entity",
    "EntityTypeDefinition",
    "create_dynamic_entity_model",
    "_dynamic_models",
    "EntityRepository",
    "DynamicEntityRepository",
    "get_session",
    "init_session_maker",
]
