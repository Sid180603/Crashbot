"""
Pytest configuration and fixtures for Crashbot tests
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db

# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("crashbot_db", "crashbot_test_db")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_crash_data() -> dict:
    """Sample crash dump data for testing"""
    return {
        "exception_code": "0xC0000005",
        "exception_message": "Access Violation",
        "faulting_module": "myapp.exe",
        "faulting_address": "0x00401234",
        "platform": "Windows 10",
        "architecture": "x64",
        "stack_trace": [
            {
                "address": "0x00401234",
                "module": "myapp.exe",
                "function": "main",
                "offset": "+0x34"
            },
            {
                "address": "0x77001234",
                "module": "ntdll.dll",
                "function": "RtlUserThreadStart",
                "offset": "+0x21"
            }
        ],
        "loaded_modules": [
            {
                "name": "myapp.exe",
                "base_address": "0x00400000",
                "size": "0x10000",
                "version": "1.0.0.0"
            }
        ],
        "threads": [
            {
                "id": 1234,
                "name": "Main Thread",
                "state": "Running"
            }
        ]
    }


@pytest.fixture
def mock_llm_response() -> dict:
    """Mock LLM analysis response"""
    return {
        "root_cause": "Null pointer dereference in main function",
        "explanation": "The application attempted to access memory at an invalid address, likely due to a null pointer dereference.",
        "solutions": [
            {
                "title": "Add null pointer check",
                "description": "Check if pointer is null before dereferencing",
                "priority": 1,
                "code_example": "if (ptr != NULL) { *ptr = value; }"
            }
        ],
        "severity": "high",
        "confidence_score": 85,
        "references": [
            "https://docs.microsoft.com/en-us/windows/win32/debug/exception-codes"
        ]
    }


@pytest.fixture
def temp_dump_file(tmp_path):
    """Create a temporary Windows minidump file for testing"""
    dump_file = tmp_path / "test_crash.dmp"
    dump_file.write_bytes(b"MDMP" + b"\x00" * 1024)
    return str(dump_file)


@pytest.fixture
def linux_dump_file(tmp_path):
    """Create a temporary Linux core dump file for testing"""
    dump_file = tmp_path / "test_crash.core"
    dump_file.write_bytes(b"\x7fELF" + b"\x00" * 1024)
    return str(dump_file)
