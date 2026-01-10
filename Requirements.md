
# Multi-Finance User Application  
## Microservices Requirements Document (OpenAPI-Compliant)

---

## 1. Overview

This document defines the functional and non-functional requirements for a **Multi-Finance User Web Application** built using a **microservices REST architecture**.  
All services **MUST expose OpenAPI 3.x compliant specifications**.

### Core Domains
- User & Identity
- Authorization
- User Profile
- Loan Management

---

## 2. Architecture Principles

- Microservices with **single responsibility**
- **Database-per-service or use entity-service**
- REST APIs with **OpenAPI 3.0+**
- Stateless services
- JWT-based security
- Event-driven integration where applicable
- Default **DENY** authorization model

---

## 3. Services Overview

| Service | Responsibility |
|------|---------------|
| API Gateway / BFF | Single entry point, auth enforcement |
| **Entity Service** ⭐ | **CRUD Operations & Database Interactions** |
| Identity & Authentication Service | Login, OTP, token issuance |
| Authorization Service | Central policy decision (RBAC + ABAC) |
| User Profile Service | Customer profile & KYC metadata |
| Loan Service | Loan products, applications, accounts |
| Document Service | KYC & loan document storage |
| Notification Service | Email/SMS orchestration |
| Audit & Compliance Service | Immutable audit logging |

---

### OpenAPI Requirements
- Versioned paths `/api/v1`
- OAuth2 / Bearer JWT security scheme
- Correlation-Id header propagation

---

## 4. Entity Service

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
- **Shared Utilities**: Uses utils-service for structured logging and config loading

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


### 4.1 Scope
CRUD Operation and Database Interactions.

### 4.2 Technology Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI (async, OpenAPI native)
- **Token Management**: PyJWT (HS256 algorithm)
- **Data Validation**: Pydantic
- **Testing**: pytest with coverage reporting
- **Logging**: Structured JSON logs
- **Server**: Uvicorn ASGI

### 4.3 Core APIs/Endpoints

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

### 5.4 Functional Requirements

#### 5.4.1 DDL Operations
- **Create needed tables in database**
  - Requestor is extracted from `X-Requestor-Id` header and recorded as the owner of the entity_type
  - Create the entity_type table if not exist
    - When entity_type exists: return ENTITY_TYPE_EXISTS error
    - When entity_type belongs to different requestor: return REQUESTOR_MISMATCH error (entity_type not available)
  - Modify the entity_type 
    - Safe modification without data loss
    - When entity_type belongs to different requestor: return REQUESTOR_MISMATCH error, do not allow modification
    - Only the original requestor (extracted from header) can modify their entity_type
 

#### 5.4.2 DML Operations
- **Perform CRUD Operations on given entity_type (example: Add user, modify user, list user, delete user)**
  - Requestor is extracted from `X-Requestor-Id` header for authorization checks
  - **Create operation**: Only allowed if entity_type owner matches requestor. Returns REQUESTOR_MISMATCH if entity_type belongs to different requestor
  - **Update operation**: Only allowed if entity_type owner matches requestor. Returns REQUESTOR_MISMATCH if entity_type belongs to different requestor
  - **Delete operation**: Only allowed if entity_type owner matches requestor. Returns REQUESTOR_MISMATCH if entity_type belongs to different requestor
  - **Read/List operation**: Allowed for any requestor, regardless of entity_type ownership
  

### 5.5 Request Headers & Requestor Management

#### 5.5.0 Required Headers
- **X-Requestor-Id** (required): Unique identifier for the service/tenant making the request. Used to enforce ownership and authorization on entity types.
  - Example: `X-Requestor-Id: user-service`
  - This header value is recorded as the owner of entity_type for DDL operations
  - Requestor cannot access/modify entity types created by different requestors (except for read operations)

### 5.5 Non-Functional Requirements

#### 5.5.1 Performance
- **Latency Targets**
  - DML & CRUD Operations: < 200ms
  - Validations < 50ms

- **Rate Limiting**:
  - As needed
- **CORS Configuration**: Configurable origins, credentials support, specific HTTP methods, custom header support (X-API-Key, X-Correlation-ID)

#### 5.5.3 Availability & Reliability
- **Uptime Target**: 99.9% SLA
- **Graceful Shutdown**: 30 second timeout
- **Health Check**: Every 10 seconds
- **Error Recovery**: Automatic retry with exponential backoff

#### 5.5.4 Observability
- **Logging**
  - Structured JSON format
  - Correlation ID propagation
  - All authentication events logged
  - Failed attempts logged
  - Token operations logged

