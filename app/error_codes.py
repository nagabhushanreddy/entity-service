"""Error codes for Entity Service API."""

from enum import Enum
from typing import Dict

class ErrorCode(str, Enum):
    """Standard error codes for Entity Service."""
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Entity Type errors (DDL)
    ENTITY_TYPE_EXISTS = "ENTITY_TYPE_EXISTS"
    ENTITY_TYPE_NOT_FOUND = "ENTITY_TYPE_NOT_FOUND"
    ENTITY_TYPE_INACTIVE = "ENTITY_TYPE_INACTIVE"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    INVALID_COLUMN_TYPE = "INVALID_COLUMN_TYPE"
    SCHEMA_MODIFICATION_FAILED = "SCHEMA_MODIFICATION_FAILED"
    DDL_OPERATION_FAILED = "DDL_OPERATION_FAILED"
    DUPLICATE_COLUMN = "DUPLICATE_COLUMN"
    
    # Entity instance errors (DML)
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ENTITY_ALREADY_EXISTS = "ENTITY_ALREADY_EXISTS"
    DML_OPERATION_FAILED = "DML_OPERATION_FAILED"
    SOFT_DELETE_FAILED = "SOFT_DELETE_FAILED"
    HARD_DELETE_FAILED = "HARD_DELETE_FAILED"
    
    # Request/Field errors
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FILTER = "INVALID_FILTER"
    INVALID_PAGINATION = "INVALID_PAGINATION"
    
    # Authorization errors
    REQUESTOR_MISMATCH = "REQUESTOR_MISMATCH"
    REQUESTOR_UNAUTHORIZED = "REQUESTOR_UNAUTHORIZED"
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Error code descriptions
ERROR_CODE_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Request validation failed",
    ErrorCode.ENTITY_TYPE_EXISTS: "Entity type already exists",
    ErrorCode.ENTITY_TYPE_NOT_FOUND: "Entity type does not exist",
    ErrorCode.ENTITY_TYPE_INACTIVE: "Entity type is inactive",
    ErrorCode.INVALID_SCHEMA: "Schema definition is invalid",
    ErrorCode.INVALID_COLUMN_TYPE: "Column type is not supported",
    ErrorCode.REQUESTOR_MISMATCH: "Entity type belongs to different requestor",
    ErrorCode.REQUESTOR_UNAUTHORIZED: "Requestor not authorized for this operation",
    ErrorCode.SCHEMA_MODIFICATION_FAILED: "Failed to modify entity type schema safely",
    ErrorCode.DDL_OPERATION_FAILED: "DDL operation failed",
    ErrorCode.DML_OPERATION_FAILED: "DML operation failed",
    ErrorCode.SOFT_DELETE_FAILED: "Soft delete operation failed",
    ErrorCode.HARD_DELETE_FAILED: "Hard delete operation failed",
    ErrorCode.DUPLICATE_COLUMN: "Column name already exists in schema",
    ErrorCode.ENTITY_NOT_FOUND: "Entity instance not found",
    ErrorCode.ENTITY_ALREADY_EXISTS: "Entity with unique constraint already exists",
    ErrorCode.MISSING_REQUIRED_FIELD: "Required field missing in request",
    ErrorCode.INVALID_FILTER: "Invalid filter parameter",
    ErrorCode.INVALID_PAGINATION: "Invalid pagination parameters",
    ErrorCode.UNAUTHORIZED: "Missing or invalid authentication",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests",
    ErrorCode.INTERNAL_ERROR: "Server error",
}
