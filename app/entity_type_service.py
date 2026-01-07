"""Service for entity type management (DDL operations)."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, DateTime, Index, select
from datetime import datetime

from app.database import Base, EntityTypeDefinition, create_dynamic_entity_model, _dynamic_models
from app.schemas import EntityTypeCreate, EntityTypeResponse, ColumnDefinition, ColumnType


class EntityTypeService:
    """Service for managing entity types (DDL operations)."""
    
    def __init__(self, session: AsyncSession, engine):
        self.session = session
        self.engine = engine
    
    def _column_type_to_sqlalchemy(self, col_def: ColumnDefinition) -> Column:
        """Convert column definition to SQLAlchemy Column."""
        type_mapping = {
            ColumnType.STRING: String(col_def.max_length or 255),
            ColumnType.INTEGER: Integer,
            ColumnType.FLOAT: Float,
            ColumnType.BOOLEAN: Boolean,
            ColumnType.TEXT: Text,
            ColumnType.JSON: JSON,
            ColumnType.DATETIME: DateTime,
        }
        
        col_type = type_mapping[col_def.type]
        
        return Column(
            col_def.name,
            col_type,
            nullable=col_def.nullable,
            unique=col_def.unique,
            index=col_def.indexed,
            default=col_def.default
        )
    
    async def create_entity_type(self, entity_type_data: EntityTypeCreate) -> EntityTypeResponse:
        """Create a new entity type and its table (DDL operation)."""
        
        # Check if entity type already exists
        result = await self.session.execute(
            select(EntityTypeDefinition).where(
                EntityTypeDefinition.entity_type == entity_type_data.entity_type
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"Entity type '{entity_type_data.entity_type}' already exists")
        
        # Generate table name
        table_name = f"entity_{entity_type_data.entity_type}"
        
        # Convert column definitions to SQLAlchemy columns
        additional_columns = {}
        schema_def = {}
        
        for col_def in entity_type_data.columns:
            additional_columns[col_def.name] = self._column_type_to_sqlalchemy(col_def)
            schema_def[col_def.name] = {
                "type": col_def.type.value,
                "nullable": col_def.nullable,
                "unique": col_def.unique,
                "indexed": col_def.indexed,
                "max_length": col_def.max_length,
                "default": col_def.default,
                "description": col_def.description
            }
        
        # Create dynamic model
        model_class = create_dynamic_entity_model(
            entity_type=entity_type_data.entity_type,
            table_name=table_name,
            additional_columns=additional_columns
        )
        
        # Create the table in database
        async with self.engine.begin() as conn:
            await conn.run_sync(model_class.__table__.create)
        
        # Cache the model
        _dynamic_models[entity_type_data.entity_type] = model_class
        
        # Register entity type in registry
        entity_type_def = EntityTypeDefinition(
            entity_type=entity_type_data.entity_type,
            table_name=table_name,
            schema_definition=schema_def,
            description=entity_type_data.description,
            created_by=entity_type_data.created_by
        )
        
        self.session.add(entity_type_def)
        await self.session.commit()
        await self.session.refresh(entity_type_def)
        
        return EntityTypeResponse.model_validate(entity_type_def)
    
    async def get_entity_type(self, entity_type: str) -> Optional[EntityTypeResponse]:
        """Get entity type definition."""
        result = await self.session.execute(
            select(EntityTypeDefinition).where(
                EntityTypeDefinition.entity_type == entity_type
            )
        )
        entity_type_def = result.scalar_one_or_none()
        
        if not entity_type_def:
            return None
        
        return EntityTypeResponse.model_validate(entity_type_def)
    
    async def list_entity_types(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> tuple[List[EntityTypeResponse], int]:
        """List all registered entity types."""
        query = select(EntityTypeDefinition)
        
        if is_active is not None:
            query = query.where(EntityTypeDefinition.is_active == is_active)
        
        # Get total count
        count_result = await self.session.execute(
            select(EntityTypeDefinition).where(
                EntityTypeDefinition.is_active == is_active if is_active is not None else True
            )
        )
        total = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        entity_types = result.scalars().all()
        
        return [EntityTypeResponse.model_validate(et) for et in entity_types], total
    
    async def delete_entity_type(self, entity_type: str) -> bool:
        """Delete entity type (mark as inactive, don't drop table)."""
        result = await self.session.execute(
            select(EntityTypeDefinition).where(
                EntityTypeDefinition.entity_type == entity_type
            )
        )
        entity_type_def = result.scalar_one_or_none()
        
        if not entity_type_def:
            return False
        
        entity_type_def.is_active = False
        entity_type_def.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def load_entity_types(self) -> None:
        """Load all registered entity types and cache their models."""
        result = await self.session.execute(
            select(EntityTypeDefinition).where(EntityTypeDefinition.is_active == True)
        )
        entity_types = result.scalars().all()
        
        for et in entity_types:
            if et.entity_type not in _dynamic_models:
                # Recreate model from schema
                additional_columns = {}
                for col_name, col_info in et.schema_definition.items():
                    col_def = ColumnDefinition(
                        name=col_name,
                        type=col_info["type"],
                        nullable=col_info.get("nullable", True),
                        unique=col_info.get("unique", False),
                        indexed=col_info.get("indexed", False),
                        max_length=col_info.get("max_length"),
                        default=col_info.get("default"),
                        description=col_info.get("description")
                    )
                    additional_columns[col_name] = self._column_type_to_sqlalchemy(col_def)
                
                model_class = create_dynamic_entity_model(
                    entity_type=et.entity_type,
                    table_name=et.table_name,
                    additional_columns=additional_columns
                )
                _dynamic_models[et.entity_type] = model_class
