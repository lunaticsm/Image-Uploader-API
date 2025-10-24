from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import DB_CONNECT_ARGS, DB_URL

engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
