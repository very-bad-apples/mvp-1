"""
Video Model Parameter Specifications

Comprehensive parameter definitions for all video generation models.
Each model has different capabilities and parameter requirements.

This module provides:
- Model-specific parameter schemas
- Parameter validation
- Default values for each model
- Parameter conversion/adaptation
"""

from typing import Dict, Any, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator
import structlog

logger = structlog.get_logger(__name__)


class AspectRatio(str, Enum):
    """Supported aspect ratios for video generation"""
    PORTRAIT = "9:16"  # Mobile/TikTok/Instagram Reels
    LANDSCAPE = "16:9"  # YouTube/Desktop
    SQUARE = "1:1"     # Instagram Posts
    WIDESCREEN = "21:9"  # Cinematic
    VERTICAL_4_5 = "4:5"  # Instagram vertical
    HORIZONTAL_4_3 = "4:3"  # Classic TV


class Resolution(BaseModel):
    """Video resolution specification"""
    width: int
    height: int

    def __str__(self):
        return f"{self.width}x{self.height}"

    @property
    def pixels(self) -> int:
        """Total pixel count"""
        return self.width * self.height


class VideoModelCapabilities(BaseModel):
    """Capabilities and constraints for a video generation model"""

    # Resolution support
    min_resolution: Resolution = Field(default=Resolution(width=512, height=512))
    max_resolution: Resolution = Field(default=Resolution(width=1920, height=1080))
    supported_aspect_ratios: List[AspectRatio] = Field(default=[AspectRatio.PORTRAIT, AspectRatio.LANDSCAPE])
    resolution_must_be_divisible_by: int = Field(default=8, description="Resolution divisibility requirement (e.g., 8, 16, 32)")

    # Duration support
    min_duration_seconds: float = Field(default=1.0)
    max_duration_seconds: float = Field(default=10.0)
    default_duration_seconds: float = Field(default=5.0)

    # Frame support
    min_frames: int = Field(default=8)
    max_frames: int = Field(default=257)
    frames_must_be_divisible_by: Optional[int] = Field(default=None, description="Frame count divisibility requirement")
    frames_formula: Optional[str] = Field(default=None, description="E.g., '8n+1' for LTX Video")

    # FPS support
    supported_fps: List[int] = Field(default=[24, 25, 30])
    default_fps: int = Field(default=24)

    # Feature support flags
    supports_text_to_video: bool = True
    supports_image_to_video: bool = False
    supports_first_frame: bool = False
    supports_last_frame: bool = False
    supports_prompt_optimizer: bool = False
    supports_motion_control: bool = False
    supports_camera_control: bool = False
    supports_guidance_scale: bool = True
    supports_negative_prompt: bool = False

    # Cost and performance
    cost_per_second: float = Field(default=0.08, description="USD per second of video")
    avg_generation_time_seconds: float = Field(default=120.0)


class VideoModelParameters(BaseModel):
    """
    Base parameters for video generation.
    Each model adapter translates these to model-specific parameters.
    """

    # Core parameters (all models)
    prompt: str = Field(..., description="Text description of the video")

    # Resolution and aspect ratio
    width: Optional[int] = Field(default=None, description="Video width in pixels")
    height: Optional[int] = Field(default=None, description="Video height in pixels")
    aspect_ratio: Optional[AspectRatio] = Field(default=AspectRatio.PORTRAIT)

    # Duration and frames
    duration: Optional[float] = Field(default=5.0, description="Duration in seconds")
    num_frames: Optional[int] = Field(default=None, description="Total number of frames (alternative to duration)")
    fps: int = Field(default=24, description="Frames per second")

    # Image inputs (for image-to-video models)
    first_frame_image: Optional[str] = Field(default=None, description="Path or URL to first frame image")
    last_frame_image: Optional[str] = Field(default=None, description="Path or URL to last frame image")

    # Generation controls
    guidance_scale: float = Field(default=7.5, description="How closely to follow the prompt (1-20)")
    num_inference_steps: int = Field(default=50, description="Number of denoising steps")
    negative_prompt: Optional[str] = Field(default=None, description="What to avoid in the video")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")

    # Motion controls
    motion_bucket_id: Optional[int] = Field(default=127, description="Motion intensity (for SVD)")
    motion_intensity: Optional[Literal["low", "medium", "high"]] = Field(default=None)

    # Model-specific
    prompt_optimizer: bool = Field(default=False, description="Use prompt optimization (Minimax)")
    camera_motion: Optional[str] = Field(default=None, description="Camera movement description")

    class Config:
        use_enum_values = True


