"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# Database path
DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "issue_positions.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database, creating all tables."""
    # Import all models to ensure they're registered
    from . import models  # noqa: F401

    # Ensure data directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create all tables
    Base.metadata.create_all(bind=engine)