- **Metrics**
  - Request latency (histogram)
  - Error rates (counter)
  - Active sessions (gauge)
  - Token creation rate (counter)

- **Tracing**
  - Correlation ID on all requests
  - X-Correlation-ID response header
  - Trace propagation to dependent services

#### 5.5.5 Data Storage
- **Current Implementation**: In-memory (for dev in memory db light weight)
- **Production**: Must be compatible via configuration to standard db engines (sql, postgresql).
- **Data Entities**:
  - Schemas/Entity_Type
  
### 5.6 Service Dependencies

#### 5.6.1 Utils service from utils-service

All config and logging related functions must use utils-service from ../utils-service:
- utils.logger
- utils.config


### 5.7 Request/Response Specifications

#### 5.7.1 Standard Response Format
```json
{
  "success": true|false,
  "data": { /* endpoint-specific data */ },
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { /* validation errors */ }
  },
  "metadata": {
    "timestamp": "ISO8601",
    "correlation_id": "UUID"
  }
}
```

#### 5.7.2 Error Codes

Use error codes in conjunction with http status codes. 

```
VALIDATION_ERROR: Request validation failed
ENTITY_TYPE_EXISTS: Entity type already exists
ENTITY_TYPE_NOT_FOUND: Entity type does not exist
ENTITY_TYPE_INACTIVE: Entity type is inactive
ENTITY_NOT_FOUND: Entity instance not found
ENTITY_ALREADY_EXISTS: Entity with unique constraint already exists
INVALID_SCHEMA: Schema definition is invalid
INVALID_COLUMN_TYPE: Column type is not supported
REQUESTOR_MISMATCH: Entity type belongs to different requestor
REQUESTOR_UNAUTHORIZED: Requestor not authorized for this operation
SCHEMA_MODIFICATION_FAILED: Failed to modify entity type schema safely
DDL_OPERATION_FAILED: DDL operation failed
DML_OPERATION_FAILED: DML operation failed
SOFT_DELETE_FAILED: Soft delete operation failed
HARD_DELETE_FAILED: Hard delete operation failed
DUPLICATE_COLUMN: Column name already exists in schema
MISSING_REQUIRED_FIELD: Required field missing in request
INVALID_FILTER: Invalid filter parameter
INVALID_PAGINATION: Invalid pagination parameters
UNAUTHORIZED: Missing or invalid authentication
RATE_LIMIT_EXCEEDED: Too many requests
INTERNAL_ERROR: Server error
```

### 5.8 OpenAPI Requirements
- **Version**: OpenAPI 3.0+
- **Endpoint**: `GET /v3/api-docs` returns complete specification
- **Security Schemes**:
  - bearerAuth (JWT tokens)
  - apiKeyAuth (X-API-Key header)
- **Request/Response Schemas**: Strict validation
- **Error Schemas**: Standardized error responses
- **Documentation**: Clear descriptions for all endpoints

### 5.9 Testing Requirements

#### 5.9.1 Unit Tests
- DML Operations
- DDL Operations
- Validations by Requestors


#### 5.9.2 Integration Tests
- Complete Flows database operations flow


#### 5.9.3 Coverage & Reporting
- Minimum 80% code coverage
- XML test reports (JUnit format)
- HTML coverage reports
- Test execution logs

#### 5.9.4 Test Framework
- pytest (Python testing framework)
- pytest-cov (coverage reporting)
- pytest-asyncio (async test support)
- TestClient (FastAPI testing)

### 5.10 Configuration Management

#### 5.10.1 Environment Variables
```
NODE_ENV=development|production
PORT=3001
JWT_ACCESS_SECRET=<min-32-chars>
JWT_REFRESH_SECRET=<min-32-chars>
JWT_ACCESS_EXPIRY=900
JWT_REFRESH_EXPIRY=604800
JWT_ALGORITHM=HS256

MFA_OTP_LENGTH=6
MFA_OTP_EXPIRY=300
MFA_OTP_ATTEMPTS=3

RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
BRUTE_FORCE_MAX_ATTEMPTS=5
BRUTE_FORCE_LOCK_TIME=900000

CORS_ORIGINS=http://localhost:3000,http://localhost:3001

GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<secret>
FACEBOOK_CLIENT_ID=<client-id>
MICROSOFT_CLIENT_ID=<client-id>

FRONTEND_URL=http://localhost:3000
LOG_LEVEL=info
```

#### 5.10.2 Secrets Management
- All secrets loaded from environment variables
- Minimum 32 character secrets for JWT
- Never commit secrets to repository
- Use Vault/KMS in production

### 5.11 Deployment Architecture

