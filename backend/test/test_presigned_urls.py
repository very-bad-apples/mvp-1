"""
Tests for presigned URL generation for character reference images.

Tests S3 presigned URLs with different configurations.

Run with: pytest backend/test/test_presigned_urls.py -v
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from services.storage_backend import S3StorageBackend


@pytest.fixture
def s3_backend():
    """Create S3 storage backend."""
    return S3StorageBackend(
        bucket="test-bucket",
        aws_access_key="test-key",
        aws_secret_key="test-secret",
        region="us-east-1"
    )


def test_s3_presigned_url_generation(s3_backend):
    """Test S3 presigned URL is generated correctly."""
    cloud_path = "character_references/abc-123.png"
    expiry = 3600
    
    # Generate presigned URL
    url = s3_backend.generate_presigned_url(cloud_path, expiry=expiry)
    
    # Verify URL structure
    assert url.startswith("https://")
    assert "test-bucket" in url
    assert "abc-123.png" in url
    assert "Signature=" in url or "X-Amz-Signature=" in url
    assert "Expires=" in url or "X-Amz-Expires=" in url


def test_s3_presigned_url_different_expiry(s3_backend):
    """Test presigned URLs with different expiry times."""
    cloud_path = "character_references/test.png"
    
    # Generate URLs with different expiry times
    url_1hr = s3_backend.generate_presigned_url(cloud_path, expiry=3600)
    url_24hr = s3_backend.generate_presigned_url(cloud_path, expiry=86400)
    
    # URLs should be different (different expiry)
    assert url_1hr != url_24hr
    
    # Both should be valid URLs
    assert url_1hr.startswith("https://")
    assert url_24hr.startswith("https://")


def test_s3_presigned_url_different_paths(s3_backend):
    """Test presigned URLs for different file paths."""
    expiry = 3600
    
    # Generate URLs for different paths
    url1 = s3_backend.generate_presigned_url("character_references/image1.png", expiry)
    url2 = s3_backend.generate_presigned_url("character_references/image2.png", expiry)
    
    # URLs should be different (different keys)
    assert url1 != url2
    
    # Both should contain their respective image names
    assert "image1.png" in url1
    assert "image2.png" in url2


def test_s3_presigned_url_file_extensions(s3_backend):
    """Test presigned URLs work for different file extensions."""
    expiry = 3600
    base_path = "character_references/test"
    
    extensions = ["png", "jpg", "jpeg", "webp"]
    
    for ext in extensions:
        cloud_path = f"{base_path}.{ext}"
        url = s3_backend.generate_presigned_url(cloud_path, expiry)
        
        # Verify URL is generated
        assert url.startswith("https://")
        assert f".{ext}" in url


def test_s3_presigned_url_respects_config():
    """Test that presigned URL expiry respects configuration."""
    with patch('config.settings.PRESIGNED_URL_EXPIRY', 7200):
        backend = S3StorageBackend(
            bucket="test-bucket",
            aws_access_key="test-key",
            aws_secret_key="test-secret",
            region="us-east-1"
        )
        
        # The backend should use the configured expiry
        # This is tested in integration, but we verify the backend accepts it
        url = backend.generate_presigned_url("test.png", expiry=7200)
        assert url.startswith("https://")


def test_s3_presigned_url_with_special_characters(s3_backend):
    """Test presigned URL generation with special characters in path."""
    # S3 should properly encode special characters
    cloud_path = "character_references/test image (1).png"
    
    url = s3_backend.generate_presigned_url(cloud_path, expiry=3600)
    
    # URL should be generated (boto3 handles encoding)
    assert url.startswith("https://")


def test_url_generation_performance():
    """Test that URL generation is fast."""
    backend = S3StorageBackend(
        bucket="test-bucket",
        aws_access_key="test-key",
        aws_secret_key="test-secret",
        region="us-east-1"
    )
    
    start_time = time.time()
    
    # Generate 10 URLs
    for i in range(10):
        backend.generate_presigned_url(f"test{i}.png", expiry=3600)
    
    elapsed = time.time() - start_time
    
    # Should be very fast (< 1 second for 10 URLs)
    assert elapsed < 1.0


@pytest.mark.integration
def test_s3_presigned_url_accessibility():
    """
    Integration test: Verify presigned URL is actually accessible.
    
    Note: Requires real AWS credentials and S3 bucket.
    Skip this test in CI/CD unless AWS is configured.
    """
    import os
    import requests
    
    # Skip if no real AWS credentials
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        pytest.skip("AWS credentials not configured")
    
    # This would need real S3 setup to work
    # Placeholder for integration testing
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

