"""
Tests for Entity Type DDL operations
Run with: pytest tests/entity_type_test.py -v
"""

import pytest
from httpx import AsyncClient

from app.database import get_session, Base, _dynamic_models
from main import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


@pytest.fixture
async def test_db_session():
    """Create test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_local = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_local() as session:
        yield session, engine

    await engine.dispose()


@pytest.fixture
async def client(test_db_session):
    """Create test client with overridden session dependency."""
    session, engine = test_db_session

    async def override_get_session():
        yield session

    from app.routes.entity_type_routes import get_entity_type_service
    from app.services import EntityTypeService
    from app.database import _dynamic_models, Base
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def override_get_entity_type_service(session: AsyncSession = Depends(get_session)):
        return EntityTypeService(session, engine)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_entity_type_service] = override_get_entity_type_service

    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

    # Clear dynamic models cache to avoid table redefinition errors
    _dynamic_models.clear()
    app.dependency_overrides.clear()


# Entity Type Creation Tests
@pytest.mark.asyncio
async def test_create_entity_type(client):
    """Test creating a new entity type."""
    entity_type_data = {
        "entity_type": "user",
        "description": "User entities",
        "columns": [
            {
                "name": "email",
                "type": "string",
                "nullable": False,
                "unique": True,
                "max_length": 255
            },
            {
                "name": "username",
                "type": "string",
                "nullable": False,
                "indexed": True,
                "max_length": 100
            }
        ],
        "created_by": "test"
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["entity_type"] == "user"
    assert data["table_name"] == "entity_user"
    assert data["description"] == "User entities"
    assert data["is_active"] is True
    assert "email" in data["schema_definition"]
    assert "username" in data["schema_definition"]


@pytest.mark.asyncio
async def test_create_entity_type_with_all_column_types(client):
    """Test creating entity type with all supported column types."""
    entity_type_data = {
        "entity_type": "test_types",
        "description": "Test all column types",
        "columns": [
            {"name": "str_col", "type": "string", "nullable": False, "max_length": 50},
            {"name": "int_col", "type": "integer", "nullable": False},
            {"name": "float_col", "type": "float", "nullable": True},
            {"name": "bool_col", "type": "boolean", "nullable": False, "default": False},
            {"name": "text_col", "type": "text", "nullable": True},
            {"name": "json_col", "type": "json", "nullable": True},
            {"name": "datetime_col", "type": "datetime", "nullable": True}
        ],
        "created_by": "test"
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 201
    
    data = response.json()
    schema = data["schema_definition"]
    assert schema["str_col"]["type"] == "string"
    assert schema["int_col"]["type"] == "integer"
    assert schema["float_col"]["type"] == "float"
    assert schema["bool_col"]["type"] == "boolean"
    assert schema["text_col"]["type"] == "text"
    assert schema["json_col"]["type"] == "json"
    assert schema["datetime_col"]["type"] == "datetime"


@pytest.mark.asyncio
async def test_create_duplicate_entity_type(client):
    """Test creating duplicate entity type fails."""
    entity_type_data = {
        "entity_type": "user",
        "columns": [
            {"name": "email", "type": "string", "nullable": False}
        ]
    }
    
    # Create first time
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 201
    
    # Try to create again
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_entity_type_invalid_name(client):
    """Test creating entity type with invalid name."""
    entity_type_data = {
        "entity_type": "User-Type",  # Invalid: uppercase and hyphen
        "columns": [
            {"name": "email", "type": "string", "nullable": False}
        ]
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_entity_type_no_columns(client):
    """Test creating entity type without columns fails."""
    entity_type_data = {
        "entity_type": "empty",
        "columns": []
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 422  # Validation error


# Entity Type Retrieval Tests
@pytest.mark.asyncio
async def test_list_entity_types_empty(client):
    """Test listing entity types when none exist."""
    response = await client.get("/api/v1/entity_type")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_entity_types(client):
    """Test listing entity types."""
    # Create multiple entity types
    for i in range(3):
        entity_type_data = {
            "entity_type": f"type_{i}",
            "columns": [
                {"name": "field", "type": "string", "nullable": False}
            ]
        }
        await client.post("/api/v1/entity_type", json=entity_type_data)
    
    response = await client.get("/api/v1/entity_type")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_entity_types_with_pagination(client):
    """Test listing entity types with pagination."""
    # Create 5 entity types
    for i in range(5):
        entity_type_data = {
            "entity_type": f"type_{i}",
            "columns": [
                {"name": "field", "type": "string", "nullable": False}
            ]
        }
        await client.post("/api/v1/entity_type", json=entity_type_data)
    
    # Get first 2
    response = await client.get("/api/v1/entity_type?skip=0&limit=2")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_entity_type(client):
    """Test getting a specific entity type."""
    # Create entity type
    entity_type_data = {
        "entity_type": "user",
        "description": "User type",
        "columns": [
            {"name": "email", "type": "string", "nullable": False}
        ]
    }
    await client.post("/api/v1/entity_type", json=entity_type_data)
    
    # Get it
    response = await client.get("/api/v1/entity_type/user")
    assert response.status_code == 200
    
    data = response.json()
    assert data["entity_type"] == "user"
    assert data["description"] == "User type"
    assert "email" in data["schema_definition"]


@pytest.mark.asyncio
async def test_get_nonexistent_entity_type(client):
    """Test getting non-existent entity type."""
    response = await client.get("/api/v1/entity_type/nonexistent")
    assert response.status_code == 404


# Entity Type Deletion Tests
@pytest.mark.asyncio
async def test_delete_entity_type(client):
    """Test deleting (deactivating) an entity type."""
    # Create entity type
    entity_type_data = {
        "entity_type": "user",
        "columns": [
            {"name": "email", "type": "string", "nullable": False}
        ]
    }
    await client.post("/api/v1/entity_type", json=entity_type_data)
    
    # Delete it
    response = await client.delete("/api/v1/entity_type/user")
    assert response.status_code == 204
    
    # Verify it's deactivated (still exists but inactive)
    response = await client.get("/api/v1/entity_type/user")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_nonexistent_entity_type(client):
    """Test deleting non-existent entity type."""
    response = await client.delete("/api/v1/entity_type/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_only_active_entity_types(client):
    """Test listing only active entity types."""
    # Create two entity types
    for i in range(2):
        entity_type_data = {
            "entity_type": f"type_{i}",
            "columns": [
                {"name": "field", "type": "string", "nullable": False}
            ]
        }
        await client.post("/api/v1/entity_type", json=entity_type_data)
    
    # Delete one
    await client.delete("/api/v1/entity_type/type_0")
    
    # List only active
    response = await client.get("/api/v1/entity_type?is_active=true")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["entity_type"] == "type_1"


# Column Constraint Tests
@pytest.mark.asyncio
async def test_column_constraints(client):
    """Test that column constraints are properly stored."""
    entity_type_data = {
        "entity_type": "constrained",
        "columns": [
            {
                "name": "unique_field",
                "type": "string",
                "nullable": False,
                "unique": True,
                "max_length": 50
            },
            {
                "name": "indexed_field",
                "type": "string",
                "nullable": True,
                "indexed": True,
                "max_length": 100
            },
            {
                "name": "default_field",
                "type": "integer",
                "nullable": False,
                "default": 42
            }
        ]
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 201
    
    data = response.json()
    schema = data["schema_definition"]
    
    # Verify unique constraint
    assert schema["unique_field"]["unique"] is True
    assert schema["unique_field"]["max_length"] == 50
    
    # Verify index
    assert schema["indexed_field"]["indexed"] is True
    
    # Verify default value
    assert schema["default_field"]["default"] == 42
