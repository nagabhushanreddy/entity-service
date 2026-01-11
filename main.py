import os
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, EntityTypeDefinition, _dynamic_models, init_session_maker
from app.routes import entity_type_router, get_dynamic_router, discovery_router, entity_router
from app.services import EntityTypeService
from app.middleware import RequestContextMiddleware, get_correlation_id
from app.exceptions import EntityServiceException
from app.error_codes import ERROR_CODE_MESSAGES, ErrorCode
from app.schemas import StandardResponse, StandardErrorDetail, StandardMetadata
from utils import logger

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
            app.include_router(dynamic_router, prefix=settings.API_PREFIX)
            logger.info(f"Registered dynamic router for entity type: {entity_type}")


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global engine
    
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Server: {settings.HOST}:{settings.PORT}")

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
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Entity API",
    description="Service for CRUD operations and entity management with dynamic table support",
    version="2.0.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(RequestContextMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(EntityServiceException)
async def entity_service_exception_handler(request, exc: EntityServiceException):
    """Handle Entity Service exceptions."""
    response = StandardResponse(
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
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(exclude_none=True, mode='json')
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = {}
    for error in exc.errors():
        field = '.'.join(str(x) for x in error['loc'][1:])
        errors[field] = error['msg']
    
    response = StandardResponse(
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
    )
    
    return JSONResponse(
        status_code=400,
        content=response.model_dump(exclude_none=True, mode='json')
    )


# Include routers
app.include_router(entity_router, prefix=settings.API_PREFIX)
app.include_router(entity_type_router, prefix=settings.API_PREFIX)
app.include_router(discovery_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_PREFIX}/docs",
    }


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.ENVIRONMENT == "development",
    )
