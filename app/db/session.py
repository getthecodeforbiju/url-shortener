from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

# Engine - the actual connection to CockroachDB
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # test connection before using it
    pool_size=10,  # max persistentconnections
    max_overflow=20,  # extra connections allowed under load
)

# Session factory - call this to get a session object
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """  FastAPI dependency — yields a DB session per request,
    closes it automatically when the request is done.
    """
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    