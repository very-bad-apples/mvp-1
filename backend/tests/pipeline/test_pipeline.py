"""
Test suite for pipeline core components.

Tests:
- Scene template system
- Asset manager operations
- Error handling system
"""

import asyncio
import pytest
from pathlib import Path
from pipeline.templates import get_scene_template, fill_template, get_available_styles, validate_template
from pipeline.asset_manager import AssetManager
from pipeline.error_handler import (
    PipelineError,
    ErrorCode,
    should_retry,
    get_retry_delay,
    ValidationError,
    APIError,
    categorize_error
)


# ============================================================================
# Template System Tests
# ============================================================================

def test_get_scene_template_luxury():
    """Test luxury template structure."""
    template = get_scene_template("luxury")

    assert template["total_duration"] == 30
    assert template["style_keywords"] == "soft lighting, elegant, premium, refined"
    assert len(template["scenes"]) == 4

    # Check scene durations
    assert template["scenes"][0]["duration"] == 8
    assert template["scenes"][1]["duration"] == 8
    assert template["scenes"][2]["duration"] == 10
    assert template["scenes"][3]["duration"] == 4

    # Check scene types
    assert template["scenes"][0]["type"] == "video"
    assert template["scenes"][1]["type"] == "video"
    assert template["scenes"][2]["type"] == "video"
    assert template["scenes"][3]["type"] == "image"  # Last scene is image

    print("✓ Luxury template structure correct")


def test_get_scene_template_energetic():
    """Test energetic template structure."""
    template = get_scene_template("energetic")

    assert template["total_duration"] == 30
    assert "vibrant" in template["style_keywords"]
    assert len(template["scenes"]) == 4

    print("✓ Energetic template structure correct")


def test_get_scene_template_minimal():
    """Test minimal template structure."""
    template = get_scene_template("minimal")

    assert template["total_duration"] == 30
    assert "clean" in template["style_keywords"]
    assert len(template["scenes"]) == 4

    print("✓ Minimal template structure correct")


def test_get_scene_template_bold():
    """Test bold template structure."""
    template = get_scene_template("bold")

    assert template["total_duration"] == 30
    assert "bold" in template["style_keywords"]
    assert len(template["scenes"]) == 4

    print("✓ Bold template structure correct")


def test_get_scene_template_default():
    """Test that invalid style returns luxury template."""
    template = get_scene_template("invalid_style")

    # Should default to luxury
    assert template["style_keywords"] == "soft lighting, elegant, premium, refined"

    print("✓ Default template fallback works")


def test_fill_template():
    """Test template placeholder filling."""
    template = get_scene_template("luxury")
    filled = fill_template(template, "Premium Watch", "Shop Now")

    # Check that placeholders were replaced
    assert "Premium Watch" in filled["scenes"][0]["voiceover_template"]
    assert "Shop Now" in filled["scenes"][3]["text_overlay"]
    assert "Premium Watch" in filled["scenes"][0]["video_prompt_template"]

    # Check that original template was not modified (deep copy)
    original = get_scene_template("luxury")
    assert "{product_name}" in original["scenes"][0]["voiceover_template"]

    print("✓ Template filling works correctly")


def test_get_available_styles():
    """Test getting list of available styles."""
    styles = get_available_styles()

    assert len(styles) == 4
    assert "luxury" in styles
    assert "energetic" in styles
    assert "minimal" in styles
    assert "bold" in styles

    print("✓ Available styles list correct")


def test_validate_template():
    """Test template validation."""
    # Valid template
    template = get_scene_template("luxury")
    assert validate_template(template) == True

    # Invalid template - missing field
    invalid = {"scenes": []}
    assert validate_template(invalid) == False

    # Invalid template - wrong number of scenes
    invalid = {
        "total_duration": 30,
        "scenes": [{"id": 1, "duration": 30, "type": "video"}]
    }
    assert validate_template(invalid) == False

    print("✓ Template validation works")


# ============================================================================
# Asset Manager Tests
# ============================================================================

@pytest.mark.asyncio
async def test_asset_manager_create_directory():
    """Test directory creation."""
    am = AssetManager("test-job-123")

    try:
        await am.create_job_directory()

        # Check that all directories were created
        assert am.job_dir.exists()
        assert am.scenes_dir.exists()
        assert am.audio_dir.exists()
        assert am.final_dir.exists()

        print("✓ Asset manager creates directories")
    finally:
        await am.cleanup()


@pytest.mark.asyncio
async def test_asset_manager_cleanup():
    """Test cleanup functionality."""
    am = AssetManager("test-job-456")

    await am.create_job_directory()
    assert am.job_dir.exists()

    await am.cleanup()
    assert not am.job_dir.exists()

    print("✓ Asset manager cleanup works")


