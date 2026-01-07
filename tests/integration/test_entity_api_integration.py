import os
import sys
import tempfile
import socket
import asyncio
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _get_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest_asyncio.fixture(scope="session")
async def server_base_url():
    # 1) Temp SQLite file and env for app
    fd, db_path = tempfile.mkstemp(prefix="entity_it_", suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

    # 2) Start app server via uvicorn
    port = _get_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    base_url = f"http://127.0.0.1:{port}"

    # 3) Wait until the server is ready
    async with httpx.AsyncClient() as client:
        for _ in range(80):  # up to ~20s
            try:
                r = await client.get(base_url + "/healthz", timeout=1.0)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.25)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                pass
            raise RuntimeError("Server failed to become ready in time")

    yield base_url

    # 4) Teardown: stop server and remove DB file
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest_asyncio.fixture
async def client(server_base_url):
    async with httpx.AsyncClient(base_url=server_base_url) as c:
        yield c


@pytest.mark.asyncio
async def test_health_live_server(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_entity_crud_cycle(client):
    # Create
    create_resp = await client.post("/api/v1/entities", json={
        "name": "IT User",
        "entity_type": "user",
        "data": {"role": "member"}
    })
    assert create_resp.status_code == 201
    entity = create_resp.json()
    eid = entity["id"]

    # Get
    get_resp = await client.get(f"/api/v1/entities/{eid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "IT User"

    # Update
    upd_resp = await client.patch(f"/api/v1/entities/{eid}", json={"status": "inactive"})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["status"] == "inactive"

    # List
    list_resp = await client.get("/api/v1/entities?entity_type=user")
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["total"] >= 1
    assert any(item["id"] == eid for item in payload["items"])  # our entity present

    # Delete (soft)
    del_resp = await client.delete(f"/api/v1/entities/{eid}")
    assert del_resp.status_code == 204

    # Verify inactive after delete
    after_resp = await client.get(f"/api/v1/entities/{eid}")
    assert after_resp.status_code == 200
    assert after_resp.json()["is_active"] is False
