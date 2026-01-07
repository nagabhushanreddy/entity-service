"""Service for dynamic entity operations (DML)."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.dynamic_repository import DynamicEntityRepository
from app.schemas import DynamicEntityCreate, DynamicEntityUpdate, DynamicEntityResponse


class DynamicEntityService:
    """Service for entity operations on type-specific tables."""
    
    def __init__(self, session: AsyncSession, entity_type: str):
        self.repository = DynamicEntityRepository(session, entity_type)
        self.entity_type = entity_type
    
    def _entity_to_dict(self, entity: Any) -> Dict[str, Any]:
        """Convert SQLAlchemy model instance to dict."""
        return {
            column.name: getattr(entity, column.name)
            for column in entity.__table__.columns
        }
    
    async def create_entity(self, entity_data: DynamicEntityCreate) -> Dict[str, Any]:
        """Create a new entity instance."""
        data_dict = entity_data.model_dump(exclude_unset=True)
        entity = await self.repository.create(data_dict)
        return self._entity_to_dict(entity)
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        entity = await self.repository.get_by_id(entity_id)
        if not entity:
            return None
        return self._entity_to_dict(entity)
    
    async def list_entities(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """List entities with filters."""
        entities, total = await self.repository.list(
            skip=skip,
            limit=limit,
            filters=filters,
            is_active=is_active
        )
        return [self._entity_to_dict(e) for e in entities], total
    
    async def update_entity(
        self,
        entity_id: str,
        entity_data: DynamicEntityUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        update_dict = entity_data.model_dump(exclude_unset=True)
        entity = await self.repository.update(entity_id, update_dict)
        if not entity:
            return None
        return self._entity_to_dict(entity)
    
    async def delete_entity(self, entity_id: str, hard_delete: bool = False) -> bool:
        """Delete an entity (soft or hard)."""
        if hard_delete:
            return await self.repository.hard_delete(entity_id)
        return await self.repository.delete(entity_id)
    
    async def entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        return await self.repository.exists(entity_id)
    
    async def count_entities(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities."""
        return await self.repository.count(filters)
