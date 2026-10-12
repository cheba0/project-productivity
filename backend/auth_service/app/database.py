from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from auth_service.app.config import settings


engine = create_engine(
    settings.auth_database_url,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
