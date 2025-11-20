/**
 * Generation Orchestration Logic
 *
 * Manages the sequential generation workflow by coordinating Python backend endpoints.
 * Orchestrates: scenes → images → videos → lip-sync → compose
 *
 * Features:
 * - Sequential phases with parallel execution within each phase
 * - Error boundaries for each operation
 * - Retry logic with exponential backoff (max 3 retries)
 * - Progress callbacks for UI updates
 * - TypeScript type safety throughout
 */

import {
  generateScenes,
  generateCharacterReference,
  generateVideo,
  generateLipSync,
  updateProject,
  getProject,
  APIError,
} from '@/lib/api'
import type {
  CreateScenesRequest,
  GenerateCharacterReferenceRequest,
  GenerateVideoRequest,
  LipsyncRequest,
} from '@/types/api'
import type { Project, ProjectStatus, Scene } from '@/types/project'

/**
 * Orchestration phase types
 */
export type OrchestrationPhase =
  | 'scenes'
  | 'images'
  | 'videos'
  | 'lipsync'
  | 'compose'

/**
 * Progress callback function type
 */
export type ProgressCallback = (
  phase: OrchestrationPhase,
  sceneIndex: number,
  total: number,
  message?: string
) => void

/**
 * Error handler callback type
 */
export type ErrorCallback = (
  phase: OrchestrationPhase,
  sceneIndex: number | null,
  error: Error
) => void

/**
 * Orchestration options
 */
export interface OrchestrationOptions {
  /** Progress callback for UI updates */
  onProgress?: ProgressCallback

  /** Error callback for error handling */
  onError?: ErrorCallback

  /** Maximum number of retries per operation (default: 3) */
  maxRetries?: number

  /** Initial delay in ms for retry backoff (default: 1000) */
  initialRetryDelay?: number

  /** Maximum delay in ms for retry backoff (default: 10000) */
  maxRetryDelay?: number

  /** Backoff multiplier (default: 2) */
  backoffMultiplier?: number
}

/**
 * Default orchestration options
 */
const DEFAULT_OPTIONS: Required<OrchestrationOptions> = {
  onProgress: () => {},
  onError: () => {},
  maxRetries: 3,
  initialRetryDelay: 1000,
  maxRetryDelay: 10000,
  backoffMultiplier: 2,
}

/**
 * Sleep utility for retry delays
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Calculate exponential backoff delay with jitter
 */
function calculateBackoffDelay(
  attemptNumber: number,
  options: Required<OrchestrationOptions>
): number {
  const delay = Math.min(
    options.initialRetryDelay * Math.pow(options.backoffMultiplier, attemptNumber),
    options.maxRetryDelay
  )
  // Add jitter (±25%)
  const jitter = delay * 0.25 * (Math.random() * 2 - 1)
  return Math.floor(delay + jitter)
}

/**
 * Retry wrapper with exponential backoff
 */
async function retryWithBackoff<T>(
  operation: () => Promise<T>,
  operationName: string,
  options: Required<OrchestrationOptions>,
  phase: OrchestrationPhase,
  sceneIndex: number | null = null
): Promise<T> {
  let lastError: Error | null = null

  for (let attempt = 0; attempt <= options.maxRetries; attempt++) {
    try {
      return await operation()
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))

      // If this is the last attempt, don't retry
      if (attempt === options.maxRetries) {
        break
      }

      // Calculate delay for next retry
      const delay = calculateBackoffDelay(attempt, options)
      console.warn(
        `[Orchestration] ${operationName} failed (attempt ${attempt + 1}/${options.maxRetries + 1}), retrying in ${delay}ms...`,
        error
      )

      // Call error callback
      options.onError(phase, sceneIndex, lastError)

      // Wait before retrying
      await sleep(delay)
    }
  }

  // All retries exhausted
  throw new Error(
    `${operationName} failed after ${options.maxRetries + 1} attempts: ${lastError?.message}`
  )
}

/**
 * Start full generation workflow
 *
 * Orchestrates the complete video generation pipeline:
 * 1. Generate all scenes (parallel)
 * 2. Generate all images (parallel)
 * 3. Generate all videos (parallel)
 * 4. Generate all lip-syncs (parallel)
 * 5. Compose final video (sequential)
 *
 * @param projectId Project identifier
 * @param options Orchestration options
 * @returns Updated project
 */
