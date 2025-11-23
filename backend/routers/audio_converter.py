"""
Audio converter endpoint router

Converts YouTube videos to MP3 format in memory (no file saving).
"""

import subprocess
from copy import deepcopy
from typing import Any, Dict, List, Optional, Literal

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, HttpUrl
from replicate.exceptions import ModelError

from services.replicate_client import get_replicate_client

logger = structlog.get_logger()

router = APIRouter(prefix="/api/audio", tags=["Audio Converter"])

MUSIC_MODEL_ID = "minimax/music-1.5"
DEFAULT_MUSIC_MODEL_KEY = "minimax_music_1_5"

AUDIO_MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "minimax_music_1_5": {
        "model_id": "minimax/music-1.5",
        "display_name": "MiniMax Music-1.5",
        "provider": "MiniMax",
        "description": (
            "Generates full-length songs (up to 4 minutes) with vocals and accompaniment."
        ),
        "docs_url": "https://replicate.com/minimax/music-1.5",
        "max_duration_seconds": 240,
        "default_params": {
            "prompt": "Energetic electro-pop track for product launch",
            # lyrics intentionally omitted - only include if user provides them
            "sample_rate": 44100,
            "bitrate": 256000,
            "audio_format": "mp3",
        },
        "parameters": [
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "description": "Control music generation with a text prompt. Valid input: 10-300 characters.",
                "control": "textarea",
                "placeholder": "Energetic electro-pop track with soaring synths"
            },
            {
                "name": "lyrics",
                "type": "string",
                "required": False,
                "description": "Lyrics (optional - leave blank for instrumental music). Use \\n to separate lines. Supports [intro][verse][chorus][bridge][outro]. Valid input: 10-600 characters if provided.",
                "control": "textarea",
                "placeholder": "[Verse]\nWe run into the night... (or leave empty for instrumental)"
            },
            {
                "name": "sample_rate",
                "type": "int",
                "required": False,
                "description": "Sample rate for the generated music (default: 44100)",
                "control": "select",
                "options": [
                    {"label": "16 kHz", "value": 16000},
                    {"label": "24 kHz", "value": 24000},
                    {"label": "32 kHz", "value": 32000},
                    {"label": "44.1 kHz (default)", "value": 44100},
                ]
            },
            {
                "name": "bitrate",
                "type": "int",
                "required": False,
                "description": "Bitrate for the generated music (default: 256000)",
                "control": "select",
                "options": [
                    {"label": "32 kbps", "value": 32000},
                    {"label": "64 kbps", "value": 64000},
                    {"label": "128 kbps", "value": 128000},
                    {"label": "256 kbps (default)", "value": 256000},
                ]
            },
            {
                "name": "audio_format",
                "type": "string",
                "required": False,
                "description": "Audio format (default: mp3)",
                "control": "select",
                "options": [
                    {"label": "MP3 (default)", "value": "mp3"},
                    {"label": "WAV", "value": "wav"},
                    {"label": "PCM", "value": "pcm"},
                ]
            },
        ],
    },
    "stable_audio_2_5": {
        "model_id": "stability-ai/stable-audio-2.5",
        "display_name": "Stable Audio 2.5",
        "provider": "Stability AI",
        "description": (
            "Text-to-audio generation focused on high-fidelity instrumentals and sound design."
        ),
        "docs_url": "https://replicate.com/stability-ai/stable-audio-2.5",
        "max_duration_seconds": 95,
        "default_params": {
            "prompt": "Cinematic trailer hit with pulse bass and rising synths",
            "steps": 8,
            "duration": 30,
            "cfg_scale": 5,
            "seed": 0,
        },
        "parameters": [
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "description": "Describe the desired audio.",
                "control": "textarea",
                "placeholder": "Cinematic trailer hit with pulse bass"
            },
            {
                "name": "steps",
                "type": "int",
                "required": False,
                "description": "Diffusion steps (4-8).",
                "control": "number",
                "min": 4,
                "max": 8,
                "step": 1
            },
            {
                "name": "duration",
                "type": "int",
                "required": False,
                "description": "Duration in seconds (1-190).",
                "control": "number",
                "min": 1,
                "max": 190,
                "step": 1
            },
            {
                "name": "cfg_scale",
                "type": "float",
                "required": False,
                "description": "Guidance scale (1-25).",
                "control": "number",
                "min": 1,
                "max": 25,
                "step": 0.5
            },
            {
                "name": "seed",
                "type": "int",
                "required": False,
                "description": "Seed for reproducible generations.",
                "control": "number",
                "min": 0,
                "step": 1
            },
        ],
    },
    "google_lyria_2": {
        "model_id": "google/lyria-2",
        "display_name": "Google Lyria 2",
        "provider": "Google DeepMind",
        "description": (
            "48kHz stereo audio generation with controllable style presets and temperature."
        ),
        "docs_url": "https://replicate.com/google/lyria-2",
        "max_duration_seconds": 60,
        "default_params": {
            "prompt": "Dreamy lo-fi beat for study sessions",
            "negative_prompt": "",
            "seed": 0,
        },
        "parameters": [
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "description": "Text prompt for audio generation.",
                "control": "textarea",
                "placeholder": "Futuristic country ballad with steel guitar"
            },
            {
                "name": "negative_prompt",
                "type": "string",
                "required": False,
                "description": "Describe what to exclude.",
                "control": "textarea",
                "placeholder": "No vocals, no drums"
            },
            {
                "name": "seed",
                "type": "int",
                "required": False,
                "description": "Seed for reproducible output.",
                "control": "number",
                "min": 0,
                "step": 1
            },
        ],
    },
    "meta_musicgen": {
        "model_id": "meta/musicgen",
        "display_name": "Meta MusicGen",
        "provider": "Meta",
        "description": "Fast music generation from text prompts or melodies.",
        "docs_url": "https://replicate.com/meta/musicgen",
        "max_duration_seconds": 30,
        "default_params": {
            "model_version": "stereo-melody-large",
            "prompt": "Upbeat funk groove with slap bass and brass stabs",
            "input_audio": "",
            "duration": 8,
            "continuation": False,
            "continuation_start": 0,
            "continuation_end": 0,
            "multi_band_diffusion": False,
            "normalization_strategy": "loudness",
            "top_k": 250,
            "top_p": 0,
            "temperature": 1,
            "classifier_free_guidance": 3,
            "output_format": "wav",
        },
        "parameters": [
            {
                "name": "model_version",
                "type": "string",
                "required": False,
                "description": "Choose a MusicGen variant.",
                "control": "select",
                "options": [
                    {"label": "Stereo Melody Large", "value": "stereo-melody-large"},
                    {"label": "Stereo Large", "value": "stereo-large"},
                    {"label": "Melody Large", "value": "melody-large"},
                    {"label": "Large", "value": "large"},
                ]
            },
            {
                "name": "prompt",
                "type": "string",
                "required": False,
                "description": "Describe the music to generate.",
                "control": "textarea",
                "placeholder": "Euphoric festival EDM drop with vocal chops"
            },
            {
                "name": "input_audio",
                "type": "string",
                "required": False,
                "description": "URL to an audio file for melody/continuation.",
                "control": "text",
                "placeholder": "https://..."
            },
            {
                "name": "duration",
                "type": "int",
                "required": False,
                "description": "Clip length in seconds.",
                "control": "number",
                "min": 1,
                "max": 30,
                "step": 1
            },
            {
                "name": "continuation",
                "type": "boolean",
                "required": False,
                "description": "Continue from `input_audio` instead of mimicking it."
            },
            {
                "name": "continuation_start",
                "type": "int",
                "required": False,
                "description": "Start time (seconds) for continuation.",
                "control": "number",
                "min": 0,
                "step": 1
            },
            {
                "name": "continuation_end",
                "type": "int",
                "required": False,
                "description": "End time (seconds) for continuation.",
                "control": "number",
                "min": 0,
                "step": 1
            },
            {
                "name": "multi_band_diffusion",
                "type": "boolean",
                "required": False,
                "description": "Enable multi-band diffusion decoding (non-stereo models only)."
            },
            {
                "name": "normalization_strategy",
                "type": "string",
                "required": False,
                "description": "Audio normalization strategy.",
                "control": "select",
                "options": [
                    {"label": "Loudness", "value": "loudness"},
                    {"label": "Clip", "value": "clip"},
                    {"label": "Peak", "value": "peak"},
                    {"label": "RMS", "value": "rms"},
                ]
            },
            {
                "name": "top_k",
                "type": "int",
                "required": False,
                "description": "Limit sampling to top-k tokens.",
                "control": "number",
                "min": 0,
                "step": 1
            },
            {
                "name": "top_p",
                "type": "float",
                "required": False,
                "description": "Nucleus sampling probability mass.",
                "control": "number",
                "min": 0,
                "max": 1,
                "step": 0.01
            },
            {
                "name": "temperature",
                "type": "float",
                "required": False,
                "description": "Sampling temperature (higher = more diverse).",
                "control": "number",
                "min": 0,
                "step": 0.05
            },
            {
                "name": "classifier_free_guidance",
                "type": "int",
                "required": False,
                "description": "Influence of inputs on output.",
                "control": "number",
                "min": 1,
                "max": 10,
                "step": 1
            },
            {
                "name": "output_format",
                "type": "string",
                "required": False,
                "description": "Audio format.",
                "control": "select",
                "options": [
                    {"label": "WAV", "value": "wav"},
                    {"label": "MP3", "value": "mp3"},
                ]
            },
        ],
    },
    "riffusion_v1": {
        "model_id": "riffusion/riffusion",
        "display_name": "Riffusion (Loop Generator)",
        "provider": "Riffusion",
        "description": (
            "Generates seamless music loops by interpolating between two prompts."
        ),
        "docs_url": "https://replicate.com/riffusion/riffusion",
        "max_duration_seconds": 12,
        "default_params": {
            "prompt_a": "solo saxophone playing smooth jazz",
            "prompt_b": "",
            "denoising": 0.75,
            "alpha": 0.5,
            "num_inference_steps": 50,
            "seed_image_id": "vibes",
        },
        "parameters": [
            {
                "name": "prompt_a",
                "type": "string",
                "required": False,
                "description": "Primary prompt describing the loop.",
                "control": "textarea",
                "placeholder": "Funky synth solo"
            },
            {
                "name": "prompt_b",
                "type": "string",
                "required": False,
                "description": "Optional second prompt for interpolation.",
                "control": "textarea",
                "placeholder": "90's rap beat"
            },
            {
                "name": "denoising",
                "type": "float",
                "required": False,
                "description": "Amount of spectrogram transformation (0-1).",
                "control": "number",
                "min": 0,
                "max": 1,
                "step": 0.05
            },
            {
                "name": "alpha",
                "type": "float",
                "required": False,
                "description": "Blend factor between prompt A and B (0-1).",
                "control": "number",
                "min": 0,
                "max": 1,
                "step": 0.05
            },
            {
                "name": "num_inference_steps",
                "type": "int",
                "required": False,
                "description": "Diffusion steps (quality vs speed).",
                "control": "number",
                "min": 1,
                "step": 1
            },
            {
                "name": "seed_image_id",
                "type": "string",
                "required": False,
                "description": "Seed spectrogram template.",
                "control": "select",
                "options": [
                    {"label": "Agile", "value": "agile"},
                    {"label": "Marim", "value": "marim"},
                    {"label": "Mask Beat Lines 80", "value": "mask_beat_lines_80"},
                    {"label": "Mask Gradient Dark", "value": "mask_gradient_dark"},
                    {"label": "Mask Gradient Top 70%", "value": "mask_gradient_top_70"},
                    {"label": "Mask Gradient Top Fifth 75%", "value": "mask_graident_top_fifth_75"},
                    {"label": "Mask Top Third 75%", "value": "mask_top_third_75"},
                    {"label": "Mask Top Third 95%", "value": "mask_top_third_95"},
                    {"label": "Motorway", "value": "motorway"},
                    {"label": "OG Beat", "value": "og_beat"},
                    {"label": "Vibes", "value": "vibes"},
                ]
            },
        ],
    },
}


