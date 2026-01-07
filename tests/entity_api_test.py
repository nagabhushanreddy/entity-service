"""
Tests for Entity API
Run with: pytest tests/ -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.dependencies import get_session
from app.database import Base
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


# Health Check Tests
@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# Entity Creation Tests
@pytest.mark.asyncio
async def test_create_entity(client):
    """Test creating an entity."""
    entity_data = {
        "name": "Test Entity",
        "entity_type": "test",
        "description": "A test entity",
        "status": "active",
        "data": {"key": "value"},
        "created_by": "test_user"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Entity"
    assert data["entity_type"] == "test"
    assert data["id"] is not None
    assert data["version"] == 1


@pytest.mark.asyncio
async def test_create_entity_missing_required_field(client):
    """Test creating entity with missing required field."""
    entity_data = {
        "entity_type": "test"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_entity_empty_name(client):
    """Test creating entity with empty name."""
    entity_data = {
        "name": "",
        "entity_type": "test"
    }

    response = await client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 422


# Entity Retrieval Tests
@pytest.mark.asyncio
async def test_get_entity(client):
    """Test retrieving an entity."""
    create_response = await client.post(
        "/api/v1/entities",
        json={
            "name": "Test Entity",
            "entity_type": "test"
        }
    )
    entity_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/entities/{entity_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entity_id
    assert data["name"] == "Test Entity"


@pytest.mark.asyncio
async def test_get_nonexistent_entity(client):
    """Test retrieving non-existent entity."""
    response = await client.get("/api/v1/entities/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_entities(client):
    """Test listing entities."""
    for i in range(3):
        await client.post(
            "/api/v1/entities",
            json={
                "name": f"Entity {i}",
                "entity_type": "test"
            }
        )

    response = await client.get("/api/v1/entities")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_entities_with_pagination(client):
    """Test listing entities with pagination."""
    for i in range(5):
        await client.post(
            "/api/v1/entities",
            json={
                "name": f"Entity {i}",
                "entity_type": "test"
            }
        )

    response = await client.get("/api/v1/entities?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["skip"] == 0
    assert data["limit"] == 2


@pytest.mark.asyncio
async def test_list_entities_with_type_filter(client):
    """Test listing entities with type filter."""
    await client.post("/api/v1/entities", json={"name": "User 1", "entity_type": "user"})
    await client.post("/api/v1/entities", json={"name": "Product 1", "entity_type": "product"})

    response = await client.get("/api/v1/entities?entity_type=user")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["entity_type"] == "user"


@pytest.mark.asyncio
async def test_list_entities_by_type(client):
    """Test listing entities by type endpoint."""
    await client.post("/api/v1/entities", json={"name": "User 1", "entity_type": "user"})
    await client.post("/api/v1/entities", json={"name": "User 2", "entity_type": "user"})

    response = await client.get("/api/v1/entities/type/user")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


# Entity Update Tests
@pytest.mark.asyncio
async def test_update_entity(client):
    """Test updating an entity."""
    create_response = await client.post(
        "/api/v1/entities",
        json={
            "name": "Original Name",
            "entity_type": "test",
            "status": "active"
        }
    )
    entity_id = create_response.json()["id"]
    original_version = create_response.json()["version"]

    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={
            "name": "Updated Name",
            "status": "inactive"
        }
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Name"
    assert data["status"] == "inactive"
    assert data["version"] == original_version + 1


@pytest.mark.asyncio
async def test_update_nonexistent_entity(client):
    """Test updating non-existent entity."""
    response = await client.patch(
        "/api/v1/entities/nonexistent",
        json={"name": "New Name"}
    )
    assert response.status_code == 404


# Entity Deletion Tests
@pytest.mark.asyncio
async def test_soft_delete_entity(client):
    """Test soft delete (mark as inactive)."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/entities/{entity_id}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(client):
    """Test deleting non-existent entity."""
    response = await client.delete("/api/v1/entities/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_head_entity_exists(client):
    """Test HEAD endpoint for entity existence."""
    create_response = await client.post(
        "/api/v1/entities",
        json={"name": "Test", "entity_type": "test"}
    )
    entity_id = create_response.json()["id"]

    response = await client.head(f"/api/v1/entities/{entity_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_head_entity_not_found(client):
    """Test HEAD endpoint for non-existent entity."""
    response = await client.head("/api/v1/entities/nonexistent")
    assert response.status_code == 404


# Integration Tests
@pytest.mark.asyncio
async def test_full_crud_cycle(client):
    """Test complete CRUD cycle."""
    create_response = await client.post(
        "/api/v1/entities",
        json={
            "name": "Test Entity",
            "entity_type": "test",
            "data": {"status": "new"}
        }
    )
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]

    get_response = await client.get(f"/api/v1/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Entity"

    update_response = await client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"data": {"status": "updated"}}
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "updated"

    delete_response = await client.delete(f"/api/v1/entities/{entity_id}")
    assert delete_response.status_code == 204
