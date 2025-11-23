/**
 * Asset types and interfaces for the AssetGallery component
 */

/**
 * Asset type enumeration
 */
export type AssetType = 'image' | 'video' | 'lipsync' | 'character'

/**
 * Asset item interface
 */
export interface Asset {
  /** Unique asset identifier */
  id: string

  /** Asset type */
  type: AssetType

  /** URL to the asset */
  url: string

  /** Optional thumbnail URL for videos */
  thumbnailUrl?: string

  /** Asset description/caption */
  description?: string

  /** Scene sequence number (if applicable) */
  sceneSequence?: number

  /** Asset metadata */
  metadata?: AssetMetadata
}

/**
 * Asset metadata interface
 */
export interface AssetMetadata {
  /** File size in bytes */
  fileSize?: number

  /** Duration in seconds (for videos) */
  duration?: number

  /** Resolution (width x height) */
  resolution?: {
    width: number
    height: number
  }

  /** Creation timestamp */
  createdAt?: string

  /** Whether this is a lip-synced video */
  isLipSynced?: boolean
}

/**
 * Asset gallery filter state
 */
export type AssetFilter = 'all' | AssetType

/**
 * Asset gallery props interface
 */
export interface AssetGalleryProps {
  /** Project scenes data */
  scenes?: Array<{
    sequence: number
    prompt: string
    /** @deprecated Use originalVideoClipUrl instead */
    videoClipUrl?: string | null
    originalVideoClipUrl?: string | null
    status?: string
  }>

  /** Character reference image ID */
  characterReferenceImageId?: string | null

  /** Loading state */
  isLoading?: boolean

  /** Error message */
  error?: string | null

  /** Custom class name */
  className?: string
}

/**
 * Asset lightbox props interface
 */
export interface AssetLightboxProps {
  /** Asset to display */
  asset: Asset | null

  /** Open state */
  isOpen: boolean

  /** Close handler */
  onClose: () => void

  /** Navigate to previous asset */
  onPrevious?: () => void

  /** Navigate to next asset */
  onNext?: () => void

  /** Download handler */
  onDownload?: (asset: Asset) => void

  /** Share handler */
  onShare?: (asset: Asset) => void
}
