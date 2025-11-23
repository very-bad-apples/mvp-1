/**
 * Type-safe API client for Python backend endpoints
 *
 * This module provides a comprehensive API client with:
 * - Type-safe functions for all backend endpoints
 * - Custom error classes for different error types
 * - Retry logic with exponential backoff
 * - Environment variable configuration
 */

import {
  CreateScenesRequest,
  CreateScenesResponse,
  GenerateCharacterReferenceRequest,
  GenerateCharacterReferenceResponse,
  UploadCharacterReferenceResponse,
  GenerateVideoRequest,
  GenerateVideoResponse,
  VideoInfoResponse,
  LipsyncRequest,
  LipsyncResponse,
  APIErrorDetail,
} from '@/types/api'
import {
  CreateProjectRequest,
  CreateProjectResponse,
  GetProjectResponse,
  UpdateProjectRequest,
  UpdateProjectResponse,
  ComposeRequest,
  ComposeResponse,
} from '@/types/project'

/**
 * Custom error classes
 */
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public errorCode?: string,
    public details?: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

export class ValidationError extends APIError {
  constructor(message: string, details?: string) {
    super(message, 400, 'VALIDATION_ERROR', details)
    this.name = 'ValidationError'
  }
}

export class ConfigurationError extends APIError {
  constructor(message: string, details?: string) {
    super(message, 500, 'CONFIGURATION_ERROR', details)
    this.name = 'ConfigurationError'
  }
}

export class NetworkError extends APIError {
  constructor(message: string, details?: string) {
    super(message, 0, 'NETWORK_ERROR', details)
    this.name = 'NetworkError'
  }
}

export class TimeoutError extends APIError {
  constructor(message: string, details?: string) {
    super(message, 503, 'TIMEOUT_ERROR', details)
    this.name = 'TimeoutError'
  }
}

export class RateLimitError extends APIError {
  constructor(message: string, details?: string) {
    super(message, 429, 'RATE_LIMIT_ERROR', details)
    this.name = 'RateLimitError'
  }
}

export class S3Error extends APIError {
  constructor(message: string, details?: string) {
    super(message, 503, 'S3_ERROR', details)
    this.name = 'S3Error'
  }
}

export class ServiceUnavailableError extends APIError {
  constructor(message: string, details?: string) {
    super(message, 503, 'SERVICE_UNAVAILABLE', details)
    this.name = 'ServiceUnavailableError'
  }
}

/**
 * Retry configuration
 */
interface RetryConfig {
  maxRetries: number
  initialDelayMs: number
  maxDelayMs: number
  backoffMultiplier: number
  retryableStatusCodes: number[]
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
}

/**
 * User-friendly error messages for different error scenarios
 */
const ERROR_MESSAGES: Record<string, { title: string; message: string; recovery: string }> = {
  NETWORK_ERROR: {
    title: 'Connection Failed',
    message: 'Unable to connect to the server. Please check your internet connection.',
    recovery: 'Retrying automatically...',
  },
  TIMEOUT_ERROR: {
    title: 'Request Timed Out',
    message: 'The request took too long to complete. This may be due to high server load.',
    recovery: 'Retrying with exponential backoff...',
  },
  RATE_LIMIT_ERROR: {
    title: 'Too Many Requests',
    message: 'You have exceeded the rate limit. Please wait a moment before trying again.',
    recovery: 'Will retry after cooldown period...',
  },
  S3_ERROR: {
    title: 'Storage Service Error',
    message: 'Unable to access cloud storage. This may be temporary.',
    recovery: 'Retrying storage operation...',
  },
  SERVICE_UNAVAILABLE: {
    title: 'Service Temporarily Unavailable',
    message: 'The video generation service is temporarily unavailable.',
    recovery: 'Retrying connection...',
  },
  CONFIGURATION_ERROR: {
    title: 'Configuration Error',
    message: 'There is a problem with the server configuration.',
    recovery: 'Please contact support if this persists.',
  },
  VALIDATION_ERROR: {
    title: 'Invalid Input',
    message: 'Please check your input and try again.',
    recovery: 'No automatic retry - please correct your input.',
  },
  NOT_FOUND: {
    title: 'Resource Not Found',
    message: 'The requested resource could not be found.',
    recovery: 'No automatic retry - please verify the resource exists.',
  },
  UNKNOWN_ERROR: {
    title: 'Unexpected Error',
    message: 'An unexpected error occurred.',
    recovery: 'Retrying operation...',
  },
}

