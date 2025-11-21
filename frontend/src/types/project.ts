/**
 * Project and Scene type definitions for the music video generation system.
 */

/**
 * Project status during the overall workflow
 * Note: These values match the backend status enum
 */
export type ProjectStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'

/**
 * Media clip with URL and duration
 */
export interface MediaClip {
  /** URL to the media file */
  url: string

  /** Duration of the media clip in seconds */
  duration: number
}

/**
 * Individual scene in a music video project
 */
export interface Scene {
  /** Scene sequence number within the project */
  sequence: number

  /** AI-generated scene description for video prompt */
  prompt: string

  /** Negative prompt - elements to exclude from this scene */
  negativePrompt: string

  /** Array of reference image URLs for this scene */
  referenceImages: string[]

  /** Audio clip for this scene */
  audioClip: MediaClip

  /** Generated video clip for this scene */
  videoClip: MediaClip

  /** Lip-synced video clip for this scene */
  lipSyncedVideoClip: MediaClip
}

/**
 * Scene within a project
 * Note: Field names match backend SceneResponse for consistency
 */
export interface ProjectScene {
  /** Scene sequence number */
  sequence: number

  /** Scene prompt */
  prompt: string

  /** Negative prompt */
  negativePrompt: string | null

  /** Scene duration in seconds */
  duration?: number

  /** Scene status */
  status: string

  /** Reference image URLs (presigned S3 URLs) */
  referenceImageUrls?: string[]

  /** Audio clip URL (presigned S3 URL) */
  audioClipUrl?: string | null

  /** Generated video clip URL (presigned S3 URL) */
  videoClipUrl?: string | null

  /** Whether this scene needs lip sync */
  needsLipSync?: boolean

  /** Lip-synced video clip URL (presigned S3 URL) */
  lipSyncedVideoClipUrl?: string | null

  /** Retry count for failed generations */
  retryCount: number

  /** Error message if failed */
  errorMessage?: string | null

  /** Creation timestamp */
  createdAt?: string

  /** Last update timestamp */
  updatedAt?: string
}

/**
 * Music video project containing multiple scenes
 * Note: Field names match backend ProjectResponse for consistency
 */
export interface Project {
  /** Unique project identifier */
  projectId: string

  /** Project mode: ad-creative or music-video (frontend-only field) */
  mode?: 'ad-creative' | 'music-video'

  /** User's original concept/idea prompt (backend: conceptPrompt) */
  conceptPrompt: string

  /** Character description used for scene generation */
  characterDescription: string

  /** Character reference image ID - used when creating/updating project */
  characterReferenceImageId?: string | null

  /** Character reference image URL - presigned S3 URL from backend */
  characterImageUrl: string | null

  /** Product description (for ad-creative mode) */
  productDescription?: string | null

  /** Product image URL - presigned S3 URL from backend */
  productImageUrl?: string | null

  /** Audio backing track URL - presigned S3 URL from backend */
  audioBackingTrackUrl?: string | null

  /** Array of scenes in this project */
  scenes: ProjectScene[]

  /** Total number of scenes */
  sceneCount: number

  /** Creation timestamp */
  createdAt: string

  /** Last update timestamp */
  updatedAt: string

  /** Current project status */
  status: ProjectStatus

  /** Overall progress percentage (0-100) - calculated frontend field */
  progress?: number

  /** Number of completed scenes */
  completedScenes: number

  /** Number of failed scenes */
  failedScenes: number

  /** Final composed video URL (backend: finalOutputUrl) */
  finalOutputUrl?: string | null
}

/**
 * API Request/Response Types
 */

/**
 * Request to create a new project
 * Note: This matches the backend's multipart/form-data structure
 */
export interface CreateProjectRequest {
  /** Project mode */
  mode: 'ad-creative' | 'music-video'

  /** User's concept/idea */
  prompt: string

  /** Character description */
  characterDescription: string

  /** Character reference image ID */
  characterReferenceImageId?: string | null

  /** Product description (for ad-creative mode) */
  productDescription?: string | null

  /** Director config name (e.g., "Wes-Anderson") */
  directorConfig?: string | null

  /** Product images (for ad-creative mode) */
  images?: File[]

  /** Audio file (for music-video mode) */
  audio?: File
}

/**
 * Response from creating a project
 * Note: Backend returns minimal response, not full project object
 */
export interface CreateProjectResponse {
  projectId: string
  status: string
  message: string
}

/**
 * Request to update a project
 */
export interface UpdateProjectRequest {
  status?: ProjectStatus
  progress?: number
  scenes?: ProjectScene[]
  completedScenes?: number
  failedScenes?: number
  characterReferenceImageId?: string | null
}

/**
 * Response from updating a project
 * Note: Backend returns full ProjectResponse - same structure as Project interface
 */
export type UpdateProjectResponse = GetProjectResponse

/**
 * Response from getting a project
 * Note: Backend returns ProjectResponse directly - same structure as Project interface
 */
export type GetProjectResponse = Omit<Project, 'mode' | 'progress'>

/**
 * Request to compose final video
 * Note: No additional fields needed - uses project metadata
 */
export interface ComposeRequest {
  // No fields needed
}

/**
 * Response from composing final video
 */
export interface ComposeResponse {
  jobId: string
  projectId: string
  status: string
  message: string
}

