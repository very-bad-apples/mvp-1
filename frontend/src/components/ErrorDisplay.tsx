/**
 * User-friendly Error Display Component
 *
 * Provides clear, actionable error messages with:
 * - User-friendly titles and descriptions
 * - Recovery status and retry information
 * - Severity-based styling
 * - Action buttons for retry/dismiss
 */

'use client'

import React from 'react'
import type { APIError } from '@/lib/api/client'
import { getUserFriendlyError } from '@/lib/api/client'
import type { ErrorSeverity, ErrorCategory } from '@/lib/error-logger'

export interface ErrorDisplayProps {
  /** The error to display */
  error: Error | APIError

  /** Optional custom title */
  title?: string

  /** Optional custom message */
  message?: string

  /** Whether to show retry information */
  showRetryInfo?: boolean

  /** Current retry attempt (if retrying) */
  retryAttempt?: number

  /** Maximum retry attempts */
  maxRetries?: number

  /** Delay until next retry (ms) */
  nextRetryDelay?: number

  /** Whether retry is in progress */
  isRetrying?: boolean

  /** Callback for manual retry button */
  onRetry?: () => void

  /** Callback for dismiss button */
  onDismiss?: () => void

  /** Optional severity override */
  severity?: ErrorSeverity

  /** Optional category override */
  category?: ErrorCategory

  /** Whether to show technical details */
  showTechnicalDetails?: boolean
}

/**
 * Get severity color classes
 */
function getSeverityClasses(severity: ErrorSeverity): {
  container: string
  icon: string
  title: string
} {
  const severityMap = {
    low: {
      container: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
      icon: 'text-blue-600 dark:text-blue-400',
      title: 'text-blue-900 dark:text-blue-100',
    },
    medium: {
      container: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800',
      icon: 'text-yellow-600 dark:text-yellow-400',
      title: 'text-yellow-900 dark:text-yellow-100',
    },
    high: {
      container: 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
      icon: 'text-orange-600 dark:text-orange-400',
      title: 'text-orange-900 dark:text-orange-100',
    },
    critical: {
      container: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
      icon: 'text-red-600 dark:text-red-400',
      title: 'text-red-900 dark:text-red-100',
    },
  }

  return severityMap[severity] || severityMap.medium
}

/**
 * Get severity icon
 */
function getSeverityIcon(severity: ErrorSeverity): string {
  const iconMap = {
    low: 'ℹ️',
    medium: '⚠️',
    high: '⚠️',
    critical: '🚨',
  }

  return iconMap[severity] || '⚠️'
}

/**
 * Format retry delay
 */
function formatRetryDelay(delayMs: number): string {
  if (delayMs < 1000) {
    return `${delayMs}ms`
  }
  const seconds = Math.round(delayMs / 1000)
  return `${seconds}s`
}

