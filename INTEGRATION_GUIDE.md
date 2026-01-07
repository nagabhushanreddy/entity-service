"""
Integration Guide for Using Entity API in Other Services

This document explains how to use the Entity API as a library in other services.
"""

# ============================================================================
# 1. COPY THE CLIENT MODULE
# ============================================================================
"""
1. Copy app/client.py to your service
   Example: services/authentication-api/entity_client.py

2. Or, create a shared module that both services can import
"""


# ============================================================================
# 2. AUTHENTICATION API INTEGRATION
# ============================================================================
"""
In services/authentication-api/main.go (Go service):

While Go cannot directly import Python modules, you can:
1. Make HTTP calls to Entity API directly
2. Or use a Python wrapper service

Example Go HTTP call:
```go
package main

import (
    "net/http"
    "bytes"
    "encoding/json"
)

func createUserEntity(userID, email string) error {
    client := &http.Client{}
    
    data := map[string]interface{}{
        "name": userID,
        "entity_type": "auth_user",
        "data": map[string]string{
            "email": email,
        },
    }
    
    jsonData, _ := json.Marshal(data)
    req, _ := http.NewRequest("POST", 
        "http://entity-api:8003/api/v1/entities", 
        bytes.NewBuffer(jsonData))
    req.Header.Set("Content-Type", "application/json")
    
    _, err := client.Do(req)
    return err
}
```

Or use the Entity API client as a microservice dependency:
- Call Entity API REST endpoints from your Go service
- No need to import Python code
- Loose coupling between services
"""


# ============================================================================
# 3. AUTHORIZATION API INTEGRATION
# ============================================================================
"""
In services/authorization-api/main.go:

Similar pattern as Authentication API:
- Use HTTP client to call Entity API
- Get entities and check their attributes
- Update entity data for authorization metadata

Example:
```go
func getRoleEntity(roleID string) (*Entity, error) {
    resp, err := http.Get(
        fmt.Sprintf("http://entity-api:8003/api/v1/entities/%s", roleID))
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var entity Entity
    json.NewDecoder(resp.Body).Decode(&entity)
    return &entity, nil
}

func listPermissionEntities() ([]Entity, error) {
    resp, err := http.Get(
        "http://entity-api:8003/api/v1/entities/type/permission")
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result struct {
        Items []Entity `json:"items"`
    }
    json.NewDecoder(resp.Body).Decode(&result)
    return result.Items, nil
}
```
"""


# ============================================================================
# 4. REPORTING API INTEGRATION
# ============================================================================
"""
In services/reporting-api/main.py:

The Reporting API is Python-based, so you can import the client directly!

from app.client import EntityAPIClientSync

def generate_user_report():
    with EntityAPIClientSync(base_url="http://entity-api:8003") as client:
        # Get all user entities
        result = client.list_entities(
            entity_type="user",
            is_active=True
        )
        
        # Generate report
        report = {
            "total_users": result["total"],
            "users": result["items"]
        }
        return report
"""


# ============================================================================
# 5. FRONTEND INTEGRATION
# ============================================================================
"""
In frontend/src/services/entityService.ts:

Create a TypeScript service wrapper:

```typescript
// src/services/entityService.ts
import axios from 'axios';

const API_BASE = process.env.REACT_APP_ENTITY_API_URL || 'http://localhost:8003';

interface Entity {
  id: string;
  name: string;
  entity_type: string;
  data?: Record<string, any>;
  [key: string]: any;
}

class EntityService {
  private client = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    headers: {
      'Content-Type': 'application/json',
    }
  });

  async createEntity(data: any): Promise<Entity> {
    const response = await this.client.post('/entities', data);
    return response.data;
  }

  async getEntity(id: string): Promise<Entity> {
    const response = await this.client.get(`/entities/${id}`);
    return response.data;
  }

  async listEntities(filters?: any): Promise<{ items: Entity[]; total: number }> {
    const response = await this.client.get('/entities', { params: filters });
    return response.data;
  }

  async updateEntity(id: string, data: any): Promise<Entity> {
    const response = await this.client.patch(`/entities/${id}`, data);
    return response.data;
  }

  async deleteEntity(id: string): Promise<void> {
    await this.client.delete(`/entities/${id}`);
  }
}

export default new EntityService();
```

Usage in components:
```typescript
// src/components/UserProfile.tsx
import entityService from '../services/entityService';

async function loadUser(userId: string) {
  try {
    const user = await entityService.getEntity(userId);
    setUserData(user);
  } catch (error) {
    console.error('Failed to load user:', error);
  }
}
```
"""


