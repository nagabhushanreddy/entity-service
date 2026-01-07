"""Client library for Entity API - can be imported and used by other services"""

import httpx
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin


class EntityAPIClient:
    """
    Client library for Entity API
    
    This client can be imported and used by other services to interact with the Entity API.
    
    Example:
        ```python
        from entity_client import EntityAPIClient
        
        client = EntityAPIClient(base_url="http://entity-api:8003")
        entity = await client.create_entity(
            name="User",
            entity_type="user",
            data={"email": "user@example.com"}
        )
        ```
    """
    
    def __init__(self, base_url: str = "http://localhost:8003", timeout: float = 30.0):
        """
        Initialize Entity API client
        
        Args:
            base_url: Base URL of the Entity API service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """Make HTTP request"""
        url = urljoin(self.base_url, endpoint)
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Entity API request failed: {e}")
    
    async def create_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        status: str = "active",
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new entity
        
        Args:
            name: Entity name
            entity_type: Entity type/category
            description: Optional description
            status: Entity status (default: active)
            data: Custom JSON data
            metadata: Entity metadata
            created_by: User who created the entity
            
        Returns:
            Created entity data
        """
        payload = {
            "name": name,
            "entity_type": entity_type,
            "description": description,
            "status": status,
            "data": data,
            "metadata": metadata,
            "created_by": created_by
        }
        return await self._request("POST", "/api/v1/entities", json=payload)
    
    async def get_entity(self, entity_id: str) -> Dict[str, Any]:
        """
        Get entity by ID
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity data
        """
        return await self._request("GET", f"/api/v1/entities/{entity_id}")
    
    async def list_entities(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        List entities with optional filters
        
        Args:
            skip: Number of records to skip
            limit: Number of records to return
            entity_type: Filter by entity type
            status: Filter by status
            is_active: Filter by active status
            
        Returns:
            List response with items and total count
        """
        params = {
            "skip": skip,
            "limit": limit,
        }
        if entity_type:
            params["entity_type"] = entity_type
        if status:
            params["status"] = status
        if is_active is not None:
            params["is_active"] = is_active
        
        return await self._request("GET", "/api/v1/entities", params=params)
    
    async def list_by_type(
        self,
        entity_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List entities by type
        
        Args:
            entity_type: Entity type to filter by
            skip: Number of records to skip
            limit: Number of records to return
            
        Returns:
            List response with items and total count
        """
        params = {"skip": skip, "limit": limit}
        return await self._request(
            "GET",
            f"/api/v1/entities/type/{entity_type}",
            params=params
        )
    
    async def update_entity(
        self,
        entity_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an entity
        
        Args:
            entity_id: Entity ID
            name: Entity name
            description: Entity description
            entity_type: Entity type
            status: Entity status
            data: Custom JSON data
            metadata: Entity metadata
            is_active: Active status
            updated_by: User who updated the entity
            
        Returns:
            Updated entity data
        """
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if entity_type is not None:
            payload["entity_type"] = entity_type
        if status is not None:
            payload["status"] = status
        if data is not None:
            payload["data"] = data
        if metadata is not None:
            payload["metadata"] = metadata
        if is_active is not None:
            payload["is_active"] = is_active
        if updated_by is not None:
            payload["updated_by"] = updated_by
        
        return await self._request("PATCH", f"/api/v1/entities/{entity_id}", json=payload)
    
    async def delete_entity(self, entity_id: str, hard_delete: bool = False) -> None:
        """
        Delete an entity
        
        Args:
            entity_id: Entity ID
            hard_delete: If True, performs hard delete; otherwise soft delete
        """
        params = {"hard_delete": hard_delete}
        await self._request("DELETE", f"/api/v1/entities/{entity_id}", params=params)
    
    async def entity_exists(self, entity_id: str) -> bool:
        """
        Check if entity exists
        
        Args:
            entity_id: Entity ID
            
        Returns:
            True if entity exists, False otherwise
        """
        try:
            await self.client.head(f"/api/v1/entities/{entity_id}")
            return True
        except httpx.HTTPError:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of Entity API
        
        Returns:
            Health status
        """
        return await self._request("GET", "/healthz")
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Synchronous wrapper for convenience
class EntityAPIClientSync:
    """
    Synchronous wrapper for Entity API client
    
    Example:
        ```python
        from entity_client import EntityAPIClientSync
        
        client = EntityAPIClientSync(base_url="http://entity-api:8003")
        entity = client.create_entity(
            name="User",
            entity_type="user",
            data={"email": "user@example.com"}
        )
        ```
    """
    
    def __init__(self, base_url: str = "http://localhost:8003", timeout: float = 30.0):
        """Initialize synchronous Entity API client"""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request"""
        try:
            response = self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Entity API request failed: {e}")
    
    def create_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        status: str = "active",
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new entity"""
        payload = {
            "name": name,
            "entity_type": entity_type,
            "description": description,
            "status": status,
            "data": data,
            "metadata": metadata,
            "created_by": created_by
        }
        return self._request("POST", "/api/v1/entities", json=payload)
    
    def get_entity(self, entity_id: str) -> Dict[str, Any]:
        """Get entity by ID"""
        return self._request("GET", f"/api/v1/entities/{entity_id}")
    
    def list_entities(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """List entities with optional filters"""
        params = {
            "skip": skip,
            "limit": limit,
        }
        if entity_type:
            params["entity_type"] = entity_type
        if status:
            params["status"] = status
        if is_active is not None:
            params["is_active"] = is_active
        
        return self._request("GET", "/api/v1/entities", params=params)
    
    def list_by_type(
        self,
        entity_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """List entities by type"""
        params = {"skip": skip, "limit": limit}
        return self._request(
            "GET",
            f"/api/v1/entities/type/{entity_type}",
            params=params
        )
    
    def update_entity(
        self,
        entity_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an entity"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if entity_type is not None:
            payload["entity_type"] = entity_type
        if status is not None:
            payload["status"] = status
        if data is not None:
            payload["data"] = data
        if metadata is not None:
            payload["metadata"] = metadata
        if is_active is not None:
            payload["is_active"] = is_active
        if updated_by is not None:
            payload["updated_by"] = updated_by
        
        return self._request("PATCH", f"/api/v1/entities/{entity_id}", json=payload)
    
    def delete_entity(self, entity_id: str, hard_delete: bool = False) -> None:
        """Delete an entity"""
        params = {"hard_delete": hard_delete}
        self._request("DELETE", f"/api/v1/entities/{entity_id}", params=params)
    
    def entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        try:
            self.client.head(f"/api/v1/entities/{entity_id}")
            return True
        except httpx.HTTPError:
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of Entity API"""
        return self._request("GET", "/healthz")
    
    def close(self):
        """Close the client"""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