class ConvertYouTubeRequest(BaseModel):
    """Request model for YouTube to MP3 conversion."""
    url: str


class MusicGenerationRequest(BaseModel):
    """Request body for MiniMax Music-1.5 generation."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description="High-level creative direction or vibe for the song.",
    )
    lyrics: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=600,
        description="Optional lyrics (10-600 characters).",
    )
    reference_audio_url: Optional[HttpUrl] = Field(
        default=None,
        description="Optional reference song (WAV/MP3/M4A, 5-30 seconds) to learn style.",
    )
    voice_reference_url: Optional[HttpUrl] = Field(
        default=None,
        description="Optional voice reference audio to mimic vocal character.",
    )
    instrumental_reference_url: Optional[HttpUrl] = Field(
        default=None,
        description="Optional instrumental-only reference track.",
    )
    style_strength: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="How strongly to follow the reference style (0-1).",
    )
    duration_seconds: int = Field(
        default=120,
        ge=10,
        le=240,
        description="Target song duration in seconds (max 240).",
    )
    language: Literal["english", "chinese"] = Field(
        default="english",
        description="Language of the lyrics currently supported by the model.",
    )
    genre: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Optional genre hint (e.g., pop, rock, edm).",
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional deterministic seed to reproduce generations.",
    )
    sample_rate_hz: int = Field(
        default=44100,
        ge=16000,
        le=48000,
        description="Sample rate of the generated audio.",
    )
    bitrate: int = Field(
        default=256000,
        ge=64000,
        le=512000,
        description="Audio bitrate for encoding.",
    )
    audio_format: Literal["mp3", "wav", "flac", "aac"] = Field(
        default="mp3",
        description="File container/codec for the generated music.",
    )
    response_format: Literal["url", "hex"] = Field(
        default="url",
        description="Output response type from Replicate (URL recommended).",
    )


class MusicGenerationResponse(BaseModel):
    """Standardized response for music generations."""

    model_id: str
    model_key: Optional[str] = None
    model_name: Optional[str] = None
    inputs: Dict[str, Any]
    outputs: List[str]
    raw_output: Optional[Any] = None


class AudioModelRunRequest(BaseModel):
    """Request body for running arbitrary audio models."""

    model_key: str = Field(..., description="Key returned from /api/audio/models")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Overrides/inputs specific to the selected model.",
    )


def _build_music_input(payload: MusicGenerationRequest) -> Dict[str, Any]:
    """Map API request to Replicate model inputs."""
    def _to_str(url: Optional[HttpUrl]) -> Optional[str]:
        return str(url) if url else None

    params: Dict[str, Any] = {
        "prompt": payload.prompt,
        "lyrics": payload.lyrics,
        "style_strength": payload.style_strength,
        "duration": payload.duration_seconds,
        "language": payload.language,
        "genre": payload.genre,
        "seed": payload.seed,
        "sample_rate": payload.sample_rate_hz,
        "bitrate": payload.bitrate,
        "format": payload.audio_format,
        "output_format": payload.response_format,
        # Reference assets
        "song_file": _to_str(payload.reference_audio_url),
        "voice_file": _to_str(payload.voice_reference_url),
        "instrumental_file": _to_str(payload.instrumental_reference_url),
    }

    # Remove None values to avoid validation errors on Replicate
    return {key: value for key, value in params.items() if value is not None}


def _normalize_music_output(raw_output: Any) -> List[str]:
    """Extract downloadable asset URLs (or hex/audio strings) from Replicate output."""
    urls: List[str] = []

    if raw_output is None:
        return urls

    if isinstance(raw_output, str):
        urls.append(raw_output)
        return urls

    if isinstance(raw_output, list):
        for item in raw_output:
            urls.extend(_normalize_music_output(item))
        return urls

    if isinstance(raw_output, dict):
        for value in raw_output.values():
            urls.extend(_normalize_music_output(value))
        return urls

    # Fallback for unexpected types
    urls.append(str(raw_output))
    return urls


@router.get(
    "/models",
    summary="List available AI audio models",
)
async def list_audio_models():
    """Return metadata and default parameters for supported audio models."""
    models: List[Dict[str, Any]] = []
    for key, data in AUDIO_MODEL_REGISTRY.items():
        model_data = deepcopy(data)
        model_data["key"] = key
        models.append(model_data)
    return {"models": models}


@router.post(
    "/models/run",
    response_model=MusicGenerationResponse,
    summary="Run an audio model with custom parameters",
)
async def run_audio_model(request: AudioModelRunRequest):
    """Execute any of the registered audio models via Replicate."""
    model_config = AUDIO_MODEL_REGISTRY.get(request.model_key)
    if not model_config:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidModel",
                "message": f"Unknown audio model '{request.model_key}'.",
            },
        )

    client = get_replicate_client()
    merged_params = deepcopy(model_config.get("default_params", {}))
    merged_params.update(request.parameters or {})
    
    # Remove lyrics if explicitly set to empty string or None (for instrumental music)
    if "lyrics" in merged_params and not merged_params["lyrics"]:
        del merged_params["lyrics"]

    try:
        raw_output = client.run_model(
            model_config["model_id"],
            input_params=merged_params,
            use_file_output=False,
        )
    except ModelError as exc:
        logs = getattr(exc.prediction, "logs", None) if hasattr(exc, "prediction") else None
        logger.error(
            "audio_model_run_failed",
            model_key=request.model_key,
            model_id=model_config["model_id"],
            logs=logs,
            error=str(exc),
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ModelError",
                "message": f"{model_config['display_name']} rejected the request.",
                "logs": logs,
            },
        ) from exc
    except Exception as exc:  # pragma: no cover
        logger.error(
            "audio_model_run_unexpected_error",
            model_key=request.model_key,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": f"Failed to call {model_config['display_name']}.",
                "details": str(exc),
            },
        ) from exc

    outputs = _normalize_music_output(raw_output)
    logger.info(
        "audio_model_run_success",
        model_key=request.model_key,
        model_id=model_config["model_id"],
        output_count=len(outputs),
    )

    return MusicGenerationResponse(
        model_id=model_config["model_id"],
        model_key=request.model_key,
        model_name=model_config["display_name"],
        inputs=merged_params,
        outputs=outputs,
        raw_output=raw_output,
    )


@router.post(
    "/generate-music",
    response_model=MusicGenerationResponse,
    summary="Generate music via MiniMax Music-1.5",
    description="""