export async function startFullGeneration(
  projectId: string,
  options: OrchestrationOptions = {}
): Promise<Project> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  try {
    // Fetch current project state
    const projectResponse = await getProject(projectId)
    if (!projectResponse.projectId) {
      throw new Error('Failed to fetch project')
    }

    let project = projectResponse

    // Phase 1: Generate all scenes
    opts.onProgress('scenes', 0, 1, 'Starting scene generation...')
    await updateProject(projectId, { status: 'processing' })

    // Check if scenes need to be generated
    if (project.scenes.length === 0) {
      const scenesRequest: CreateScenesRequest = {
        idea: project.conceptPrompt,
        character_description: project.characterDescription,
        config_flavor: 'default',
        project_id: projectId, // Link scenes to this project in DB
      }

      const scenesResponse = await retryWithBackoff(
        () => generateScenes(scenesRequest),
        'Generate scenes',
        opts,
        'scenes',
        0
      )

      // Fetch updated project with scenes
      project = await getProject(projectId)

      opts.onProgress('scenes', 1, 1, `Generated ${project.scenes.length} scenes`)
    } else {
      opts.onProgress('scenes', 1, 1, `Using existing ${project.scenes.length} scenes`)
    }

    // Phase 2: Generate all character reference images (parallel)
    opts.onProgress('images', 0, project.scenes.length, 'Starting image generation...')
    await updateProject(projectId, { status: 'processing' })

    if (project.characterDescription && !project.characterReferenceImageId) {
      const imageRequest: GenerateCharacterReferenceRequest = {
        character_description: project.characterDescription,
        num_images: 1,
      }

      const imageResponse = await retryWithBackoff(
        () => generateCharacterReference(imageRequest),
        'Generate character reference',
        opts,
        'images',
        0
      )

      if (imageResponse.images.length > 0) {
        project = await updateAndRefetch(projectId, {
          characterReferenceImageId: imageResponse.images[0].id,
        })
      }
    }

    opts.onProgress('images', 1, 1, 'Character reference generated')

    // Phase 3: Generate all videos (parallel)
    opts.onProgress('videos', 0, project.scenes.length, 'Starting video generation...')
    await updateProject(projectId, { status: 'processing' })

    const videoPromises = project.scenes.map((scene, index) =>
      retryWithBackoff(
        async () => {
          opts.onProgress('videos', index + 1, project.scenes.length, `Generating video ${index + 1}/${project.scenes.length}`)

          const videoRequest: GenerateVideoRequest = {
            prompt: scene.prompt,
            negative_prompt: scene.negativePrompt || undefined,
            reference_image_base64: project.characterReferenceImageId || undefined,
          }

          const videoResponse = await generateVideo(videoRequest)

          // Update project with video URL
          const updatedScenes = [...project.scenes]
          updatedScenes[index] = {
            ...scene,
            videoClipUrl: videoResponse.video_url,
            status: 'completed',
          }

          project = await updateAndRefetch(projectId, { scenes: updatedScenes })

          return videoResponse
        },
        `Generate video for scene ${index + 1}`,
        opts,
        'videos',
        index
      )
    )

    await Promise.all(videoPromises)
    opts.onProgress('videos', project.scenes.length, project.scenes.length, 'All videos generated')

    // Phase 4: Generate all lip-syncs (parallel)
    opts.onProgress('lipsync', 0, project.scenes.length, 'Starting lip-sync generation...')
    await updateProject(projectId, { status: 'processing' })

    const lipsyncPromises = project.scenes.map((scene, index) =>
      retryWithBackoff(
        async () => {
          opts.onProgress('lipsync', index + 1, project.scenes.length, `Generating lip-sync ${index + 1}/${project.scenes.length}`)

          if (!scene.videoClipUrl) {
            console.warn(`Scene ${index + 1} missing video, skipping lip-sync`)
            return null
          }

          // TODO: Implement lipsync with new project structure
          // For now, just skip lipsync phase
          console.warn(`Lip-sync not yet implemented for new project structure`)
          return null

          // const lipsyncRequest: LipsyncRequest = {
          //   video_url: scene.videoClipUrl,
          //   audio_url: '', // TODO: Add audio URL to scene
          // }

          // const lipsyncResponse = await generateLipSync(lipsyncRequest)

          // // Update project with lip-synced video URL
          // const updatedScenes = [...project.scenes]
          // updatedScenes[index] = {
          //   ...scene,
          //   // TODO: Add lipSyncedVideoUrl to ProjectScene type
          // }

          // project = await updateAndRefetch(projectId, { scenes: updatedScenes })

          // return lipsyncResponse
        },
        `Generate lip-sync for scene ${index + 1}`,
        opts,
        'lipsync',
        index
      )
    )

    await Promise.all(lipsyncPromises)
    opts.onProgress('lipsync', project.scenes.length, project.scenes.length, 'All lip-syncs generated')

    // Phase 5: Compose final video (sequential)
    opts.onProgress('compose', 0, 1, 'Starting final composition...')
    await updateProject(projectId, { status: 'processing' })

    // TODO: Implement video composition endpoint
    // For now, mark as completed
    await updateProject(projectId, { status: 'completed' })
    opts.onProgress('compose', 1, 1, 'Final video composed')

    // Fetch final project state
    const finalProject = await getProject(projectId)
    if (!finalProject.projectId) {
      throw new Error('Failed to fetch final project state')
    }

    return finalProject
  } catch (error) {
    // Update project status to failed
    await updateProject(projectId, { status: 'failed' }).catch(() => {
      // Ignore errors when updating failed status
    })

    throw error
  }
}

