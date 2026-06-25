from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from beelife.db.models import SQLModel


@pytest.fixture(scope="function")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("timescale/timescaledb:latest-pg16") as postgres:
        yield postgres


@pytest.fixture(scope="function")
async def async_engine(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create a fresh engine + tables for each test."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    db = postgres_container.dbname

    database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    engine = create_async_engine(database_url, echo=False)

    async with engine.connect() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("SELECT create_hypertable('beedar_readings', 'timestamp', if_not_exists => TRUE)"))
        await conn.execute(text("SELECT create_hypertable('weather_observations', 'timestamp', if_not_exists => TRUE)"))
        await conn.commit()

    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    connection = await async_engine.connect()
    transaction = await connection.begin()

    async_session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = async_session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