# ==================== MODEL-SPECIFIC CONFIGURATIONS ====================


class MinimaxVideoParams(BaseModel):
    """Parameters for Minimax Video-01 (Hailuo)"""

    prompt: str
    prompt_optimizer: bool = True
    first_frame_image: Optional[str] = None
    last_image_url: Optional[str] = None


MINIMAX_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=1280, height=720),
    max_resolution=Resolution(width=1280, height=720),
    supported_aspect_ratios=[AspectRatio.LANDSCAPE, AspectRatio.PORTRAIT, AspectRatio.SQUARE],
    resolution_must_be_divisible_by=16,

    min_duration_seconds=1.0,
    max_duration_seconds=6.0,
    default_duration_seconds=6.0,

    min_frames=25,
    max_frames=150,  # 6 seconds * 25 fps
    default_fps=25,
    supported_fps=[25],

    supports_text_to_video=True,
    supports_image_to_video=True,
    supports_first_frame=True,
    supports_last_frame=True,
    supports_prompt_optimizer=True,
    supports_camera_control=True,
    supports_guidance_scale=False,  # Not exposed in API

    cost_per_second=0.12 / 6,  # $0.12 for 6 seconds
    avg_generation_time_seconds=180.0
)


class LTXVideoParams(BaseModel):
    """Parameters for LTX Video (Lightricks)"""

    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 768
    height: int = 512
    num_frames: int = 121  # Must be 8n+1
    num_inference_steps: int = 50
    guidance_scale: float = 3.0
    seed: Optional[int] = None
    frame_rate: int = 25
    image: Optional[str] = None  # First frame for image-to-video


LTX_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=512, height=512),
    max_resolution=Resolution(width=1216, height=704),
    supported_aspect_ratios=[AspectRatio.PORTRAIT, AspectRatio.LANDSCAPE, AspectRatio.SQUARE],
    resolution_must_be_divisible_by=32,

    min_duration_seconds=1.0,
    max_duration_seconds=10.0,
    default_duration_seconds=5.0,

    min_frames=9,  # 8n+1 formula
    max_frames=257,  # 8*32 + 1
    frames_formula="8n+1",
    frames_must_be_divisible_by=None,

    supported_fps=[24, 25, 30],
    default_fps=25,

    supports_text_to_video=True,
    supports_image_to_video=True,
    supports_first_frame=True,
    supports_guidance_scale=True,
    supports_negative_prompt=True,

    cost_per_second=0.08 / 5,
    avg_generation_time_seconds=90.0
)


class StableVideoDiffusionParams(BaseModel):
    """Parameters for Stable Video Diffusion (image-to-video only)"""

    image: str  # Required - input image path/URL
    num_frames: int = 25
    fps: int = 6
    motion_bucket_id: int = 127  # 1-255, higher = more motion
    cond_aug: float = 0.02  # Conditioning augmentation
    decoding_t: int = 14  # Number of frames decoded at a time
    seed: Optional[int] = None


