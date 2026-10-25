from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic import command
from app.main import create_app
from app.shared.database import engine, get_db


@pytest.fixture
def test_engine():
    # Cada prueba usa un esquema nuevo, nunca las tablas del usuario.
    schema = f"test_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    isolated = create_engine(
        engine.url, connect_args={"options": f"-csearch_path={schema}"}
    )
    try:
        with isolated.begin() as connection:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield isolated
    finally:
        isolated.dispose()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))


@pytest.fixture
def client(test_engine):
    app = create_app()

    def override_db():
        with Session(test_engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as http:
        yield http
