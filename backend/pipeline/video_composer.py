"""
Video Composer with MoviePy Integration

Composes final video from generated assets:
- Video scenes (MP4 files)
- Voiceovers (MP3 files)
- CTA image (PNG file)
- Optional background music

Features:
- Audio-video synchronization
- Smooth transitions between scenes
- CTA image as final scene
- Background music mixing
- 9:16 vertical format optimization
- Export settings for social media
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import time

import structlog
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    vfx
)
from pipeline.asset_manager import AssetManager

logger = structlog.get_logger(__name__)


class VideoCompositionError(Exception):
    """Raised when video composition fails"""
    pass


class VideoComposer:
    """
    Compose final video from generated assets.

    Features:
    - Load video scenes, voiceovers, CTA image
    - Sync audio with video
    - Add transitions between scenes
    - Composite CTA image as final frame
    - Add optional background music
    - Export final video (9:16 format, MP4)

    Example:
        >>> composer = VideoComposer()
        >>> final_video = await composer.compose_video(
        ...     video_scenes=["scene1.mp4", "scene2.mp4"],
        ...     voiceovers=["vo1.mp3", "vo2.mp3"],
        ...     cta_image_path="cta.png",
        ...     asset_manager=am
        ... )
    """

    def __init__(self, asset_manager: Optional[AssetManager] = None):
        """
        Initialize VideoComposer.

        Args:
            asset_manager: AssetManager instance for file operations
        """
        self.asset_manager = asset_manager
        self.logger = structlog.get_logger().bind(service="video_composer")

        # Default export settings for 9:16 vertical video
        self.default_settings = {
            "fps": 30,
            "codec": "libx264",
            "audio_codec": "aac",
            "preset": "medium",  # Balance speed vs compression
            "bitrate": "5000k",  # 5 Mbps for high quality
            "audio_bitrate": "192k",
            "target_resolution": (1080, 1920),  # 9:16 aspect ratio
        }

        self.logger.info("video_composer_initialized")

    async def compose_video(
        self,
        video_scenes: List[str],
        voiceovers: List[str],
        cta_image_path: str,
        background_music_path: Optional[str] = None,
        output_path: Optional[str] = None,
        transition_duration: float = 0.5,
        cta_duration: float = 4.0,
        background_music_volume: float = 0.1
    ) -> str:
        """
        Compose final video from all assets.

        Steps:
        1. Load all video clips
        2. Sync audio with video for each scene
        3. Add transitions between scenes
        4. Append CTA image as final scene
        5. Add background music (if provided)
        6. Export final video

        Args:
            video_scenes: List of paths to video clips
            voiceovers: List of paths to audio files (must match video_scenes length)
            cta_image_path: Path to CTA image
            background_music_path: Optional path to background music
            output_path: Optional output path (defaults to asset_manager)
            transition_duration: Duration of fade transitions (default: 0.5s)
            cta_duration: Duration to display CTA image (default: 4.0s)
            background_music_volume: Background music volume (default: 0.1)

        Returns:
            Path to final composed video

        Raises:
            VideoCompositionError: If composition fails

        Example:
            >>> final_video = await composer.compose_video(
            ...     video_scenes=["scene1.mp4", "scene2.mp4"],
            ...     voiceovers=["vo1.mp3", "vo2.mp3"],
            ...     cta_image_path="cta.png"
            ... )
        """
        self.logger.info(
            "starting_video_composition",
            num_scenes=len(video_scenes),
            has_background_music=background_music_path is not None,
            transition_duration=transition_duration
        )

        # Validate inputs
        if len(video_scenes) != len(voiceovers):
            raise VideoCompositionError(
                f"Mismatch: {len(video_scenes)} video scenes but {len(voiceovers)} voiceovers"
            )

        if not video_scenes:
            raise VideoCompositionError("No video scenes provided")

        try:
            # Run composition in thread pool (MoviePy is blocking)
            final_path = await asyncio.to_thread(
                self._compose_video_sync,
                video_scenes,
                voiceovers,
                cta_image_path,
                background_music_path,
                output_path,
                transition_duration,
                cta_duration,
                background_music_volume
            )

            self.logger.info(
                "video_composition_complete",
                output_path=final_path
            )

            return final_path

        except Exception as e:
            self.logger.error(
                "video_composition_failed",
                error=str(e)
            )
            raise VideoCompositionError(f"Failed to compose video: {e}") from e

    def _compose_video_sync(
        self,
        video_scenes: List[str],
        voiceovers: List[str],
        cta_image_path: str,
        background_music_path: Optional[str],
        output_path: Optional[str],
        transition_duration: float,
        cta_duration: float,
        background_music_volume: float
    ) -> str:
        """
        Synchronous video composition (runs in thread pool).

        This method does the actual MoviePy work which is blocking.
        """
        self.logger.info("loading_clips")

        # Load and sync all scene clips with their voiceovers
        synced_clips = []
        for i, (video_path, audio_path) in enumerate(zip(video_scenes, voiceovers), 1):
            self.logger.debug(
                "processing_scene",
                scene=i,
                video=video_path,
                audio=audio_path
            )

            synced_clip = self._sync_audio_to_video(video_path, audio_path)
            synced_clips.append(synced_clip)

        self.logger.info(
            "clips_loaded_and_synced",
            num_clips=len(synced_clips)
        )

        # Add fade transitions
        self.logger.info("adding_transitions")
        transitioned_clips = self._add_transitions(synced_clips, transition_duration)

        # Concatenate all scene clips
        self.logger.info("concatenating_scenes")
        main_video = concatenate_videoclips(transitioned_clips, method="compose")

        # Create CTA scene
        self.logger.info("creating_cta_scene")
        cta_clip = self._create_cta_scene(cta_image_path, cta_duration)

        # Add fade in for CTA
        cta_clip = cta_clip.fadein(duration=0.5)

        # Concatenate main video with CTA
        self.logger.info("appending_cta")
        final_video = concatenate_videoclips([main_video, cta_clip], method="compose")

        # Add background music if provided
        if background_music_path:
            self.logger.info(
                "adding_background_music",
                volume=background_music_volume
            )
            final_video = self._add_background_music(
                final_video,
                background_music_path,
                background_music_volume
            )

        # Ensure 9:16 aspect ratio
        final_video = self._ensure_aspect_ratio(final_video)

        # Determine output path
        if output_path is None:
            timestamp = int(time.time())
            filename = f"final_video_{timestamp}.mp4"

            if self.asset_manager:
                output_path = str(self.asset_manager.final_dir / filename)
            else:
                output_path = f"/tmp/{filename}"

        # Export video
        self.logger.info(
            "exporting_video",
            output_path=output_path,
            duration=final_video.duration
        )

        final_video = self._export_video(final_video, output_path)

        # Clean up clips to free memory
        self.logger.debug("cleaning_up_clips")
        for clip in synced_clips:
            clip.close()
        cta_clip.close()
        main_video.close()

        return output_path

    def _load_video_clip(self, video_path: str) -> VideoFileClip:
        """
        Load a video clip from file.

        Args:
            video_path: Path to video file

        Returns:
            VideoFileClip object
        """
        try:
            clip = VideoFileClip(video_path)
            self.logger.debug(
                "video_clip_loaded",
                path=video_path,
                duration=clip.duration,
                size=clip.size
            )
            return clip
        except Exception as e:
            self.logger.error(
                "failed_to_load_video",
                path=video_path,
                error=str(e)
            )
            raise VideoCompositionError(f"Failed to load video {video_path}: {e}")

    def _sync_audio_to_video(self, video_path: str, audio_path: str) -> VideoFileClip:
        """
        Sync voiceover audio with video clip.

        Strategy:
        - If video shorter than audio: extend video (freeze last frame)
        - If video longer than audio: trim video to match audio
        - Set audio track to video

        Args:
            video_path: Path to video file
            audio_path: Path to audio file

        Returns:
            Video clip with synced audio
        """
        # Load video and audio
        video_clip = self._load_video_clip(video_path)

        try:
            audio_clip = AudioFileClip(audio_path)
        except Exception as e:
            video_clip.close()
            raise VideoCompositionError(f"Failed to load audio {audio_path}: {e}")

        video_duration = video_clip.duration
        audio_duration = audio_clip.duration

        self.logger.debug(
            "syncing_audio_video",
            video_duration=video_duration,
            audio_duration=audio_duration
        )

        # Adjust video duration to match audio
        if video_duration < audio_duration:
            # Video too short - freeze last frame
            freeze_duration = audio_duration - video_duration
            self.logger.debug(
                "extending_video",
                freeze_duration=freeze_duration
            )

            # Get last frame as image
            last_frame = video_clip.get_frame(video_duration - 0.001)
            freeze_clip = ImageClip(last_frame, duration=freeze_duration)
            freeze_clip = freeze_clip.set_fps(video_clip.fps)

            # Concatenate original video with freeze frame
            video_clip = concatenate_videoclips([video_clip, freeze_clip])

        elif video_duration > audio_duration:
            # Video too long - trim to audio duration
            self.logger.debug(
                "trimming_video",
                original_duration=video_duration,
                new_duration=audio_duration
            )
            video_clip = video_clip.subclip(0, audio_duration)

        # Set audio
        video_clip = video_clip.set_audio(audio_clip)

        self.logger.debug(
            "audio_synced",
            final_duration=video_clip.duration
        )

        return video_clip

    def _add_transitions(
        self,
        clips: List[VideoFileClip],
        transition_duration: float = 0.5
    ) -> List[VideoFileClip]:
        """
        Add fade transitions to clips.

        Each clip gets:
        - Fade in at start (except first clip)
        - Fade out at end (except last clip)

        Args:
            clips: List of video clips
            transition_duration: Duration of fade effect

        Returns:
            List of clips with transitions applied
        """
        if not clips:
            return clips

        transitioned = []

        for i, clip in enumerate(clips):
            # Apply fade in (except for first clip)
            if i > 0:
                clip = clip.fadein(duration=transition_duration)

            # Apply fade out (except for last clip)
            if i < len(clips) - 1:
                clip = clip.fadeout(duration=transition_duration)

            transitioned.append(clip)

        return transitioned

    def _create_cta_scene(self, cta_image_path: str, duration: float = 4.0) -> ImageClip:
        """
        Create video clip from CTA static image.

        Args:
            cta_image_path: Path to CTA image (PNG with text overlay)
            duration: How long to display CTA (default 4 seconds)

        Returns:
            Video clip of static CTA image
        """
        try:
            cta_clip = ImageClip(cta_image_path, duration=duration)

            # Ensure 9:16 aspect ratio (1080x1920)
            target_width, target_height = self.default_settings["target_resolution"]

            # Resize to match target height, maintaining aspect ratio
            cta_clip = cta_clip.resize(height=target_height)

            # If width doesn't match, crop or pad
            if cta_clip.w != target_width:
                self.logger.debug(
                    "adjusting_cta_width",
                    current=cta_clip.w,
                    target=target_width
                )
                cta_clip = cta_clip.resize(width=target_width)

            self.logger.debug(
                "cta_scene_created",
                duration=duration,
                size=(cta_clip.w, cta_clip.h)
            )

            return cta_clip

        except Exception as e:
            raise VideoCompositionError(f"Failed to create CTA scene: {e}")

    def _add_background_music(
        self,
        video_clip: VideoFileClip,
        music_path: str,
        volume: float = 0.1
    ) -> VideoFileClip:
        """
        Add background music to entire video.

        - Loop music if shorter than video
        - Mix with voiceover audio (lower volume)

        Args:
            video_clip: Video clip to add music to
            music_path: Path to music file
            volume: Music volume (0.0 to 1.0, default 0.1)

        Returns:
            Video clip with background music
        """
        try:
            music = AudioFileClip(music_path)

            # Loop music to match video duration
            if music.duration < video_clip.duration:
                self.logger.debug(
                    "looping_background_music",
                    music_duration=music.duration,
                    video_duration=video_clip.duration
                )

                # Calculate how many loops needed
                num_loops = int(video_clip.duration / music.duration) + 1
                music_clips = [music] * num_loops
                music = concatenate_videoclips([AudioFileClip(music_path) for _ in range(num_loops)])

            # Trim to exact video duration
            music = music.subclip(0, video_clip.duration)

            # Reduce volume
            music = music.volumex(volume)

            # Mix with existing audio
            if video_clip.audio:
                final_audio = CompositeAudioClip([video_clip.audio, music])
                video_clip = video_clip.set_audio(final_audio)
            else:
                video_clip = video_clip.set_audio(music)

            self.logger.debug("background_music_added")

            return video_clip

        except Exception as e:
            self.logger.warning(
                "failed_to_add_background_music",
                error=str(e)
            )
            # Return original clip if music fails (non-critical)
            return video_clip

    def _ensure_aspect_ratio(self, video_clip: VideoFileClip) -> VideoFileClip:
        """
        Ensure video is 9:16 aspect ratio (1080x1920).

        If not already correct aspect ratio:
        - Resize to target height
        - Crop or pad width as needed

        Args:
            video_clip: Input video clip

        Returns:
            Video clip with 9:16 aspect ratio
        """
        target_width, target_height = self.default_settings["target_resolution"]
        current_width, current_height = video_clip.size

        # Check if already correct aspect ratio
        target_aspect = target_width / target_height
        current_aspect = current_width / current_height

        if abs(current_aspect - target_aspect) < 0.01:
            # Already correct aspect ratio
            if current_height != target_height:
                video_clip = video_clip.resize(height=target_height)
            return video_clip

        self.logger.debug(
            "adjusting_aspect_ratio",
            current_size=(current_width, current_height),
            target_size=(target_width, target_height)
        )

        # Resize to target height
        video_clip = video_clip.resize(height=target_height)

        # Adjust width if needed
        if video_clip.w != target_width:
            video_clip = video_clip.resize(width=target_width)

        return video_clip

    def _export_video(
        self,
        video_clip: VideoFileClip,
        output_path: str,
        fps: Optional[int] = None,
        codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        preset: Optional[str] = None,
        bitrate: Optional[str] = None,
        audio_bitrate: Optional[str] = None
    ) -> str:
        """
        Export final video to file.

        Settings optimized for:
        - 9:16 vertical format
        - Social media (Instagram, TikTok, YouTube Shorts)
        - High quality, reasonable file size

        Args:
            video_clip: Video clip to export
            output_path: Path to save video
            fps: Frames per second (default: 30)
            codec: Video codec (default: libx264)
            audio_codec: Audio codec (default: aac)
            preset: Encoding preset (default: medium)
            bitrate: Video bitrate (default: 5000k)
            audio_bitrate: Audio bitrate (default: 192k)

        Returns:
            Path to exported video
        """
        # Use defaults if not specified
        fps = fps or self.default_settings["fps"]
        codec = codec or self.default_settings["codec"]
        audio_codec = audio_codec or self.default_settings["audio_codec"]
        preset = preset or self.default_settings["preset"]
        bitrate = bitrate or self.default_settings["bitrate"]
        audio_bitrate = audio_bitrate or self.default_settings["audio_bitrate"]

        self.logger.info(
            "exporting_video",
            output_path=output_path,
            fps=fps,
            codec=codec,
            bitrate=bitrate
        )

        try:
            video_clip.write_videofile(
                output_path,
                fps=fps,
                codec=codec,
                audio_codec=audio_codec,
                preset=preset,
                bitrate=bitrate,
                audio_bitrate=audio_bitrate,
                threads=4,  # Use multiple threads for faster encoding
                logger=None  # Suppress MoviePy's verbose logging
            )

            # Validate exported file
            output_file = Path(output_path)
            if not output_file.exists():
                raise VideoCompositionError(f"Export failed: file not created at {output_path}")

            file_size = output_file.stat().st_size
            self.logger.info(
                "video_exported_successfully",
                output_path=output_path,
                file_size_mb=file_size / (1024 * 1024)
            )

            return output_path

        except Exception as e:
            raise VideoCompositionError(f"Failed to export video: {e}")


def create_video_composer(asset_manager: Optional[AssetManager] = None) -> VideoComposer:
    """
    Factory function to create VideoComposer instance.

    Args:
        asset_manager: Optional AssetManager for file operations

    Returns:
        Configured VideoComposer instance

    Example:
        >>> composer = create_video_composer(asset_manager=am)
        >>> video = await composer.compose_video(...)
    """
    return VideoComposer(asset_manager=asset_manager)
