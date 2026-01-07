
# Entity API

A RESTful microservice for CRUD operations and entity management with **dynamic table creation**. Each entity type gets its own dedicated table for better performance and relational integrity.

## Features

- **Dynamic Table Creation**: Create entity types (DDL) that generate dedicated database tables
- **Type-Specific CRUD Operations**: Each entity type has its own REST endpoints and table
- **Complete CRUD Operations**: Create, Read, Update, and Delete entities with full REST support
- **RESTful API**: Follows REST and OpenAPI standards
- **Async/Await**: Fully asynchronous operations for high performance
- **Database Support**: SQLAlchemy ORM with SQLite (easily swappable for PostgreSQL, MySQL, etc.)
- **Soft Deletes**: Non-destructive deletion with hard delete option
- **Versioning**: Automatic version tracking on entity updates
- **Filtering & Pagination**: Advanced filtering and pagination support
- **OpenAPI Documentation**: Auto-generated interactive documentation per entity type
- **Library Mode**: Can be imported and used by other services
- **Type Safety**: Full Pydantic schema validation
- **Error Handling**: Comprehensive error responses with proper HTTP status codes
- **Shared Utilities**: Uses utils-api for structured logging and config loading

## Architecture

### Multi-Table Design

Unlike traditional single-table approaches, this API creates **separate tables for each entity type**:

```
Database Structure:
├── entity_type_definitions (registry table)
├── entity_user (dynamically created)
├── entity_product (dynamically created)
└── entity_* (other types)
```

**Benefits:**
- ✅ Better query performance with dedicated indexes
- ✅ Relational integrity and constraints per type
- ✅ Type-specific columns (not generic JSON)
- ✅ Cleaner data model
- ✅ Easier to optimize per entity type

## Quick Start

### Prerequisites
- Python 3.9+
- pip or poetry

### Local Development

```bash
# Clone and navigate to the service
cd services/entity-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (includes local utils-api)
pip install -r requirements.txt

# Run the service
uvicorn main:app --reload --host 0.0.0.0 --port 8003
```

The API will be available at `http://localhost:8003`

### OpenAPI Documentation
- Interactive Swagger UI: `http://localhost:8003/api/v1/docs`
- ReDoc: `http://localhost:8003/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8003/api/v1/openapi.json`

## API Endpoints

### Health Check
- `GET /healthz` - Service health check

### Agent/Service Discovery

The API provides comprehensive discovery endpoints for automated agent/service integration:

#### Get Service Information
```http
GET /api/v1/discovery/
```

Returns service metadata, capabilities, and available endpoints.

Response:
```json
{
  "service": {
    "name": "entity-api",
    "version": "2.0.0",
    "description": "Entity API - Dynamic entity management",
    "api_version": "v1"
  },
  "capabilities": {
    "ddl_operations": true,
    "dml_operations": true,
    "dynamic_tables": true,
    "soft_delete": true
  },
  "endpoints": {
    "openapi": "/api/v1/openapi.json",
    "docs": "/api/v1/docs",
    "discovery": "/api/v1/discovery",
    "entity_types": "/api/v1/discovery/entity-types",
    "schemas": "/api/v1/discovery/schemas"
  }
}
```

#### Discover Entity Types
```http
GET /api/v1/discovery/entity-types
```

Returns all registered entity types with their endpoints and metadata.

Response:
```json
{
  "total": 2,
  "entity_types": {
    "user": {
      "table_name": "entity_user",
      "description": "User entities",
      "endpoints": {
        "create": "/api/v1/user",
        "list": "/api/v1/user",
        "get": "/api/v1/user/{id}"
      },
      "schema_url": "/api/v1/discovery/schemas/user"
    }
  }
}
```

#### Get Entity Type Schema
```http
GET /api/v1/discovery/schemas/{entity_type}
```

Returns detailed schema including column definitions, constraints, and example payloads.