/**
 * Get user-friendly error message for error code
 */
export function getUserFriendlyError(
  error: APIError
): { title: string; message: string; recovery: string; canRetry: boolean } {
  const errorInfo = ERROR_MESSAGES[error.errorCode || 'UNKNOWN_ERROR'] || ERROR_MESSAGES.UNKNOWN_ERROR

  return {
    ...errorInfo,
    canRetry: error.statusCode ? DEFAULT_RETRY_CONFIG.retryableStatusCodes.includes(error.statusCode) : false,
  }
}

/**
 * Sleep utility for retry delays
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Calculate exponential backoff delay
 */
function calculateBackoffDelay(
  attemptNumber: number,
  config: RetryConfig
): number {
  const delay = Math.min(
    config.initialDelayMs * Math.pow(config.backoffMultiplier, attemptNumber),
    config.maxDelayMs
  )
  // Add jitter (±25%)
  const jitter = delay * 0.25 * (Math.random() * 2 - 1)
  return Math.floor(delay + jitter)
}

/**
 * Check if error is retryable
 */
function isRetryableError(error: unknown, config: RetryConfig): boolean {
  if (error instanceof APIError) {
    // Don't retry client errors (400-499) except 408 (timeout) and 429 (rate limit)
    if (error.statusCode && error.statusCode >= 400 && error.statusCode < 500) {
      return config.retryableStatusCodes.includes(error.statusCode)
    }
    // Retry all server errors (500-599)
    if (error.statusCode && error.statusCode >= 500) {
      return true
    }
    // Retry S3 and service unavailable errors
    if (error instanceof S3Error || error instanceof ServiceUnavailableError) {
      return true
    }
    return false
  }
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true // Network errors are retryable
  }
  return false
}

/**
 * Callback type for retry progress updates
 */
export type RetryProgressCallback = (attempt: number, maxAttempts: number, delayMs: number, error: Error) => void

/**
 * Log retry attempt with structured information
 */
function logRetryAttempt(
  operationName: string,
  attempt: number,
  maxRetries: number,
  delay: number,
  error: Error
): void {
  const errorInfo = error instanceof APIError ? getUserFriendlyError(error) : null

  console.warn(
    `[API Retry] ${operationName} failed (attempt ${attempt + 1}/${maxRetries + 1})`,
    {
      attemptNumber: attempt + 1,
      totalAttempts: maxRetries + 1,
      nextRetryIn: `${delay}ms`,
      errorType: error.constructor.name,
      errorMessage: error.message,
      errorCode: error instanceof APIError ? error.errorCode : 'UNKNOWN',
      retryable: errorInfo?.canRetry ?? true,
      recovery: errorInfo?.recovery ?? 'Retrying...',
    }
  )
}

/**
 * Base fetch wrapper with error handling
 */