#### 5.11.1 Development
```
python -m uvicorn src.main:app --reload
```

#### 5.11.2 Production
```
gunicorn "src.main:app" --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

#### 5.11.3 Containerization
- Docker image with Python 3.10 base
- Health check endpoint
- Graceful shutdown handling
- Environment variable configuration

### 5.12 Acceptance Criteria
- [ ] All endpoints OpenAPI compliant
- [ ] All DDL operations compliant
- [ ] All DML operation complaint
- [ ] All validations compliant
- [ ] Test coverage >= 80%
- [ ] All error codes documented
- [ ] Correlation ID propagation working
- [ ] Performance tests passed (P95 < 300ms)
- [ ] Integration with utils-service completed


---

## 6. Cross-Cutting Requirements

### 6.1 Observability & Monitoring
- **Structured Logging**: JSON format with correlation ID propagation (see section 5.5.4)
- **Metrics**: Request latency, error rates, active sessions (section 5.5.4)
- **Distributed Tracing**: Correlation ID on all requests for end-to-end visibility
- **Health Monitoring**: `/health` endpoint for readiness/liveness checks

### 6.2 API Standards
- **OpenAPI 3.0+**: All services expose `/v3/api-docs` with complete schema documentation
- **Error Handling**: Standardized error response format (section 5.7)
- **Request/Response**: Strict Pydantic validation
- **API Versioning**: Version via paths (e.g., `/api/v1`)

### 6.3 Testing & Quality
- **Test-Driven Development**: Unit, integration, and end-to-end tests
- **Code Coverage**: Minimum 80% coverage requirement
- **Test Reports**: XML (JUnit) and HTML formats for CI/CD integration
- **Test Frameworks**: pytest with pytest-cov and pytest-asyncio

### 6.4 Service Dependencies & Reusability
- **Entity-Service**: All CRUD operations (User, ApiKey, ResetToken, SsoLinkage)
- **Utils-Service**: Common utilities (config, logging)
- **Notification-Service**: Email/SMS delivery integration

### 6.5 API Discoverability
- OpenAPI schemas support AI agent discovery
- Clear operation descriptions and example payloads
- Comprehensive error documentation

### 6.6 Project structure

All microservices MUST follow a consistent directory structure for maintainability and discoverability:

**Root Level:**
- `main.py` - Application entry point with FastAPI app, lifespan, middleware
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies (pytest, black, mypy, coverage)
- `.env.example` - Environment variable template
- `README.md` - Service documentation
- `config/` - Configuration files (JSON/YAML) with placeholder support

**Application Module (`app/`):**
- `config.py` - Configuration loader (utils-service first, local JSON fallback)
- `schemas.py` - Pydantic models for request/response validation
- `exceptions.py` - Custom exception classes with error codes
- `middleware.py` - Request context, correlation ID, logging middleware
- `error_codes.py` - Service-specific error code definitions
- `client.py` - Async/Sync client library for inter-service communication

**Organized Submodules:**
- `app/database/` - All database-related code
  - `database.py` - SQLAlchemy models and ORM definitions
  - `repository.py` - Data access layer (queries, filters)
  - `dependencies.py` - FastAPI dependency injection (sessions)
- `app/routes/` - API route handlers (thin layer, delegates to services)
  - Organized by domain/resource (e.g., `user_routes.py`, `entity_type_routes.py`)
- `app/services/` - Business logic layer
  - Organized by domain (e.g., `user_service.py`, `entity_type_service.py`)
  - Contains authorization checks, workflow orchestration

**Testing:**
- `tests/` - All test files
  - `unit/` - Unit tests for services and utilities
  - `integration/` - Integration tests for API endpoints
  - Test files named `test_*.py` for pytest discovery

**Standards:**
- Each directory with Python code MUST have `__init__.py` for clean imports
- Use absolute imports: `from app.services import UserService`
- Export commonly used classes/functions in `__init__.py` files
- Follow layered architecture: Routes → Services → Repositories → Database

---

## 7. Implementation Status

For detailed implementation status, progress tracking, and open items, please refer to [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

---

## 8. Future Work / TODO Items

### 8.1 Security (Phase 2)
- **Transport Security**: TLS 1.2+ everywhere, mTLS for internal service-to-service communication
- **Secrets Management**: All sensitive data via environment variables/Vault/KMS
- **Input Validation**: Comprehensive input validation beyond basic type checking
- **Output Encoding**: Prevent injection attacks
- **Token Management**: JWT validation, authorization scopes, and fine-grained permissions
- **Audit Logging**: Immutable audit trail for all DDL/DML operations with requestor and timestamp

---

**End of Document**
