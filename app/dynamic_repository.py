"""Repository for dynamic entity operations on type-specific tables."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import _dynamic_models


class DynamicEntityRepository:
    """Repository for entity operations on dynamically created tables."""
    
    def __init__(self, session: AsyncSession, entity_type: str):
        self.session = session
        self.entity_type = entity_type
        
        if entity_type not in _dynamic_models:
            raise ValueError(f"Entity type '{entity_type}' not found or not registered")
        
        self.model_class = _dynamic_models[entity_type]
    
    async def create(self, entity_data: Dict[str, Any]) -> Any:
        """Create a new entity instance."""
        entity = self.model_class(**entity_data)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """Get entity by ID."""
        query = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Any], int]:
        """List entities with filters."""
        query = select(self.model_class)
        
        # Apply filters
        if is_active is not None:
            query = query.where(self.model_class.is_active == is_active)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        
        # Get total count
        count_query = select(func.count()).select_from(self.model_class)
        if is_active is not None:
            count_query = count_query.where(self.model_class.is_active == is_active)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    count_query = count_query.where(getattr(self.model_class, key) == value)
        
        total = await self.session.scalar(count_query)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        entities = result.scalars().all()
        
        return entities, total
    
    async def update(self, entity_id: str, update_data: Dict[str, Any]) -> Optional[Any]:
        """Update an entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
        
        entity.updated_at = datetime.utcnow()
        entity.version += 1
        
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Soft delete an entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        
        entity.is_active = False
        entity.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def hard_delete(self, entity_id: str) -> bool:
        """Hard delete an entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        
        await self.session.delete(entity)
        await self.session.commit()
        return True
    
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        entity = await self.get_by_id(entity_id)
        return entity is not None
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities."""
        query = select(func.count()).select_from(self.model_class)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        return await self.session.scalar(query)
