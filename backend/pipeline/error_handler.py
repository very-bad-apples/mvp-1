"""
Comprehensive error handling for video generation pipeline.

Provides structured error handling with:
- Categorized error codes for all failure scenarios
- User-friendly error messages
- Retry logic determination
- Detailed error context for debugging
"""

from enum import Enum
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """
    Enumeration of all possible error codes in the pipeline.

    Organized by category:
    - API Errors: Client-side input validation errors
    - Pipeline Errors: Failures in video generation stages
    - External API Errors: Third-party service failures
    - System Errors: Infrastructure and storage issues
    """

    # API Errors (4xx - client errors)
    INVALID_INPUT = "INVALID_INPUT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_STYLE = "INVALID_STYLE"
    INVALID_CTA = "INVALID_CTA"

    # Pipeline Errors (5xx - processing errors)
    SCRIPT_GENERATION_FAILED = "SCRIPT_GENERATION_FAILED"
    VOICE_GENERATION_FAILED = "VOICE_GENERATION_FAILED"
    VIDEO_GENERATION_FAILED = "VIDEO_GENERATION_FAILED"
    IMAGE_GENERATION_FAILED = "IMAGE_GENERATION_FAILED"
    COMPOSITION_FAILED = "COMPOSITION_FAILED"
    TEMPLATE_ERROR = "TEMPLATE_ERROR"
    ASSET_DOWNLOAD_FAILED = "ASSET_DOWNLOAD_FAILED"

    # External API Errors (retryable)
    CLAUDE_API_ERROR = "CLAUDE_API_ERROR"
    REPLICATE_API_ERROR = "REPLICATE_API_ERROR"
    ELEVENLABS_API_ERROR = "ELEVENLABS_API_ERROR"
    OPENAI_API_ERROR = "OPENAI_API_ERROR"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_TIMEOUT = "API_TIMEOUT"

    # System Errors
    REDIS_CONNECTION_ERROR = "REDIS_CONNECTION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    DISK_FULL = "DISK_FULL"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FFMPEG_ERROR = "FFMPEG_ERROR"

    # Job Management Errors
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_EXPIRED = "JOB_EXPIRED"
    JOB_ALREADY_PROCESSING = "JOB_ALREADY_PROCESSING"
    JOB_CANCELLED = "JOB_CANCELLED"


