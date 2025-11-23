import { ProjectScene } from '@/types/project'

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
