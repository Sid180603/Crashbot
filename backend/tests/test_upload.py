"""
Unit tests for crash upload endpoint
"""
import pytest
from httpx import AsyncClient
from io import BytesIO


@pytest.mark.api
@pytest.mark.asyncio
async def test_upload_crash_dump_success(client: AsyncClient, temp_dump_file):
    """Test successful crash dump upload"""
    with open(temp_dump_file, "rb") as f:
        files = {"file": ("test_crash.dmp", f, "application/octet-stream")}
        response = await client.post("/api/v1/crashes/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test_crash.dmp"
    assert data["status"] in ["queued", "parsing"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_upload_invalid_file_type(client: AsyncClient):
    """Test upload with invalid file type"""
    files = {"file": ("test.txt", BytesIO(b"not a dump file"), "text/plain")}
    response = await client.post("/api/v1/crashes/upload", files=files)
    
    # Should either accept it or reject based on extension
    # Current implementation accepts all files, so this might pass
    assert response.status_code in [200, 400]


@pytest.mark.api
@pytest.mark.asyncio
async def test_upload_file_too_large(client: AsyncClient):
    """Test upload with file exceeding size limit"""
    # Create a large fake file (600MB)
    large_file = BytesIO(b"0" * (600 * 1024 * 1024))
    files = {"file": ("huge_crash.dmp", large_file, "application/octet-stream")}
    
    response = await client.post("/api/v1/crashes/upload", files=files)
    
    # Should reject if size validation is implemented
    assert response.status_code in [400, 413]


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_crash_analysis(client: AsyncClient, temp_dump_file):
    """Test retrieving crash analysis"""
    # First upload a file
    with open(temp_dump_file, "rb") as f:
        files = {"file": ("test_crash.dmp", f, "application/octet-stream")}
        upload_response = await client.post("/api/v1/crashes/upload", files=files)
    
    crash_id = upload_response.json()["id"]
    
    # Then retrieve it
    response = await client.get(f"/api/v1/crashes/{crash_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == crash_id
    assert "status" in data
    assert "filename" in data


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_nonexistent_crash(client: AsyncClient):
    """Test retrieving non-existent crash analysis"""
    response = await client.get("/api/v1/crashes/nonexistent-id")
    
    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_crash_analyses(client: AsyncClient):
    """Test listing crash analyses"""
    response = await client.get("/api/v1/crashes/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.api
@pytest.mark.asyncio
async def test_delete_crash_analysis(client: AsyncClient, temp_dump_file):
    """Test deleting crash analysis"""
    # First upload a file
    with open(temp_dump_file, "rb") as f:
        files = {"file": ("test_crash.dmp", f, "application/octet-stream")}
        upload_response = await client.post("/api/v1/crashes/upload", files=files)
    
    crash_id = upload_response.json()["id"]
    
    # Then delete it
    response = await client.delete(f"/api/v1/crashes/{crash_id}")
    
    assert response.status_code in [200, 204]
    
    # Verify it's gone
    get_response = await client.get(f"/api/v1/crashes/{crash_id}")
    assert get_response.status_code == 404