SVD_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=576, height=1024),
    max_resolution=Resolution(width=576, height=1024),
    supported_aspect_ratios=[AspectRatio.PORTRAIT],
    resolution_must_be_divisible_by=64,

    min_duration_seconds=1.0,
    max_duration_seconds=4.0,
    default_duration_seconds=4.0,

    min_frames=14,
    max_frames=25,

    supported_fps=[6, 12, 24],
    default_fps=6,

    supports_text_to_video=False,  # Image-to-video only
    supports_image_to_video=True,
    supports_first_frame=True,
    supports_motion_control=True,
    supports_guidance_scale=False,

    cost_per_second=0.05 / 4,
    avg_generation_time_seconds=60.0
)


class SeedanceProParams(BaseModel):
    """Parameters for ByteDance Seedance-1-Pro"""

    prompt: str
    width: int = 720
    height: int = 1280
    duration: Literal["4s", "6s"] = "6s"
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    first_frame: Optional[str] = None
    last_frame: Optional[str] = None
    seed: Optional[int] = None


SEEDANCE_PRO_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=720, height=1280),
    max_resolution=Resolution(width=1280, height=720),
    supported_aspect_ratios=[AspectRatio.PORTRAIT, AspectRatio.LANDSCAPE, AspectRatio.SQUARE],

    min_duration_seconds=4.0,
    max_duration_seconds=6.0,
    default_duration_seconds=6.0,

    min_frames=96,  # 4s * 24fps
    max_frames=144,  # 6s * 24fps

    supported_fps=[24],
    default_fps=24,

    supports_text_to_video=True,
    supports_image_to_video=True,
    supports_first_frame=True,
    supports_last_frame=True,
    supports_camera_control=True,

    cost_per_second=0.40 / 6,
    avg_generation_time_seconds=300.0
)


class HailuoParams(BaseModel):
    """Parameters for Minimax Hailuo 2.3"""

    prompt: str
    resolution: Literal["720P", "1080P"] = "720P"
    duration: Literal["5s", "10s"] = "5s"
    prompt_optimizer: bool = True
    seed: Optional[int] = None


HAILUO_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=1280, height=720),
    max_resolution=Resolution(width=1920, height=1080),
    supported_aspect_ratios=[AspectRatio.LANDSCAPE, AspectRatio.PORTRAIT],

    min_duration_seconds=5.0,
    max_duration_seconds=10.0,
    default_duration_seconds=5.0,

    supported_fps=[25, 30],
    default_fps=25,

    supports_text_to_video=True,
    supports_prompt_optimizer=True,

    cost_per_second=0.15 / 5,
    avg_generation_time_seconds=240.0
)


class VeoParams(BaseModel):
    """Parameters for Google Veo 3.1"""

    prompt: str
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    duration: int = 5  # seconds
    seed: Optional[int] = None


VEO_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=720, height=1280),
    max_resolution=Resolution(width=1920, height=1080),
    supported_aspect_ratios=[AspectRatio.PORTRAIT, AspectRatio.LANDSCAPE, AspectRatio.SQUARE],

    min_duration_seconds=2.0,
    max_duration_seconds=10.0,
    default_duration_seconds=5.0,

    supported_fps=[24, 30],
    default_fps=30,

    supports_text_to_video=True,

    cost_per_second=0.20 / 5,
    avg_generation_time_seconds=180.0
)


class SoraParams(BaseModel):
    """Parameters for OpenAI Sora 2"""

    prompt: str
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    duration: int = 5  # seconds (1-20)
    resolution: Literal["480p", "720p", "1080p"] = "1080p"
    seed: Optional[int] = None


SORA_CAPABILITIES = VideoModelCapabilities(
    min_resolution=Resolution(width=720, height=1280),
    max_resolution=Resolution(width=1920, height=1080),
    supported_aspect_ratios=[AspectRatio.PORTRAIT, AspectRatio.LANDSCAPE, AspectRatio.SQUARE],

    min_duration_seconds=1.0,
    max_duration_seconds=20.0,
    default_duration_seconds=5.0,

    supported_fps=[24, 30],
    default_fps=30,

    supports_text_to_video=True,

    cost_per_second=0.50 / 5,
    avg_generation_time_seconds=300.0
)


