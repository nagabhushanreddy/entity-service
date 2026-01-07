"""API routes for entity type management (DDL operations)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.dependencies import get_session
from app.entity_type_service import EntityTypeService
from app.schemas import (
    EntityTypeCreate,
    EntityTypeResponse,
    EntityTypeListResponse,
    ErrorResponse
)
from app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

entity_type_router = APIRouter(prefix="/entity_type", tags=["entity-types-ddl"])


async def get_entity_type_service(session: AsyncSession = Depends(get_session)) -> EntityTypeService:
    """Dependency to get EntityTypeService with engine access."""
    from main import engine
    return EntityTypeService(session, engine)


@entity_type_router.post(
    "",
    response_model=EntityTypeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input or entity type already exists"},
    }
)
async def create_entity_type(
    entity_type_data: EntityTypeCreate,
    service: EntityTypeService = Depends(get_entity_type_service)
) -> EntityTypeResponse:
    """
    Create a new entity type and its table (DDL operation).
    
    - **entity_type**: Name of the entity type (e.g., 'user', 'product')
    - **description**: Optional description
    - **columns**: List of column definitions for the table
    - **created_by**: User creating the entity type
    
    Example:
    ```json
    {
        "entity_type": "user",
        "description": "User entities",
        "columns": [
            {"name": "email", "type": "string", "nullable": false, "unique": true, "max_length": 255},
            {"name": "username", "type": "string", "nullable": false, "indexed": true, "max_length": 100},
            {"name": "age", "type": "integer", "nullable": true}
        ],
        "created_by": "admin"
    }
    ```
    """
    try:
        return await service.create_entity_type(entity_type_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@entity_type_router.get(
    "",
    response_model=EntityTypeListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
    }
)
async def list_entity_types(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    service: EntityTypeService = Depends(get_entity_type_service)
) -> EntityTypeListResponse:
    """
    List all registered entity types.
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Number of records to return (max 1000)
    - **is_active**: Filter by active status
    """
    items, total = await service.list_entity_types(skip=skip, limit=limit, is_active=is_active)
    return EntityTypeListResponse(items=items, total=total)


@entity_type_router.get(
    "/{entity_type}",
    response_model=EntityTypeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Entity type not found"},
    }
)
async def get_entity_type(
    entity_type: str,
    service: EntityTypeService = Depends(get_entity_type_service)
) -> EntityTypeResponse:
    """Get a specific entity type definition."""
    result = await service.get_entity_type(entity_type)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )
    return result


@entity_type_router.delete(
    "/{entity_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Entity type not found"},
    }
)
async def delete_entity_type(
    entity_type: str,
    service: EntityTypeService = Depends(get_entity_type_service)
) -> None:
    """
    Deactivate an entity type (soft delete).
    
    Note: This marks the entity type as inactive but does not drop the table.
    """
    success = await service.delete_entity_type(entity_type)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )
