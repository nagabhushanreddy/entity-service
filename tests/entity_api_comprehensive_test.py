"""
Comprehensive tests for Entity API
Tests edge cases, error handling, data validation, and complex scenarios
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import get_session, Base
from main import app


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
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db_session):
    """Create test client with overridden session dependency."""

    async def override_get_session():
        yield test_db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


# ===== Data Validation Tests =====

@pytest.mark.asyncio
async def test_create_entity_with_all_fields(client):
    """Test creating entity with all possible fields."""
    entity_data = {
        "name": "Complete Entity",
        "entity_type": "complete",
        "description": "Entity with all fields",
        "status": "active",
        "data": {
            "nested": {
                "field": "value",
                "number": 42,
                "bool": True
            },
            "array": [1, 2, 3]
        },
        "metadata": {
            "source": "test",
            "version": "1.0",
            "tags": ["test", "complete"]
        },
        "created_by": "test_user"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Complete Entity"
    assert data["data"]["nested"]["field"] == "value"
    assert data["metadata"]["source"] == "test"
    assert len(data["metadata"]["tags"]) == 2


@pytest.mark.asyncio
async def test_create_entity_with_minimal_fields(client):
    """Test creating entity with only required fields."""
    entity_data = {
        "name": "Minimal Entity",
        "entity_type": "minimal"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Entity"
    assert data["entity_type"] == "minimal"
    assert data["status"] == "active"
    assert data["is_active"] is True
    assert data["version"] == 1


@pytest.mark.asyncio
async def test_create_entity_with_long_name(client):
    """Test entity name length validation."""
    long_name = "A" * 255
    entity_data = {
        "name": long_name,
        "entity_type": "test"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    assert response.json()["name"] == long_name


@pytest.mark.asyncio
async def test_create_entity_with_too_long_name(client):
    """Test entity name exceeds max length."""
    too_long_name = "A" * 256
    entity_data = {
        "name": too_long_name,
        "entity_type": "test"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_entity_with_unicode_characters(client):
    """Test entity with unicode characters in name and description."""
    entity_data = {
        "name": "Entity 测试 🚀",
        "entity_type": "unicode",
        "description": "Description with émojis 🎉 and spëcial çharacters"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    data = response.json()
    assert "测试" in data["name"]
    assert "🚀" in data["name"]
    assert "émojis" in data["description"]


@pytest.mark.asyncio
async def test_create_entity_with_null_optional_fields(client):
    """Test creating entity with explicit null values for optional fields."""
    entity_data = {
        "name": "Test Entity",
        "entity_type": "test",
        "description": None,
        "data": None,
        "metadata": None
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    data = response.json()
    assert data["description"] is None
    assert data["data"] is None
    assert data["metadata"] is None


# ===== Update Tests =====

@pytest.mark.asyncio
async def test_update_entity_partial(client):
    """Test partial update of entity."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Original", "entity_type": "test", "status": "active"}
    )
    entity_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"name": "Updated"}
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated"
    assert data["entity_type"] == "test"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_update_entity_multiple_times(client):
    """Test multiple updates increase version."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]
    
    for i in range(1, 4):
        update_response = await client.patch(
            f"/api/v1/entities/{entity_id}",
            json={"name": f"Version {i}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["version"] == i + 1


@pytest.mark.asyncio
async def test_update_entity_change_type(client):
    """Test changing entity type via update."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "type1"}
    )
    entity_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"entity_type": "type2"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["entity_type"] == "type2"


@pytest.mark.asyncio
async def test_update_entity_complex_data(client):
    """Test updating complex nested data structures."""
    create_response = await client.post(
        "/api/v1/entities",
        json={
            "name": "Test",
            "entity_type": "test",
            "data": {"key1": "value1"}
        }
    )
    entity_id = create_response.json()["id"]

    new_data = {
        "key1": "updated",
        "key2": {
            "nested": ["array", "of", "values"],
            "number": 123
        }
    }

    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"data": new_data}
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["data"]["key1"] == "updated"
    assert data["data"]["key2"]["nested"] == ["array", "of", "values"]


