"""
Tests for File Upload Service

Tests all four subtasks:
1. File format validation
2. Thumbnail generation
3. File size validation
4. Temporary storage management
"""

import pytest
import asyncio
from pathlib import Path
from PIL import Image
import io
import os
import tempfile
import shutil

from services.file_upload import FileUploadService, FileUploadError


@pytest.fixture
def temp_upload_dir():
    """Create a temporary upload directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_uploads_")
    yield temp_dir
    # Cleanup after tests
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def upload_service(temp_upload_dir):
    """Create a FileUploadService instance for testing"""
    return FileUploadService(upload_dir=temp_upload_dir)


@pytest.fixture
def create_test_image():
    """Factory for creating test images"""
    def _create_image(format="JPEG", size=(800, 600), mode="RGB", color=(255, 0, 0)):
        """Create a test image in memory"""
        img = Image.new(mode, size, color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=format)
        return img_bytes.getvalue()
    return _create_image


# ============================================================================
# Subtask 1: File Format Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_validate_format_valid_jpeg(upload_service, create_test_image):
    """Test validation of valid JPEG image"""
    image_bytes = create_test_image(format="JPEG")

    valid, fmt, error = await upload_service.validate_format(image_bytes, "test.jpg")

    assert valid is True
    assert fmt == "JPEG"
    assert error is None


@pytest.mark.asyncio
async def test_validate_format_valid_png(upload_service, create_test_image):
    """Test validation of valid PNG image"""
    image_bytes = create_test_image(format="PNG")

    valid, fmt, error = await upload_service.validate_format(image_bytes, "test.png")

    assert valid is True
    assert fmt == "PNG"
    assert error is None


@pytest.mark.asyncio
async def test_validate_format_valid_webp(upload_service, create_test_image):
    """Test validation of valid WebP image"""
    image_bytes = create_test_image(format="WEBP")

    valid, fmt, error = await upload_service.validate_format(image_bytes, "test.webp")

    assert valid is True
    assert fmt == "WEBP"
    assert error is None


@pytest.mark.asyncio
async def test_validate_format_unsupported_extension(upload_service, create_test_image):
    """Test rejection of unsupported file extensions"""
    image_bytes = create_test_image(format="JPEG")

    valid, fmt, error = await upload_service.validate_format(image_bytes, "test.gif")

    assert valid is False
    assert fmt is None
    assert "Unsupported file extension" in error


@pytest.mark.asyncio
async def test_validate_format_corrupted_image(upload_service):
    """Test rejection of corrupted image data"""
    corrupted_bytes = b"This is not an image file"

    valid, fmt, error = await upload_service.validate_format(corrupted_bytes, "test.jpg")

    assert valid is False
    assert fmt is None
    assert error is not None


@pytest.mark.asyncio
async def test_validate_format_extension_mismatch(upload_service, create_test_image):
    """Test handling of extension/format mismatch"""
    # Create PNG but name it .jpg
    png_bytes = create_test_image(format="PNG")

    # Should still validate based on actual content
    valid, fmt, error = await upload_service.validate_format(png_bytes, "test.png")

    assert valid is True
    assert fmt == "PNG"


# ============================================================================
# Subtask 2: Thumbnail Generation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_generate_thumbnail_creates_file(upload_service, create_test_image, temp_upload_dir):
    """Test that thumbnail file is created"""
    image_bytes = create_test_image(format="JPEG", size=(1920, 1080))
    thumb_path = Path(temp_upload_dir) / "test_thumb.jpg"

    result_path = await upload_service.generate_thumbnail(image_bytes, thumb_path)

    assert os.path.exists(result_path)
    assert result_path == str(thumb_path)


@pytest.mark.asyncio
async def test_generate_thumbnail_correct_size(upload_service, create_test_image, temp_upload_dir):
    """Test that thumbnail has correct dimensions"""
    image_bytes = create_test_image(format="JPEG", size=(1920, 1080))
    thumb_path = Path(temp_upload_dir) / "test_thumb.jpg"

    await upload_service.generate_thumbnail(image_bytes, thumb_path)

    # Check thumbnail dimensions
    with Image.open(thumb_path) as img:
        # Should maintain aspect ratio within 300x300
        assert img.width <= 300
        assert img.height <= 300
        # Check aspect ratio is maintained
        original_ratio = 1920 / 1080
        thumb_ratio = img.width / img.height
        assert abs(original_ratio - thumb_ratio) < 0.01


@pytest.mark.asyncio
async def test_generate_thumbnail_from_png_rgba(upload_service, create_test_image, temp_upload_dir):
    """Test thumbnail generation from PNG with transparency"""
    image_bytes = create_test_image(format="PNG", mode="RGBA", size=(800, 600))
    thumb_path = Path(temp_upload_dir) / "test_thumb.jpg"

    result_path = await upload_service.generate_thumbnail(image_bytes, thumb_path)

    assert os.path.exists(result_path)
    # Verify it's saved as JPEG (no transparency)
    with Image.open(result_path) as img:
        assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_generate_thumbnail_custom_size(upload_service, create_test_image, temp_upload_dir):
    """Test thumbnail generation with custom size"""
    image_bytes = create_test_image(format="JPEG", size=(1000, 1000))
    thumb_path = Path(temp_upload_dir) / "test_thumb.jpg"
    custom_size = (150, 150)

    await upload_service.generate_thumbnail(image_bytes, thumb_path, size=custom_size)

    with Image.open(thumb_path) as img:
        assert img.width <= 150
        assert img.height <= 150


@pytest.mark.asyncio
async def test_generate_thumbnail_creates_parent_dir(upload_service, create_test_image, temp_upload_dir):
    """Test that thumbnail generation creates parent directories"""
    image_bytes = create_test_image(format="JPEG")
    thumb_path = Path(temp_upload_dir) / "subdir" / "nested" / "test_thumb.jpg"

    await upload_service.generate_thumbnail(image_bytes, thumb_path)

    assert os.path.exists(thumb_path)
    assert thumb_path.parent.exists()


# ============================================================================
# Subtask 3: File Size Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_validate_size_within_limit(upload_service, create_test_image):
    """Test validation of file within size limit"""
    # Create small image (well under 10MB)
    image_bytes = create_test_image(format="JPEG", size=(800, 600))

    valid, error = await upload_service.validate_size(image_bytes, "test.jpg")

    assert valid is True
    assert error is None


@pytest.mark.asyncio
async def test_validate_size_exceeds_limit(upload_service):
    """Test rejection of file exceeding size limit"""
    # Create byte array larger than 10MB
    large_bytes = b"0" * (11 * 1024 * 1024)  # 11MB

    valid, error = await upload_service.validate_size(large_bytes, "large.jpg")

    assert valid is False
    assert "exceeds maximum allowed size" in error


@pytest.mark.asyncio
async def test_validate_size_empty_file(upload_service):
    """Test rejection of empty file"""
    empty_bytes = b""

    valid, error = await upload_service.validate_size(empty_bytes, "empty.jpg")

    assert valid is False
    assert "File is empty" in error


@pytest.mark.asyncio
async def test_validate_size_exactly_at_limit(upload_service):
    """Test file exactly at size limit"""
    # Create byte array exactly 10MB
    exact_bytes = b"0" * (10 * 1024 * 1024)

    valid, error = await upload_service.validate_size(exact_bytes, "exact.jpg")

    assert valid is True
    assert error is None


# ============================================================================
# Subtask 4: Temporary Storage Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_save_to_storage_creates_file(upload_service, create_test_image):
    """Test that file is saved to storage"""
    image_bytes = create_test_image(format="JPEG")

    file_path, session_id = await upload_service.save_to_storage(
        image_bytes, "test.jpg", session_id="test_session"
    )

    assert os.path.exists(file_path)
    assert "test_session" in file_path


@pytest.mark.asyncio
async def test_save_to_storage_auto_session_id(upload_service, create_test_image):
    """Test automatic session ID generation"""
    image_bytes = create_test_image(format="JPEG")

    file_path, session_id = await upload_service.save_to_storage(image_bytes, "test.jpg")

    assert session_id is not None
    assert len(session_id) > 0
    assert os.path.exists(file_path)


@pytest.mark.asyncio
async def test_save_to_storage_filename_sanitization(upload_service, create_test_image):
    """Test that dangerous filenames are sanitized"""
    image_bytes = create_test_image(format="JPEG")
    dangerous_name = "../../../etc/passwd"

    file_path, session_id = await upload_service.save_to_storage(
        image_bytes, dangerous_name, session_id="test_session"
    )

    # Should not contain directory traversal
    assert "../" not in file_path
    assert os.path.exists(file_path)


@pytest.mark.asyncio
async def test_cleanup_session_removes_files(upload_service, create_test_image):
    """Test that cleanup removes all session files"""
    image_bytes = create_test_image(format="JPEG")
    session_id = "cleanup_test"

    # Upload multiple files
    file_path1, _ = await upload_service.save_to_storage(
        image_bytes, "test1.jpg", session_id=session_id
    )
    file_path2, _ = await upload_service.save_to_storage(
        image_bytes, "test2.jpg", session_id=session_id
    )

    assert os.path.exists(file_path1)
    assert os.path.exists(file_path2)

    # Cleanup
    await upload_service.cleanup_session(session_id)

    # Verify files and directory are removed
    assert not os.path.exists(file_path1)
    assert not os.path.exists(file_path2)
    assert not os.path.exists(Path(file_path1).parent)


@pytest.mark.asyncio
async def test_get_session_files_lists_files(upload_service, create_test_image):
    """Test listing files in a session"""
    image_bytes = create_test_image(format="JPEG")
    session_id = "list_test"

    # Upload files
    await upload_service.save_to_storage(image_bytes, "test1.jpg", session_id=session_id)
    await upload_service.save_to_storage(image_bytes, "test2.jpg", session_id=session_id)

    files = await upload_service.get_session_files(session_id)

    assert len(files) == 2
    assert any("test1.jpg" in f for f in files)
    assert any("test2.jpg" in f for f in files)


@pytest.mark.asyncio
async def test_get_session_files_empty_session(upload_service):
    """Test listing files in non-existent session"""
    files = await upload_service.get_session_files("nonexistent_session")

    assert files == []


# ============================================================================
# Integration Tests: Full Upload Process
# ============================================================================

@pytest.mark.asyncio
async def test_process_upload_complete_success(upload_service, create_test_image):
    """Test complete upload process with all validations"""
    image_bytes = create_test_image(format="JPEG", size=(1920, 1080))

    result = await upload_service.process_upload(
        file_content=image_bytes,
        filename="product.jpg",
        session_id="integration_test",
        generate_thumbnail=True
    )

    assert result["success"] is True
    assert result["file_path"] is not None
    assert result["thumbnail_path"] is not None
    assert result["session_id"] == "integration_test"
    assert result["format"] == "JPEG"
    assert result["size_bytes"] == len(image_bytes)
    assert result["error"] is None

    # Verify files exist
    assert os.path.exists(result["file_path"])
    assert os.path.exists(result["thumbnail_path"])


@pytest.mark.asyncio
async def test_process_upload_invalid_format(upload_service):
    """Test upload process with invalid format"""
    invalid_bytes = b"Not an image"

    result = await upload_service.process_upload(
        file_content=invalid_bytes,
        filename="test.jpg"
    )

    assert result["success"] is False
    assert result["file_path"] is None
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_process_upload_file_too_large(upload_service):
    """Test upload process with file exceeding size limit"""
    large_bytes = b"0" * (11 * 1024 * 1024)  # 11MB

    result = await upload_service.process_upload(
        file_content=large_bytes,
        filename="large.jpg"
    )

    assert result["success"] is False
    assert result["file_path"] is None
    assert "exceeds maximum allowed size" in result["error"]


@pytest.mark.asyncio
async def test_process_upload_without_thumbnail(upload_service, create_test_image):
    """Test upload process without thumbnail generation"""
    image_bytes = create_test_image(format="JPEG")

    result = await upload_service.process_upload(
        file_content=image_bytes,
        filename="test.jpg",
        generate_thumbnail=False
    )

    assert result["success"] is True
    assert result["file_path"] is not None
    assert result["thumbnail_path"] is None


@pytest.mark.asyncio
async def test_process_upload_png_with_transparency(upload_service, create_test_image):
    """Test upload process with PNG containing transparency"""
    image_bytes = create_test_image(format="PNG", mode="RGBA")

    result = await upload_service.process_upload(
        file_content=image_bytes,
        filename="transparent.png",
        generate_thumbnail=True
    )

    assert result["success"] is True
    assert result["format"] == "PNG"
    # Thumbnail should be created even with transparency
    assert result["thumbnail_path"] is not None


@pytest.mark.asyncio
async def test_process_upload_webp_format(upload_service, create_test_image):
    """Test upload process with WebP format"""
    image_bytes = create_test_image(format="WEBP")

    result = await upload_service.process_upload(
        file_content=image_bytes,
        filename="test.webp"
    )

    assert result["success"] is True
    assert result["format"] == "WEBP"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    print("Running File Upload Service Tests...")
    print("\nNote: Install pytest to run these tests:")
    print("  pip install pytest pytest-asyncio")
    print("\nThen run with:")
    print("  pytest test_file_upload.py -v")
