from contextlib import asynccontextmanager
from typing import List, Optional  # <--- Added Optional here
import uuid

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import engine, Base, get_db
import app.models as models
import app.schemas as schemas


# Global variable to store our dummy user's UUID (Python 3.9 compatible)
DUMMY_USER_ID: Optional[uuid.UUID] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global DUMMY_USER_ID

    # 1. Create tables in PostgreSQL if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed a Dummy User so courses can be attached to a valid user_id
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(models.User).where(models.User.email == "dummy@example.com")
        )
        dummy_user = result.scalars().first()

        if not dummy_user:
            dummy_user = models.User(
                email="dummy@example.com",
                hashed_password="notahashedpasswordyet",
            )
            session.add(dummy_user)
            await session.commit()
            await session.refresh(dummy_user)

        DUMMY_USER_ID = dummy_user.id

    yield  # Application runs while sitting here


app = FastAPI(
    title="Teachmate API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


# ==========================================
# COURSE CRUD ENDPOINTS
# ==========================================

@app.post(
    "/courses/",
    response_model=schemas.CourseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Courses"],
)
async def create_course(
    course_in: schemas.CourseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new course linked to the dummy user."""
    new_course = models.Course(
        title=course_in.title,
        #description=course_in.description,
        user_id=DUMMY_USER_ID,
    )

    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)

    return new_course


@app.get(
    "/courses/",
    response_model=List[schemas.CourseResponse],
    tags=["Courses"],
)
async def get_courses(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all courses from PostgreSQL."""
    result = await db.execute(select(models.Course))
    courses = result.scalars().all()
    return courses


@app.get(
    "/courses/{course_id}",
    response_model=schemas.CourseResponse,
    tags=["Courses"],
)
async def get_course_by_id(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single course by its UUID."""
    result = await db.execute(
        select(models.Course).where(models.Course.id == course_id)
    )
    course = result.scalars().first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found",
        )

    return course