@pytest.mark.asyncio
async def test_asset_manager_save_file():
    """Test saving file content."""
    am = AssetManager("test-job-789")

    try:
        await am.create_job_directory()

        # Save test file
        content = b"test video data"
        path = await am.save_file(content, "test.mp4", "scenes")

        # Check file exists and has correct content
        file_path = Path(path)
        assert file_path.exists()
        assert file_path.read_bytes() == content

        print("✓ Asset manager saves files")
    finally:
        await am.cleanup()


@pytest.mark.asyncio
async def test_asset_manager_validate_file():
    """Test file validation."""
    am = AssetManager("test-job-validation")

    try:
        await am.create_job_directory()

        # Save test file
        content = b"x" * 1000  # 1000 bytes
        await am.save_file(content, "test.mp4", "scenes")

        # Should be valid (>= 100 bytes)
        assert await am.validate_file("test.mp4", "scenes", min_size=100) == True

        # Should be invalid (< 2000 bytes)
        assert await am.validate_file("test.mp4", "scenes", min_size=2000) == False

        # Non-existent file should be invalid
        assert await am.validate_file("nonexistent.mp4", "scenes") == False

        print("✓ Asset manager validates files")
    finally:
        await am.cleanup()


@pytest.mark.asyncio
async def test_asset_manager_list_files():
    """Test listing files."""
    am = AssetManager("test-job-list")

    try:
        await am.create_job_directory()

        # Save multiple test files
        await am.save_file(b"data1", "file1.mp4", "scenes")
        await am.save_file(b"data2", "file2.mp4", "scenes")
        await am.save_file(b"data3", "audio.mp3", "audio")

        # List scenes
        scene_files = await am.list_files("scenes")
        assert len(scene_files) == 2

        # List audio
        audio_files = await am.list_files("audio")
        assert len(audio_files) == 1

        print("✓ Asset manager lists files")
    finally:
        await am.cleanup()


@pytest.mark.asyncio
async def test_asset_manager_disk_usage():
    """Test disk usage calculation."""
    am = AssetManager("test-job-disk")

    try:
        await am.create_job_directory()

        # Save test files
        await am.save_file(b"x" * 1000, "file1.mp4", "scenes")
        await am.save_file(b"x" * 2000, "file2.mp4", "scenes")

        # Calculate disk usage
        usage = await am.get_disk_usage()
        assert usage >= 3000  # At least 3000 bytes

        print("✓ Asset manager calculates disk usage")
    finally:
        await am.cleanup()


# ============================================================================
# Error Handler Tests
# ============================================================================

def test_pipeline_error_creation():
    """Test creating pipeline errors."""
    error = PipelineError(
        ErrorCode.INVALID_INPUT,
        "Test error message",
        {"field": "product_name"}
    )

    assert error.code == ErrorCode.INVALID_INPUT
    assert error.message == "Test error message"
    assert error.details["field"] == "product_name"

    print("✓ PipelineError creation works")


def test_pipeline_error_to_dict():
    """Test error serialization."""
    error = PipelineError(
        ErrorCode.INVALID_INPUT,
        "Test error",
        {"field": "test"}
    )

    error_dict = error.to_dict()

    assert "error_code" in error_dict
    assert "message" in error_dict
    assert "details" in error_dict
    assert "user_message" in error_dict
    assert error_dict["error_code"] == "INVALID_INPUT"

    print("✓ Error serialization works")


def test_user_friendly_messages():
    """Test user-friendly error messages."""
    error = PipelineError(ErrorCode.FILE_TOO_LARGE, "File exceeds limit")
    message = error.get_user_friendly_message()

    assert "10MB" in message
    assert "large" in message.lower()

    print("✓ User-friendly messages work")


def test_should_retry_logic():
    """Test retry logic determination."""
    # Transient errors should retry
    error = PipelineError(ErrorCode.CLAUDE_API_ERROR, "API down")
    assert should_retry(error) == True

    error = PipelineError(ErrorCode.API_TIMEOUT, "Timeout")
    assert should_retry(error) == True

    # Client errors should not retry
    error = PipelineError(ErrorCode.INVALID_INPUT, "Bad input")
    assert should_retry(error) == False

    error = PipelineError(ErrorCode.FILE_TOO_LARGE, "Too big")
    assert should_retry(error) == False

    # Built-in exceptions
    assert should_retry(TimeoutError()) == True
    assert should_retry(ConnectionError()) == True
    assert should_retry(ValueError()) == False

    print("✓ Retry logic works correctly")


