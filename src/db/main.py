"""Database initialization and session helpers.

This module creates the SQLAlchemy async engine and exposes helpers for
initializing the database schema and creating async sessions. The engine
is configured from `Config.DATABASE_URL` so it can be swapped between
environments (sqlite for local development, postgres for production,
etc.).
"""

from sqlalchemy.ext.asyncio import create_async_engine
from src.config import Config
from sqlmodel import SQLModel
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from src.auth.models import User
from sqlmodel import select
from sqlalchemy.exc import DatabaseError




engine = create_async_engine(
    url=Config.DATABASE_URL,
    echo=True,
)

async def init_db():

    async with engine.begin() as conn:

        from src.auth.models import User
        from src.elections.models import (
            AllowedVoter,
            Vote,
            Election,
            Position,
            Candidate
        )
        await conn.run_sync(SQLModel.metadata.create_all)

# Session factory configured for async operations
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
)

async def get_Session():
    #Async context manager yielding a database session.
    
    async with async_session_maker() as session:
        yield session

async def db_cleanup():
    async with async_session_maker() as session:
    
            
        try:
            statement = select(User).where(User.email_verified == False)
            result = await session.exec(statement)
            unverified_users = result.all()

            for user in unverified_users:
                session.delete(user)
            await session.commit()
            print("daily cleanup done")
        
        except Exception as e:
            await session.rollback()
            print(f" Cleanup Failed: {e}")
        