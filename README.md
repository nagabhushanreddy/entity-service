# Entity Service

A FastAPI-based microservice for dynamic entity management with schema-driven CRUD operations, requestor-based ownership, and full OpenAPI compliance.

## Quick Start

### Prerequisites
- Python 3.9+
- pip or poetry

### Local Development

```bash
# Clone and navigate to the service
cd services/entity-service

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (includes utils-service in editable mode)
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Run the service
python ./main.py
```

The API will be available at `http://localhost:8003`

### OpenAPI Documentation
- Interactive Swagger UI: `http://localhost:8003/api/v1/docs`
- ReDoc: `http://localhost:8003/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8003/api/v1/openapi.json`

---

## Architecture

### Project Structure

```
entity-service/
├── main.py                    # FastAPI application entry point with lifespan, dynamic routing
├── requirements.txt           # Python dependencies (includes utils-service -e)
├── requirements-dev.txt       # Development dependencies (pytest, black, mypy, etc.)
├── .env.example               # Environment variables template
├── config/                    # Configuration directory (loaded at startup)
│   ├── app.json              # API metadata: version, prefix (/api/${version}), project name, port
│   ├── database.json         # Database connection settings (SQLite default)
│   ├── logging.json          # Logging config (console + rotating file/error handlers)
│   ├── paths.json            # Service paths (logs/, data/ auto-created)
│   └── README.md             # Config usage and environment override patterns
├── app/
│   ├── __init__.py
│   ├── config.py             # Config loader: utils-service preferred → local JSON fallback
│   ├── schemas.py            # Pydantic models (StandardResponse wrapper, error schemas, etc.)
│   ├── exceptions.py         # Custom exceptions (EntityTypeExists, RequestorMismatch, etc.)
│   ├── middleware.py         # Request context middleware (X-Requestor-Id, correlation ID)
│   ├── error_codes.py        # Entity service error codes (DDL/DML specific, not auth-focused)
│   ├── client.py             # Async/Sync client library for other services
│   ├── database/             # Database layer
│   │   ├── __init__.py
│   │   ├── database.py       # SQLAlchemy ORM models (EntityType, DynamicEntity)
│   │   ├── repository.py     # Data access layer for entity types
│   │   ├── dynamic_repository.py # Data access layer for dynamic entities
│   │   └── dependencies.py   # FastAPI dependency injection (sessions)
│   ├── routes/               # API route handlers
│   │   ├── __init__.py
│   │   ├── entity_type_routes.py  # DDL endpoints (/entity-types GET/POST/PATCH/DELETE)
│   │   ├── dynamic_routes.py      # DML endpoints (auto-generated per entity type)
│   │   ├── discovery_routes.py    # Agent discovery endpoints (/discovery/*)
│   │   └── routes.py              # Legacy entity routes
│   └── services/             # Business logic layer
│       ├── __init__.py
│       ├── entity_type_service.py # DDL logic (create/update/list entity types, ownership)
│       ├── dynamic_service.py     # DML logic (CRUD for dynamic entities, authorization)
│       └── service.py             # Legacy entity service
├── tests/
│   ├── discovery_test.py      # Discovery endpoints and agent integration
│   ├── entity_type_test.py    # DDL operations (create/update/list entity types)
│   └── entity_api_test.py     # DML/CRUD operations on dynamic entities
├── logs/                      # Auto-created at startup; rotating files (10 MB, 5 backups)
└── data/                      # Auto-created; for SQLite DB and temporary data
```

### Key Components

**Config & Startup:**
- `app/config.py`: Centralized loader with **utils-service first** → **local JSON fallback**
  - `${VAR}` placeholder resolution (env-first, then config values) via `utils.config.resolve_placeholders()`
  - Dynamic API prefix from config: `/api/${version}` resolves to `/api/v1` at startup
- `main.py`: FastAPI app with lifespan, dynamic route generation, OpenAPI config
  - Calls `initialize_config()` at startup to load config, initialize logging, set `CONFIG_DIR`
  - Creates dynamic routes for each discovered entity type

**Request/Response Standards:**
- `app/schemas.py`: **Standard response wrapper** for all endpoints:
  ```json
  {
    "success": true,
    "data": { ... },
    "error": null,
    "metadata": { "correlation_id": "...", "timestamp": "..." }
  }
  ```
- `app/middleware.py`: 
  - Extracts `X-Requestor-Id` header (identifies service/tenant making request)
  - Auto-generates correlation ID per request for tracing
  - Stores in request context for access in handlers

**Authorization & Ownership:**
- **DDL (Entity Types)**: Requestor from header is recorded as owner; only owner can modify
- **DML (Entities)**: Create/Update/Delete blocked if entity_type belongs to different requestor; Read/List allowed
- Requestor mismatch returns `403 Forbidden` with `REQUESTOR_MISMATCH` error code

**Error Codes** (entity-specific, not auth-focused):
- DDL: `ENTITY_TYPE_EXISTS`, `ENTITY_TYPE_NOT_FOUND`, `INVALID_SCHEMA`, `SCHEMA_MODIFICATION_FAILED`
- DML: `ENTITY_NOT_FOUND`, `ENTITY_ALREADY_EXISTS`, `SOFT_DELETE_FAILED`, `HARD_DELETE_FAILED`
- Auth/Tenant: `REQUESTOR_MISMATCH`, `REQUESTOR_UNAUTHORIZED`
- Validation: `INVALID_COLUMN_TYPE`, `DUPLICATE_COLUMN`, `MISSING_REQUIRED_FIELD`, `INVALID_FILTER`

---

## Configuration

### Environment & Config Files

Config is loaded from **utils-service first**, then local `config/*.json` files as fallback.

Create a `.env` file to override defaults:

```env
# Service & API
SERVICE_NAME=entity-service
API_PREFIX=/api/v1
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite+aiosqlite:///./entity.db
# For PostgreSQL: postgresql+asyncpg://user:password@localhost:5432/entity_db

# Config directory (default: config)
CONFIG_DIR=config
```

### Config Directory Structure

- `config/app.json`: API metadata (version, prefix, project name)
- `config/database.json`: DB connection URL
- `config/logging.json`: Logging setup (handlers, formatters, levels)
- `config/paths.json`: Service directories (logs, data)

Placeholders like `${version}` and `${SERVICE_NAME}` are resolved at startup (env-first, then config values).

---

## API Endpoints

### DDL Operations (Entity Types)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/v1/entity-types` | Create entity type (requestor is owner) | X-Requestor-Id |
| `GET` | `/api/v1/entity-types` | List all entity types | X-Requestor-Id |
| `GET` | `/api/v1/entity-types/{type_name}` | Get entity type schema | X-Requestor-Id |
| `PATCH` | `/api/v1/entity-types/{type_name}` | Update entity type (owner only) | X-Requestor-Id |
| `DELETE` | `/api/v1/entity-types/{type_name}` | Delete entity type (owner only) | X-Requestor-Id |

### DML Operations (Dynamic Entities)

Auto-generated per entity type under `/api/v1/{entity_type}/...`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/v1/{entity_type}` | Create entity | X-Requestor-Id |
| `GET` | `/api/v1/{entity_type}` | List entities (with pagination, filters) | X-Requestor-Id |
| `GET` | `/api/v1/{entity_type}/{entity_id}` | Get entity by ID | X-Requestor-Id |
| `PATCH` | `/api/v1/{entity_type}/{entity_id}` | Update entity (partial) | X-Requestor-Id |
| `DELETE` | `/api/v1/{entity_type}/{entity_id}` | Soft/hard delete entity | X-Requestor-Id |
| `HEAD` | `/api/v1/{entity_type}/{entity_id}` | Check entity existence | X-Requestor-Id |

### Discovery Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/discovery/` | Service info and capabilities |
| `GET /api/v1/discovery/entity-types` | List all entity types with endpoints |
| `GET /api/v1/discovery/schemas` | All entity type schemas |
| `GET /api/v1/discovery/schemas/{type}` | Specific entity type schema |
| `GET /api/v1/discovery/operations` | All supported operations |

---

## Using Entity Service as a Library

### Async Client

```python
from app.client import EntityAPIClient

async def main():
    async with EntityAPIClient(base_url="http://localhost:8003") as client:
        # Create entity type
        entity_type = await client.create_entity_type(
            name="user",
            schema={"columns": [{"name": "email", "type": "string"}]}
        )
        
        # Create entity
        entity = await client.create_entity(
            entity_type="user",
            data={"email": "john@example.com"}
        )
        
        # Get entity
        entity = await client.get_entity("user", entity["id"])
        
        # List entities
        result = await client.list_entities("user", limit=10, offset=0)
        
        # Update entity
        updated = await client.update_entity(
            "user", entity["id"],
            data={"email": "jane@example.com"}
        )
        
        # Delete entity
        await client.delete_entity("user", entity["id"])
```

### Synchronous Client

```python
from app.client import EntityAPIClientSync

with EntityAPIClientSync(base_url="http://localhost:8003") as client:
    entity_type = client.create_entity_type(name="user", schema={...})
    entity = client.create_entity("user", data={...})
    result = client.list_entities("user")
    client.delete_entity("user", entity["id"])
```

---

## Database Support

### SQLite (Default)
Good for development:
```env
DATABASE_URL=sqlite+aiosqlite:///./entity.db
```

### PostgreSQL (Recommended for Production)
```bash
pip install asyncpg
```

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/entity_db
```

### MySQL
```bash
pip install aiomysql
```

```env
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/entity_db
```

---

## Development

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Test files:
- `tests/discovery_test.py`: Discovery endpoints
- `tests/entity_type_test.py`: DDL operations
- `tests/entity_api_test.py`: DML/CRUD operations

### Code Quality

```bash
black app/
flake8 app/
mypy app/
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "./main.py"]
```

```bash
docker build -t entity-service:latest .
docker run -p 8003:8003 entity-service:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: entity-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: entity-service
        image: entity-service:latest
        ports:
        - containerPort: 8003
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: entity-secrets
              key: database-url
```

---

## Security

- **Authentication**: Implement JWT/OAuth2 in API Gateway; entity-service validates `X-Requestor-Id` header
- **Authorization**: Requestor-based ownership for DDL; requestor mismatch returns `403 Forbidden`
- **HTTPS**: Required in production
- **Input Validation**: Pydantic schemas validate all requests
- **Rate Limiting**: Configured in API Gateway (future: per-service limits)

---

## Monitoring & Logging

Logs rotate at 10 MB with 5 backups:
- General: `logs/entity-service.log`
- Errors: `logs/entity-service.error.log`

Correlation IDs included in all logs for request tracing.

---

## Performance Tips

1. **Pagination**: Use `limit`/`offset` to avoid large responses
2. **Filtering**: Filter server-side (by type, status, etc.) instead of client-side
3. **Indexing**: Database indexes on `entity_type`, `is_active`, `created_by`
4. **Caching**: Implement Redis for frequently accessed schemas

---

## Contributing

1. Create a feature branch
2. Make changes with proper tests
3. Follow code style (black, flake8, mypy)
4. Submit pull request

---

## License

See LICENSE file in the root directory.