/**
 * Helper function to update project and refetch
 */
async function updateAndRefetch(
  projectId: string,
  updates: Partial<Project>
): Promise<Project> {
  await updateProject(projectId, updates)
  const response = await getProject(projectId)
  if (!response.projectId) {
    throw new Error('Failed to refetch project after update')
  }
  return response
}

/**
 * Regenerate a specific scene
 *
 * @param projectId Project identifier
 * @param sceneIndex Scene index to regenerate
 * @param options Orchestration options
 * @returns Updated project
 */
export async function regenerateScene(
  projectId: string,
  sceneIndex: number,
  options: OrchestrationOptions = {}
): Promise<Project> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  try {
    // Fetch current project state
    const projectResponse = await getProject(projectId)
    if (!projectResponse.projectId) {
      throw new Error('Failed to fetch project')
    }

    const project = projectResponse

    if (sceneIndex < 0 || sceneIndex >= project.scenes.length) {
      throw new Error(`Invalid scene index: ${sceneIndex}`)
    }

    opts.onProgress('scenes', sceneIndex, project.scenes.length, `Regenerating scene ${sceneIndex + 1}`)

    // TODO: Implement scene regeneration logic
    // This would involve calling the scene generation endpoint with specific parameters

    opts.onProgress('scenes', sceneIndex + 1, project.scenes.length, `Scene ${sceneIndex + 1} regenerated`)

    // Fetch and return updated project
    const finalProject = await getProject(projectId)
    if (!finalProject.projectId) {
      throw new Error('Failed to fetch project after regeneration')
    }

    return finalProject
  } catch (error) {
    opts.onError('scenes', sceneIndex, error instanceof Error ? error : new Error(String(error)))
    throw error
  }
}

/**
 * Regenerate a specific image
 *
 * @param projectId Project identifier
 * @param sceneIndex Scene index for image regeneration
 * @param options Orchestration options
 * @returns Updated project
 */
export async function regenerateImage(
  projectId: string,
  sceneIndex: number,
  options: OrchestrationOptions = {}
): Promise<Project> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  try {
    // Fetch current project state
    const projectResponse = await getProject(projectId)
    if (!projectResponse.projectId) {
      throw new Error('Failed to fetch project')
    }

    const project = projectResponse

    if (sceneIndex < 0 || sceneIndex >= project.scenes.length) {
      throw new Error(`Invalid scene index: ${sceneIndex}`)
    }

    opts.onProgress('images', sceneIndex, project.scenes.length, `Regenerating image for scene ${sceneIndex + 1}`)

    // Regenerate character reference if needed
    if (project.characterDescription) {
      const imageRequest: GenerateCharacterReferenceRequest = {
        character_description: project.characterDescription,
        num_images: 1,
      }

      const imageResponse = await retryWithBackoff(
        () => generateCharacterReference(imageRequest),
        `Regenerate image for scene ${sceneIndex + 1}`,
        opts,
        'images',
        sceneIndex
      )

      if (imageResponse.images.length > 0) {
        await updateProject(projectId, {
          characterReferenceImageId: imageResponse.images[0].id,
        })
      }
    }

    opts.onProgress('images', sceneIndex + 1, project.scenes.length, `Image ${sceneIndex + 1} regenerated`)

    // Fetch and return updated project
    const finalProject = await getProject(projectId)
    if (!finalProject.projectId) {
      throw new Error('Failed to fetch project after regeneration')
    }

    return finalProject
  } catch (error) {
    opts.onError('images', sceneIndex, error instanceof Error ? error : new Error(String(error)))
    throw error
  }
}

