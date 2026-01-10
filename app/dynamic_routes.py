"""API routes for dynamic entity operations (DML on type-specific tables)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.dependencies import get_session
from app.dynamic_service import DynamicEntityService
from app.entity_type_service import EntityTypeService
from app.schemas import (
    DynamicEntityCreate,
    DynamicEntityUpdate,
    DynamicEntityListResponse,
    ErrorResponse
)
from app.middleware import get_requestor_id


def get_dynamic_router(entity_type: str) -> APIRouter:
    """Create a dynamic router for a specific entity type."""
    
    router = APIRouter(prefix=f"/{entity_type}", tags=[f"{entity_type}-dml"])
    
    def get_service(session: AsyncSession = Depends(get_session)) -> DynamicEntityService:
        """Dependency to get DynamicEntityService for this entity type."""
        try:
            from main import engine
            entity_type_service = EntityTypeService(session, engine)
            return DynamicEntityService(session, entity_type, entity_type_service)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity type '{entity_type}' not found or not registered"
            )
    
    @router.post(
        "",
        response_model=Dict[str, Any],
        status_code=status.HTTP_201_CREATED,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid input"},
            403: {"model": ErrorResponse, "description": "Requestor does not own this entity type"},
            404: {"model": ErrorResponse, "description": "Entity type not found"},
        }
    )
    async def create_entity(
        entity_data: DynamicEntityCreate,
        service: DynamicEntityService = Depends(get_service)
    ) -> Dict[str, Any]:
        f"""
        Create a new {entity_type} entity.
        
        Provide the entity data according to the schema defined for this entity type.
        Only the owner of the entity type can create entities.
        """
        requestor = get_requestor_id()
        return await service.create_entity(entity_data, requestor=requestor)
    
    @router.get(
        "",
        response_model=DynamicEntityListResponse,
        responses={
            404: {"model": ErrorResponse, "description": "Entity type not found"},
        }
    )
    async def list_entities(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        service: DynamicEntityService = Depends(get_service)
    ) -> DynamicEntityListResponse:
        f"""
        List all {entity_type} entities with optional filters.
        
        - **skip**: Number of records to skip (for pagination)
        - **limit**: Number of records to return (max 1000)
        - **is_active**: Filter by active status
        
        Note: Read access is allowed for any requestor.
        """
        items, total = await service.list_entities(
            skip=skip,
            limit=limit,
            is_active=is_active
        )
        return DynamicEntityListResponse(items=items, total=total, skip=skip, limit=limit)
    
    @router.get(
        "/{entity_id}",
        response_model=Dict[str, Any],
        responses={
            404: {"model": ErrorResponse, "description": "Entity not found"},
        }
    )
    async def get_entity(
        entity_id: str = Path(..., description="Entity ID"),
        service: DynamicEntityService = Depends(get_service)
    ) -> Dict[str, Any]:
        f"""
        Get a specific {entity_type} entity by ID.
        
        Note: Read access is allowed for any requestor.
        """
        entity = await service.get_entity(entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.capitalize()} entity with id {entity_id} not found"
            )
        return entity
    
    @router.patch(
        "/{entity_id}",
        response_model=Dict[str, Any],
        responses={
            403: {"model": ErrorResponse, "description": "Requestor does not own this entity type"},
            404: {"model": ErrorResponse, "description": "Entity not found"},
            400: {"model": ErrorResponse, "description": "Invalid input"},
        }
    )
    async def update_entity(
        entity_id: str = Path(..., description="Entity ID"),
        entity_data: DynamicEntityUpdate = ...,
        service: DynamicEntityService = Depends(get_service)
    ) -> Dict[str, Any]:
        f"""
        Update a {entity_type} entity.
        
        Only provided fields will be updated (partial updates supported).
        Only the owner of the entity type can update entities.
        """
        requestor = get_requestor_id()
        entity = await service.update_entity(entity_id, entity_data, requestor=requestor)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.capitalize()} entity with id {entity_id} not found"
            )
        return entity
    
    @router.delete(
        "/{entity_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            403: {"model": ErrorResponse, "description": "Requestor does not own this entity type"},
            404: {"model": ErrorResponse, "description": "Entity not found"},
        }
    )
    async def delete_entity(
        entity_id: str = Path(..., description="Entity ID"),
        hard_delete: bool = Query(False, description="Perform hard delete instead of soft delete"),
        service: DynamicEntityService = Depends(get_service)
    ) -> None:
        f"""
        Delete a {entity_type} entity.
        
        By default, performs a soft delete (marks as inactive).
        Use hard_delete=true to permanently remove the entity.
        Only the owner of the entity type can delete entities.
        """
        requestor = get_requestor_id()
        success = await service.delete_entity(entity_id, hard_delete=hard_delete, requestor=requestor)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.capitalize()} entity with id {entity_id} not found"
            )
    
    @router.head(
        "/{entity_id}",
        status_code=status.HTTP_200_OK,
        responses={
            404: {"description": "Entity not found"},
        }
    )
    async def entity_exists(
        entity_id: str = Path(..., description="Entity ID"),
        service: DynamicEntityService = Depends(get_service)
    ) -> None:
        f"""
        Check if a {entity_type} entity exists (returns 200 if exists, 404 if not).
        
        Note: Read access is allowed for any requestor.
        """
        exists = await service.entity_exists(entity_id)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.capitalize()} entity with id {entity_id} not found"
            )
    
    return router
