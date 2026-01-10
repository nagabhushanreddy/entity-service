# Entity Service - Developer Quick Reference

## Key Changes for Developers

### 1. Standard Response Format
All API responses follow this format:
```json
{
  "success": true|false,
  "data": { /* response data */ },
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { /* validation errors */ }
  },
  "metadata": {
    "timestamp": "2026-01-09T12:34:56.789Z",
    "correlation_id": "uuid-here"
  }
}
```

### 2. Required Header
All requests must include:
```
X-Requestor-Id: service-or-tenant-name
```
This header identifies the service/tenant making the request and is used for authorization.

### 3. Response Headers
All responses include:
```
X-Correlation-Id: uuid-here
```
Use this for tracing requests across services.

### 4. Error Codes
Entity-service specific error codes:
- `VALIDATION_ERROR`: Request validation failed
- `ENTITY_TYPE_EXISTS`: Entity type already exists (409)
- `ENTITY_TYPE_NOT_FOUND`: Entity type not found (404)
- `ENTITY_TYPE_INACTIVE`: Entity type is inactive (400)
- `ENTITY_NOT_FOUND`: Entity instance not found (404)
- `REQUESTOR_MISMATCH`: Entity type belongs to different requestor (403)
- `REQUESTOR_UNAUTHORIZED`: Requestor not authorized (403)
- `INVALID_SCHEMA`: Schema definition is invalid (400)
- `INVALID_COLUMN_TYPE`: Column type not supported (400)
- `DUPLICATE_COLUMN`: Column name already exists (400)
- `DDL_OPERATION_FAILED`: DDL operation failed (500)
- `DML_OPERATION_FAILED`: DML operation failed (500)

### 5. Authorization Rules

#### DDL Operations (Entity Type Management)
- **Create**: Requestor becomes owner. Replaces old `created_by` in request body.
- **Read**: Open to any requestor
- **Delete**: Owner-only (requestor who created it)

#### DML Operations (Entity CRUD)
- **Create**: Owner-only (requestor who owns entity type)
- **Read/List**: Open to any requestor
- **Update**: Owner-only
- **Delete**: Owner-only

### 6. Key Files Modified
- `app/error_codes.py` - NEW: Error code definitions
- `app/exceptions.py` - NEW: Custom exception classes
- `app/middleware.py` - NEW: Request context middleware
- `app/schemas.py` - UPDATED: Standard response models
- `app/entity_type_service.py` - UPDATED: Requestor-aware
- `app/entity_type_routes.py` - UPDATED: Requestor extraction
- `app/dynamic_service.py` - UPDATED: Requestor-aware authorization
- `app/dynamic_routes.py` - UPDATED: Requestor extraction
- `main.py` - UPDATED: Exception handlers, middleware

### 7. Context Access in Routes
```python
from app.middleware import get_requestor_id, get_correlation_id

requestor = get_requestor_id()  # Get current request's requestor
correlation_id = get_correlation_id()  # Get correlation ID for tracing
```

### 8. Exception Handling Examples

Throw EntityServiceException to return proper response:
```python
from app.exceptions import EntityTypeExistsError, RequestorMismatchError

# This will automatically return 409 with proper error format
raise EntityTypeExistsError(entity_type_name)

# This will automatically return 403 with proper error format
raise RequestorMismatchError(entity_type_name, requestor)
```

### 9. Testing with Headers
```python
# Include X-Requestor-Id header in requests
response = client.post(
    "/api/v1/entity_type",
    json=data,
    headers={"X-Requestor-Id": "user-service"}
)

# Check correlation ID in response
correlation_id = response.headers.get("X-Correlation-Id")
```

### 10. Database Models
Entity types include these auto-managed fields:
- `id`: UUID (auto-generated)
- `created_by`: String (set from X-Requestor-Id header)
- `created_at`: DateTime (auto-set)
- `updated_at`: DateTime (auto-updated)
- `updated_by`: String (optional)
- `is_active`: Boolean (default True)
- `version`: Integer (auto-incremented on update)

## Migration Guide

### From Old to New Format

**Old Error Response:**
```json
{
  "detail": "Error message",
  "error_code": "CODE"
}
```

**New Error Response:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "details": null
  },
  "metadata": {
    "timestamp": "2026-01-09T12:34:56.789Z",
    "correlation_id": "uuid-here"
  }
}
```

### Old Request (no requestor):
```
POST /api/v1/entity_type
{
  "entity_type": "user",
  "created_by": "admin"
}
```

### New Request (with requestor header):
```
POST /api/v1/entity_type
X-Requestor-Id: admin

{
  "entity_type": "user"
}
```

## Next Steps
1. Update test fixtures to use async context managers
2. Update integration tests with X-Requestor-Id headers
3. Update client libraries to extract and include correlation IDs
4. Document API changes for consuming services
5. Add metrics/logging integration for correlation IDs