# ============================================================================
# 6. SERVICE-TO-SERVICE COMMUNICATION PATTERNS
# ============================================================================
"""
Pattern 1: Direct HTTP Calls
- Simplest for polyglot services
- No language-specific imports
- Loosely coupled

Pattern 2: Shared Client Library
- For Python services only
- Consistent interface
- Easier to maintain

Pattern 3: Message Queue Integration
- For asynchronous operations
- Decoupled from Entity API
- Better for batch operations

Example with RabbitMQ/Kafka:
```python
# Service publishes entity creation event
await message_queue.publish("entity.created", {
    "entity_id": "...",
    "entity_type": "user",
    "timestamp": "..."
})

# Another service subscribes and processes
@message_queue.subscribe("entity.created")
async def on_entity_created(message):
    entity = await client.get_entity(message["entity_id"])
    # Process entity
```
"""


# ============================================================================
# 7. CONFIGURATION AND ENVIRONMENT
# ============================================================================
"""
For each service, set environment variables:

Authentication API (.env):
```
ENTITY_API_URL=http://entity-api:8003
```

Authorization API (.env):
```
ENTITY_API_URL=http://entity-api:8003
```

Reporting API (.env):
```
ENTITY_API_URL=http://entity-api:8003
```

Frontend (.env):
```
REACT_APP_ENTITY_API_URL=http://localhost:8003
REACT_APP_ENTITY_API_URL=https://api.example.com/entity  # Production
```

Docker Compose (development):
```yaml
version: '3.8'
services:
  entity-api:
    build: ./services/entity-api
    ports:
      - "8003:8003"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/entity_db
  
  auth-api:
    build: ./services/authentication-api
    ports:
      - "8001:8001"
    environment:
      - ENTITY_API_URL=http://entity-api:8003
    depends_on:
      - entity-api
  
  authz-api:
    build: ./services/authorization-api
    ports:
      - "8002:8002"
    environment:
      - ENTITY_API_URL=http://entity-api:8003
    depends_on:
      - entity-api
  
  reporting-api:
    build: ./services/reporting-api
    ports:
      - "8004:8004"
    environment:
      - ENTITY_API_URL=http://entity-api:8003
    depends_on:
      - entity-api
```
"""


# ============================================================================
# 8. BEST PRACTICES
# ============================================================================
"""
1. Use Environment Variables
   - Don't hardcode Entity API URL
   - Different URLs for dev, staging, prod

2. Implement Retry Logic
   - Handle transient failures
   - Use exponential backoff
   
3. Cache Entities
   - Cache frequently accessed entities
   - Implement cache invalidation
   
4. Error Handling
   - Handle Entity API outages gracefully
   - Provide meaningful error messages
   
5. Authentication
   - Add JWT/OAuth2 to Entity API
   - Verify caller identity
   
6. Rate Limiting
   - Implement client-side rate limiting
   - Respect API limits
   
7. Monitoring
   - Log all Entity API calls
   - Monitor response times
   - Alert on failures
   
8. Testing
   - Mock Entity API in tests
   - Use fixtures for entity data
"""


# ============================================================================
# 9. TESTING WITH MOCKS
# ============================================================================
"""
Example: Testing with mock Entity API client

# test_user_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_entity_client():
    client = AsyncMock()
    client.get_entity.return_value = {
        "id": "123",
        "name": "Test User",
        "entity_type": "user"
    }
    client.create_entity.return_value = {
        "id": "456",
        "name": "New User",
        "entity_type": "user"
    }
    return client

@pytest.mark.asyncio
async def test_create_user(mock_entity_client):
    # Use mock instead of real API
    user = await mock_entity_client.create_entity(
        name="New User",
        entity_type="user"
    )
    assert user["id"] == "456"
    mock_entity_client.create_entity.assert_called_once()
"""


# ============================================================================
# 10. DEPLOYMENT CHECKLIST
# ============================================================================
"""
Before deploying Entity API to production:

□ Set up PostgreSQL database
□ Configure environment variables
□ Enable HTTPS
□ Add authentication/authorization
□ Implement rate limiting
□ Set up monitoring and logging
□ Configure backups
□ Load testing (test with expected traffic)
□ Security audit
□ API versioning strategy
□ Documentation updated
□ Error handling tested
□ Graceful shutdown
□ Health check configured
□ Metrics exposed
□ Logs aggregated
"""