@pytest.mark.asyncio
async def test_update_entity_set_inactive(client):
    """Test setting entity as inactive via update."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"is_active": False}
    )

    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False


# ===== List and Filter Tests =====

@pytest.mark.asyncio
async def test_list_entities_empty(client):
    """Test listing entities when none exist."""
    response = await client.get("/api/v1/entities")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_list_entities_with_multiple_filters(client):
    """Test listing with multiple filter combinations."""
    # Create test data
    await client.post("/api/v1/entities", json={"name": "Active User", "entity_type": "user", "status": "active"})
    await client.post("/api/v1/entities", json={"name": "Inactive User", "entity_type": "user", "status": "inactive"})
    await client.post("/api/v1/entities", json={"name": "Active Product", "entity_type": "product", "status": "active"})

    # Filter by type and status
    response = await client.get("/api/v1/entities?entity_type=user&status=active")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Active User"


@pytest.mark.asyncio
async def test_list_entities_with_is_active_filter(client):
    """Test filtering by is_active status."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]
    
    # Soft delete the entity
    await client.delete(f"/api/v1/entities/{entity_id}")

    # Create another active entity
    await client.post("/api/v1/entities", json={"name": "Active", "entity_type": "test"})

    # Filter for active entities only
    response = await client.get("/api/v1/entities?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Active"

    # Filter for inactive entities
    response = await client.get("/api/v1/entities?is_active=false")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test"


@pytest.mark.asyncio
async def test_list_entities_pagination_edge_cases(client):
    """Test pagination edge cases."""
    # Create 5 entities
    for i in range(5):
        await client.post("/api/v1/entities", json={"name": f"Entity {i}", "entity_type": "test"})

    # Test skip beyond total
    response = await client.get("/api/v1/entities?skip=10&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 0

    # Test limit = 1
    response = await client.get("/api/v1/entities?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1

    # Test skip = total - 1
    response = await client.get("/api/v1/entities?skip=4&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_entities_max_limit(client):
    """Test that limit is capped at 1000."""
    response = await client.get("/api/v1/entities?limit=2000")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_entities_negative_skip(client):
    """Test negative skip parameter."""
    response = await client.get("/api/v1/entities?skip=-1")
    assert response.status_code == 422


# ===== Delete Tests =====

@pytest.mark.asyncio
async def test_hard_delete_entity(client):
    """Test hard delete removes entity completely."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "To Delete", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/entities/{entity_id}?hard_delete=true")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/entities/{entity_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_soft_delete_then_hard_delete(client):
    """Test soft delete followed by hard delete."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    # Soft delete
    await client.delete(f"/api/v1/entities/{entity_id}")
    get_response = await client.get(f"/api/v1/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False

    # Hard delete
    await client.delete(f"/api/v1/entities/{entity_id}?hard_delete=true")
    get_response = await client.get(f"/api/v1/entities/{entity_id}")
    assert get_response.status_code == 404


# ===== Special Character and Edge Case Tests =====

@pytest.mark.asyncio
async def test_entity_with_special_chars_in_type(client):
    """Test entity_type with allowed special characters."""
    entity_data = {
        "name": "Test",
        "entity_type": "test_type_123"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_entity_with_empty_data_object(client):
    """Test entity with empty data object."""
    entity_data = {
        "name": "Test",
        "entity_type": "test",
        "data": {}
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    assert response.json()["data"] == {}


@pytest.mark.asyncio
async def test_entity_with_very_large_data(client):
    """Test entity with large data payload."""
    large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
    entity_data = {
        "name": "Large Data Entity",
        "entity_type": "test",
        "data": large_data
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    data = response.json()
    assert len(data["data"]) == 100


# ===== Error Recovery Tests =====

@pytest.mark.asyncio
async def test_update_after_soft_delete(client):
    """Test updating entity after soft delete."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    # Soft delete
    await client.delete(f"/api/v1/entities/{entity_id}")

    # Try to update
    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"name": "Updated After Delete"}
    )
    
    # Should succeed
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated After Delete"


@pytest.mark.asyncio
async def test_reactivate_soft_deleted_entity(client):
    """Test reactivating a soft-deleted entity."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    # Soft delete
    await client.delete(f"/api/v1/entities/{entity_id}")

    # Reactivate
    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"is_active": True}
    )

    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is True


# ===== Complex Workflow Tests =====

@pytest.mark.asyncio
async def test_entity_lifecycle(client):
    """Test complete entity lifecycle."""
    # Create
    create_response = await client.post(
        "/api/v1/entities",
        json={
            "name": "Lifecycle Entity",
            "entity_type": "lifecycle",
            "status": "draft",
            "data": {"stage": "initial"}
        }
    )
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]
    assert create_response.json()["version"] == 1

    # Update to review stage
    update1 = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"status": "review", "data": {"stage": "review"}}
    )
    assert update1.status_code == 200
    assert update1.json()["version"] == 2

    # Update to approved stage
    update2 = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"status": "approved", "data": {"stage": "approved"}}
    )
    assert update2.status_code == 200
    assert update2.json()["version"] == 3

    # Verify history via version
    final = await client.get(f"/api/v1/entities/{entity_id}")
    assert final.json()["status"] == "approved"
    assert final.json()["data"]["stage"] == "approved"

    # Archive (soft delete)
    await client.delete(f"/api/v1/entities/{entity_id}")
    
    # Verify still accessible but inactive
    archived = await client.get(f"/api/v1/entities/{entity_id}")
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False


@pytest.mark.asyncio
async def test_bulk_operations(client):
    """Test creating and managing multiple entities."""
    # Bulk create
    entity_ids = []
    for i in range(10):
        response = await client.post(
            "/api/v1/entities",
            json={
                "name": f"Bulk Entity {i}",
                "entity_type": "bulk",
                "data": {"index": i}
            }
        )
        entity_ids.append(response.json()["id"])

    # Verify all created
    list_response = await client.get("/api/v1/entities?entity_type=bulk")
    assert list_response.json()["total"] == 10

    # Bulk soft delete half
    for entity_id in entity_ids[:5]:
        await client.delete(f"/api/v1/entities/{entity_id}")

    # Verify counts
    all_response = await client.get("/api/v1/entities?entity_type=bulk")
    assert all_response.json()["total"] == 10

    active_response = await client.get("/api/v1/entities?entity_type=bulk&is_active=true")
    assert active_response.json()["total"] == 5


# ===== Entity Type Specific Tests =====

@pytest.mark.asyncio
async def test_list_by_type_endpoint(client):
    """Test the type-specific listing endpoint."""
    # Create entities of different types
    await client.post("/api/v1/entities", json={"name": "User 1", "entity_type": "user"})
    await client.post("/api/v1/entities", json={"name": "User 2", "entity_type": "user"})
    await client.post("/api/v1/entities", json={"name": "Product 1", "entity_type": "product"})

    # Test type-specific endpoint
    response = await client.get("/api/v1/entities/type/user")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["entity_type"] == "user" for item in data["items"])


@pytest.mark.asyncio
async def test_list_by_nonexistent_type(client):
    """Test listing by type that doesn't exist."""
    response = await client.get("/api/v1/entities/type/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0