async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
  retryConfig: Partial<RetryConfig> = {}
): Promise<T> {
  const config: RetryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig }
  let lastError: Error | null = null

  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      // Build headers - API key is now handled server-side by Next.js proxy routes
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
      }

      const response = await fetch(url, {
        ...options,
        headers,
      })

      // Handle non-OK responses
      if (!response.ok) {
        const contentType = response.headers.get('content-type')
        let errorDetail: APIErrorDetail | null = null
        let textDetails: string | null = null

        // Try to parse error as JSON
        if (contentType?.includes('application/json')) {
          try {
            errorDetail = await response.json()
          } catch {
            // If JSON parsing fails, try to get text
            try {
              textDetails = await response.text()
            } catch {
              // If text parsing also fails, use generic error
            }
          }
        } else {
          // Non-JSON response, try to get text
          try {
            textDetails = await response.text()
          } catch {
            // If text parsing fails, use generic error
          }
        }

        const message =
          errorDetail?.message ||
          errorDetail?.error ||
          `HTTP ${response.status}: ${response.statusText}`
        const details = errorDetail?.details || textDetails || 'No additional details'

        // Create appropriate error type
        if (response.status === 400) {
          throw new ValidationError(message, details)
        } else if (response.status === 404) {
          throw new APIError(message, 404, 'NOT_FOUND', details)
        } else if (response.status === 429) {
          throw new RateLimitError(message, details)
        } else if (response.status === 503) {
          // Check if this is an S3-specific error
          if (message.toLowerCase().includes('s3') || message.toLowerCase().includes('storage')) {
            throw new S3Error(message, details)
          }
          throw new ServiceUnavailableError(message, details)
        } else if (response.status === 504) {
          throw new TimeoutError(message, details)
        } else if (response.status >= 500) {
          // Check if this is a configuration error
          if (
            message.toLowerCase().includes('config') ||
            message.toLowerCase().includes('environment') ||
            message.toLowerCase().includes('api key')
          ) {
            throw new ConfigurationError(message, details)
          }
          throw new APIError(message, response.status, 'INTERNAL_ERROR', details)
        } else {
          throw new APIError(
            message,
            response.status,
            errorDetail?.error_code,
            details
          )
        }
      }

      // Parse successful response
      const contentType = response.headers.get('content-type')
      if (contentType?.includes('application/json')) {
        return (await response.json()) as T
      }

      // For non-JSON responses, return response object
      return response as unknown as T
    } catch (error) {
      lastError = error as Error

      // Check if we should retry
      if (attempt < config.maxRetries && isRetryableError(error, config)) {
        const delay = calculateBackoffDelay(attempt, config)
        logRetryAttempt(url, attempt, config.maxRetries, delay, lastError)
        await sleep(delay)
        continue
      }

      // If not retryable or max retries reached, throw the error
      if (error instanceof APIError) {
        throw error
      }

      // Wrap unknown errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network request failed', error.message)
      }

      throw new APIError(
        error instanceof Error ? error.message : 'Unknown error occurred',
        undefined,
        'UNKNOWN_ERROR',
        error instanceof Error ? error.stack : undefined
      )
    }
  }

  // Should never reach here, but TypeScript needs it
  throw lastError || new APIError('Max retries exceeded')
}

/**
 * API Route Paths (relative URLs to Next.js proxy routes)
 */
const API_ROUTES = {
  // Project routes
  PROJECTS: '/api/mv/projects',
  PROJECT_BY_ID: (id: string) => `/api/mv/projects/${id}`,
  PROJECT_SCENES: (id: string, sequence: number) => `/api/mv/projects/${id}/scenes/${sequence}`,
  PROJECT_COMPOSE: (id: string) => `/api/mv/projects/${id}/compose`,
  PROJECT_GENERATE: (id: string) => `/api/mv/projects/${id}/generate`,

  // Generation routes
  CREATE_SCENES: '/api/mv/create_scenes',
  GENERATE_CHARACTER_REF: '/api/mv/generate_character_reference',
  UPLOAD_CHARACTER_REF: '/api/mv/upload_character_reference',
  GENERATE_VIDEO: '/api/mv/generate_video',
  LIPSYNC: '/api/mv/lipsync',
  STITCH_VIDEOS: '/api/mv/stitch-videos',

  // Retrieval routes
  GET_CHARACTER_REF: (imageId: string) => `/api/mv/get_character_reference/${imageId}`,
  GET_VIDEO: (videoId: string) => `/api/mv/get_video/${videoId}`,
  GET_VIDEO_INFO: (videoId: string) => `/api/mv/get_video/${videoId}/info`,

  // Config routes
  CONFIG_FLAVORS: '/api/mv/get_config_flavors',
  DIRECTOR_CONFIGS: '/api/mv/get_director_configs',

  // Audio routes
  AUDIO_DOWNLOAD: '/api/audio/download',
  AUDIO_GET: (audioId: string) => `/api/audio/get/${audioId}`,
  AUDIO_INFO: (audioId: string) => `/api/audio/info/${audioId}`,
  AUDIO_CONVERT_YOUTUBE: '/api/audio/convert-youtube',

  // Jobs routes
  JOB_BY_ID: (jobId: string) => `/api/jobs/${jobId}`,

  // Health check
  HEALTH: '/api/health',
} as const

/**
 * API Client Functions
 */

