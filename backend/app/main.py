from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import engine, Base
# IMPORTANT: Import models here so SQLAlchemy knows about them before creating tables!
import app.models  


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager: Runs code BEFORE the application starts up,
    and handles cleanup when the application shuts down.
    """
    # Startup: Create tables in PostgreSQL
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield  # Application runs while sitting here
    
    # Shutdown logic goes here (if needed in the future)


# Initialize FastAPI app with the lifespan event handler
app = FastAPI(
    title="My FastAPI Backend",
    version="1.0.0",
    lifespan=lifespan
)


# Health Check Route
@app.get("/")
async def health_check():
    return {"status": "healthy"}