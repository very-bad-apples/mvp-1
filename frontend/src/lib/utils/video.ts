import { ProjectScene } from '@/types/project'

/**
 * Get the preferred video URL for a scene based on availability and preferences.
 *
 * Priority (when preferOriginal is false):
 * 1. workingVideoClipUrl (trimmed version)
 * 2. lipSyncedVideoClipUrl (lip-synced version)
 * 3. videoClipUrl (original)
 *
 * Priority (when preferOriginal is true):
 * 1. videoClipUrl (original)
 * 2. originalVideoClipUrl (backup original)
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
    return scene.videoClipUrl ?? scene.originalVideoClipUrl ?? undefined
  }

  return (
    scene.workingVideoClipUrl ??
    scene.lipSyncedVideoClipUrl ??
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
    scene.workingVideoClipUrl ||
    scene.lipSyncedVideoClipUrl ||
    scene.videoClipUrl ||
    scene.originalVideoClipUrl
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
  originalBackup?: string
} {
  return {
    working: scene.workingVideoClipUrl ?? undefined,
    lipSynced: scene.lipSyncedVideoClipUrl ?? undefined,
    original: scene.videoClipUrl ?? undefined,
    originalBackup: scene.originalVideoClipUrl ?? undefined,
  }
}