/**
 * Project Management Functions
 */

/**
 * Create a new project
 * @param data Project creation data
 * @returns Created project response
 */
export async function createProject(
  data: CreateProjectRequest
): Promise<CreateProjectResponse> {
  const url = API_ROUTES.PROJECTS

  // Build FormData for multipart/form-data request
  const formData = new FormData()
  formData.append('mode', data.mode)
  formData.append('prompt', data.prompt)

  if (data.characterDescription) {
    formData.append('characterDescription', data.characterDescription)
  }

  if (data.characterReferenceImageId) {
    formData.append('characterReferenceImageId', data.characterReferenceImageId)
  }

  if (data.productDescription) {
    formData.append('productDescription', data.productDescription)
  }

  if (data.productReferenceImageId) {
    formData.append('productReferenceImageId', data.productReferenceImageId)
  }

  if (data.directorConfig) {
    formData.append('directorConfig', data.directorConfig)
  }

  // Add product images if provided (for ad-creative mode)
  if (data.images && data.images.length > 0) {
    data.images.forEach((image) => {
      formData.append('images', image)
    })
  }

  // Add audio file if provided (for music-video mode)
  if (data.audio) {
    formData.append('audio', data.audio)
  }

  // API key handled by proxy route
  const headers: Record<string, string> = {}

  // Use fetch directly (not apiFetch) because FormData sets its own Content-Type with boundary
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    const contentType = response.headers.get('content-type')
    let errorDetail = null

    if (contentType?.includes('application/json')) {
      try {
        errorDetail = await response.json()
      } catch {
        // Ignore parse errors
      }
    }

    const message = errorDetail?.message || `HTTP ${response.status}: ${response.statusText}`
    const details = errorDetail?.details || 'No additional details'

    throw new APIError(
      message,
      response.status,
      errorDetail?.error_code,
      details
    )
  }

  return await response.json()
}

/**
 * Get a project by ID
 * @param projectId Project identifier
 * @returns Project data
 */
export async function getProject(
  projectId: string
): Promise<GetProjectResponse> {
  const url = API_ROUTES.PROJECT_BY_ID(projectId)
  return apiFetch<GetProjectResponse>(url, {
    method: 'GET',
  })
}

/**
 * Update a project
 * @param projectId Project identifier
 * @param data Project update data
 * @returns Updated project response
 */
export async function updateProject(
  projectId: string,
  data: UpdateProjectRequest
): Promise<UpdateProjectResponse> {
  const url = API_ROUTES.PROJECT_BY_ID(projectId)
  return apiFetch<UpdateProjectResponse>(url, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/**
 * Update a specific scene
 * @param projectId Project identifier
 * @param sequence Scene sequence number
 * @param data Scene update data
 * @returns Updated scene response
 */
export async function updateScene(
  projectId: string,
  sequence: number,
  data: { prompt?: string; negativePrompt?: string }
): Promise<any> {
  const url = API_ROUTES.PROJECT_SCENES(projectId, sequence)
  return apiFetch<any>(url, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/**
 * Generation Functions
 */

/**
 * Generate scene descriptions
 * @param data Scene generation request
 * @returns Generated scenes
 */
export async function generateScenes(
  data: CreateScenesRequest
): Promise<CreateScenesResponse> {
  const url = API_ROUTES.CREATE_SCENES
  return apiFetch<CreateScenesResponse>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    {
      maxRetries: 2, // Reduce retries for long-running operations
    }
  )
}

/**
 * Generate character reference images
 * @param data Character reference request
 * @returns Generated character reference images
 */
export async function generateCharacterReference(
  data: GenerateCharacterReferenceRequest
): Promise<GenerateCharacterReferenceResponse> {
  const url = API_ROUTES.GENERATE_CHARACTER_REF
  return apiFetch<GenerateCharacterReferenceResponse>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    {
      maxRetries: 2, // Reduce retries for long-running operations
    }
  )
}

/**
 * Upload a character reference image file
 * @param file Image file to upload
 * @returns Upload response with image_id (UUID)
 */
export async function uploadCharacterReference(
  file: File
): Promise<UploadCharacterReferenceResponse> {
  const url = API_ROUTES.UPLOAD_CHARACTER_REF

  // Create FormData for multipart/form-data request
  const formData = new FormData()
  formData.append('file', file)

  // Don't set Content-Type - browser will set it with boundary for FormData
  // API key handled by proxy route
  const headers: Record<string, string> = {}

  // Use fetch directly for file uploads (FormData sets its own Content-Type with boundary)
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Upload failed' }))
    throw new APIError(
      errorData.message || 'Failed to upload character reference image',
      response.status,
      errorData.error,
      errorData.details
    )
  }
  
  return response.json()
}

/**
 * Generate a video clip
 * @param data Video generation request
 * @returns Generated video response
 */
export async function generateVideo(
  data: GenerateVideoRequest
): Promise<GenerateVideoResponse> {
  const url = API_ROUTES.GENERATE_VIDEO
  return apiFetch<GenerateVideoResponse>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    {
      maxRetries: 1, // Minimal retries for very long-running operations
    }
  )
}

