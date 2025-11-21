/**
 * useProjectPolling - React Hook for Polling Project Status
 *
 * This hook polls the project API endpoint every 3 seconds to get real-time updates
 * on project status. It automatically stops polling when the project reaches a
 * terminal state (completed or error) and implements exponential backoff for
 * network errors to prevent excessive retries.
 *
 * Features:
 * - Polls every 3 seconds by default
 * - Automatic stop on terminal states (completed/error)
 * - Automatic stop on unrecoverable errors (404, 403, project not found)
 * - Automatic stop after 5 consecutive errors
 * - Exponential backoff for recoverable network errors (1s → 2s → 4s → 8s, max 30s)
 * - Proper cleanup to prevent memory leaks
 * - Loading and error state management
 * - Manual refetch capability
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { getProject } from '@/lib/api/client'
import { Project, ProjectStatus } from '@/types/project'
import { APIError } from '@/lib/api/client'

/**
 * Configuration for polling behavior
 */
interface PollingConfig {
  /** Polling interval in milliseconds */
  intervalMs: number
  /** Initial backoff delay in milliseconds */
  initialBackoffMs: number
  /** Maximum backoff delay in milliseconds */
  maxBackoffMs: number
  /** Backoff multiplier for exponential backoff */
  backoffMultiplier: number
}

/**
 * Default polling configuration
 */
const DEFAULT_CONFIG: PollingConfig = {
  intervalMs: 3000, // 3 seconds
  initialBackoffMs: 1000, // 1 second
  maxBackoffMs: 30000, // 30 seconds
  backoffMultiplier: 2, // Double each time
}

/**
 * Hook state interface
 */
interface UseProjectPollingState {
  project: Project | null
  loading: boolean
  error: string | null
}

/**
 * Hook return value interface
 */
interface UseProjectPollingReturn extends UseProjectPollingState {
  /** Manually trigger a refetch of the project */
  refetch: () => Promise<void>
  /** Check if polling is currently active */
  isPolling: boolean
  /** Optimistically update project state (useful for immediate UI updates) */
  setOptimisticProject: (project: Project) => void
}

/**
 * Check if a project status requires active polling
 * Only poll for statuses that indicate active backend processing
 */
function shouldPollStatus(status: Project['status'] | undefined): boolean {
  if (!status) return false

  // Only poll for active processing states
  // Backend uses 'processing' for all active work
  const activeStates: Project['status'][] = [
    'processing'
  ]

  return activeStates.includes(status)
}

/**
 * Custom hook to poll project status with automatic updates
 *
 * @param projectId - The ID of the project to poll
 * @param config - Optional polling configuration
 * @returns Project data, loading state, error state, and refetch function
 *
 * @example
 * ```tsx
 * function ProjectPage({ projectId }: { projectId: string }) {
 *   const { project, loading, error, refetch, isPolling } = useProjectPolling(projectId)
 *
 *   if (loading && !project) return <div>Loading...</div>
 *   if (error) return <div>Error: {error}</div>
 *   if (!project) return <div>Project not found</div>
 *
 *   return (
 *     <div>
 *       <h1>{project.conceptPrompt}</h1>
 *       <p>Status: {project.status}</p>
 *       {isPolling && <p>Polling for updates...</p>}
 *       <button onClick={refetch}>Refresh</button>
 *     </div>
 *   )
 * }
 * ```
 */
