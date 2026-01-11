"""Database configuration and models."""

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer, MetaData
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Type
import uuid

Base = declarative_base()
metadata_obj = MetaData()


class EntityTypeDefinition(Base):
    """Registry table for entity types with their schema definitions."""
    
    __tablename__ = "entity_type_definitions"
    
    entity_type = Column(String(100), primary_key=True)
    table_name = Column(String(100), nullable=False, unique=True)
    schema_definition = Column(JSON, nullable=False)  # Column definitions
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<EntityTypeDefinition(type={self.entity_type}, table={self.table_name})>"


def create_dynamic_entity_model(
    entity_type: str,
    table_name: str,
    additional_columns: Optional[Dict[str, Any]] = None
) -> Type:
    """Create a dynamic SQLAlchemy model for an entity type.
    
    Args:
        entity_type: Name of the entity type
        table_name: Database table name
        additional_columns: Optional dict of column_name -> SQLAlchemy Column
        
    Returns:
        Dynamically created SQLAlchemy model class
    """
    base_columns = {
        "__tablename__": table_name,
        "id": Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        "is_active": Column(Boolean, default=True, nullable=False),
        "created_at": Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False),
        "updated_at": Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False),
        "created_by": Column(String(255), nullable=True),
        "updated_by": Column(String(255), nullable=True),
        "version": Column(Integer, default=1, nullable=False),
    }
    
    if additional_columns:
        base_columns.update(additional_columns)
    
    model_class = type(
        f"{entity_type.capitalize()}Entity",
        (Base,),
        base_columns
    )
    
    return model_class


# Cache for dynamically created models
_dynamic_models: Dict[str, Type] = {}


class Entity(Base):
    """Base entity model for CRUD operations."""
    
    __tablename__ = "entities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="active", nullable=False)
    data = Column(JSON, nullable=True)
    entity_metadata = Column("metadata", JSON, nullable=True)  # Renamed to avoid SQLAlchemy reserved name
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<Entity(id={self.id}, name={self.name}, type={self.entity_type})>"