Call MiniMax's Music-1.5 model on Replicate to synthesize full songs with vocals and instrumentation.
Supports reference style tracks, lyrics-to-music workflows, and adjustable style strength.
""",
)
async def generate_music(request: MusicGenerationRequest):
    """
    Generate music using the minimax/music-1.5 model on Replicate.
    """
    client = get_replicate_client()
    input_params = _build_music_input(request)

    logger.info(
        "music_generation_request",
        model_id=MUSIC_MODEL_ID,
        has_reference=bool(request.reference_audio_url),
        duration=input_params.get("duration"),
        style_strength=input_params.get("style_strength"),
    )

    try:
        raw_output = client.run_model(
            MUSIC_MODEL_ID,
            input_params=input_params,
            use_file_output=False,
        )
    except ModelError as exc:
        logs = getattr(exc.prediction, "logs", None) if hasattr(exc, "prediction") else None
        logger.error(
            "music_generation_model_error",
            model_id=MUSIC_MODEL_ID,
            logs=logs,
            error=str(exc),
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ModelError",
                "message": "MiniMax Music-1.5 rejected the request.",
                "logs": logs,
            },
        ) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(
            "music_generation_unexpected_error",
            model_id=MUSIC_MODEL_ID,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to call minimax/music-1.5.",
                "details": str(exc),
            },
        ) from exc

    outputs = _normalize_music_output(raw_output)
    logger.info(
        "music_generation_success",
        model_id=MUSIC_MODEL_ID,
        output_count=len(outputs),
    )

    return MusicGenerationResponse(
        model_id=MUSIC_MODEL_ID,
        model_key=DEFAULT_MUSIC_MODEL_KEY,
        model_name=AUDIO_MODEL_REGISTRY[DEFAULT_MUSIC_MODEL_KEY]["display_name"],
        inputs=input_params,
        outputs=outputs,
        raw_output=raw_output,
    )


@router.post(
    "/convert-youtube",
    responses={
        200: {"description": "MP3 audio file", "content": {"audio/mpeg": {}}},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or conversion failure"}
    },
    summary="Convert YouTube to MP3 (Memory Only)",
    description="""
