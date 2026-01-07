"""Business logic layer for entity operations"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import EntityRepository
from app.schemas import EntityCreate, EntityUpdate, EntityResponse
from app.database import Entity


class EntityService:
    """Service for entity business logic"""
    
    def __init__(self, session: AsyncSession):
        self.repository = EntityRepository(session)
    
    async def create_entity(self, entity_data: EntityCreate) -> EntityResponse:
        """Create a new entity"""
        entity = await self.repository.create(entity_data)
        return EntityResponse.model_validate(entity)
    
    async def get_entity(self, entity_id: str) -> Optional[EntityResponse]:
        """Get entity by ID"""
        entity = await self.repository.get_by_id(entity_id)
        if not entity:
            return None
        return EntityResponse.model_validate(entity)
    
    async def list_entities(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[EntityResponse], int]:
        """List entities with filters"""
        entities, total = await self.repository.list(
            skip=skip,
            limit=limit,
            entity_type=entity_type,
            status=status,
            is_active=is_active
        )
        return [EntityResponse.model_validate(e) for e in entities], total
    
    async def update_entity(
        self,
        entity_id: str,
        entity_data: EntityUpdate
    ) -> Optional[EntityResponse]:
        """Update an entity"""
        entity = await self.repository.update(entity_id, entity_data)
        if not entity:
            return None
        return EntityResponse.model_validate(entity)
    
    async def delete_entity(self, entity_id: str, hard_delete: bool = False) -> bool:
        """Delete an entity (soft or hard)"""
        if hard_delete:
            return await self.repository.hard_delete(entity_id)
        return await self.repository.delete(entity_id)
    
    async def list_by_type(
        self,
        entity_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[EntityResponse], int]:
        """List entities by type"""
        entities, total = await self.repository.list_by_type(entity_type, skip, limit)
        return [EntityResponse.model_validate(e) for e in entities], total
    
    async def entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        return await self.repository.exists(entity_id)
    
    async def count_entities(self, entity_type: Optional[str] = None) -> int:
        """Count entities"""
        return await self.repository.count(entity_type)