Response:
```json
{
  "entity_type": "user",
  "columns": {
    "email": {"type": "string", "nullable": false, "unique": true},
    "username": {"type": "string", "nullable": false, "indexed": true}
  },
  "required_fields": ["email", "username"],
  "unique_fields": ["email"],
  "indexed_fields": ["username"],
  "example_create": {
    "email": "example@test.com",
    "username": "example_user"
  }
}
```

#### List All Schemas
```http
GET /api/v1/discovery/schemas
```

Returns schemas for all registered entity types.

#### Get Supported Operations
```http
GET /api/v1/discovery/operations
```

Returns all supported DDL and DML operations with details.

### DDL Operations (Entity Type Management)

#### Create Entity Type
```http
POST /api/v1/entity_type
Content-Type: application/json

{
	"entity_type": "user",
	"description": "User entities",
	"columns": [
		{
			"name": "email",
			"type": "string",
			"nullable": false,
			"unique": true,
			"max_length": 255
		},
		{
			"name": "username",
			"type": "string",
			"nullable": false,
			"indexed": true,
			"max_length": 100
		},
		{
			"name": "age",
			"type": "integer",
			"nullable": true
		}
	],
	"created_by": "admin"
}
```

Response: `201 Created`
```json
{
	"entity_type": "user",
	"table_name": "entity_user",
	"schema_definition": {
		"email": {"type": "string", "nullable": false, "unique": true, "max_length": 255},
		"username": {"type": "string", "nullable": false, "indexed": true, "max_length": 100},
		"age": {"type": "integer", "nullable": true}
	},
	"description": "User entities",
	"is_active": true,
	"created_at": "2026-01-06T10:30:00Z",
	"updated_at": "2026-01-06T10:30:00Z",
	"created_by": "admin"
}
```

**Supported Column Types:**
- `string` - VARCHAR with configurable max_length
- `integer` - INT
- `float` - FLOAT
- `boolean` - BOOLEAN
- `text` - TEXT (unlimited length)
- `json` - JSON
- `datetime` - DATETIME

#### List Entity Types
```http
GET /api/v1/entity_type?skip=0&limit=10
```

#### Get Entity Type
```http
GET /api/v1/entity_type/user
```

#### Delete Entity Type (Deactivate)
```http
DELETE /api/v1/entity_type/user
```

### DML Operations (Entity Instance CRUD)

Once an entity type is created, it gets its own REST endpoints:

#### Create Entity Instance
```http
POST /api/v1/user
Content-Type: application/json

{
	"email": "john@example.com",
	"username": "john_doe",
	"age": 30,
	"created_by": "api"
}
```

Response: `201 Created`
```json
{
	"id": "550e8400-e29b-41d4-a716-446655440000",
	"email": "john@example.com",
	"username": "john_doe",
	"age": 30,
	"is_active": true,
	"created_at": "2026-01-06T10:35:00Z",
	"updated_at": "2026-01-06T10:35:00Z",
	"created_by": "api",
	"updated_by": null,
	"version": 1
}
```

#### List Entities
```http
GET /api/v1/user?skip=0&limit=10&is_active=true
```

#### Get Entity
```http
GET /api/v1/user/{entity_id}
```

#### Update Entity
```http
PATCH /api/v1/user/{entity_id}
Content-Type: application/json

{
	"age": 31,
	"updated_by": "api"
}
```

#### Delete Entity
```http
DELETE /api/v1/user/{entity_id}
```

Default: Soft delete (marks as inactive)
```http
DELETE /api/v1/user/{entity_id}?hard_delete=true
```

Hard delete: Permanently removes entity

Response: `204 No Content`

#### Check Entity Exists
```http
HEAD /api/v1/user/{entity_id}
```

Response: `200 OK` if exists, `404 Not Found` if not

## Using Entity API as a Library

### Async Client

