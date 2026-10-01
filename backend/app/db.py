"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create all tables if they do not exist."""
    from app import models  # noqa: F401  Registers table metadata.

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
