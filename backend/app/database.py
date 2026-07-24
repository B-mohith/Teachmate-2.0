import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
load_dotenv()

# 1. Fetch connection details from environment variables (.env)
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
# "postgres_db" is the service name from your docker-compose.yml!
DB_HOST = os.getenv("POSTGRES_HOST", "localhost") 
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Construct the Async PostgreSQL Connection String
# Driver: postgresql+asyncpg
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print("--------------------------------------------------")
print(f"CONNECTING WITH URL: {DATABASE_URL}")
print("--------------------------------------------------")
# 2. Create the Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to True to log raw SQL statements in your terminal (great for debugging)
)

# 3. Create the Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 4. Create a Base class for your future database models (Tables)
class Base(DeclarativeBase):
    pass

# 5. The Session Generator (Dependency for FastAPI)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()