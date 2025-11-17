/**
 * Project and Scene type definitions for the music video generation system.
 */

/**
 * Project status during the overall workflow
 */
export type ProjectStatus =
  | 'creating-scenes'
  | 'generating-images'
  | 'generating-videos'
  | 'generating-lipsync'
  | 'composing'
  | 'completed'
  | 'error'

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
 */
export interface ProjectScene {
  /** Scene ID */
  id?: number

  /** Scene sequence number */
  sequence: number

  /** Scene prompt */
  prompt: string

  /** Negative prompt */
  negativePrompt: string

  /** Scene status */
  status?: 'pending' | 'generating' | 'completed' | 'failed'

  /** Generated video ID */
  videoId?: string | null

  /** Generated video URL */
  videoUrl?: string | null

  /** Retry count for failed generations */
  retryCount?: number
}

/**
 * Music video project containing multiple scenes
 */
export interface Project {
  /** Unique project identifier */
  projectId: string

  /** Project mode: ad-creative or music-video */
  mode: 'ad-creative' | 'music-video'

  /** User's original concept/idea prompt */
  idea: string

  /** Character description used for scene generation */
  characterDescription: string

  /** Character reference image ID (optional) */
  characterRefImage: string | null

  /** Array of scenes in this project */
  scenes: ProjectScene[]

  /** Creation timestamp */
  createdAt: string

  /** Last update timestamp */
  updatedAt: string

  /** Current project status */
  status: ProjectStatus

  /** Overall progress percentage (0-100) */
  progress: number

  /** Number of completed scenes */
  completedScenes: number

  /** Number of failed scenes */
  failedScenes: number

  /** Final composed video URL (available when status is 'completed') */
  finalVideoUrl?: string | null

  /** Final video metadata */
  finalVideoMetadata?: {
    duration: number
    fileSize: number
    resolution: string
    format: string
  }
}

/**
 * API Request/Response Types
 */

/**
 * Request to create a new project
 */
export interface CreateProjectRequest {
  /** Unique project identifier */
  projectId: string

  /** Project mode */
  mode: 'ad-creative' | 'music-video'

  /** User's concept/idea */
  idea: string

  /** Character description */
  characterDescription?: string

  /** Character reference image ID */
  characterRefImage?: string | null

  /** Initial scenes */
  scenes: Array<{
    id?: number
    sequence: number
    prompt: string
    negativePrompt: string
  }>
}

/**
 * Response from creating a project
 */
export interface CreateProjectResponse {
  success: boolean
  projectId: string
  project: Project
  error?: string
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
  characterRefImage?: string | null
}

/**
 * Response from updating a project
 */
export interface UpdateProjectResponse {
  success: boolean
  project: Project
  error?: string
}

/**
 * Response from getting a project
 */
export interface GetProjectResponse {
  success: boolean
  project: Project | null
  error?: string
}