Convert YouTube video to MP3 format without saving any files.

This endpoint:
1. Validates the YouTube URL
2. Downloads audio using yt-dlp directly to memory (stdout)
3. Returns MP3 data as streaming response
4. NO files are created on the server

**IMPORTANT:** This is a synchronous endpoint that may take 10-60+ seconds.

**Process:**
- yt-dlp downloads to stdout (memory stream)
- Audio captured in BytesIO (memory variable)
- Returned as HTTP response
- NO temporary files created

**Required Fields:**
- url: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)
"""
)
async def convert_youtube_to_mp3(request: ConvertYouTubeRequest):
    """
    Convert YouTube video to MP3 in memory (no file saving).
    
    Args:
        request: ConvertYouTubeRequest with YouTube URL
        
    Returns:
        MP3 audio file as streaming response
        
    Raises:
        HTTPException: If URL is invalid or download fails
    """
    try:
        logger.info(
            "youtube_conversion_request_received",
            url=request.url[:100] if len(request.url) > 100 else request.url
        )

        # Validate URL
        if not request.url or not request.url.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "URL is required",
                    "details": "The 'url' field cannot be empty"
                }
            )

        # Basic YouTube URL validation
        url = request.url.strip()
        if "youtube.com" not in url and "youtu.be" not in url:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid YouTube URL",
                    "details": "URL must be a valid YouTube link (youtube.com or youtu.be)"
                }
            )

        # Download audio directly to memory using yt-dlp
        logger.info("starting_youtube_download_to_memory", url=url[:100])
        
        # Find yt-dlp executable (prefer venv version)
        import shutil
        yt_dlp_path = shutil.which("yt-dlp")
        if not yt_dlp_path:
            # Try common venv locations
            import sys
            from pathlib import Path
            
            # Check if running in venv
            venv_bin = Path(sys.executable).parent
            possible_paths = [
                venv_bin / "yt-dlp.exe",  # Windows
                venv_bin / "yt-dlp",       # Linux/Mac
            ]
            
            for path in possible_paths:
                if path.exists():
                    yt_dlp_path = str(path)
                    break
            
            if not yt_dlp_path:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "ConfigurationError",
                        "message": "yt-dlp not found",
                        "details": "yt-dlp is not installed or not in PATH. Please install it with: pip install yt-dlp"
                    }
                )
        
        logger.info("using_yt_dlp", path=yt_dlp_path)
        
        command = [
            yt_dlp_path,
            '-f', 'bestaudio[ext=m4a]/bestaudio',  # Prefer m4a (faster, no conversion needed)
            '-o', '-',  # Output to stdout (memory)
            '--no-warnings',
            '--no-playlist',  # Don't download playlist
            '--quiet',
            '--progress',  # Show progress for debugging
            url
        ]

        # Run yt-dlp and capture output in memory
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180  # 3 minute timeout
        )

        if process.returncode != 0:
            error_message = process.stderr.decode('utf-8', errors='ignore')
            logger.error(
                "youtube_download_failed",
                url=url[:100],
                error=error_message,
                return_code=process.returncode
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DownloadError",
                    "message": "Failed to download audio from YouTube",
                    "details": error_message or "Unknown error occurred"
                }
            )

        # Audio data is now in memory (process.stdout)
        audio_data = process.stdout
        
        if not audio_data or len(audio_data) == 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DownloadError",
                    "message": "No audio data received from YouTube",
                    "details": "The download completed but no audio data was captured"
                }
            )

        logger.info(
            "youtube_conversion_completed",
            url=url[:100],
            audio_size_bytes=len(audio_data)
        )

        # Return MP3 data as streaming response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=audio.mp3"
            }
        )

    except subprocess.TimeoutExpired:
        logger.error("youtube_download_timeout", url=request.url[:100])
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TimeoutError",
                "message": "YouTube download timed out",
                "details": "The download took longer than 3 minutes. Try a shorter video."
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "youtube_conversion_unexpected_error",
            url=request.url[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during conversion",
                "details": str(e)
            }
        )

