

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
