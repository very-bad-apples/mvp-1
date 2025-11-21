/**
 * Comprehensive Error Logging Infrastructure
 *
 * Provides structured error logging with:
 * - Contextual information (user, session, environment)
 * - Error categorization and severity levels
 * - Stack trace capture
 * - Performance metrics
 * - Integration with monitoring services
 */

import type { OrchestrationPhase } from './orchestration'

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

/**
 * Error category types
 */
export enum ErrorCategory {
  NETWORK = 'network',
  API = 'api',
  STORAGE = 'storage',
  VALIDATION = 'validation',
  CONFIGURATION = 'configuration',
  ORCHESTRATION = 'orchestration',
  UNKNOWN = 'unknown',
}

/**
 * Structured error log entry
 */
export interface ErrorLogEntry {
  // Identification
  timestamp: string
  errorId: string
  sessionId?: string
  userId?: string

  // Error details
  message: string
  errorType: string
  errorCode?: string
  category: ErrorCategory
  severity: ErrorSeverity

  // Context
  phase?: OrchestrationPhase
  sceneIndex?: number | null
  projectId?: string
  operation?: string

  // Technical details
  stack?: string
  url?: string
  statusCode?: number

  // Recovery information
  isRetryable: boolean
  attemptNumber?: number
  maxAttempts?: number
  nextRetryDelay?: number

  // Performance
  duration?: number
  memory?: number

  // User agent and environment
  userAgent?: string
  platform?: string
  viewport?: { width: number; height: number }

  // Additional context
  metadata?: Record<string, any>
}

/**
 * Error logger class
 */
export class ErrorLogger {
  private sessionId: string
  private logs: ErrorLogEntry[] = []
  private maxLogs = 100 // Keep last 100 errors in memory

  constructor() {
    this.sessionId = this.generateSessionId()
  }

  /**
   * Generate a unique session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Generate a unique error ID
   */
  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Determine error category from error object
   */
  private categorizeError(error: Error): ErrorCategory {
    const message = error.message.toLowerCase()
    const errorType = error.constructor.name.toLowerCase()

    if (errorType.includes('network') || message.includes('network') || message.includes('fetch')) {
      return ErrorCategory.NETWORK
    }
    if (errorType.includes('api') || message.includes('api')) {
      return ErrorCategory.API
    }
    if (errorType.includes('s3') || errorType.includes('storage') || message.includes('storage')) {
      return ErrorCategory.STORAGE
    }
    if (errorType.includes('validation') || message.includes('validation')) {
      return ErrorCategory.VALIDATION
    }
    if (errorType.includes('config') || message.includes('config')) {
      return ErrorCategory.CONFIGURATION
    }
    if (errorType.includes('orchestration') || message.includes('orchestration')) {
      return ErrorCategory.ORCHESTRATION
    }

    return ErrorCategory.UNKNOWN
  }

  /**
   * Determine error severity from error object and context
   */
  private determineSeverity(error: Error, context: Partial<ErrorLogEntry>): ErrorSeverity {
    // Critical: Configuration errors, system failures
    if (context.category === ErrorCategory.CONFIGURATION) {
      return ErrorSeverity.CRITICAL
    }

    // High: Non-retryable errors, orchestration failures
    if (!context.isRetryable || context.category === ErrorCategory.ORCHESTRATION) {
      return ErrorSeverity.HIGH
    }

    // Medium: API errors, storage errors
    if (context.category === ErrorCategory.API || context.category === ErrorCategory.STORAGE) {
      return ErrorSeverity.MEDIUM
    }

    // Low: Network errors (retryable), validation errors
    return ErrorSeverity.LOW
  }

  /**
   * Get current viewport dimensions
   */
  private getViewport(): { width: number; height: number } {
    if (typeof window !== 'undefined') {
      return {
        width: window.innerWidth,
        height: window.innerHeight,
      }
    }
    return { width: 0, height: 0 }
  }

  /**
   * Get browser/platform information
   */
  private getPlatformInfo(): { userAgent: string; platform: string } {
    if (typeof navigator !== 'undefined') {
      return {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
      }
    }
    return { userAgent: '', platform: '' }
  }

  /**
   * Log an error with full context
   */
  log(
    error: Error,
    context: {
      phase?: OrchestrationPhase
      sceneIndex?: number | null
      projectId?: string
      operation?: string
      url?: string
      statusCode?: number
      isRetryable?: boolean
      attemptNumber?: number
      maxAttempts?: number
      nextRetryDelay?: number
      duration?: number
      metadata?: Record<string, any>
    } = {}
  ): ErrorLogEntry {
    const category = this.categorizeError(error)
    const platformInfo = this.getPlatformInfo()
    const viewport = this.getViewport()

    const logEntry: ErrorLogEntry = {
      // Identification
      timestamp: new Date().toISOString(),
      errorId: this.generateErrorId(),
      sessionId: this.sessionId,

      // Error details
      message: error.message,
      errorType: error.constructor.name,
      errorCode: (error as any).errorCode,
      category,
      severity: this.determineSeverity(error, { ...context, category, isRetryable: context.isRetryable ?? false }),

      // Context
      phase: context.phase,
      sceneIndex: context.sceneIndex,
      projectId: context.projectId,
      operation: context.operation,

      // Technical details
      stack: error.stack,
      url: context.url,
      statusCode: context.statusCode,

      // Recovery information
      isRetryable: context.isRetryable ?? false,
      attemptNumber: context.attemptNumber,
      maxAttempts: context.maxAttempts,
      nextRetryDelay: context.nextRetryDelay,

      // Performance
      duration: context.duration,
      memory: typeof performance !== 'undefined' && (performance as any).memory
        ? (performance as any).memory.usedJSHeapSize
        : undefined,

      // Environment
      userAgent: platformInfo.userAgent,
      platform: platformInfo.platform,
      viewport,

      // Additional context
      metadata: context.metadata,
    }

    // Store in memory
    this.logs.push(logEntry)
    if (this.logs.length > this.maxLogs) {
      this.logs.shift() // Remove oldest log
    }

    // Console logging with appropriate level
    this.consoleLog(logEntry)

    // Send to monitoring service (if configured)
    this.sendToMonitoring(logEntry)

    return logEntry
  }

