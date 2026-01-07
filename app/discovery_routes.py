"""API routes for service discovery and metadata."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.dependencies import get_session
from app.entity_type_service import EntityTypeService
from app.database import _dynamic_models
from app.config import settings

discovery_router = APIRouter(prefix="/discovery", tags=["discovery"])


async def get_entity_type_service(session: AsyncSession = Depends(get_session)) -> EntityTypeService:
    """Dependency to get EntityTypeService."""
    from main import engine
    return EntityTypeService(session, engine)


@discovery_router.get("/", response_model=Dict[str, Any])
async def get_service_info() -> Dict[str, Any]:
    """
    Get service discovery information for agent/service integration.
    
    Returns service metadata, capabilities, and available endpoints.
    """
    return {
        "service": {
            "name": settings.SERVICE_NAME,
            "version": "2.0.0",
            "description": "Entity API - Dynamic entity management with type-specific tables",
            "api_version": "v1",
            "base_url": "/api/v1"
        },
        "capabilities": {
            "ddl_operations": True,
            "dml_operations": True,
            "dynamic_tables": True,
            "soft_delete": True,
            "hard_delete": True,
            "versioning": True,
            "filtering": True,
            "pagination": True,
            "bulk_operations": False
        },
        "endpoints": {
            "openapi": "/api/v1/openapi.json",
            "docs": "/api/v1/docs",
            "redoc": "/api/v1/redoc",
            "health": "/healthz",
            "discovery": "/api/v1/discovery",
            "entity_types": "/api/v1/discovery/entity-types",
            "schemas": "/api/v1/discovery/schemas"
        },
        "supported_column_types": [
            "string", "integer", "float", "boolean", "text", "json", "datetime"
        ],
        "authentication": {
            "required": False,
            "methods": []
        }
    }


@discovery_router.get("/entity-types", response_model=Dict[str, Any])
async def discover_entity_types(
    service: EntityTypeService = Depends(get_entity_type_service)
) -> Dict[str, Any]:
    """
    Discover all registered entity types and their endpoints.
    
    Returns a map of entity types to their REST endpoints and schemas.
    Useful for agents to dynamically discover available entity types.
    """
    entity_types, total = await service.list_entity_types(limit=1000)
    
    entity_type_map = {}
    for et in entity_types:
        if et.is_active:
            entity_type_map[et.entity_type] = {
                "table_name": et.table_name,
                "description": et.description,
                "endpoints": {
                    "create": f"/api/v1/{et.entity_type}",
                    "list": f"/api/v1/{et.entity_type}",
                    "get": f"/api/v1/{et.entity_type}/{{id}}",
                    "update": f"/api/v1/{et.entity_type}/{{id}}",
                    "delete": f"/api/v1/{et.entity_type}/{{id}}",
                    "exists": f"/api/v1/{et.entity_type}/{{id}}"
                },
                "methods": {
                    "create": "POST",
                    "list": "GET",
                    "get": "GET",
                    "update": "PATCH",
                    "delete": "DELETE",
                    "exists": "HEAD"
                },
                "schema_url": f"/api/v1/discovery/schemas/{et.entity_type}",
                "created_at": et.created_at.isoformat(),
                "updated_at": et.updated_at.isoformat()
            }
    
    return {
        "total": total,
        "entity_types": entity_type_map,
        "discovery_time": "2026-01-06T00:00:00Z"
    }


@discovery_router.get("/schemas", response_model=Dict[str, Any])
async def list_all_schemas(
    service: EntityTypeService = Depends(get_entity_type_service)
) -> Dict[str, Any]:
    """
    Get schemas for all registered entity types.
    
    Returns detailed schema information including column definitions,
    types, constraints, and validation rules.
    """
    entity_types, total = await service.list_entity_types(limit=1000)
    
    schemas = {}
    for et in entity_types:
        if et.is_active:
            schemas[et.entity_type] = {
                "entity_type": et.entity_type,
                "table_name": et.table_name,
                "description": et.description,
                "columns": et.schema_definition,
                "base_columns": {
                    "id": {"type": "string", "nullable": False, "description": "Unique identifier (UUID)"},
                    "is_active": {"type": "boolean", "nullable": False, "description": "Active status flag"},
                    "created_at": {"type": "datetime", "nullable": False, "description": "Creation timestamp"},
                    "updated_at": {"type": "datetime", "nullable": False, "description": "Last update timestamp"},
                    "created_by": {"type": "string", "nullable": True, "description": "Creator identifier"},
                    "updated_by": {"type": "string", "nullable": True, "description": "Last updater identifier"},
                    "version": {"type": "integer", "nullable": False, "description": "Version number for optimistic locking"}
                }
            }
    
    return {
        "total": total,
        "schemas": schemas
    }


@discovery_router.get("/schemas/{entity_type}", response_model=Dict[str, Any])
async def get_entity_type_schema(
    entity_type: str,
    service: EntityTypeService = Depends(get_entity_type_service)
) -> Dict[str, Any]:
    """
    Get detailed schema for a specific entity type.
    
    Returns column definitions, types, constraints, and examples.
    Useful for agents to understand the structure before creating entities.
    """
    et = await service.get_entity_type(entity_type)
    
    if not et:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )
    
    # Generate example payload
    example_create = {}
    for col_name, col_info in et.schema_definition.items():
        col_type = col_info["type"]
        if col_type == "string":
            example_create[col_name] = "example_string"
        elif col_type == "integer":
            example_create[col_name] = 42
        elif col_type == "float":
            example_create[col_name] = 3.14
        elif col_type == "boolean":
            example_create[col_name] = True
        elif col_type == "text":
            example_create[col_name] = "Example text content"
        elif col_type == "json":
            example_create[col_name] = {"key": "value"}
        elif col_type == "datetime":
            example_create[col_name] = "2026-01-06T10:00:00Z"
    
    return {
        "entity_type": et.entity_type,
        "table_name": et.table_name,
        "description": et.description,
        "columns": et.schema_definition,
        "base_columns": {
            "id": {"type": "string", "nullable": False, "description": "Unique identifier (UUID)"},
            "is_active": {"type": "boolean", "nullable": False, "description": "Active status flag"},
            "created_at": {"type": "datetime", "nullable": False, "description": "Creation timestamp"},
            "updated_at": {"type": "datetime", "nullable": False, "description": "Last update timestamp"},
            "created_by": {"type": "string", "nullable": True, "description": "Creator identifier"},
            "updated_by": {"type": "string", "nullable": True, "description": "Last updater identifier"},
            "version": {"type": "integer", "nullable": False, "description": "Version number"}
        },
        "required_fields": [
            col_name for col_name, col_info in et.schema_definition.items()
            if not col_info.get("nullable", True)
        ],
        "indexed_fields": [
            col_name for col_name, col_info in et.schema_definition.items()
            if col_info.get("indexed", False)
        ],
        "unique_fields": [
            col_name for col_name, col_info in et.schema_definition.items()
            if col_info.get("unique", False)
        ],
        "example_create": example_create,
        "endpoints": {
            "create": f"/api/v1/{entity_type}",
            "list": f"/api/v1/{entity_type}",
            "get": f"/api/v1/{entity_type}/{{id}}",
            "update": f"/api/v1/{entity_type}/{{id}}",
            "delete": f"/api/v1/{entity_type}/{{id}}"
        }
    }


@discovery_router.get("/operations", response_model=Dict[str, Any])
def get_supported_operations() -> Dict[str, Any]:
    """
    Get all supported DDL and DML operations.
    
    Returns detailed information about available operations,
    their HTTP methods, parameters, and response formats.
    """
    return {
        "ddl_operations": {
            "create_entity_type": {
                "method": "POST",
                "endpoint": "/api/v1/entity_type",
                "description": "Create a new entity type and table",
                "request_body": {
                    "entity_type": "string (required, lowercase, underscores)",
                    "description": "string (optional)",
                    "columns": "array of column definitions (required)",
                    "created_by": "string (optional)"
                },
                "response_code": 201
            },
            "list_entity_types": {
                "method": "GET",
                "endpoint": "/api/v1/entity_type",
                "description": "List all registered entity types",
                "query_params": ["skip", "limit", "is_active"],
                "response_code": 200
            },
            "get_entity_type": {
                "method": "GET",
                "endpoint": "/api/v1/entity_type/{entity_type}",
                "description": "Get entity type definition",
                "response_code": 200
            },
            "delete_entity_type": {
                "method": "DELETE",
                "endpoint": "/api/v1/entity_type/{entity_type}",
                "description": "Deactivate entity type (soft delete)",
                "response_code": 204
            }
        },
        "dml_operations": {
            "create_entity": {
                "method": "POST",
                "endpoint": "/api/v1/{entity_type}",
                "description": "Create a new entity instance",
                "request_body": "Dynamic based on entity type schema",
                "response_code": 201
            },
            "list_entities": {
                "method": "GET",
                "endpoint": "/api/v1/{entity_type}",
                "description": "List entity instances with filtering",
                "query_params": ["skip", "limit", "is_active"],
                "response_code": 200
            },
            "get_entity": {
                "method": "GET",
                "endpoint": "/api/v1/{entity_type}/{id}",
                "description": "Get entity instance by ID",
                "response_code": 200
            },
            "update_entity": {
                "method": "PATCH",
                "endpoint": "/api/v1/{entity_type}/{id}",
                "description": "Update entity instance (partial)",
                "request_body": "Dynamic based on entity type schema",
                "response_code": 200
            },
            "delete_entity": {
                "method": "DELETE",
                "endpoint": "/api/v1/{entity_type}/{id}",
                "description": "Delete entity instance (soft or hard)",
                "query_params": ["hard_delete"],
                "response_code": 204
            },
            "check_entity_exists": {
                "method": "HEAD",
                "endpoint": "/api/v1/{entity_type}/{id}",
                "description": "Check if entity exists",
                "response_code": 200
            }
        }
    }
