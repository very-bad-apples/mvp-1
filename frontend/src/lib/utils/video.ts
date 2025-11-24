import { ProjectScene } from '@/types/project'

/**
 * Extract the S3 key path from a presigned URL.
 * This is used to identify if the underlying video file has changed,
 * even when presigned URLs are regenerated with new signatures/expires.
 *
 * @param url - Presigned URL (e.g., "https://bucket.s3.amazonaws.com/path/to/video.mp4?AWSAccessKeyId=...")
 * @returns S3 key path (e.g., "path/to/video.mp4") or the original URL if parsing fails
 */
export function extractS3KeyFromUrl(url: string | undefined | null): string | null {
  if (!url) return null
  
  try {
    const urlObj = new URL(url)
    // Remove leading slash from pathname
    const path = urlObj.pathname.startsWith('/') ? urlObj.pathname.slice(1) : urlObj.pathname
    return path || null
  } catch {
    // If URL parsing fails, return null (will cause video to reload, which is safe)
    return null
  }
}

/**
 * Get a stable identifier for a video URL based on its S3 key path.
 * This allows us to detect when the actual video file changes vs when
 * just the presigned URL is regenerated.
 *
 * @param url - Video URL
 * @returns Stable identifier based on S3 key path
 */
export function getVideoStableId(url: string | undefined | null): string | null {
  return extractS3KeyFromUrl(url)
}

/**
 * Get the preferred video URL for a scene based on availability and preferences.
 *
 * Priority (when preferOriginal is false):
 * 1. workingVideoClipUrl (trimmed version)
 * 2. lipSyncedVideoClipUrl (lip-synced version)
 * 3. originalVideoClipUrl (original unmodified clip)
 * 4. videoClipUrl (deprecated fallback)
 *
 * Priority (when preferOriginal is true):
 * 1. originalVideoClipUrl (primary original field)
 * 2. videoClipUrl (deprecated fallback)
 *
 * @param scene - The project scene
 * @param preferOriginal - Whether to prefer the original video over processed versions
 * @returns The video URL or undefined if no video is available
 */
export function getSceneVideoUrl(
  scene: ProjectScene,
  preferOriginal: boolean = false
): string | undefined {
  if (preferOriginal) {
    return scene.originalVideoClipUrl ?? scene.videoClipUrl ?? undefined
  }

  return (
    scene.workingVideoClipUrl ??
    scene.lipSyncedVideoClipUrl ??
    scene.originalVideoClipUrl ??
    scene.videoClipUrl ??
    undefined
  )
}

/**
 * Check if a scene has a video available
 *
 * @param scene - The project scene
 * @returns true if the scene has at least one video URL
 */
export function hasSceneVideo(scene: ProjectScene): boolean {
  return !!(
    scene.originalVideoClipUrl ||
    scene.workingVideoClipUrl ||
    scene.lipSyncedVideoClipUrl ||
    scene.videoClipUrl
  )
}

/**
 * Get all available video URLs for a scene
 *
 * @param scene - The project scene
 * @returns Object with all available video URLs
 */
export function getAllSceneVideoUrls(scene: ProjectScene): {
  working?: string
  lipSynced?: string
  original?: string
  deprecated?: string
} {
  return {
    working: scene.workingVideoClipUrl ?? undefined,
    lipSynced: scene.lipSyncedVideoClipUrl ?? undefined,
    original: scene.originalVideoClipUrl ?? undefined,
    deprecated: scene.videoClipUrl ?? undefined,
  }
}
