"""Custom exceptions for Entity Service."""

from typing import Optional, Any, Dict
from app.error_codes import ErrorCode, ERROR_CODE_MESSAGES


class EntityServiceException(Exception):
    """Base exception for Entity Service."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize exception."""
        self.error_code = error_code
        self.message = message or ERROR_CODE_MESSAGES.get(error_code, "Unknown error")
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(EntityServiceException):
    """Validation failed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=400,
            details=details
        )


class EntityTypeExistsError(EntityServiceException):
    """Entity type already exists."""
    def __init__(self, entity_type: str):
        super().__init__(
            error_code=ErrorCode.ENTITY_TYPE_EXISTS,
            message=f"Entity type '{entity_type}' already exists",
            status_code=409
        )


class EntityTypeNotFoundError(EntityServiceException):
    """Entity type not found."""
    def __init__(self, entity_type: str):
        super().__init__(
            error_code=ErrorCode.ENTITY_TYPE_NOT_FOUND,
            message=f"Entity type '{entity_type}' does not exist",
            status_code=404
        )


class EntityTypeInactiveError(EntityServiceException):
    """Entity type is inactive."""
    def __init__(self, entity_type: str):
        super().__init__(
            error_code=ErrorCode.ENTITY_TYPE_INACTIVE,
            message=f"Entity type '{entity_type}' is inactive",
            status_code=400
        )


class InvalidSchemaError(EntityServiceException):
    """Schema definition is invalid."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.INVALID_SCHEMA,
            message=message,
            status_code=400,
            details=details
        )


class InvalidColumnTypeError(EntityServiceException):
    """Column type is not supported."""
    def __init__(self, column_type: str):
        super().__init__(
            error_code=ErrorCode.INVALID_COLUMN_TYPE,
            message=f"Column type '{column_type}' is not supported",
            status_code=400
        )


class DuplicateColumnError(EntityServiceException):
    """Column name already exists."""
    def __init__(self, column_name: str):
        super().__init__(
            error_code=ErrorCode.DUPLICATE_COLUMN,
            message=f"Column '{column_name}' already exists in schema",
            status_code=400
        )


class RequestorMismatchError(EntityServiceException):
    """Entity type belongs to different requestor."""
    def __init__(self, entity_type: str, requestor: str):
        super().__init__(
            error_code=ErrorCode.REQUESTOR_MISMATCH,
            message=f"Entity type '{entity_type}' is not available for requestor '{requestor}'",
            status_code=403
        )


class RequestorUnauthorizedError(EntityServiceException):
    """Requestor not authorized for this operation."""
    def __init__(self, operation: str, entity_type: str):
        super().__init__(
            error_code=ErrorCode.REQUESTOR_UNAUTHORIZED,
            message=f"Requestor is not authorized to {operation} on entity type '{entity_type}'",
            status_code=403
        )


class EntityNotFoundError(EntityServiceException):
    """Entity instance not found."""
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            error_code=ErrorCode.ENTITY_NOT_FOUND,
            message=f"Entity '{entity_id}' not found in '{entity_type}'",
            status_code=404
        )


class SchemaModificationFailedError(EntityServiceException):
    """Failed to modify entity type schema safely."""
    def __init__(self, message: str):
        super().__init__(
            error_code=ErrorCode.SCHEMA_MODIFICATION_FAILED,
            message=message,
            status_code=400
        )


class DDLOperationFailedError(EntityServiceException):
    """DDL operation failed."""
    def __init__(self, message: str):
        super().__init__(
            error_code=ErrorCode.DDL_OPERATION_FAILED,
            message=message,
            status_code=500
        )


class DMLOperationFailedError(EntityServiceException):
    """DML operation failed."""
    def __init__(self, message: str):
        super().__init__(
            error_code=ErrorCode.DML_OPERATION_FAILED,
            message=message,
            status_code=500
        )


class SoftDeleteFailedError(EntityServiceException):
    """Soft delete operation failed."""
    def __init__(self, message: str):
        super().__init__(
            error_code=ErrorCode.SOFT_DELETE_FAILED,
            message=message,
            status_code=500
        )


class HardDeleteFailedError(EntityServiceException):
    """Hard delete operation failed."""
    def __init__(self, message: str):
        super().__init__(
            error_code=ErrorCode.HARD_DELETE_FAILED,
            message=message,
            status_code=500
        )
