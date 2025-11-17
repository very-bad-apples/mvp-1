/**
 * Type definitions for the FinalVideoPlayer component
 */

/**
 * Video metadata display information
 */
export interface VideoMetadata {
  /** Video title */
  title: string

  /** Video description */
  description?: string

  /** Video duration in seconds */
  duration: number

  /** File size in bytes */
  fileSize?: number

  /** Resolution (e.g., "1920x1080") */
  resolution?: string

  /** Video format (e.g., "mp4", "webm") */
  format?: string

  /** Creation timestamp */
  createdAt?: string
}

/**
 * Video source configuration
 */
export interface VideoSource {
  /** Video URL */
  url: string

  /** Video type/format */
  type?: string

  /** Quality label (e.g., "1080p", "720p") */
  quality?: string
}

/**
 * Video player control state
 */
export interface VideoControlState {
  /** Whether video is currently playing */
  isPlaying: boolean

  /** Whether video is muted */
  isMuted: boolean

  /** Volume level (0-1) */
  volume: number

  /** Current playback time in seconds */
  currentTime: number

  /** Total duration in seconds */
  duration: number

  /** Whether player is in fullscreen mode */
  isFullscreen: boolean

  /** Playback rate/speed (0.5, 1, 1.5, 2, etc.) */
  playbackRate: number

  /** Buffer percentage (0-100) */
  buffered: number

  /** Whether video is currently loading */
  isLoading: boolean

  /** Whether controls are visible */
  showControls: boolean
}

/**
 * Share options for video
 */
export interface ShareOptions {
  /** Share method type */
  method: 'copy' | 'twitter' | 'facebook' | 'native' | 'email'

  /** URL to share */
  url: string

  /** Share title */
  title?: string

  /** Share description */
  description?: string
}

/**
 * Download options for video
 */
export interface DownloadOptions {
  /** Video URL to download */
  url: string

  /** Suggested filename */
  filename?: string

  /** Whether to force download vs. opening in new tab */
  forceDownload?: boolean
}

/**
 * Props for FinalVideoPlayer component
 */
export interface FinalVideoPlayerProps {
  /** Video source URL or sources array */
  src: string | VideoSource[]

  /** Optional poster/thumbnail image */
  poster?: string

  /** Video metadata for display */
  metadata?: VideoMetadata

  /** Whether to autoplay the video */
  autoPlay?: boolean

  /** Whether to start muted */
  muted?: boolean

  /** Whether to loop the video */
  loop?: boolean

  /** Custom CSS classes */
  className?: string

  /** Whether to show the download button */
  showDownload?: boolean

  /** Whether to show the share button */
  showShare?: boolean

  /** Whether to show metadata display */
  showMetadata?: boolean

  /** Callback when video ends */
  onEnded?: () => void

  /** Callback when video errors */
  onError?: (error: Error) => void

  /** Callback when video starts playing */
  onPlay?: () => void

  /** Callback when video pauses */
  onPause?: () => void

  /** Callback when download is initiated */
  onDownload?: () => void

  /** Callback when share is initiated */
  onShare?: (method: string) => void
}

/**
 * Keyboard shortcuts configuration
 */
export interface KeyboardShortcut {
  /** Key or key combination */
  key: string

  /** Alternative keys */
  altKeys?: string[]

  /** Description of the action */
  description: string

  /** Action handler */
  action: () => void
}