/**
 * Generate lip-synced video
 * @param data Lipsync generation request
 * @returns Lip-synced video response
 */
export async function generateLipSync(
  data: LipsyncRequest
): Promise<LipsyncResponse> {
  const url = API_ROUTES.LIPSYNC
  return apiFetch<LipsyncResponse>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    {
      maxRetries: 1, // Minimal retries for very long-running operations
    }
  )
}

/**
 * File Retrieval Functions
 */

/**
 * Get character reference image by ID
 * @param imageId Image identifier
 * @returns Response object (use response.blob() to get image data)
 */
export async function getCharacterReference(imageId: string): Promise<Response> {
  const url = API_ROUTES.GET_CHARACTER_REF(imageId)
  return apiFetch<Response>(url, {
    method: 'GET',
  })
}

/**
 * Get video by ID
 * @param videoId Video identifier
 * @returns Response object (use response.blob() to get video data)
 */
export async function getVideo(videoId: string): Promise<Response> {
  const url = API_ROUTES.GET_VIDEO(videoId)
  return apiFetch<Response>(url, {
    method: 'GET',
  })
}

/**
 * Get video information
 * @param videoId Video identifier
 * @returns Video metadata
 */
export async function getVideoInfo(videoId: string): Promise<VideoInfoResponse> {
  const url = API_ROUTES.GET_VIDEO_INFO(videoId)
  return apiFetch<VideoInfoResponse>(url, {
    method: 'GET',
  })
}

/**
 * Utility Functions
 */

/**
 * Build full URL for character reference image
 * @param imageId Image identifier
 * @returns Full URL to image
 */
export function getCharacterReferenceUrl(imageId: string): string {
  return API_ROUTES.GET_CHARACTER_REF(imageId)
}

/**
 * Build full URL for video
 * @param videoId Video identifier
 * @returns Full URL to video
 */
export function getVideoUrl(videoId: string): string {
  return API_ROUTES.GET_VIDEO(videoId)
}

/**
 * Get available configuration flavors
 * @returns Available config flavors
 */
export async function getConfigFlavors(): Promise<{ flavors: string[] }> {
  const url = API_ROUTES.CONFIG_FLAVORS
  return apiFetch<{ flavors: string[] }>(url, {
    method: 'GET',
  })
}

/**
 * Get available director configs
 * @returns List of available director config names
 */
export async function getDirectorConfigs(): Promise<{ configs: string[] }> {
  const url = API_ROUTES.DIRECTOR_CONFIGS
  return apiFetch<{ configs: string[] }>(url, {
    method: 'GET',
  })
}

/**
 * Compose final video from all scenes
 * @param projectId Project identifier
 * @param data Composition request (empty object)
 * @returns Composition job response
 */
export async function composeVideo(
  projectId: string,
  data: ComposeRequest = {}
): Promise<ComposeResponse> {
  const url = API_ROUTES.PROJECT_COMPOSE(projectId)
  return apiFetch<ComposeResponse>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    {
      maxRetries: 1, // Minimal retries for composition operations
    }
  )
}

/**
 * Health check utility
 * @returns True if API is reachable
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const url = API_ROUTES.HEALTH
    const response = await fetch(url, { method: 'GET' })
    return response.ok
  } catch {
    return false
  }
}
