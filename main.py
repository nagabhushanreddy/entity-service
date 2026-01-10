from contextlib import asynccontextmanager
from datetime import datetime
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings, config, initialize_config
from app.database import Base, EntityTypeDefinition, _dynamic_models
from app.dependencies import get_session, init_session_maker
from app.entity_type_routes import entity_type_router
from app.entity_type_service import EntityTypeService
from app.dynamic_routes import get_dynamic_router
from app.discovery_routes import discovery_router
from app.routes import entity_router
from app.middleware import RequestContextMiddleware, get_correlation_id
from app.exceptions import EntityServiceException
from app.error_codes import ERROR_CODE_MESSAGES
from app.schemas import StandardResponse, StandardErrorDetail, StandardMetadata
from utils import init_app_logging

# Configure logging
logger = init_app_logging(
    service_name=settings.SERVICE_NAME
)

# Initialize database
engine = None


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def load_entity_types():
    """Load registered entity types and create dynamic routers."""
    session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        entity_type_service = EntityTypeService(session, engine)
        await entity_type_service.load_entity_types()
        
        # Register dynamic routers for each entity type
        for entity_type in _dynamic_models.keys():
            dynamic_router = get_dynamic_router(entity_type)
            app.include_router(dynamic_router, prefix=config.api_prefix)
            logger.info(f"Registered dynamic router for entity type: {entity_type}")


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan"""
    global engine
    
    # Startup
    # Initialize configuration and logging via utils-service (with local fallback)
    initialize_config()

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        future=True,
        pool_pre_ping=True
    )
    
    session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    init_session_maker(session_maker)
    
    await init_db()
    await load_entity_types()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app with OpenAPI metadata
app = FastAPI(
    title="Entity API",
    description="Service for CRUD operations and entity management with dynamic table support",
    version="2.0.0",
    lifespan=lifespan,
    openapi_url=f"{config.api_prefix}/openapi.json",
    docs_url=f"{config.api_prefix}/docs",
    redoc_url=f"{config.api_prefix}/redoc"
)

# Add middleware for request context handling
app.add_middleware(RequestContextMiddleware)


# Exception handlers
@app.exception_handler(EntityServiceException)
async def entity_service_exception_handler(request, exc: EntityServiceException):
    """Handle Entity Service exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse(
            success=False,
            data=None,
            error=StandardErrorDetail(
                code=exc.error_code.value,
                message=exc.message,
                details=exc.details if exc.details else None
            ),
            metadata=StandardMetadata(
                correlation_id=get_correlation_id()
            )
        ).model_dump(exclude_none=True)
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    from app.error_codes import ErrorCode
    errors = {}
    for error in exc.errors():
        field = '.'.join(str(x) for x in error['loc'][1:])
        errors[field] = error['msg']
    
    return JSONResponse(
        status_code=400,
        content=StandardResponse(
            success=False,
            data=None,
            error=StandardErrorDetail(
                code=ErrorCode.VALIDATION_ERROR.value,
                message=ERROR_CODE_MESSAGES[ErrorCode.VALIDATION_ERROR],
                details=errors if errors else None
            ),
            metadata=StandardMetadata(
                correlation_id=get_correlation_id()
            )
        ).model_dump(exclude_none=True)
    )


# Health check endpoint
@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# Include routers
app.include_router(entity_router, prefix=config.api_prefix)
app.include_router(entity_type_router, prefix=config.api_prefix)
app.include_router(discovery_router, prefix=config.api_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
