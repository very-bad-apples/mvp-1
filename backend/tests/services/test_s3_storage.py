"""
Tests for S3 storage service validation functions.

Tests the validate_s3_key() function which ensures S3 keys are not URLs.
"""

import pytest
from services.s3_storage import validate_s3_key


class TestValidateS3Key:
    """Test cases for validate_s3_key() function."""

    def test_valid_s3_key(self):
        """Test that valid S3 keys are accepted."""
        key = validate_s3_key("mv/projects/123/file.png", "test")
        assert key == "mv/projects/123/file.png"

    def test_valid_s3_key_with_path(self):
        """Test that S3 keys with deeper paths are accepted."""
        key = validate_s3_key("mv/projects/123/scenes/001/video.mp4", "test")
        assert key == "mv/projects/123/scenes/001/video.mp4"

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert validate_s3_key(None, "test") is None

    def test_empty_string_returns_empty(self):
        """Test that empty string is accepted (edge case)."""
        key = validate_s3_key("", "test")
        assert key == ""

    def test_whitespace_stripped(self):
        """Test that whitespace is stripped."""
        key = validate_s3_key("  mv/projects/123/file.png  ", "test")
        assert key == "mv/projects/123/file.png"

    def test_http_url_rejected(self):
        """Test that HTTP URLs are rejected."""
        with pytest.raises(ValueError, match="must be an S3 key"):
            validate_s3_key("http://bucket.s3.amazonaws.com/file.png", "test")

    def test_https_url_rejected(self):
        """Test that HTTPS URLs are rejected."""
        with pytest.raises(ValueError, match="must be an S3 key"):
            validate_s3_key("https://bucket.s3.amazonaws.com/file.png", "test")

    def test_s3_url_rejected(self):
        """Test that s3:// URLs are rejected."""
        with pytest.raises(ValueError, match="must be an S3 key"):
            validate_s3_key("s3://bucket/file.png", "test")

    def test_presigned_url_with_x_amz_rejected(self):
        """Test that presigned URLs with X-Amz signature are rejected."""
        with pytest.raises(ValueError, match="presigned URL"):
            validate_s3_key(
                "mv/projects/123/file.png?X-Amz-Signature=abc123&X-Amz-Date=20231117",
                "test"
            )

    def test_presigned_url_with_aws_access_key_rejected(self):
        """Test that presigned URLs with AWSAccessKeyId are rejected."""
        with pytest.raises(ValueError, match="presigned URL"):
            validate_s3_key(
                "mv/projects/123/file.png?AWSAccessKeyId=AKIA123&Signature=abc",
                "test"
            )

    def test_valid_key_with_query_param_but_no_signature_accepted(self):
        """Test that keys with query params but no signature are accepted (edge case)."""
        # This is an edge case - unlikely but technically valid S3 key format
        key = validate_s3_key("mv/projects/123/file.png?version=1", "test")
        assert key == "mv/projects/123/file.png?version=1"

    def test_error_message_includes_field_name(self):
        """Test that error messages include the field name for debugging."""
        with pytest.raises(ValueError) as exc_info:
            validate_s3_key("https://example.com/file.png", "characterImageS3Key")
        assert "characterImageS3Key" in str(exc_info.value)

    def test_error_message_shows_truncated_url(self):
        """Test that error messages show truncated URL for readability."""
        long_url = "https://" + "x" * 100 + ".com/file.png"
        with pytest.raises(ValueError) as exc_info:
            validate_s3_key(long_url, "test")
        # Should truncate to first 50 chars
        assert len(str(exc_info.value)) < len(long_url) + 100