```python
from app.client import EntityAPIClient

async def main():
		async with EntityAPIClient(base_url="http://entity-api:8003") as client:
				# Create entity
				entity = await client.create_entity(
						name="John Doe",
						entity_type="user",
						data={"email": "john@example.com"}
				)
        
				# Get entity
				entity = await client.get_entity(entity["id"])
        
				# List entities
				result = await client.list_entities(
						entity_type="user",
						status="active"
				)
        
				# Update entity
				updated = await client.update_entity(
						entity["id"],
						name="Jane Doe"
				)
        
				# Delete entity
				await client.delete_entity(entity["id"])
```

### Synchronous Client

```python
from app.client import EntityAPIClientSync

with EntityAPIClientSync(base_url="http://entity-api:8003") as client:
		# All methods work the same but are synchronous
		entity = client.create_entity(
				name="John Doe",
				entity_type="user"
		)
    
		entity = client.get_entity(entity["id"])
		result = client.list_entities(entity_type="user")
		client.delete_entity(entity["id"])
```

### Using in Other Services

Copy the `app/client.py` file to your service and import it:

```python
# In your authentication-api or other service
from entity_client import EntityAPIClient, EntityAPIClientSync

# Use it to interact with Entity API
client = EntityAPIClientSync(base_url="http://entity-api:8003")
user_entity = client.get_entity("user-id-123")
```

## Architecture

### Project Structure
```
entity-api/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration settings
│   ├── database.py        # SQLAlchemy models
│   ├── schemas.py         # Pydantic request/response models
│   ├── repository.py      # Data access layer
│   ├── service.py         # Business logic layer
│   ├── routes.py          # API endpoints
│   └── client.py          # Client library for other services
```

### Design Patterns

- **Layered Architecture**: Separation of concerns with data, service, and API layers
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **Async/Await**: Non-blocking operations throughout
- **Dependency Injection**: FastAPI's dependency system for session management

## Configuration

Create a `.env` file to override defaults:

```env
DATABASE_URL=sqlite+aiosqlite:///./entity.db
DB_ECHO=false
SERVICE_NAME=entity-api
LOG_LEVEL=INFO
```

For production with PostgreSQL:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/entity_db
```

## Database Support

### SQLite (Default)
Good for development and small deployments:
```
DATABASE_URL=sqlite+aiosqlite:///./entity.db
```

### PostgreSQL (Recommended for Production)
Install additional dependency:
```bash
pip install asyncpg
```

Update `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

### MySQL
Install additional dependency:
```bash
pip install aiomysql
```

Update `.env`:
```
DATABASE_URL=mysql+aiomysql://user:password@host:3306/dbname
```

## Development

### Running Tests
```bash
pip install pytest pytest-asyncio httpx
pytest tests -v
```

Test files:
- [`tests/discovery_test.py`](tests/discovery_test.py) - Discovery endpoints and agent integration
- [`tests/entity_type_test.py`](tests/entity_type_test.py) - DDL operations for entity types  
- [`tests/entity_api_test.py`](tests/entity_api_test.py) - Legacy CRUD tests (deprecated)

### Code Quality
```bash
pip install black flake8 mypy
black app/
flake8 app/
mypy app/
```

## Deployment

### Docker

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

Build and run:
```bash
docker build -t entity-api:latest .
docker run -p 8003:8003 entity-api:latest
```

### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/entity-api
gcloud run deploy entity-api \
	--image gcr.io/$PROJECT_ID/entity-api \
	--port 8003 \
	--memory 512Mi \
	--cpu 1 \
	--set-env-vars DATABASE_URL=postgresql+asyncpg://...
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
	name: entity-api
spec:
	replicas: 3
	selector:
		matchLabels:
			app: entity-api
	template:
		metadata:
			labels:
				app: entity-api
		spec:
			containers:
			- name: entity-api
				image: gcr.io/PROJECT_ID/entity-api:latest
				ports:
				- containerPort: 8003
				env:
				- name: DATABASE_URL
					valueFrom:
						secretKeyRef:
							name: entity-api-secrets
							key: database-url
				livenessProbe:
					httpGet:
						path: /healthz
						port: 8003
					initialDelaySeconds: 30
					periodSeconds: 10
