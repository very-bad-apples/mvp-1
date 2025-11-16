"""
Video backend factory for selecting the appropriate video generation service.
"""

from typing import Callable


def get_video_backend(backend_name: str) -> Callable:
    """
    Factory function to get the appropriate video generation backend.

    Args:
        backend_name: Name of the backend ('replicate' or 'gemini')

    Returns:
        Video generation function for the specified backend

    Raises:
        ValueError: If backend_name is not recognized
    """
    if backend_name == "replicate":
        from mv.video_backends.replicate_backend import generate_video_replicate
        return generate_video_replicate
    elif backend_name == "gemini":
        from mv.video_backends.gemini_backend import generate_video_gemini
        return generate_video_gemini
    else:
        raise ValueError(
            f"Unknown video backend: {backend_name}. "
            f"Supported backends: 'replicate', 'gemini'"
        )
