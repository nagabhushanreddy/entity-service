"""Data repository for entity operations"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.database.database import Entity
from app.schemas import EntityCreate, EntityUpdate


class EntityRepository:
    """Repository for entity database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity_data: EntityCreate) -> Entity:
        """Create a new entity"""
        entity = Entity(
            name=entity_data.name,
            description=entity_data.description,
            entity_type=entity_data.entity_type,
            status=entity_data.status,
            data=entity_data.data,
            entity_metadata=entity_data.metadata,
            created_by=entity_data.created_by
        )
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        query = select(Entity).where(Entity.id == entity_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Entity], int]:
        """List entities with filters"""
        query = select(Entity)
        
        # Apply filters
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if status:
            query = query.where(Entity.status == status)
        if is_active is not None:
            query = query.where(Entity.is_active == is_active)
        
        # Get total count
        count_query = select(func.count()).select_from(Entity)
        if entity_type:
            count_query = count_query.where(Entity.entity_type == entity_type)
        if status:
            count_query = count_query.where(Entity.status == status)
        if is_active is not None:
            count_query = count_query.where(Entity.is_active == is_active)
        
        total = await self.session.scalar(count_query)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        entities = result.scalars().all()
        
        return entities, total
    
    async def update(self, entity_id: str, entity_data: EntityUpdate) -> Optional[Entity]:
        """Update an entity"""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None
        
        # Update fields
        update_data = entity_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        
        entity.updated_at = datetime.utcnow()
        entity.version += 1
        
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Soft delete an entity"""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        
        entity.is_active = False
        entity.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def hard_delete(self, entity_id: str) -> bool:
        """Hard delete an entity"""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        
        await self.session.delete(entity)
        await self.session.commit()
        return True
    
    async def list_by_type(
        self,
        entity_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Entity], int]:
        """List entities by type"""
        return await self.list(skip=skip, limit=limit, entity_type=entity_type)
    
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        entity = await self.get_by_id(entity_id)
        return entity is not None
    
    async def count(self, entity_type: Optional[str] = None) -> int:
        """Count entities"""
        query = select(func.count()).select_from(Entity)
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        return await self.session.scalar(query)