class PipelineError(Exception):
    """
    Base exception for pipeline errors.

    Provides structured error information including:
    - Error code for categorization
    - Detailed message for logging
    - Context dictionary for debugging
    - User-friendly message for API responses

    Example:
        >>> raise PipelineError(
        ...     ErrorCode.INVALID_INPUT,
        ...     "Product name is required",
        ...     {"field": "product_name"}
        ... )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        """
        Initialize pipeline error.

        Args:
            code: Error code from ErrorCode enum
            message: Detailed error message for logging
            details: Additional context (field names, values, etc.)
            user_message: Optional override for user-friendly message
        """
        self.code = code
        self.message = message
        self.details = details or {}
        self._user_message = user_message
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for API responses.

        Returns:
            Dictionary with error information

        Example:
            >>> error = PipelineError(ErrorCode.INVALID_INPUT, "Missing field")
            >>> print(error.to_dict())
            {
                "error_code": "INVALID_INPUT",
                "message": "Missing field",
                "details": {},
                "user_message": "Please check your input and try again."
            }
        """
        return {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
            "user_message": self.get_user_friendly_message()
        }

    def get_user_friendly_message(self) -> str:
        """
        Returns user-friendly error message.

        If a custom user message was provided, returns that.
        Otherwise, returns a predefined friendly message based on error code.

        Returns:
            User-friendly error message string
        """
        if self._user_message:
            return self._user_message

        friendly_messages = {
            # API Errors
            ErrorCode.INVALID_INPUT: "Please check your input and try again.",
            ErrorCode.FILE_TOO_LARGE: "Image file is too large. Please use an image under 10MB.",
            ErrorCode.UNSUPPORTED_FORMAT: "File format not supported. Please use PNG, JPG, or WebP.",
            ErrorCode.MISSING_REQUIRED_FIELD: "Required field is missing. Please check your request.",
            ErrorCode.INVALID_STYLE: "Invalid style selected. Choose from: luxury, energetic, minimal, or bold.",
            ErrorCode.INVALID_CTA: "Call-to-action text is invalid. Please use 2-30 characters.",

            # Pipeline Errors
            ErrorCode.SCRIPT_GENERATION_FAILED: "Failed to generate script. Please try again.",
            ErrorCode.VOICE_GENERATION_FAILED: "Failed to generate voiceover. Please try again.",
            ErrorCode.VIDEO_GENERATION_FAILED: "Failed to generate video. Please try again or contact support.",
            ErrorCode.IMAGE_GENERATION_FAILED: "Failed to generate image. Please try again.",
            ErrorCode.COMPOSITION_FAILED: "Failed to compose final video. Please try again or contact support.",
            ErrorCode.TEMPLATE_ERROR: "Template error occurred. Please contact support.",
            ErrorCode.ASSET_DOWNLOAD_FAILED: "Failed to download asset. Please check the URL and try again.",

            # External API Errors
            ErrorCode.CLAUDE_API_ERROR: "AI service temporarily unavailable. Please try again in a moment.",
            ErrorCode.REPLICATE_API_ERROR: "Video generation service temporarily unavailable. Please try again.",
            ErrorCode.ELEVENLABS_API_ERROR: "Voice service temporarily unavailable. Please try again.",
            ErrorCode.OPENAI_API_ERROR: "AI service temporarily unavailable. Please try again.",
            ErrorCode.API_RATE_LIMIT: "Too many requests. Please wait a moment and try again.",
            ErrorCode.API_TIMEOUT: "Request timed out. Please try again.",

            # System Errors
            ErrorCode.REDIS_CONNECTION_ERROR: "System temporarily unavailable. Please try again.",
            ErrorCode.DATABASE_ERROR: "Database error occurred. Please try again or contact support.",
            ErrorCode.STORAGE_ERROR: "Storage error occurred. Please try again or contact support.",
            ErrorCode.DISK_FULL: "System storage full. Please contact support.",
            ErrorCode.PERMISSION_DENIED: "Permission denied. Please contact support.",
            ErrorCode.FFMPEG_ERROR: "Video processing error. Please try again or contact support.",

            # Job Management Errors
            ErrorCode.JOB_NOT_FOUND: "Job not found. It may have expired.",
            ErrorCode.JOB_EXPIRED: "Job has expired. Please submit a new request.",
            ErrorCode.JOB_ALREADY_PROCESSING: "Job is already being processed.",
            ErrorCode.JOB_CANCELLED: "Job was cancelled.",
        }

        return friendly_messages.get(
            self.code,
            "An error occurred. Please try again or contact support."
        )

    def log_error(self) -> None:
        """
        Log error with appropriate level and context.

        Logs different error categories at different levels:
        - Client errors (4xx): WARNING
        - Retryable errors: WARNING
        - System errors: ERROR
        """
        log_data = {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details
        }

        # Client errors are warnings (user input issues)
        if self.code in [
            ErrorCode.INVALID_INPUT,
            ErrorCode.FILE_TOO_LARGE,
            ErrorCode.UNSUPPORTED_FORMAT,
            ErrorCode.MISSING_REQUIRED_FIELD,
            ErrorCode.INVALID_STYLE,
            ErrorCode.INVALID_CTA
        ]:
            logger.warning(f"Client error: {log_data}")

        # Retryable errors are warnings
        elif should_retry(self):
            logger.warning(f"Retryable error: {log_data}")

        # All other errors are critical
        else:
            logger.error(f"Pipeline error: {log_data}")

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"


