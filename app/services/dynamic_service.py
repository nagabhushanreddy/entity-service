"""Service for dynamic entity operations (DML)."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DynamicEntityRepository
from app.schemas import DynamicEntityCreate, DynamicEntityUpdate, DynamicEntityResponse
from app.services import EntityTypeService
from app.exceptions import RequestorMismatchError


class DynamicEntityService:
    """Service for entity operations on type-specific tables."""
    
    def __init__(self, session: AsyncSession, entity_type: str, entity_type_service: Optional[EntityTypeService] = None):
        self.repository = DynamicEntityRepository(session, entity_type)
        self.entity_type = entity_type
        self.entity_type_service = entity_type_service
        self.session = session
    
    async def check_requestor_ownership(self, requestor: str) -> None:
        """Check if requestor owns this entity type.
        
        Raises:
            RequestorMismatchError: If requestor doesn't own the entity type
        """
        if not self.entity_type_service:
            # If service not provided, skip check (for read-only operations)
            return
        
        try:
            await self.entity_type_service.get_entity_type(self.entity_type, requestor=requestor)
        except Exception:
            # If check fails, raise RequestorMismatch
            raise RequestorMismatchError(self.entity_type, requestor)
    
    def _entity_to_dict(self, entity: Any) -> Dict[str, Any]:
        """Convert SQLAlchemy model instance to dict."""
        return {
            column.name: getattr(entity, column.name)
            for column in entity.__table__.columns
        }
    
    async def create_entity(self, entity_data: DynamicEntityCreate, requestor: Optional[str] = None) -> Dict[str, Any]:
        """Create a new entity instance.
        
        Args:
            entity_data: Entity data to create
            requestor: Requestor making the request (for authorization check)
            
        Raises:
            RequestorMismatchError: If requestor doesn't own the entity type
        """
        if requestor:
            await self.check_requestor_ownership(requestor)
        
        data_dict = entity_data.model_dump(exclude_unset=True)
        entity = await self.repository.create(data_dict)
        return self._entity_to_dict(entity)
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID. Available for any requestor (read-only)."""
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
        """List entities with filters. Available for any requestor (read-only)."""
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
        entity_data: DynamicEntityUpdate,
        requestor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an entity.
        
        Args:
            entity_id: ID of entity to update
            entity_data: Updated entity data
            requestor: Requestor making the request (for authorization check)
            
        Raises:
            RequestorMismatchError: If requestor doesn't own the entity type
        """
        if requestor:
            await self.check_requestor_ownership(requestor)
        
        update_dict = entity_data.model_dump(exclude_unset=True)
        entity = await self.repository.update(entity_id, update_dict)
        if not entity:
            return None
        return self._entity_to_dict(entity)
    
    async def delete_entity(self, entity_id: str, hard_delete: bool = False, requestor: Optional[str] = None) -> bool:
        """Delete an entity (soft or hard).
        
        Args:
            entity_id: ID of entity to delete
            hard_delete: Whether to perform hard delete
            requestor: Requestor making the request (for authorization check)
            
        Raises:
            RequestorMismatchError: If requestor doesn't own the entity type
        """
        if requestor:
            await self.check_requestor_ownership(requestor)
        
        if hard_delete:
            return await self.repository.hard_delete(entity_id)
        return await self.repository.delete(entity_id)
    
    async def entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists. Available for any requestor (read-only)."""
        return await self.repository.exists(entity_id)
    
    async def count_entities(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities. Available for any requestor (read-only)."""
        return await self.repository.count(filters)
