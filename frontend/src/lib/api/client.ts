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
    if (!error.statusCode) return false
    return config.retryableStatusCodes.includes(error.statusCode)
  }
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true // Network errors are retryable
  }
  return false
}

/**
 * Get API key from environment
 */
function getAPIKey(): string | undefined {
  return process.env.NEXT_PUBLIC_API_KEY
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
      // Build headers with API key for backend requests
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
      }

      // Add API key header if available and URL is for backend (not Next.js routes)
      const apiKey = getAPIKey()
      if (apiKey && (url.startsWith('http') || url.startsWith('/api/mv'))) {
        headers['X-API-Key'] = apiKey
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
        } else if (response.status === 503 || response.status === 504) {
          throw new TimeoutError(message, details)
        } else if (response.status >= 500) {
          throw new ConfigurationError(message, details)
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
        console.warn(
          `[API] Request failed (attempt ${attempt + 1}/${config.maxRetries + 1}), retrying in ${delay}ms...`,
          error
        )
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
 * Get API URL from environment
 */
function getAPIUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) {
    throw new ConfigurationError(
      'API URL not configured',
      'NEXT_PUBLIC_API_URL environment variable is not set'
    )
  }
  return apiUrl
}

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
  const url = `${getAPIUrl()}/api/mv/projects`

  // Build FormData for multipart/form-data request
  const formData = new FormData()
  formData.append('mode', data.mode)
  formData.append('prompt', data.prompt)
  formData.append('characterDescription', data.characterDescription)

  if (data.characterReferenceImageId) {
    formData.append('characterReferenceImageId', data.characterReferenceImageId)
  }

  if (data.productDescription) {
    formData.append('productDescription', data.productDescription)
  }

  if (data.directorConfig) {
    formData.append('directorConfig', data.directorConfig)
  }

  if (data.configFlavor) {
    formData.append('configFlavor', data.configFlavor)
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

  // Get API key
  const apiKey = getAPIKey()
  const headers: Record<string, string> = {}
  if (apiKey && (url.startsWith('http') || url.startsWith('/api/mv'))) {
    headers['X-API-Key'] = apiKey
  }

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
  const url = `${getAPIUrl()}/api/mv/projects/${projectId}`
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
  const url = `${getAPIUrl()}/api/mv/projects/${projectId}`
  return apiFetch<UpdateProjectResponse>(url, {
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
  const url = `${getAPIUrl()}/api/mv/create_scenes`
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
  const url = `${getAPIUrl()}/api/mv/generate_character_reference`
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
 * Generate a video clip
 * @param data Video generation request
 * @returns Generated video response
 */
export async function generateVideo(
  data: GenerateVideoRequest
): Promise<GenerateVideoResponse> {
  const url = `${getAPIUrl()}/api/mv/generate_video`
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
  const url = `${getAPIUrl()}/api/mv/lipsync`
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
  const url = `${getAPIUrl()}/api/mv/get_character_reference/${imageId}`
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
  const url = `${getAPIUrl()}/api/mv/get_video/${videoId}`
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
  const url = `${getAPIUrl()}/api/mv/get_video/${videoId}/info`
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
  return `${getAPIUrl()}/api/mv/get_character_reference/${imageId}`
}

/**
 * Build full URL for video
 * @param videoId Video identifier
 * @returns Full URL to video
 */
export function getVideoUrl(videoId: string): string {
  return `${getAPIUrl()}/api/mv/get_video/${videoId}`
}

/**
 * Get available configuration flavors
 * @returns Available config flavors
 */
export async function getConfigFlavors(): Promise<{ flavors: string[] }> {
  const url = `${getAPIUrl()}/api/mv/get_config_flavors`
  return apiFetch<{ flavors: string[] }>(url, {
    method: 'GET',
  })
}

/**
 * Get available director configs
 * @returns List of available director config names
 */
export async function getDirectorConfigs(): Promise<{ configs: string[] }> {
  const url = `${getAPIUrl()}/api/mv/get_director_configs`
  return apiFetch<{ configs: string[] }>(url, {
    method: 'GET',
  })
}

/**
 * Health check utility
 * @returns True if API is reachable
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const url = `${getAPIUrl()}/health`
    const response = await fetch(url, { method: 'GET' })
    return response.ok
  } catch {
    return false
  }
}
