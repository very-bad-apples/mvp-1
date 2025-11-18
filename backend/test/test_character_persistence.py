"""
Unit tests for AssetPersistenceService character reference persistence.

Tests the following methods:
- persist_character_reference()
- associate_character_images_with_job()
- get_character_reference_url()

Run with: pytest backend/test/test_character_persistence.py -v
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from services.asset_persistence import AssetPersistenceService
from services.storage_backend import S3StorageBackend


@pytest.fixture
def mock_s3_storage():
    """Mock S3 storage backend."""
    storage = Mock(spec=S3StorageBackend)
    storage.upload_file = AsyncMock(return_value="https://s3.example.com/image.png")
    storage.exists = AsyncMock(return_value=True)
    storage.generate_presigned_url = Mock(return_value="https://s3.example.com/image.png?sig=abc")
    return storage




@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake image data")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.mark.asyncio
async def test_persist_character_reference_standalone(mock_s3_storage, temp_image_file):
    """Test persisting a standalone character reference image (no job)."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    
    image_id = str(uuid.uuid4())
    url = await service.persist_character_reference(
        image_id=image_id,
        local_image_path=temp_image_file,
        job_id=None
    )
    
    # Verify upload was called with correct cloud path
    mock_s3_storage.upload_file.assert_called_once()
    call_args = mock_s3_storage.upload_file.call_args
    assert call_args[0][0] == temp_image_file
    assert call_args[0][1] == f"character_references/{image_id}.png"
    
    # Verify URL returned
    assert url == "https://s3.example.com/image.png"


@pytest.mark.asyncio
async def test_persist_character_reference_with_job(mock_s3_storage, temp_image_file):
    """Test persisting a character reference image associated with a job."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    
    image_id = str(uuid.uuid4())
    job_id = "job-123"
    
    url = await service.persist_character_reference(
        image_id=image_id,
        local_image_path=temp_image_file,
        job_id=job_id
    )
    
    # Verify upload was called with correct cloud path
    mock_s3_storage.upload_file.assert_called_once()
    call_args = mock_s3_storage.upload_file.call_args
    assert call_args[0][0] == temp_image_file
    assert call_args[0][1] == f"videos/{job_id}/intermediate/character_reference/{image_id}.png"
    
    # Verify URL returned
    assert url == "https://s3.example.com/image.png"


@pytest.mark.asyncio
async def test_persist_character_reference_file_not_found(mock_s3_storage):
    """Test error handling when image file doesn't exist."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    
    with pytest.raises(FileNotFoundError):
        await service.persist_character_reference(
            image_id="abc-123",
            local_image_path="/nonexistent/image.png",
            job_id=None
        )


@pytest.mark.asyncio
async def test_associate_character_images_with_job(mock_s3_storage):
    """Test associating character images with a job."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    
    # Use actual character_reference directory for this test
    actual_char_ref_dir = Path(__file__).parent.parent / "mv" / "outputs" / "character_reference"
    actual_char_ref_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test images
    image_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    
    try:
        # Create test images in actual location
        for image_id in image_ids:
            image_path = actual_char_ref_dir / f"{image_id}.png"
            image_path.write_bytes(b"fake image data")
        
        # Create temp job directory
        with tempfile.TemporaryDirectory() as job_dir:
            urls = await service.associate_character_images_with_job(
                job_id="job-456",
                image_ids=image_ids,
                local_base_path=job_dir
            )
            
            # Verify results
            assert isinstance(urls, list)
            assert len(urls) == 2
            assert all(url == "https://s3.example.com/image.png" for url in urls)
            
            # Verify images were copied to job directory
            job_char_ref_dir = Path(job_dir) / "character_reference"
            assert job_char_ref_dir.exists()
            copied_files = list(job_char_ref_dir.glob("*.png"))
            assert len(copied_files) == 2
            
    finally:
        # Cleanup test images from actual location
        for image_id in image_ids:
            image_path = actual_char_ref_dir / f"{image_id}.png"
            if image_path.exists():
                image_path.unlink()


@pytest.mark.asyncio
async def test_get_character_reference_url_s3(mock_s3_storage):
    """Test generating presigned URL for S3 storage."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    
    with patch('services.asset_persistence.settings') as mock_settings:
        mock_settings.PRESIGNED_URL_EXPIRY = 3600
        
        url = await service.get_character_reference_url(
            image_id="abc-123",
            job_id="job-456",
            extension="png"
        )
    
    # Verify exists was called
    mock_s3_storage.exists.assert_called_once_with(
        "videos/job-456/intermediate/character_reference/abc-123.png"
    )
    
    # Verify presigned URL was generated
    mock_s3_storage.generate_presigned_url.assert_called_once()
    assert url == "https://s3.example.com/image.png?sig=abc"


@pytest.mark.asyncio
async def test_get_character_reference_url_not_exists(mock_s3_storage):
    """Test URL generation when image doesn't exist."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    mock_s3_storage.exists = AsyncMock(return_value=False)
    
    url = await service.get_character_reference_url(
        image_id="nonexistent",
        job_id=None,
        extension="png"
    )
    
    # Should return None when image doesn't exist
    assert url is None
    
    # Presigned URL should not be called
    mock_s3_storage.generate_presigned_url.assert_not_called()


@pytest.mark.asyncio
async def test_persist_job_assets_includes_character_references(mock_s3_storage):
    """Test that persist_job_assets includes character_references in result."""
    service = AssetPersistenceService(storage_backend=mock_s3_storage)
    
    # Create temp job directory with character_reference subdirectory
    with tempfile.TemporaryDirectory() as job_dir:
        char_ref_dir = Path(job_dir) / "character_reference"
        char_ref_dir.mkdir()
        
        # Create test image
        test_image = char_ref_dir / "test.png"
        test_image.write_bytes(b"fake image data")
        
        result = await service.persist_job_assets(
            job_id="job-789",
            local_base_path=job_dir
        )
        
        # Verify character_references key exists in result
        assert "character_references" in result
        assert isinstance(result["character_references"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

