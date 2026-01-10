"""
Tests for Discovery API endpoints
Run with: pytest tests/discovery_test.py -v
"""

import pytest
from httpx import AsyncClient
from fastapi import Depends

from app.database import get_session, Base, EntityTypeDefinition, _dynamic_models
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
    
    async def override_get_entity_type_service(session: AsyncSession = Depends(get_session)):
        return EntityTypeService(session, engine)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_entity_type_service] = override_get_entity_type_service

    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

    # Clear dynamic models cache to avoid table redefinition errors
    _dynamic_models.clear()
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_entity_type(client):
    """Create a sample entity type for discovery tests."""
    entity_type_data = {
        "entity_type": "user",
        "description": "User entities for testing",
        "columns": [
            {
                "name": "email",
                "type": "string",
                "nullable": False,
                "unique": True,
                "max_length": 255,
                "description": "User email address"
            },
            {
                "name": "username",
                "type": "string",
                "nullable": False,
                "indexed": True,
                "max_length": 100,
                "description": "Username"
            },
            {
                "name": "age",
                "type": "integer",
                "nullable": True,
                "description": "User age"
            },
            {
                "name": "is_verified",
                "type": "boolean",
                "nullable": False,
                "default": False
            }
        ],
        "created_by": "test"
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 201
    return response.json()


# Service Discovery Tests
@pytest.mark.asyncio
async def test_get_service_info(client):
    """Test service discovery endpoint."""
    response = await client.get("/api/v1/discovery/")
    assert response.status_code == 200
    
    data = response.json()
    assert "service" in data
    assert data["service"]["name"] == "entity-api"
    assert data["service"]["version"] == "2.0.0"
    assert "capabilities" in data
    assert data["capabilities"]["ddl_operations"] is True
    assert data["capabilities"]["dml_operations"] is True
    assert data["capabilities"]["dynamic_tables"] is True
    assert "endpoints" in data
    assert "supported_column_types" in data
    
    # Verify supported column types
    expected_types = ["string", "integer", "float", "boolean", "text", "json", "datetime"]
    for col_type in expected_types:
        assert col_type in data["supported_column_types"]


@pytest.mark.asyncio
async def test_discover_entity_types_empty(client):
    """Test entity type discovery when no types exist."""
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 0
    assert data["entity_types"] == {}


@pytest.mark.asyncio
async def test_discover_entity_types_with_data(client, sample_entity_type):
    """Test entity type discovery with existing entity types."""
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert "user" in data["entity_types"]
    
    user_type = data["entity_types"]["user"]
    assert user_type["table_name"] == "entity_user"
    assert user_type["description"] == "User entities for testing"
    
    # Verify endpoints are present
    assert "endpoints" in user_type
    assert user_type["endpoints"]["create"] == "/api/v1/user"
    assert user_type["endpoints"]["list"] == "/api/v1/user"
    assert user_type["endpoints"]["get"] == "/api/v1/user/{id}"
    assert user_type["endpoints"]["update"] == "/api/v1/user/{id}"
    assert user_type["endpoints"]["delete"] == "/api/v1/user/{id}"
    
    # Verify HTTP methods
    assert "methods" in user_type
    assert user_type["methods"]["create"] == "POST"
    assert user_type["methods"]["list"] == "GET"
    assert user_type["methods"]["update"] == "PATCH"
    assert user_type["methods"]["delete"] == "DELETE"


@pytest.mark.asyncio
async def test_discover_schemas_all(client, sample_entity_type):
    """Test discovering all schemas."""
    response = await client.get("/api/v1/discovery/schemas")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert "schemas" in data
    assert "user" in data["schemas"]
    
    user_schema = data["schemas"]["user"]
    assert user_schema["entity_type"] == "user"
    assert user_schema["table_name"] == "entity_user"
    assert "columns" in user_schema
    assert "base_columns" in user_schema
    
    # Verify base columns are documented
    assert "id" in user_schema["base_columns"]
    assert "is_active" in user_schema["base_columns"]
    assert "created_at" in user_schema["base_columns"]
    assert "version" in user_schema["base_columns"]


@pytest.mark.asyncio
async def test_discover_specific_schema(client, sample_entity_type):
    """Test discovering schema for a specific entity type."""
    response = await client.get("/api/v1/discovery/schemas/user")
    assert response.status_code == 200
    
    data = response.json()
    assert data["entity_type"] == "user"
    assert data["table_name"] == "entity_user"
    assert data["description"] == "User entities for testing"
    
    # Verify columns
    assert "columns" in data
    assert "email" in data["columns"]
    assert data["columns"]["email"]["type"] == "string"
    assert data["columns"]["email"]["nullable"] is False
    assert data["columns"]["email"]["unique"] is True
    
    # Verify required fields
    assert "required_fields" in data
    assert "email" in data["required_fields"]
    assert "username" in data["required_fields"]
    assert "age" not in data["required_fields"]  # nullable
    
    # Verify unique fields
    assert "unique_fields" in data
    assert "email" in data["unique_fields"]
    
    # Verify indexed fields
    assert "indexed_fields" in data
    assert "username" in data["indexed_fields"]
    
    # Verify example payload
    assert "example_create" in data
    assert "email" in data["example_create"]
    assert "username" in data["example_create"]
    
    # Verify endpoints
    assert "endpoints" in data
    assert data["endpoints"]["create"] == "/api/v1/user"


@pytest.mark.asyncio
async def test_discover_nonexistent_schema(client):
    """Test discovering schema for non-existent entity type."""
    response = await client.get("/api/v1/discovery/schemas/nonexistent")
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data
    assert "nonexistent" in data["detail"]


@pytest.mark.asyncio
async def test_discover_operations(client):
    """Test discovering supported operations."""
    response = await client.get("/api/v1/discovery/operations")
    assert response.status_code == 200
    
    data = response.json()
    assert "ddl_operations" in data
    assert "dml_operations" in data
    
    # Verify DDL operations
    ddl_ops = data["ddl_operations"]
    assert "create_entity_type" in ddl_ops
    assert "list_entity_types" in ddl_ops
    assert "get_entity_type" in ddl_ops
    assert "delete_entity_type" in ddl_ops
    
    # Verify create_entity_type details
    create_op = ddl_ops["create_entity_type"]
    assert create_op["method"] == "POST"
    assert create_op["endpoint"] == "/api/v1/entity_type"
    assert "description" in create_op
    assert create_op["response_code"] == 201
    
    # Verify DML operations
    dml_ops = data["dml_operations"]
    assert "create_entity" in dml_ops
    assert "list_entities" in dml_ops
    assert "get_entity" in dml_ops
    assert "update_entity" in dml_ops
    assert "delete_entity" in dml_ops
    assert "check_entity_exists" in dml_ops
    
    # Verify create_entity details
    create_entity_op = dml_ops["create_entity"]
    assert create_entity_op["method"] == "POST"
    assert create_entity_op["endpoint"] == "/api/v1/{entity_type}"
    assert create_entity_op["response_code"] == 201


# Integration Tests - Full Discovery Flow
@pytest.mark.asyncio
async def test_full_discovery_flow(client):
    """Test complete discovery flow: service -> entity types -> schemas -> operations."""
    
    # Step 1: Discover service
    response = await client.get("/api/v1/discovery/")
    assert response.status_code == 200
    service_info = response.json()
    assert service_info["service"]["name"] == "entity-api"
    
    # Step 2: Create an entity type via DDL
    entity_type_data = {
        "entity_type": "product",
        "description": "Product catalog",
        "columns": [
            {"name": "name", "type": "string", "nullable": False, "max_length": 255},
            {"name": "price", "type": "float", "nullable": False},
            {"name": "stock", "type": "integer", "nullable": False, "default": 0}
        ],
        "created_by": "discovery_test"
    }
    
    response = await client.post("/api/v1/entity_type", json=entity_type_data)
    assert response.status_code == 201
    
    # Step 3: Discover entity types
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    entity_types = response.json()
    assert "product" in entity_types["entity_types"]
    
    # Step 4: Get product schema
    response = await client.get("/api/v1/discovery/schemas/product")
    assert response.status_code == 200
    schema = response.json()
    assert schema["entity_type"] == "product"
    assert "name" in schema["columns"]
    assert "price" in schema["columns"]
    
    # Step 5: Use discovered endpoint to create entity
    create_endpoint = schema["endpoints"]["create"]
    example_data = {
        "name": "Test Product",
        "price": 29.99,
        "stock": 100,
        "created_by": "discovery_test"
    }
    
    response = await client.post(create_endpoint, json=example_data)
    assert response.status_code == 201
    product = response.json()
    assert product["name"] == "Test Product"
    assert product["price"] == 29.99
    
    # Step 6: List entities using discovered endpoint
    list_endpoint = schema["endpoints"]["list"]
    response = await client.get(list_endpoint)
    assert response.status_code == 200
    products = response.json()
    assert products["total"] == 1


@pytest.mark.asyncio
async def test_schema_example_payload_accuracy(client, sample_entity_type):
    """Test that example payloads in schema are valid for creating entities."""
    
    # Get schema with example
    response = await client.get("/api/v1/discovery/schemas/user")
    assert response.status_code == 200
    schema = response.json()
    
    # Use the example payload to create an entity
    example = schema["example_create"]
    example["email"] = "test@example.com"  # Make it unique
    example["username"] = "testuser"
    example["created_by"] = "test"
    
    create_endpoint = schema["endpoints"]["create"]
    response = await client.post(create_endpoint, json=example)
    assert response.status_code == 201
    
    created = response.json()
    assert created["email"] == "test@example.com"
    assert created["username"] == "testuser"


@pytest.mark.asyncio
async def test_multiple_entity_types_discovery(client):
    """Test discovery with multiple entity types."""
    
    # Create multiple entity types
    types_to_create = [
        {
            "entity_type": "user",
            "description": "Users",
            "columns": [{"name": "email", "type": "string", "nullable": False}]
        },
        {
            "entity_type": "product",
            "description": "Products",
            "columns": [{"name": "name", "type": "string", "nullable": False}]
        },
        {
            "entity_type": "order",
            "description": "Orders",
            "columns": [{"name": "order_id", "type": "string", "nullable": False}]
        }
    ]
    
    for entity_type_data in types_to_create:
        response = await client.post("/api/v1/entity_type", json=entity_type_data)
        assert response.status_code == 201
    
    # Discover all entity types
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 3
    assert "user" in data["entity_types"]
    assert "product" in data["entity_types"]
    assert "order" in data["entity_types"]
    
    # Verify each has proper endpoints
    for entity_type in ["user", "product", "order"]:
        et_info = data["entity_types"][entity_type]
        assert et_info["endpoints"]["create"] == f"/api/v1/{entity_type}"
        assert et_info["endpoints"]["list"] == f"/api/v1/{entity_type}"