export function useProjectPolling(
  projectId: string,
  config: Partial<PollingConfig> & { enabled?: boolean } = {}
): UseProjectPollingReturn {
  // Extract enabled flag (defaults to true for backwards compatibility)
  const { enabled = true, ...pollingConfigOverrides } = config

  // Memoize config to prevent recreating on every render
  const pollingConfig = useMemo(
    () => ({ ...DEFAULT_CONFIG, ...pollingConfigOverrides }),
    [pollingConfigOverrides.intervalMs, pollingConfigOverrides.initialBackoffMs, pollingConfigOverrides.maxBackoffMs, pollingConfigOverrides.backoffMultiplier]
  )

  // State management
  const [state, setState] = useState<UseProjectPollingState>({
    project: null,
    loading: true,
    error: null,
  })

  // Refs for mutable values that shouldn't trigger re-renders
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const backoffDelayRef = useRef<number>(pollingConfig.initialBackoffMs)
  const consecutiveErrorsRef = useRef<number>(0)
  const isPollingRef = useRef<boolean>(false)
  const isMountedRef = useRef<boolean>(true)
  const pendingTimeoutsRef = useRef<Set<NodeJS.Timeout>>(new Set())

  /**
   * Fetch project data from API
   */
  const fetchProject = useCallback(async () => {
    // Don't fetch if component is unmounted
    if (!isMountedRef.current) return

    try {
      setState(prev => ({ ...prev, loading: true }))

      const response = await getProject(projectId)

      // Only update state if component is still mounted
      if (!isMountedRef.current) return

      // Response is the project data directly (not wrapped)
      if (response.projectId) {
        // Reset error counters on successful fetch
        consecutiveErrorsRef.current = 0
        backoffDelayRef.current = pollingConfig.initialBackoffMs

        // Add calculated progress field to backend response
        const project: Project = {
          ...response,
          mode: 'music-video', // Frontend-only field, default value
          progress: Math.round((response.completedScenes / Math.max(response.sceneCount, 1)) * 100),
        }

        setState({
          project,
          loading: false,
          error: null,
        })

        // Check if we should start or stop polling based on status
        const needsPolling = shouldPollStatus(response.status as ProjectStatus)

        if (!needsPolling) {
          // Status doesn't require polling - make sure polling is stopped
          console.log(
            `[useProjectPolling] Project status '${response.status}' doesn't require polling`
          )
          if (isPollingRef.current || intervalRef.current) {
            console.log('[useProjectPolling] Stopping polling')
            isPollingRef.current = false
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            pendingTimeoutsRef.current.forEach(timeout => clearTimeout(timeout))
            pendingTimeoutsRef.current.clear()
          }
        } else if (!isPollingRef.current && !intervalRef.current) {
          // Status requires polling but we're not polling yet - start it
          console.log(
            `[useProjectPolling] Project status '${response.status}' requires polling, starting`
          )
          startPolling()
        }
      } else {
        // Project not found or error - stop polling
        console.warn(
          `[useProjectPolling] Project ${projectId} not found or error occurred, stopping polling`
        )

        setState(prev => ({
          ...prev,
          loading: false,
          error: 'Failed to fetch project',
        }))

        // Stop polling on project not found
        console.log('[useProjectPolling] Stopping polling due to project not found')
        isPollingRef.current = false
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        pendingTimeoutsRef.current.forEach(timeout => clearTimeout(timeout))
        pendingTimeoutsRef.current.clear()
      }
    } catch (err) {
      // Only update state if component is still mounted
      if (!isMountedRef.current) return

      consecutiveErrorsRef.current++

      const errorMessage =
        err instanceof APIError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Unknown error occurred'

      // Check if this is an unrecoverable error
      const isUnrecoverableError =
        (err instanceof APIError && (err.statusCode === 404 || err.statusCode === 403)) ||
        consecutiveErrorsRef.current >= 5 // Stop after 5 consecutive errors

      if (isUnrecoverableError) {
        console.warn(
          `[useProjectPolling] Unrecoverable error for project ${projectId} (status: ${err instanceof APIError ? err.statusCode : 'N/A'}), stopping polling permanently:`,
          errorMessage
        )

        setState(prev => ({
          ...prev,
          loading: false,
          error: errorMessage,
        }))

        // Stop polling permanently on unrecoverable errors
        console.log('[useProjectPolling] Stopping polling due to unrecoverable error')
        isPollingRef.current = false
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        pendingTimeoutsRef.current.forEach(timeout => clearTimeout(timeout))
        pendingTimeoutsRef.current.clear()
        return
      }

      // Calculate exponential backoff for recoverable errors
      const backoffDelay = Math.min(
        pollingConfig.initialBackoffMs *
          Math.pow(pollingConfig.backoffMultiplier, consecutiveErrorsRef.current - 1),
        pollingConfig.maxBackoffMs
      )
      backoffDelayRef.current = backoffDelay

      console.warn(
        `[useProjectPolling] Error fetching project ${projectId} (attempt ${consecutiveErrorsRef.current}), ` +
          `backing off for ${backoffDelay}ms:`,
        errorMessage
      )

      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }))

      // Apply exponential backoff by temporarily clearing the interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null

        // Restart polling after backoff delay
        const timeoutId = setTimeout(() => {
          pendingTimeoutsRef.current.delete(timeoutId)
          if (isMountedRef.current && isPollingRef.current) {
            startPolling()
          }
        }, backoffDelay)

        pendingTimeoutsRef.current.add(timeoutId)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, pollingConfig])

  /**
   * Start polling for project updates
   */
  const startPolling = useCallback(() => {
    // Don't start if already polling or unmounted
    if (intervalRef.current || !isMountedRef.current) return

    isPollingRef.current = true

    // Fetch immediately
    fetchProject()

    // Set up interval for subsequent fetches
    intervalRef.current = setInterval(() => {
      fetchProject()
    }, pollingConfig.intervalMs)
  }, [fetchProject, pollingConfig.intervalMs])

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    console.log('[useProjectPolling] Stopping polling permanently')
    isPollingRef.current = false

    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    // Clear all pending timeout callbacks
    pendingTimeoutsRef.current.forEach(timeout => clearTimeout(timeout))
    pendingTimeoutsRef.current.clear()
  }, [])

  /**
   * Manual refetch function (exposed to consumers)
   */
  const refetch = useCallback(async () => {
    await fetchProject()
  }, [fetchProject])

  /**
   * Optimistically update project state
   * Useful for immediate UI updates before server confirmation
   */
  const setOptimisticProject = useCallback((project: Project) => {
    setState(prev => ({
      ...prev,
      project,
      loading: false,
      error: null,
    }))

    // Check if we should start polling based on optimistic status
    const needsPolling = shouldPollStatus(project.status as ProjectStatus)
    if (needsPolling && !isPollingRef.current && !intervalRef.current) {
      console.log(
        `[useProjectPolling] Optimistic status '${project.status}' requires polling, starting`
      )
      startPolling()
    }
  }, [startPolling])

  /**
   * Fetch once on mount, don't start interval polling
   * Polling will only happen for active processing states via shouldPollStatus check
   */
  useEffect(() => {
    isMountedRef.current = true

    // Just fetch once on mount
    fetchProject()

    // Cleanup function
    return () => {
      isMountedRef.current = false
      stopPolling()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]) // Only re-fetch when projectId changes

  return {
    ...state,
    refetch,
    isPolling: isPollingRef.current,
    setOptimisticProject,
  }
}