# ==================== MODEL REGISTRY ====================


class VideoModelSpec(BaseModel):
    """Complete specification for a video model"""

    model_id: str
    display_name: str
    description: str
    capabilities: VideoModelCapabilities
    param_class: type  # Pydantic model for parameters

    class Config:
        arbitrary_types_allowed = True


VIDEO_MODEL_REGISTRY: Dict[str, VideoModelSpec] = {
    "minimax": VideoModelSpec(
        model_id="minimax/video-01",
        display_name="Minimax Video-01 (Kling)",
        description="High-quality 6s videos with camera control, 720p, 25fps",
        capabilities=MINIMAX_CAPABILITIES,
        param_class=MinimaxVideoParams
    ),

    "ltxv": VideoModelSpec(
        model_id="lightricks/ltx-video",
        display_name="LTX Video",
        description="Fast text/image-to-video, up to 10s, 1216x704, 30fps",
        capabilities=LTX_CAPABILITIES,
        param_class=LTXVideoParams
    ),

    "svd": VideoModelSpec(
        model_id="stability-ai/stable-video-diffusion",
        display_name="Stable Video Diffusion",
        description="Image-to-video only, 4s max, 576x1024, motion control",
        capabilities=SVD_CAPABILITIES,
        param_class=StableVideoDiffusionParams
    ),

    "seedance-pro": VideoModelSpec(
        model_id="bytedance/seedance-1-pro",
        display_name="Seedance-1 Pro",
        description="Cinematic quality, 6s max, 720-1280p, first/last frame",
        capabilities=SEEDANCE_PRO_CAPABILITIES,
        param_class=SeedanceProParams
    ),

    "hailuo": VideoModelSpec(
        model_id="minimax/hailuo-2.3",
        display_name="Hailuo 2.3",
        description="High-fidelity video, up to 10s, 720-1080p, prompt optimizer",
        capabilities=HAILUO_CAPABILITIES,
        param_class=HailuoParams
    ),

    "veo": VideoModelSpec(
        model_id="google/veo-3.1",
        display_name="Google Veo 3.1",
        description="High-quality video, up to 10s, context-aware",
        capabilities=VEO_CAPABILITIES,
        param_class=VeoParams
    ),

    "sora": VideoModelSpec(
        model_id="openai/sora-2",
        display_name="OpenAI Sora 2",
        description="Flagship video model, up to 20s, 480-1080p, synced audio",
        capabilities=SORA_CAPABILITIES,
        param_class=SoraParams
    ),
}


# ==================== PARAMETER ADAPTER ====================