export function ErrorDisplay({
  error,
  title,
  message,
  showRetryInfo = true,
  retryAttempt,
  maxRetries,
  nextRetryDelay,
  isRetrying = false,
  onRetry,
  onDismiss,
  severity = 'medium',
  category,
  showTechnicalDetails = false,
}: ErrorDisplayProps): JSX.Element {
  // Get user-friendly error information if error is an APIError
  const errorInfo =
    'errorCode' in error && 'statusCode' in error
      ? getUserFriendlyError(error as APIError)
      : null

  // Determine display values
  const displayTitle = title || errorInfo?.title || 'Error Occurred'
  const displayMessage = message || errorInfo?.message || error.message
  const displayRecovery = errorInfo?.recovery || 'Please try again'
  const canRetry = errorInfo?.canRetry ?? true

  // Get styling classes
  const classes = getSeverityClasses(severity)
  const icon = getSeverityIcon(severity)

  return (
    <div
      className={`rounded-lg border p-4 ${classes.container}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`flex-shrink-0 text-2xl ${classes.icon}`} aria-hidden="true">
          {icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className={`font-semibold text-lg mb-1 ${classes.title}`}>
            {displayTitle}
          </h3>

          {/* Message */}
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
            {displayMessage}
          </p>

          {/* Recovery info */}
          {showRetryInfo && (
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              {isRetrying ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                  <span>
                    {retryAttempt && maxRetries
                      ? `Retrying (${retryAttempt}/${maxRetries})...`
                      : 'Retrying...'}
                    {nextRetryDelay && ` Next attempt in ${formatRetryDelay(nextRetryDelay)}`}
                  </span>
                </div>
              ) : (
                <span>{displayRecovery}</span>
              )}
            </div>
          )}

          {/* Retry attempt info */}
          {showRetryInfo && retryAttempt && maxRetries && !isRetrying && (
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              <span>
                {retryAttempt >= maxRetries
                  ? `All retry attempts exhausted (${maxRetries}/${maxRetries})`
                  : `Attempt ${retryAttempt}/${maxRetries}`}
              </span>
            </div>
          )}

          {/* Technical details (collapsible) */}
          {showTechnicalDetails && (
            <details className="mt-3 text-xs">
              <summary className="cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
                Technical Details
              </summary>
              <div className="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded font-mono text-gray-700 dark:text-gray-300 overflow-x-auto">
                <div>
                  <strong>Error Type:</strong> {error.constructor.name}
                </div>
                {'errorCode' in error && (
                  <div>
                    <strong>Error Code:</strong> {(error as any).errorCode}
                  </div>
                )}
                {'statusCode' in error && (
                  <div>
                    <strong>Status Code:</strong> {(error as any).statusCode}
                  </div>
                )}
                {category && (
                  <div>
                    <strong>Category:</strong> {category}
                  </div>
                )}
                {error.stack && (
                  <div className="mt-2">
                    <strong>Stack Trace:</strong>
                    <pre className="mt-1 text-xs whitespace-pre-wrap">{error.stack}</pre>
                  </div>
                )}
              </div>
            </details>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 mt-3">
            {onRetry && canRetry && !isRetrying && (
              <button
                onClick={onRetry}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                disabled={isRetrying}
              >
                Retry Now
              </button>
            )}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Compact error banner for inline display
 */
export function ErrorBanner({
  error,
  onDismiss,
}: {
  error: Error | APIError
  onDismiss?: () => void
}): JSX.Element {
  const errorInfo =
    'errorCode' in error && 'statusCode' in error
      ? getUserFriendlyError(error as APIError)
      : null

  const displayMessage = errorInfo?.message || error.message

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 text-red-900 dark:text-red-100"
      role="alert"
    >
      <span className="text-xl" aria-hidden="true">
        ⚠️
      </span>
      <p className="flex-1 text-sm">{displayMessage}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-red-900 dark:text-red-100 hover:text-red-700 dark:hover:text-red-300 transition-colors"
          aria-label="Dismiss error"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  )
}

/**
 * Toast-style error notification
 */
export function ErrorToast({
  error,
  onDismiss,
  autoDismissDelay = 5000,
}: {
  error: Error | APIError
  onDismiss?: () => void
  autoDismissDelay?: number
}): JSX.Element {
  React.useEffect(() => {
    if (autoDismissDelay > 0 && onDismiss) {
      const timer = setTimeout(onDismiss, autoDismissDelay)
      return () => clearTimeout(timer)
    }
  }, [autoDismissDelay, onDismiss])

  const errorInfo =
    'errorCode' in error && 'statusCode' in error
      ? getUserFriendlyError(error as APIError)
      : null

  const displayTitle = errorInfo?.title || 'Error'
  const displayMessage = errorInfo?.message || error.message

  return (
    <div
      className="fixed bottom-4 right-4 max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 animate-slide-up"
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="text-xl flex-shrink-0" aria-hidden="true">
          ⚠️
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
            {displayTitle}
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {displayMessage}
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Dismiss"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}