```

## Agent/Service Integration

### Automated Discovery

The Entity API supports **full agent discovery** for automated integration. Agents/services can:

1. **Discover service capabilities** without prior knowledge
2. **Find entity types dynamically** at runtime
3. **Get schemas** to understand data structures
4. **Generate client code** based on discovered schemas

#### Python Agent Example

```python
import httpx

async def discover_and_use_api():
    async with httpx.AsyncClient() as client:
        # 1. Discover service
        response = await client.get("http://localhost:8003/api/v1/discovery/")
        service_info = response.json()
        print(f"Service: {service_info['service']['name']}")
        
        # 2. Discover entity types
        response = await client.get("http://localhost:8003/api/v1/discovery/entity-types")
        entity_types = response.json()['entity_types']
        
        # 3. Get schema for 'user' entity
        response = await client.get("http://localhost:8003/api/v1/discovery/schemas/user")
        schema = response.json()
        
        # 4. Create entity using discovered endpoint
        endpoint = schema['endpoints']['create']
        example_data = schema['example_create']
        await client.post(f"http://localhost:8003{endpoint}", json=example_data)
```

See [`agent_discovery_example.py`](agent_discovery_example.py) for a complete agent implementation.

#### Discovery Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/discovery/` | Service info and capabilities |
| `GET /api/v1/discovery/entity-types` | List all entity types with endpoints |
| `GET /api/v1/discovery/schemas` | All entity type schemas |
| `GET /api/v1/discovery/schemas/{type}` | Specific entity type schema |
| `GET /api/v1/discovery/operations` | All supported operations |

### Integration Patterns

#### 1. Runtime Discovery Pattern
```python
# Agent discovers and adapts to available entity types at runtime
agent = EntityAPIAgent()
await agent.discover_service()
await agent.discover_entity_types()

# Work with any discovered type
for entity_type in agent.entity_types:
    schema = await agent.discover_schema(entity_type)
    # Use schema to create/update entities
```

#### 2. Schema-First Pattern
```python
# Download schemas and generate typed clients
schemas = await client.get("/api/v1/discovery/schemas")
generate_typed_client(schemas)  # Generate Python/TypeScript client
```

#### 3. Service Mesh Integration
```yaml
# Kubernetes Service Discovery
apiVersion: v1
kind: Service
metadata:
  name: entity-api
  annotations:
    discovery.service.url: "/api/v1/discovery/"
```

## Performance

### Optimization Tips

1. **Connection Pooling**: SQLAlchemy handles this automatically
2. **Pagination**: Always use limit parameter to avoid large responses
3. **Filtering**: Filter by type or status server-side instead of client-side
4. **Caching**: Implement Redis for frequently accessed entities
5. **Database Indexing**: Indexes on `entity_type`, `status`, and `is_active` are created by default

### Load Testing

```bash
pip install locust

# Create locustfile.py with your load tests
locust -f locustfile.py --host=http://localhost:8003
```

## Security Considerations

- Implement authentication (JWT, OAuth2) before entity-api in your API gateway
- Use HTTPS in production
- Validate and sanitize input data
- Implement rate limiting on the service
- Use database encryption for sensitive data
- Regularly audit and rotate access credentials

## Monitoring & Logging

The service logs all operations with timestamps and severity levels. Integration with monitoring tools:

- **Datadog**: Add Datadog APM middleware
- **Prometheus**: Expose metrics endpoint
- **ELK Stack**: Pipe logs to Elasticsearch
- **Cloud Logging**: For GCP deployment

## API Response Codes

- `200 OK`: Successful GET/PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid input
- `404 Not Found`: Entity not found
- `500 Internal Server Error`: Server error

## Contributing

1. Create a feature branch
2. Make changes with proper tests
3. Follow code style guidelines
4. Submit pull request

## License

See LICENSE file in the root directory.