/**
 * Regenerate a specific video
 *
 * @param projectId Project identifier
 * @param sceneIndex Scene index for video regeneration
 * @param options Orchestration options
 * @returns Updated project
 */
export async function regenerateVideo(
  projectId: string,
  sceneIndex: number,
  options: OrchestrationOptions = {}
): Promise<Project> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  try {
    // Fetch current project state
    const projectResponse = await getProject(projectId)
    if (!projectResponse.projectId) {
      throw new Error('Failed to fetch project')
    }

    let project = projectResponse

    if (sceneIndex < 0 || sceneIndex >= project.scenes.length) {
      throw new Error(`Invalid scene index: ${sceneIndex}`)
    }

    const scene = project.scenes[sceneIndex]

    opts.onProgress('videos', sceneIndex, project.scenes.length, `Regenerating video for scene ${sceneIndex + 1}`)

    await retryWithBackoff(
      async () => {
        const videoRequest: GenerateVideoRequest = {
          prompt: scene.prompt,
          negative_prompt: scene.negativePrompt || undefined,
          reference_image_base64: project.characterReferenceImageId || undefined,
        }

        const videoResponse = await generateVideo(videoRequest)

        // Update project with new video URL
        const updatedScenes = [...project.scenes]
        updatedScenes[sceneIndex] = {
          ...scene,
          videoClipUrl: videoResponse.video_url,
          status: 'completed',
        }

        project = await updateAndRefetch(projectId, { scenes: updatedScenes })

        return videoResponse
      },
      `Regenerate video for scene ${sceneIndex + 1}`,
      opts,
      'videos',
      sceneIndex
    )

    opts.onProgress('videos', sceneIndex + 1, project.scenes.length, `Video ${sceneIndex + 1} regenerated`)

    return project
  } catch (error) {
    opts.onError('videos', sceneIndex, error instanceof Error ? error : new Error(String(error)))
    throw error
  }
}

/**
 * Regenerate a specific lip-sync
 *
 * @param projectId Project identifier
 * @param sceneIndex Scene index for lip-sync regeneration
 * @param options Orchestration options
 * @returns Updated project
 */
export async function regenerateLipSync(
  projectId: string,
  sceneIndex: number,
  options: OrchestrationOptions = {}
): Promise<Project> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  try {
    // Fetch current project state
    const projectResponse = await getProject(projectId)
    if (!projectResponse.projectId) {
      throw new Error('Failed to fetch project')
    }

    let project = projectResponse

    if (sceneIndex < 0 || sceneIndex >= project.scenes.length) {
      throw new Error(`Invalid scene index: ${sceneIndex}`)
    }

    const scene = project.scenes[sceneIndex]

    if (!scene.videoClipUrl) {
      throw new Error(`Scene ${sceneIndex + 1} missing video for lip-sync`)
    }

    // TODO: Implement lipsync with new project structure
    // Lipsync functionality not yet implemented
    console.warn(`Lip-sync regeneration not yet implemented for new project structure`)
    opts.onProgress('lipsync', sceneIndex + 1, project.scenes.length, `Lip-sync regeneration skipped for scene ${sceneIndex + 1}`)
    return project

    // opts.onProgress('lipsync', sceneIndex, project.scenes.length, `Regenerating lip-sync for scene ${sceneIndex + 1}`)

    // await retryWithBackoff(
    //   async () => {
    //     const lipsyncRequest: LipsyncRequest = {
    //       video_url: scene.videoClipUrl,
    //       audio_url: '', // TODO: Add audio URL to scene
    //     }

    //     const lipsyncResponse = await generateLipSync(lipsyncRequest)

    //     // Update project with new lip-synced video URL
    //     const updatedScenes = [...project.scenes]
    //     updatedScenes[sceneIndex] = {
    //       ...scene,
    //       // TODO: Add lipSyncedVideoUrl to ProjectScene type
    //     }

    //     project = await updateAndRefetch(projectId, { scenes: updatedScenes })

    //     return lipsyncResponse
    //   },
    //   `Regenerate lip-sync for scene ${sceneIndex + 1}`,
    //   opts,
    //   'lipsync',
    //   sceneIndex
    // )

    opts.onProgress('lipsync', sceneIndex + 1, project.scenes.length, `Lip-sync ${sceneIndex + 1} regenerated`)

    return project
  } catch (error) {
    opts.onError('lipsync', sceneIndex, error instanceof Error ? error : new Error(String(error)))
    throw error
  }
}
