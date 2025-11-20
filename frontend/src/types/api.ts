/**
 * API type definitions for Python backend endpoints
 */

/**
 * Scene generation request/response types
 */
export interface CreateScenesRequest {
  idea: string
  character_description: string
  character_characteristics?: string
  number_of_scenes?: number
  video_type?: string
  video_characteristics?: string
  camera_angle?: string
  config_flavor?: string
  project_id?: string
}

export interface SceneDescription {
  description: string
  negative_description: string
}

export interface CreateScenesResponse {
  scenes: SceneDescription[]
  output_files: {
    json?: string
    markdown?: string
  }
  metadata: {
    idea: string
    number_of_scenes: number
    parameters_used: {
      character_characteristics: string
      video_type: string
      video_characteristics: string
      camera_angle: string
    }
  }
}

/**
 * Character reference generation request/response types
 */
export interface GenerateCharacterReferenceRequest {
  character_description: string
  num_images?: number
  aspect_ratio?: string
  safety_filter_level?: string
  person_generation?: string
  output_format?: string
  negative_prompt?: string
  seed?: number
}

export interface CharacterReferenceImage {
  id: string
  path: string
  cloud_url: string | null
}

export interface GenerateCharacterReferenceResponse {
  images: CharacterReferenceImage[]
  metadata: {
    character_description: string
    model_used: string
    num_images_requested: number
    num_images_generated: number
    parameters_used: Record<string, any>
    generation_timestamp: string
  }
}

/**
 * Video generation request/response types
 */
export interface GenerateVideoRequest {
  prompt: string
  negative_prompt?: string
  aspect_ratio?: string
  duration?: number
  generate_audio?: boolean
  seed?: number
  reference_image_base64?: string
  video_rules_template?: string
  backend?: 'replicate' | 'gemini'
}

export interface GenerateVideoResponse {
  video_id: string
  video_path: string
  video_url: string
  metadata: {
    prompt: string
    backend_used: string
    model_used: string
    parameters_used: Record<string, any>
    generation_timestamp: string
    processing_time_seconds: number
  }
}

/**
 * Video info response type
 */
export interface VideoInfoResponse {
  video_id: string
  exists: boolean
  file_size_bytes: number | null
  created_at: string | null
  is_mock?: boolean
}

/**
 * Lipsync generation request/response types
 */
export interface LipsyncRequest {
  video_url: string
  audio_url: string
  temperature?: number
  occlusion_detection_enabled?: boolean
  active_speaker_detection?: boolean
}

export interface LipsyncResponse {
  video_id: string
  video_path: string
  video_url: string
  metadata: {
    video_url: string
    audio_url: string
    model_used: string
    parameters_used: {
      temperature?: number
      occlusion_detection_enabled?: boolean
      active_speaker_detection?: boolean
    }
    generation_timestamp: string
    processing_time_seconds: number
    file_size_bytes: number
  }
}

/**
 * Error response types
 */
export interface APIErrorDetail {
  error: string
  message: string
  details?: string
  error_code?: string
  backend_used?: string
  timestamp?: string
}