  /**
   * Log to console with appropriate level and formatting
   */
  private consoleLog(entry: ErrorLogEntry): void {
    const style = this.getConsoleStyle(entry.severity)
    const prefix = `[${entry.severity.toUpperCase()}] [${entry.category}]`

    const logData = {
      errorId: entry.errorId,
      timestamp: entry.timestamp,
      message: entry.message,
      phase: entry.phase,
      sceneIndex: entry.sceneIndex,
      isRetryable: entry.isRetryable,
      attemptNumber: entry.attemptNumber,
      maxAttempts: entry.maxAttempts,
      nextRetryDelay: entry.nextRetryDelay ? `${entry.nextRetryDelay}ms` : undefined,
      statusCode: entry.statusCode,
      errorCode: entry.errorCode,
      metadata: entry.metadata,
    }

    if (entry.severity === ErrorSeverity.CRITICAL || entry.severity === ErrorSeverity.HIGH) {
      console.error(prefix, entry.message, logData, entry.stack)
    } else if (entry.severity === ErrorSeverity.MEDIUM) {
      console.warn(prefix, entry.message, logData)
    } else {
      console.info(prefix, entry.message, logData)
    }
  }

  /**
   * Get console styling for severity level
   */
  private getConsoleStyle(severity: ErrorSeverity): string {
    const styles = {
      [ErrorSeverity.CRITICAL]: 'color: red; font-weight: bold;',
      [ErrorSeverity.HIGH]: 'color: orange; font-weight: bold;',
      [ErrorSeverity.MEDIUM]: 'color: yellow;',
      [ErrorSeverity.LOW]: 'color: blue;',
    }
    return styles[severity]
  }

  /**
   * Send error log to monitoring service
   * (Placeholder for integration with services like Sentry, LogRocket, etc.)
   */
  private sendToMonitoring(entry: ErrorLogEntry): void {
    // TODO: Integrate with monitoring service
    // Example: Sentry, LogRocket, DataDog, etc.
    // if (window.Sentry) {
    //   window.Sentry.captureException(new Error(entry.message), {
    //     extra: entry,
    //   })
    // }
  }

  /**
   * Get all logs from current session
   */
  getLogs(): ErrorLogEntry[] {
    return [...this.logs]
  }

  /**
   * Get logs filtered by category
   */
  getLogsByCategory(category: ErrorCategory): ErrorLogEntry[] {
    return this.logs.filter(log => log.category === category)
  }

  /**
   * Get logs filtered by severity
   */
  getLogsBySeverity(severity: ErrorSeverity): ErrorLogEntry[] {
    return this.logs.filter(log => log.severity === severity)
  }

  /**
   * Get logs for a specific phase
   */
  getLogsByPhase(phase: OrchestrationPhase): ErrorLogEntry[] {
    return this.logs.filter(log => log.phase === phase)
  }

  /**
   * Clear all logs
   */
  clearLogs(): void {
    this.logs = []
  }

  /**
   * Export logs as JSON
   */
  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2)
  }

  /**
   * Get error statistics
   */
  getStatistics(): {
    total: number
    byCategory: Record<ErrorCategory, number>
    bySeverity: Record<ErrorSeverity, number>
    retryableCount: number
    averageRetries: number
  } {
    const stats = {
      total: this.logs.length,
      byCategory: {} as Record<ErrorCategory, number>,
      bySeverity: {} as Record<ErrorSeverity, number>,
      retryableCount: 0,
      averageRetries: 0,
    }

    let totalRetries = 0
    let retriedErrors = 0

    this.logs.forEach(log => {
      // Count by category
      stats.byCategory[log.category] = (stats.byCategory[log.category] || 0) + 1

      // Count by severity
      stats.bySeverity[log.severity] = (stats.bySeverity[log.severity] || 0) + 1

      // Count retryable errors
      if (log.isRetryable) {
        stats.retryableCount++
      }

      // Calculate retry stats
      if (log.attemptNumber && log.attemptNumber > 1) {
        totalRetries += log.attemptNumber - 1
        retriedErrors++
      }
    })

    stats.averageRetries = retriedErrors > 0 ? totalRetries / retriedErrors : 0

    return stats
  }
}

/**
 * Global error logger instance
 */
export const errorLogger = new ErrorLogger()
