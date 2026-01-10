"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict, List, Generic, TypeVar
from datetime import datetime
from enum import Enum
import uuid

T = TypeVar('T')


class ColumnType(str, Enum):
    """Supported column types for entity schema definition."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TEXT = "text"
    JSON = "json"
    DATETIME = "datetime"


class ColumnDefinition(BaseModel):
    """Schema for defining a column in an entity type."""
    name: str = Field(..., min_length=1, max_length=100, description="Column name")
    type: ColumnType = Field(..., description="Column data type")
    nullable: bool = Field(default=True, description="Whether column can be null")
    unique: bool = Field(default=False, description="Whether column must be unique")
    indexed: bool = Field(default=False, description="Whether to create index")
    max_length: Optional[int] = Field(None, description="Max length for string types")
    default: Optional[Any] = Field(None, description="Default value")
    description: Optional[str] = Field(None, max_length=500, description="Column description")


class EntityTypeCreate(BaseModel):
    """Schema for creating a new entity type (DDL operation)."""
    entity_type: str = Field(..., min_length=1, max_length=100, pattern="^[a-z][a-z0-9_]*$", description="Entity type name (lowercase, underscores)")
    description: Optional[str] = Field(None, max_length=1000, description="Entity type description")
    columns: List[ColumnDefinition] = Field(..., min_length=1, description="Column definitions")
    created_by: Optional[str] = Field(None, description="User creating the entity type")


class EntityTypeResponse(BaseModel):
    """Schema for entity type response."""
    entity_type: str
    table_name: str
    schema_definition: Dict[str, Any]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class EntityTypeListResponse(BaseModel):
    """Schema for entity type list response."""
    items: List[EntityTypeResponse]
    total: int


# Dynamic entity schemas (for DML operations on specific entity types)
class DynamicEntityCreate(BaseModel):
    """Schema for creating an entity instance of a specific type."""
    model_config = ConfigDict(extra="allow")  # Allow additional fields based on entity type schema
    
    created_by: Optional[str] = Field(None, description="User who created the entity")


class DynamicEntityUpdate(BaseModel):
    """Schema for updating an entity instance."""
    model_config = ConfigDict(extra="allow")  # Allow additional fields based on entity type schema
    
    is_active: Optional[bool] = Field(None)
    updated_by: Optional[str] = Field(None, description="User who updated the entity")


class DynamicEntityResponse(BaseModel):
    """Schema for entity instance response."""
    model_config = ConfigDict(from_attributes=True, extra="allow")
    
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    version: int


class DynamicEntityListResponse(BaseModel):
    """Schema for dynamic entity list response."""
    items: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int


class EntityBase(BaseModel):
    """Base entity schema"""
    
    name: str = Field(..., min_length=1, max_length=255, description="Entity name")
    description: Optional[str] = Field(None, max_length=1000, description="Entity description")
    entity_type: str = Field(..., min_length=1, max_length=100, description="Entity type")
    status: str = Field(default="active", description="Entity status")
    data: Optional[dict[str, Any]] = Field(None, description="Custom entity data")
    metadata: Optional[dict[str, Any]] = Field(None, description="Entity metadata")


class EntityCreate(EntityBase):
    """Schema for creating an entity"""
    
    created_by: Optional[str] = Field(None, description="User who created the entity")


class EntityUpdate(BaseModel):
    """Schema for updating an entity"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    entity_type: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = Field(None)
    data: Optional[dict[str, Any]] = Field(None)
    metadata: Optional[dict[str, Any]] = Field(None)
    is_active: Optional[bool] = Field(None)
    updated_by: Optional[str] = Field(None)


class EntityResponse(EntityBase):
    """Schema for entity response"""
    
    id: str = Field(..., description="Entity ID")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    version: int
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to handle entity_metadata -> metadata mapping"""
        if hasattr(obj, 'entity_metadata'):
            # Create a dict with proper field names
            data = {
                'id': obj.id,
                'name': obj.name,
                'description': obj.description,
                'entity_type': obj.entity_type,
                'status': obj.status,
                'data': obj.data,
                'metadata': obj.entity_metadata,  # Map entity_metadata to metadata
                'is_active': obj.is_active,
                'created_at': obj.created_at,
                'updated_at': obj.updated_at,
                'created_by': obj.created_by,
                'updated_by': obj.updated_by,
                'version': obj.version
            }
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


class EntityListResponse(BaseModel):
    """Schema for list response"""
    
    items: list[EntityResponse]
    total: int
    skip: int
    limit: int


class StandardErrorDetail(BaseModel):
    """Standard error detail schema"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class StandardMetadata(BaseModel):
    """Standard response metadata"""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="ISO8601 timestamp")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request correlation ID")


class StandardResponse(BaseModel, Generic[T]):
    """Standard response wrapper for all API responses"""
    success: bool = Field(..., description="Whether request was successful")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[StandardErrorDetail] = Field(None, description="Error information if failed")
    metadata: StandardMetadata = Field(default_factory=StandardMetadata, description="Response metadata")


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Schema for health check response"""
    
    status: str
    timestamp: datetime