def should_retry(error: Exception) -> bool:
    """
    Determines if an error is transient and should be retried.

    Transient errors include:
    - External API failures (Claude, Replicate, ElevenLabs)
    - Network timeouts
    - Rate limiting
    - Temporary infrastructure issues

    Args:
        error: Exception to check

    Returns:
        True if error is transient and should be retried, False otherwise

    Example:
        >>> error = PipelineError(ErrorCode.CLAUDE_API_ERROR, "API down")
        >>> should_retry(error)
        True
        >>> error = PipelineError(ErrorCode.INVALID_INPUT, "Bad input")
        >>> should_retry(error)
        False
    """
    transient_error_codes = [
        # External API errors (service might be temporarily down)
        ErrorCode.CLAUDE_API_ERROR,
        ErrorCode.REPLICATE_API_ERROR,
        ErrorCode.ELEVENLABS_API_ERROR,
        ErrorCode.OPENAI_API_ERROR,
        ErrorCode.API_RATE_LIMIT,
        ErrorCode.API_TIMEOUT,

        # Infrastructure errors (might resolve)
        ErrorCode.REDIS_CONNECTION_ERROR,
        ErrorCode.DATABASE_ERROR,
        ErrorCode.STORAGE_ERROR,

        # Asset download failures (network issues)
        ErrorCode.ASSET_DOWNLOAD_FAILED,
    ]

    if isinstance(error, PipelineError):
        return error.code in transient_error_codes

    # Also retry on common Python exceptions
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True

    return False


def get_retry_delay(attempt: int, base_delay: float = 2.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay for retry attempts.

    Uses formula: min(base_delay * (2 ** attempt), max_delay)

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds (default: 2.0)
        max_delay: Maximum delay in seconds (default: 60.0)

    Returns:
        Delay in seconds for this attempt

    Example:
        >>> get_retry_delay(0)  # First retry
        2.0
        >>> get_retry_delay(1)  # Second retry
        4.0
        >>> get_retry_delay(2)  # Third retry
        8.0
        >>> get_retry_delay(10)  # Caps at max_delay
        60.0
    """
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


def categorize_error(error: Exception) -> ErrorCode:
    """
    Categorize a generic exception into an ErrorCode.

    Useful for converting Python built-in exceptions into pipeline error codes.

    Args:
        error: Exception to categorize

    Returns:
        Appropriate ErrorCode for the exception

    Example:
        >>> categorize_error(TimeoutError())
        ErrorCode.API_TIMEOUT
        >>> categorize_error(PermissionError())
        ErrorCode.PERMISSION_DENIED
    """
    error_type = type(error).__name__

    # Map common exceptions to error codes
    mapping = {
        "TimeoutError": ErrorCode.API_TIMEOUT,
        "ConnectionError": ErrorCode.REDIS_CONNECTION_ERROR,
        "PermissionError": ErrorCode.PERMISSION_DENIED,
        "FileNotFoundError": ErrorCode.STORAGE_ERROR,
        "OSError": ErrorCode.STORAGE_ERROR,
        "MemoryError": ErrorCode.STORAGE_ERROR,
    }

    return mapping.get(error_type, ErrorCode.STORAGE_ERROR)


class ValidationError(PipelineError):
    """
    Error for input validation failures.

    Convenience subclass for validation errors.
    """

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Name of invalid field
            details: Additional context
        """
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            ErrorCode.INVALID_INPUT,
            message,
            error_details
        )


class APIError(PipelineError):
    """
    Error for external API failures.

    Convenience subclass for API errors with automatic retry flagging.
    """

    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        """
        Initialize API error.

        Args:
            service: Name of the API service (claude, replicate, elevenlabs)
            message: Error message
            status_code: HTTP status code if available
            details: Additional context
        """
        # Map service names to error codes
        service_codes = {
            "claude": ErrorCode.CLAUDE_API_ERROR,
            "replicate": ErrorCode.REPLICATE_API_ERROR,
            "elevenlabs": ErrorCode.ELEVENLABS_API_ERROR,
            "openai": ErrorCode.OPENAI_API_ERROR,
        }

        code = service_codes.get(service.lower(), ErrorCode.CLAUDE_API_ERROR)

        error_details = details or {}
        error_details["service"] = service
        if status_code:
            error_details["status_code"] = status_code

        super().__init__(code, message, error_details)