class VideoParameterAdapter:
    """
    Adapts generic VideoModelParameters to model-specific parameters.

    This class handles the translation between our unified parameter interface
    and the specific parameter requirements of each model.
    """

    @staticmethod
    def adapt_for_model(
        model_name: str,
        params: VideoModelParameters
    ) -> Dict[str, Any]:
        """
        Convert generic parameters to model-specific parameters.

        Args:
            model_name: Name of the model (e.g., "minimax", "ltxv")
            params: Generic video parameters

        Returns:
            Dictionary of model-specific parameters

        Raises:
            ValueError: If model not found or parameters invalid
        """
        if model_name not in VIDEO_MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model '{model_name}'. "
                f"Available: {list(VIDEO_MODEL_REGISTRY.keys())}"
            )

        spec = VIDEO_MODEL_REGISTRY[model_name]
        caps = spec.capabilities

        # Validate against capabilities
        VideoParameterAdapter._validate_params(params, caps)

        # Model-specific adaptation
        if model_name == "minimax":
            return VideoParameterAdapter._adapt_minimax(params, caps)
        elif model_name == "ltxv":
            return VideoParameterAdapter._adapt_ltx(params, caps)
        elif model_name == "svd":
            return VideoParameterAdapter._adapt_svd(params, caps)
        elif model_name == "seedance-pro":
            return VideoParameterAdapter._adapt_seedance(params, caps)
        elif model_name == "hailuo":
            return VideoParameterAdapter._adapt_hailuo(params, caps)
        elif model_name == "veo":
            return VideoParameterAdapter._adapt_veo(params, caps)
        elif model_name == "sora":
            return VideoParameterAdapter._adapt_sora(params, caps)
        else:
            # Fallback: basic parameters
            return {"prompt": params.prompt}

    @staticmethod
    def _validate_params(params: VideoModelParameters, caps: VideoModelCapabilities):
        """Validate parameters against model capabilities"""

        # Check duration
        if params.duration:
            if params.duration < caps.min_duration_seconds:
                raise ValueError(
                    f"Duration {params.duration}s below minimum {caps.min_duration_seconds}s"
                )
            if params.duration > caps.max_duration_seconds:
                raise ValueError(
                    f"Duration {params.duration}s exceeds maximum {caps.max_duration_seconds}s"
                )

        # Check FPS
        if params.fps not in caps.supported_fps:
            logger.warning(
                "fps_not_supported",
                requested=params.fps,
                supported=caps.supported_fps,
                using_default=caps.default_fps
            )

        # Check image-to-video support
        if params.first_frame_image and not caps.supports_first_frame:
            raise ValueError("Model does not support first frame image input")

    @staticmethod
    def _adapt_minimax(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for Minimax Video-01"""
        adapted = {
            "prompt": params.prompt,
            "prompt_optimizer": params.prompt_optimizer,
        }

        if params.first_frame_image:
            adapted["first_frame_image"] = params.first_frame_image

        if params.last_frame_image:
            adapted["last_image_url"] = params.last_frame_image

        return adapted

    @staticmethod
    def _adapt_ltx(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for LTX Video"""

        # Calculate num_frames using 8n+1 formula
        if params.num_frames:
            num_frames = params.num_frames
        else:
            # duration * fps, then round to nearest 8n+1
            target_frames = int(params.duration * params.fps)
            n = (target_frames - 1) // 8
            num_frames = 8 * n + 1

        adapted = {
            "prompt": params.prompt,
            "num_frames": num_frames,
            "width": params.width or 768,
            "height": params.height or 512,
            "num_inference_steps": params.num_inference_steps,
            "guidance_scale": params.guidance_scale,
            "frame_rate": params.fps,
        }

        if params.negative_prompt:
            adapted["negative_prompt"] = params.negative_prompt

        if params.seed:
            adapted["seed"] = params.seed

        if params.first_frame_image:
            adapted["image"] = params.first_frame_image

        return adapted

    @staticmethod
    def _adapt_svd(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for Stable Video Diffusion"""

        if not params.first_frame_image:
            raise ValueError("Stable Video Diffusion requires first_frame_image")

        # Map motion intensity to motion_bucket_id
        motion_map = {"low": 50, "medium": 127, "high": 200}
        motion_bucket = params.motion_bucket_id
        if params.motion_intensity:
            motion_bucket = motion_map.get(params.motion_intensity, 127)

        num_frames = params.num_frames or int(params.duration * params.fps)

        return {
            "image": params.first_frame_image,
            "num_frames": min(num_frames, 25),
            "fps": params.fps,
            "motion_bucket_id": motion_bucket,
            "cond_aug": 0.02,
            "decoding_t": 14,
            "seed": params.seed,
        }

    @staticmethod
    def _adapt_seedance(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for Seedance-1 Pro"""

        # Duration must be "4s" or "6s"
        duration_str = "6s" if params.duration >= 5 else "4s"

        adapted = {
            "prompt": params.prompt,
            "duration": duration_str,
            "aspect_ratio": params.aspect_ratio.value if params.aspect_ratio else "9:16",
            "width": params.width or 720,
            "height": params.height or 1280,
        }

        if params.first_frame_image:
            adapted["first_frame"] = params.first_frame_image

        if params.last_frame_image:
            adapted["last_frame"] = params.last_frame_image

        if params.seed:
            adapted["seed"] = params.seed

        return adapted

    @staticmethod
    def _adapt_hailuo(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for Hailuo 2.3"""

        # Duration must be "5s" or "10s"
        duration_str = "10s" if params.duration >= 7.5 else "5s"

        # Resolution must be "720P" or "1080P"
        resolution_str = "1080P" if (params.width or 1280) >= 1920 else "720P"

        return {
            "prompt": params.prompt,
            "resolution": resolution_str,
            "duration": duration_str,
            "prompt_optimizer": params.prompt_optimizer,
            "seed": params.seed,
        }

    @staticmethod
    def _adapt_veo(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for Google Veo"""

        return {
            "prompt": params.prompt,
            "aspect_ratio": params.aspect_ratio.value if params.aspect_ratio else "9:16",
            "duration": int(params.duration),
            "seed": params.seed,
        }

    @staticmethod
    def _adapt_sora(params: VideoModelParameters, caps: VideoModelCapabilities) -> Dict[str, Any]:
        """Adapt parameters for OpenAI Sora"""

        # Determine resolution string
        height = params.height or 1280
        if height >= 1080:
            resolution_str = "1080p"
        elif height >= 720:
            resolution_str = "720p"
        else:
            resolution_str = "480p"

        return {
            "prompt": params.prompt,
            "aspect_ratio": params.aspect_ratio.value if params.aspect_ratio else "9:16",
            "duration": int(min(params.duration, 20)),  # Max 20s
            "resolution": resolution_str,
            "seed": params.seed,
        }


# ==================== UTILITY FUNCTIONS ====================


def get_model_spec(model_name: str) -> VideoModelSpec:
    """Get the full specification for a model"""
    if model_name not in VIDEO_MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model '{model_name}'. "
            f"Available: {list(VIDEO_MODEL_REGISTRY.keys())}"
        )
    return VIDEO_MODEL_REGISTRY[model_name]


def list_models() -> Dict[str, VideoModelSpec]:
    """Get all available video models"""
    return VIDEO_MODEL_REGISTRY.copy()


def get_model_info(model_name: str) -> Dict[str, Any]:
    """Get human-readable information about a model"""
    spec = get_model_spec(model_name)
    caps = spec.capabilities

    return {
        "model_id": spec.model_id,
        "display_name": spec.display_name,
        "description": spec.description,
        "resolution": {
            "min": str(caps.min_resolution),
            "max": str(caps.max_resolution),
            "divisible_by": caps.resolution_must_be_divisible_by,
        },
        "duration": {
            "min_seconds": caps.min_duration_seconds,
            "max_seconds": caps.max_duration_seconds,
            "default_seconds": caps.default_duration_seconds,
        },
        "frames": {
            "min": caps.min_frames,
            "max": caps.max_frames,
            "formula": caps.frames_formula,
        },
        "fps": {
            "supported": caps.supported_fps,
            "default": caps.default_fps,
        },
        "aspect_ratios": [ar.value for ar in caps.supported_aspect_ratios],
        "features": {
            "text_to_video": caps.supports_text_to_video,
            "image_to_video": caps.supports_image_to_video,
            "first_frame": caps.supports_first_frame,
            "last_frame": caps.supports_last_frame,
            "prompt_optimizer": caps.supports_prompt_optimizer,
            "motion_control": caps.supports_motion_control,
            "camera_control": caps.supports_camera_control,
            "guidance_scale": caps.supports_guidance_scale,
            "negative_prompt": caps.supports_negative_prompt,
        },
        "cost": {
            "per_second_usd": caps.cost_per_second,
            "avg_generation_time_seconds": caps.avg_generation_time_seconds,
        }
    }
