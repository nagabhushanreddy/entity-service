
"""
Tests for Discovery API endpoints
Run with: pytest tests/discovery_test.py -v
Or run directly: python tests/discovery_test.py [options]

Options when running directly:
    all              - Run all tests (including skipped)
    isolation        - Run only non-isolation tests
    skipped          - Run only skipped tests
    service          - Run service discovery tests
    entities         - Run entity type discovery tests
    operations       - Run operations discovery tests
    integration      - Run integration tests
    [pattern]        - Run tests matching pattern (e.g., 'test_get_service')
"""

import os
import sys
from helper import bootstrap, select_and_run
bootstrap()

import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import Depends
from app.database import get_session, Base, EntityTypeDefinition, _dynamic_models
from main import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def client(test_db_session):
    """Create test client with overridden session dependency."""
    from app.routes.entity_type_routes import get_entity_type_service
    from app.services import EntityTypeService
    from app.database import _dynamic_models, Base
    
    # Note: We don't clear _dynamic_models here because models should persist
    # across tests to avoid SQLAlchemy Base registry conflicts
    
    session, engine = test_db_session

    async def override_get_session():
        yield session

    async def override_get_entity_type_service(session: AsyncSession = Depends(get_session)):
        return EntityTypeService(session, engine)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_entity_type_service] = override_get_entity_type_service

    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

    # Don't clear dynamic models - let them persist across tests
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_entity_type(client, test_db_session):
    """Create a sample entity type for discovery tests."""
    session, engine = test_db_session
    
    # Check if the entity type model already exists in _dynamic_models from a previous test
    # This prevents SQLAlchemy errors when trying to recreate the same model class
    if "discovery_user" in _dynamic_models:
        # Model exists, check if DB record exists in current test's database
        check_response = await client.get("/api/v1/entity_type")
        if check_response.status_code == 200:
            entity_types = check_response.json()
            if "discovery_user" in entity_types:
                # Both model and DB record exist, fetch details
                detail_response = await client.get("/api/v1/entity_type/discovery_user")
                if detail_response.status_code == 200:
                    return detail_response.json()
        
        # Model exists but not in current test's DB
        # Manually insert the EntityTypeDefinition record
        from app.database import EntityTypeDefinition
        from datetime import datetime
        
        entity_type_def = EntityTypeDefinition(
            entity_type="discovery_user",
            table_name="entity_discovery_user",
            schema_definition={
                "email": {
                    "type": "string",
                    "nullable": False,
                    "unique": True,
                    "max_length": 255,
                    "description": "User email address"
                },
                "username": {
                    "type": "string",
                    "nullable": False,
                    "indexed": True,
                    "max_length": 100,
                    "description": "Username"
                },
                "age": {
                    "type": "integer",
                    "nullable": True,
                    "description": "User age"
                },
                "is_verified": {
                    "type": "boolean",
                    "nullable": False,
                    "default": False
                }
            },
            description="User entities for testing",
            is_active=True,
            created_by="test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(entity_type_def)
        await session.commit()
        await session.refresh(entity_type_def)
        
        return {
            "entity_type": entity_type_def.entity_type,
            "table_name": entity_type_def.table_name,
            "description": entity_type_def.description,
            "is_active": entity_type_def.is_active,
            "created_by": entity_type_def.created_by
        }
    
    # Create new entity type (model and DB record via API)
    entity_type_data = {
        "entity_type": "discovery_user",
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
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_get_service_info(client):
    """Test service discovery endpoint."""
    response = await client.get("/api/v1/discovery/")
    assert response.status_code == 200
    
    data = response.json()
    assert "service" in data
    assert data["service"]["name"] == "entity-service"
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


@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_discover_entity_types_empty(client):
    """Test entity type discovery when no types exist."""
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 0
    assert data["entity_types"] == {}


@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_discover_entity_types_with_data(client, sample_entity_type):
    """Test entity type discovery with existing entity types."""
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] >= 1
    assert "discovery_user" in data["entity_types"]
    
    user_type = data["entity_types"]["discovery_user"]
    assert user_type["table_name"] == "entity_discovery_user"
    assert user_type["description"] == "User entities for testing"
    
    # Verify endpoints are present
    assert "endpoints" in user_type
    assert user_type["endpoints"]["create"] == "/api/v1/discovery_user"
    assert user_type["endpoints"]["list"] == "/api/v1/discovery_user"
    assert user_type["endpoints"]["get"] == "/api/v1/discovery_user/{id}"
    assert user_type["endpoints"]["update"] == "/api/v1/discovery_user/{id}"
    assert user_type["endpoints"]["delete"] == "/api/v1/discovery_user/{id}"
    
    # Verify HTTP methods
    assert "methods" in user_type
    assert user_type["methods"]["create"] == "POST"
    assert user_type["methods"]["list"] == "GET"
    assert user_type["methods"]["update"] == "PATCH"
    assert user_type["methods"]["delete"] == "DELETE"


@pytest.mark.order(6)
@pytest.mark.asyncio
async def test_discover_schemas_all(client, sample_entity_type):
    """Test discovering all schemas."""
    response = await client.get("/api/v1/discovery/schemas")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert "schemas" in data
    assert "discovery_user" in data["schemas"]
    
    user_schema = data["schemas"]["discovery_user"]
    assert user_schema["entity_type"] == "discovery_user"
    assert user_schema["table_name"] == "entity_discovery_user"
    assert "columns" in user_schema
    assert "base_columns" in user_schema
    
    # Verify base columns are documented
    assert "id" in user_schema["base_columns"]
    assert "is_active" in user_schema["base_columns"]
    assert "created_at" in user_schema["base_columns"]
    assert "version" in user_schema["base_columns"]


@pytest.mark.order(7)
@pytest.mark.asyncio
async def test_discover_specific_schema(client, sample_entity_type):
    """Test discovering schema for a specific entity type."""
    response = await client.get("/api/v1/discovery/schemas/discovery_user")
    assert response.status_code == 200
    
    data = response.json()
    assert data["entity_type"] == "discovery_user"
    assert data["table_name"] == "entity_discovery_user"
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
    assert data["endpoints"]["create"] == "/api/v1/discovery_user"


# @pytest.mark.skip(reason="Test isolation issues with fixture setup")
@pytest.mark.order(4)
@pytest.mark.asyncio
async def test_discover_nonexistent_schema(client):
    """Test discovering schema for non-existent entity type."""
    response = await client.get("/api/v1/discovery/schemas/nonexistent")
    assert response.status_code == 404
    
    data = response.json()
    assert "error" in data
    assert "nonexistent" in data["error"]["message"]


@pytest.mark.order(5)
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
@pytest.mark.order(8)
@pytest.mark.asyncio
async def test_full_discovery_flow(client):
    """Test complete discovery flow: service -> entity types -> schemas -> operations."""
    from app.routes import get_dynamic_router
    from main import app
    from app.config import settings
    
    # Step 1: Discover service
    response = await client.get("/api/v1/discovery/")
    assert response.status_code == 200
    service_info = response.json()
    assert service_info["service"]["name"] == "entity-service"
    
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
    
    # Manually register the dynamic router (since tests don't restart the app)
    product_router = get_dynamic_router("product")
    app.include_router(product_router, prefix=settings.API_PREFIX)
    
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


@pytest.mark.order(9)
@pytest.mark.asyncio
async def test_schema_example_payload_accuracy(client, sample_entity_type):
    """Test that example payloads in schema are valid for creating entities."""
    from app.routes import get_dynamic_router
    from main import app
    from app.config import settings
    
    # Register dynamic router for discovery_user entity type
    if "discovery_user" in _dynamic_models:
        user_router = get_dynamic_router("discovery_user")
        app.include_router(user_router, prefix=settings.API_PREFIX)
    
    # Get schema with example
    response = await client.get("/api/v1/discovery/schemas/discovery_user")
    assert response.status_code == 200
    schema = response.json()
    
    # Use the example payload to create an entity
    example = schema["example_create"]
    example["email"] = "test@example.com"  # Make it unique
    example["username"] = "testuser"
    example["created_by"] = "test"
    
    create_endpoint = schema["endpoints"]["create"]
    # Add X-Requestor-Id header to match the owner of the entity type
    response = await client.post(create_endpoint, json=example, headers={"X-Requestor-Id": "test"})
    assert response.status_code == 201
    
    created = response.json()
    assert created["email"] == "test@example.com"
    assert created["username"] == "testuser"


@pytest.mark.order(10)
@pytest.mark.asyncio
async def test_multiple_entity_types_discovery(client):
    """Test discovery with multiple entity types."""
    from app.routes import get_dynamic_router
    from main import app
    from app.config import settings
    
    # Create multiple entity types
    types_to_create = [
        {
            "entity_type": "test_user",
            "description": "Users",
            "columns": [{"name": "email", "type": "string", "nullable": False}],
            "created_by": "test"
        },
        {
            "entity_type": "test_product",
            "description": "Products",
            "columns": [{"name": "name", "type": "string", "nullable": False}],
            "created_by": "test"
        },
        {
            "entity_type": "test_order",
            "description": "Orders",
            "columns": [{"name": "order_id", "type": "string", "nullable": False}],
            "created_by": "test"
        }
    ]
    
    for entity_type_data in types_to_create:
        response = await client.post("/api/v1/entity_type", json=entity_type_data)
        assert response.status_code == 201
        
        # Register dynamic router for each created entity type
        entity_type_name = entity_type_data["entity_type"]
        entity_router = get_dynamic_router(entity_type_name)
        app.include_router(entity_router, prefix=settings.API_PREFIX)
    
    # Discover all entity types
    response = await client.get("/api/v1/discovery/entity-types")
    assert response.status_code == 200
    
    data = response.json()
    # Should have at least 3 (might have more from previous tests due to _dynamic_models persistence)
    assert data["total"] >= 3
    assert "test_user" in data["entity_types"]
    assert "test_product" in data["entity_types"]
    assert "test_order" in data["entity_types"]
    
    # Verify each has proper endpoints
    for entity_type in ["test_user", "test_product", "test_order"]:
        et_info = data["entity_types"][entity_type]
        assert et_info["endpoints"]["create"] == f"/api/v1/{entity_type}"
        assert et_info["endpoints"]["list"] == f"/api/v1/{entity_type}"


if __name__ == "__main__":
    # Delegate to helper-runner with selectors or flags
    select_and_run(__file__, sys.argv[1:])
