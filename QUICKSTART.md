"""
Quick Setup Guide for Entity API

Run these commands to get started:

## 1. Install Dependencies
```bash
cd services/entity-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Run Locally
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8003
```

## 3. Access API Documentation
- Swagger UI: http://localhost:8003/api/v1/docs
- ReDoc: http://localhost:8003/api/v1/redoc

## 4. Run with Docker Compose
```bash
docker-compose up
```

## 5. Run Tests
```bash
pip install pytest pytest-asyncio
pytest tests -v
```

Test coverage:
- Discovery endpoints: `pytest tests/discovery_test.py -v`
- Entity type DDL: `pytest tests/entity_type_test.py -v`

## 6. Try the Agent Discovery Example
```bash
python agent_discovery_example.py
```

This demonstrates how agents can discover and use the API dynamically.
Copy `app/client.py` to your service and:

```python
from app.client import EntityAPIClientSync

with EntityAPIClientSync(base_url="http://entity-api:8003") as client:
    entity = client.create_entity(
        name="My Entity",
        entity_type="example"
    )
```

## Production Checklist
- [ ] Configure PostgreSQL database
- [ ] Set environment variables (.env file)
- [ ] Enable HTTPS
- [ ] Add authentication
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Load testing
"""