def test_retry_delay_calculation():
    """Test exponential backoff calculation."""
    # Test exponential growth
    assert get_retry_delay(0) == 2.0
    assert get_retry_delay(1) == 4.0
    assert get_retry_delay(2) == 8.0
    assert get_retry_delay(3) == 16.0

    # Test max delay cap
    assert get_retry_delay(10) == 60.0

    print("✓ Retry delay calculation works")


def test_validation_error():
    """Test ValidationError convenience class."""
    error = ValidationError("Invalid product name", field="product_name")

    assert error.code == ErrorCode.INVALID_INPUT
    assert error.details["field"] == "product_name"

    print("✓ ValidationError works")


def test_api_error():
    """Test APIError convenience class."""
    error = APIError("claude", "API is down", status_code=503)

    assert error.code == ErrorCode.CLAUDE_API_ERROR
    assert error.details["service"] == "claude"
    assert error.details["status_code"] == 503
    assert should_retry(error) == True

    print("✓ APIError works")


def test_categorize_error():
    """Test exception categorization."""
    assert categorize_error(TimeoutError()) == ErrorCode.API_TIMEOUT
    assert categorize_error(PermissionError()) == ErrorCode.PERMISSION_DENIED
    assert categorize_error(ConnectionError()) == ErrorCode.REDIS_CONNECTION_ERROR

    print("✓ Error categorization works")


# ============================================================================
# Integration Tests
# ============================================================================

def test_all_templates_valid():
    """Test that all style templates are valid."""
    styles = get_available_styles()

    for style in styles:
        template = get_scene_template(style)
        assert validate_template(template) == True, f"{style} template is invalid"

    print("✓ All templates are valid")


@pytest.mark.asyncio
async def test_asset_manager_concurrent_operations():
    """Test concurrent asset manager operations."""
    managers = [AssetManager(f"test-job-concurrent-{i}") for i in range(3)]

    try:
        # Create all directories concurrently
        await asyncio.gather(*[am.create_job_directory() for am in managers])

        # Verify all exist
        for am in managers:
            assert am.job_dir.exists()

        print("✓ Concurrent asset manager operations work")
    finally:
        # Cleanup all
        await asyncio.gather(*[am.cleanup() for am in managers])


def test_error_handling_complete_flow():
    """Test complete error handling flow."""
    # Create error
    error = PipelineError(
        ErrorCode.CLAUDE_API_ERROR,
        "Claude API returned 503",
        {"status_code": 503, "retry_after": 60}
    )

    # Check if should retry
    assert should_retry(error) == True

    # Get retry delay
    delay = get_retry_delay(0)
    assert delay == 2.0

    # Convert to dict for API response
    error_dict = error.to_dict()
    assert error_dict["error_code"] == "CLAUDE_API_ERROR"

    # Get user message
    message = error.get_user_friendly_message()
    assert "temporarily unavailable" in message.lower()

    print("✓ Complete error handling flow works")


# ============================================================================
# Run Tests
# ============================================================================

def run_sync_tests():
    """Run all synchronous tests."""
    print("\n" + "="*60)
    print("RUNNING TEMPLATE SYSTEM TESTS")
    print("="*60)
    test_get_scene_template_luxury()
    test_get_scene_template_energetic()
    test_get_scene_template_minimal()
    test_get_scene_template_bold()
    test_get_scene_template_default()
    test_fill_template()
    test_get_available_styles()
    test_validate_template()
    test_all_templates_valid()

    print("\n" + "="*60)
    print("RUNNING ERROR HANDLER TESTS")
    print("="*60)
    test_pipeline_error_creation()
    test_pipeline_error_to_dict()
    test_user_friendly_messages()
    test_should_retry_logic()
    test_retry_delay_calculation()
    test_validation_error()
    test_api_error()
    test_categorize_error()
    test_error_handling_complete_flow()


async def run_async_tests():
    """Run all asynchronous tests."""
    print("\n" + "="*60)
    print("RUNNING ASSET MANAGER TESTS")
    print("="*60)
    await test_asset_manager_create_directory()
    await test_asset_manager_cleanup()
    await test_asset_manager_save_file()
    await test_asset_manager_validate_file()
    await test_asset_manager_list_files()
    await test_asset_manager_disk_usage()
    await test_asset_manager_concurrent_operations()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PIPELINE CORE COMPONENT TESTS")
    print("="*60)

    # Run synchronous tests
    run_sync_tests()

    # Run asynchronous tests
    asyncio.run(run_async_tests())

    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✓")
    print("="*60)
    print("\nSummary:")
    print("- Scene templates: 4 styles defined (luxury, energetic, minimal, bold)")
    print("- Asset manager: Full file operations with retry logic")
    print("- Error handling: Comprehensive error codes and user-friendly messages")
    print("\nNext Steps: Phase 2 implementation (Tasks 13-19)")
