import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.database as database_module
from app.database import Base, get_db
from app.main import app as fastapi_app
import app.middleware.account_isolation  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def disable_real_llm(monkeypatch: pytest.MonkeyPatch):
    from app.config import get_settings
    from app.services.llm_client import reset_llm_client

    settings = get_settings().model_copy(
        update={"openai_api_key": None, "dna_tag_use_celery": False}
    )
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.llm_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.dna_trigger.get_settings", lambda: settings)
    reset_llm_client()
    yield
    reset_llm_client()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    original_session_factory = database_module.async_session_factory
    database_module.async_session_factory = session_factory

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
    database_module.async_session_factory = original_session_factory
