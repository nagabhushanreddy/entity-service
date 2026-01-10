"""API routes for entity endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_session
from app.services.service import EntityService
from app.schemas import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    ErrorResponse
)

entity_router = APIRouter(prefix="/entities", tags=["entities"])
@entity_router.post(
    "",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
    }
)
async def create_entity(
    entity_data: EntityCreate,
    session: AsyncSession = Depends(get_session)
) -> EntityResponse:
    """
    Create a new entity
    
    - **name**: Name of the entity (required)
    - **entity_type**: Type/category of the entity (required)
    - **description**: Optional description
    - **status**: Entity status (default: active)
    - **data**: Custom JSON data
    - **metadata**: Entity metadata
    """
    service = EntityService(session)
    return await service.create_entity(entity_data)


@entity_router.get(
    "",
    response_model=EntityListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
    }
)
async def list_entities(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    session: AsyncSession = Depends(get_session)
) -> EntityListResponse:
    """
    List all entities with optional filters
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Number of records to return (max 1000)
    - **entity_type**: Filter by entity type
    - **status**: Filter by status
    - **is_active**: Filter by active status
    """
    service = EntityService(session)
    items, total = await service.list_entities(
        skip=skip,
        limit=limit,
        entity_type=entity_type,
        status=status,
        is_active=is_active
    )
    return EntityListResponse(items=items, total=total, skip=skip, limit=limit)


@entity_router.get(
    "/{entity_id}",
    response_model=EntityResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Entity not found"},
    }
)
async def get_entity(
    entity_id: str,
    session: AsyncSession = Depends(get_session)
) -> EntityResponse:
    """Get a specific entity by ID"""
    service = EntityService(session)
    entity = await service.get_entity(entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
    return entity


@entity_router.patch(
    "/{entity_id}",
    response_model=EntityResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Entity not found"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
    }
)
async def update_entity(
    entity_id: str,
    entity_data: EntityUpdate,
    session: AsyncSession = Depends(get_session)
) -> EntityResponse:
    """
    Update an entity
    
    Only provided fields will be updated (partial updates supported)
    """
    service = EntityService(session)
    entity = await service.update_entity(entity_id, entity_data)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
    return entity


@entity_router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Entity not found"},
    }
)
async def delete_entity(
    entity_id: str,
    hard_delete: bool = Query(False, description="Perform hard delete instead of soft delete"),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Delete an entity
    
    By default, performs a soft delete (marks as inactive).
    Use hard_delete=true to permanently remove the entity.
    """
    service = EntityService(session)
    success = await service.delete_entity(entity_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )


@entity_router.get(
    "/type/{entity_type}",
    response_model=EntityListResponse,
)
async def list_entities_by_type(
    entity_type: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session)
) -> EntityListResponse:
    """
    List entities filtered by type
    
    - **entity_type**: The entity type to filter by
    """
    service = EntityService(session)
    items, total = await service.list_by_type(entity_type, skip, limit)
    return EntityListResponse(items=items, total=total, skip=skip, limit=limit)


@entity_router.head(
    "/{entity_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Entity not found"},
    }
)
async def entity_exists(
    entity_id: str,
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Check if an entity exists (returns 200 if exists, 404 if not)
    """
    service = EntityService(session)
    exists = await service.entity_exists(entity_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
