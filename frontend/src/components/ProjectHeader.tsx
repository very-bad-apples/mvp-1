'use client'

import * as React from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { ProjectStatus } from '@/types/project'
import { Calendar, Download, Play, X } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Props for the ProjectHeader component
 */
export interface ProjectHeaderProps {
  /** Project title/name */
  title: string

  /** Unique project identifier */
  projectId: string

  /** Current status of the project */
  status: ProjectStatus

  /** Date project was created */
  createdAt: Date

  /** Generation mode (music-video or ad-creative) */
  mode: 'music-video' | 'ad-creative'

  /** User's original concept prompt */
  conceptPrompt: string

  /** Overall progress percentage (0-100) */
  progress: number

  /** Callback when start generation is clicked */
  onStartGeneration?: () => void

  /** Callback when cancel is clicked */
  onCancel?: () => void

  /** Callback when download is clicked */
  onDownload?: () => void

  /** Additional className for custom styling */
  className?: string
}

/**
 * Status badge configuration mapping status to colors and labels
 */
const statusConfig: Record<
  ProjectStatus,
  { label: string; className: string; variant?: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  pending: {
    label: 'Pending',
    className: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  },
  processing: {
    label: 'Processing',
    className: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  },
  completed: {
    label: 'Completed',
    className: 'bg-green-500/10 text-green-400 border-green-500/20',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-500/10 text-red-400 border-red-500/20',
    variant: 'destructive',
  },
}

/**
 * ProjectHeader Component
 *
 * Displays project metadata, status, progress, and control buttons.
 * Designed for dark theme with blue accents and responsive layout.
 *
 * @example
 * ```tsx
 * <ProjectHeader
 *   title="My Music Video"
 *   projectId="proj_123"
 *   status="generating-videos"
 *   createdAt={new Date()}
 *   mode="music-video"
 *   conceptPrompt="A futuristic city with neon lights"
 *   progress={45}
 *   onStartGeneration={() => console.log('Start')}
 *   onCancel={() => console.log('Cancel')}
 *   onDownload={() => console.log('Download')}
 * />
 * ```
 */
export function ProjectHeader({
  title,
  projectId,
  status,
  createdAt,
  mode,
  conceptPrompt,
  progress,
  onStartGeneration,
  onCancel,
  onDownload,
  className,
}: ProjectHeaderProps) {
  const config = statusConfig[status]
  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'
  const isProcessing = !isCompleted && !isFailed

  // Format date
  const formattedDate = createdAt.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <header
      className={cn(
        'w-full rounded-xl border border-gray-700/50 bg-gray-800/50 backdrop-blur-sm shadow-xl',
        className
      )}
    >
      <div className="p-6 space-y-6">
        {/* Top Section: Title, ID, and Status */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="space-y-2 flex-1 min-w-0">
            {/* Project Title */}
            <h1 className="text-2xl sm:text-3xl font-bold text-white truncate">
              {title}
            </h1>

            {/* Project ID and Mode */}
            <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400">
              <span className="font-mono">{projectId}</span>
              <span className="hidden sm:inline text-gray-600">•</span>
              <span className="capitalize">{mode.replace('-', ' ')}</span>
            </div>
          </div>

          {/* Status Badge */}
          <Badge
            variant={config.variant}
            className={cn('shrink-0 text-sm px-3 py-1', config.className)}
          >
            {config.label}
          </Badge>
        </div>

        {/* Progress Bar */}
        {isProcessing && (
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-400">Progress</span>
              <span className="text-white font-medium">{Math.round(progress)}%</span>
            </div>
            <Progress
              value={progress}
              className="h-2 bg-gray-700/50"
            />
          </div>
        )}

        {/* Metadata Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
          {/* Created Date */}
          <div className="flex items-start gap-3">
            <Calendar className="w-5 h-5 text-gray-400 mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Created</p>
              <p className="text-sm text-gray-300">{formattedDate}</p>
            </div>
          </div>

          {/* Concept Prompt */}
          <div className="flex items-start gap-3">
            <div className="w-5 h-5 flex items-center justify-center mt-0.5 shrink-0">
              <div className="w-2 h-2 rounded-full bg-blue-400" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Concept</p>
              <p className="text-sm text-gray-300 line-clamp-2">{conceptPrompt}</p>
            </div>
          </div>
        </div>

        {/* Control Buttons */}
        <div className="flex flex-wrap gap-3 pt-2">
          {/* Start Generation Button - shown when not processing */}
          {!isProcessing && !isCompleted && onStartGeneration && (
            <Button
              onClick={onStartGeneration}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              disabled={isFailed}
            >
              <Play className="w-4 h-4" />
              Start Generation
            </Button>
          )}

          {/* Cancel Button - shown during processing */}
          {isProcessing && onCancel && (
            <Button
              onClick={onCancel}
              variant="outline"
              className="border-red-500/50 text-red-400 hover:bg-red-500/10"
            >
              <X className="w-4 h-4" />
              Cancel
            </Button>
          )}

          {/* Download Button - shown when completed */}
          {isCompleted && onDownload && (
            <Button
              onClick={onDownload}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <Download className="w-4 h-4" />
              Download
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
