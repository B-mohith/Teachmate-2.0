from contextlib import asynccontextmanager
from datetime import timedelta
from typing import List, Optional  # <--- Added Optional here
import uuid

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import engine, Base, get_db
import app.models as models
import app.schemas as schemas
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


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
    current_user: models.User = Depends(get_current_user),  # <--- PROTECTED
):
    """Create a new course linked directly to the logged-in user."""
    new_course = models.Course(
        title=course_in.title,
        #description=course_in.description,
        user_id=current_user.id,  # Set user_id from token payload
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
    current_user: models.User = Depends(get_current_user),  # <--- PROTECTED
):
    """Retrieve all courses created specifically by the logged-in user."""
    result = await db.execute(
        select(models.Course).where(models.Course.user_id == current_user.id)
    )
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
    current_user: models.User = Depends(get_current_user),  # <--- PROTECTED
):
    """Fetch a specific course by ID, ensuring it belongs to the logged-in user."""
    result = await db.execute(
        select(models.Course).where(
            models.Course.id == course_id,
            models.Course.user_id == current_user.id,
        )
    )
    course = result.scalars().first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found",
        )

    return course

# ==========================================
# AUTHENTICATION & USER ENDPOINTS
# ==========================================

@app.post(
    "/users/signup",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
async def signup(
    user_in: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with an email and hashed password."""
    # 1. Check if email already exists
    result = await db.execute(
        select(models.User).where(models.User.email == user_in.email)
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # 2. Hash the user's password
    hashed_pwd = hash_password(user_in.password)

    # 3. Create and save new user record
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_pwd,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@app.post(
    "/auth/login",
    response_model=schemas.Token,
    tags=["Authentication"],
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user credentials using OAuth2 form data.
    Note: OAuth2 spec uses 'username' field to pass the email.
    """
    # 1. Fetch user by email (passed in form_data.username)
    result = await db.execute(
        select(models.User).where(models.User.email == form_data.username)
    )
    user = result.scalars().first()

    # 2. Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create JWT access token with user's UUID string as 'sub'
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }