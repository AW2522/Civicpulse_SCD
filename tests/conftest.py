import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config import settings
from app.core.database import Base, get_db
from app.core.redis import get_redis_client

# Use SQLite in-memory for fast, deterministic unit tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Create database tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def mock_redis():
    """Creates a mock Redis client fixture for testing."""
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.ttl.return_value = 60
    mock.delete.return_value = 1
    return mock


@pytest_asyncio.fixture
async def client(mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """HTTP AsyncClient fixture for FastAPI application testing."""
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("app.core.redis.get_redis_client", return_value=mock_redis), \
         patch("app.services.rate_limiter.get_redis_client", return_value=mock_redis), \
         patch("app.services.stats_service.get_redis_client", return_value=mock_redis), \
         patch("app.services.complaint_service.get_redis_client", return_value=mock_redis), \
         patch("app.providers.triage_factory.get_redis_client", return_value=mock_redis), \
         patch("app.routes.probes.check_db_health", return_value=True), \
         patch("app.routes.probes.check_redis_health", return_value=True):
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
