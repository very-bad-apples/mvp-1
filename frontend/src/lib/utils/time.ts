/**
 * Time formatting utilities for video and duration display
 */

/**
 * Format time for video player display (MM:SS or M:SS)
 * Example: 125 seconds → "2:05"
 */
export function formatVideoTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Format time with precision for trimmer display
 * Example: 65.5 seconds → "1:05.5" or 5.5 seconds → "5.5s"
 */
export function formatPreciseTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(1)
  return mins > 0 ? `${mins}:${secs.padStart(4, "0")}` : `${secs}s`
}

/**
 * Format duration in human-readable format
 * Example: 125 seconds → "2m 5s" or 45 seconds → "45s"
 */
export function formatDuration(durationInSeconds?: number): string {
  if (!durationInSeconds) return '0s'
  const minutes = Math.floor(durationInSeconds / 60)
  const seconds = Math.floor(durationInSeconds % 60)
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}
