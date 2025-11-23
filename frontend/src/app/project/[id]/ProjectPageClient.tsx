'use client'

/**
 * ProjectPageClient - Main Project Dashboard
 *
 * This component orchestrates the complete project view with:
 * - Real-time project status polling
 * - Component integration (Header, PhaseTracker, Scenes, Assets, FinalVideo)
 * - Start generation and regeneration controls
 * - Conditional rendering based on project status
 * - Error handling and loading states
 */

import { useCallback, useMemo, useState } from 'react'
import Link from 'next/link'
import { Video, ChevronLeft, CheckCircle2, Circle, Film, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useToast } from '@/hooks/useToast'
import { useProjectPolling } from '@/hooks/useProjectPolling'
import { ProjectStatus, ProjectScene } from '@/types/project'
import { AssetGallery } from '@/components/AssetGallery'
import FinalVideoPlayer from '@/components/FinalVideoPlayer'
import { LipsyncOptionsModal, type LipsyncOptions } from '@/components/LipsyncOptionsModal'

const statusConfig: Record<ProjectStatus, { color: string; label: string }> = {
  'pending': { color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20', label: 'Pending' },
  'processing': { color: 'bg-blue-500/10 text-blue-500 border-blue-500/20', label: 'Processing' },
  'completed': { color: 'bg-green-500/10 text-green-500 border-green-500/20', label: 'Completed' },
  'failed': { color: 'bg-red-500/10 text-red-500 border-red-500/20', label: 'Failed' },
}

interface Phase {
  id: string
  label: string
  completed: boolean
}

function getPhases(status: ProjectStatus): Phase[] {
  // Simplified phase tracking based on new status model
  // Backend uses 'pending', 'processing', 'completed', 'failed'
  const phases: Phase[] = [
    { id: 'scenes', label: 'Scenes', completed: false },
    { id: 'images', label: 'Images', completed: false },
    { id: 'videos', label: 'Videos', completed: false },
    { id: 'lipsync', label: 'Lip-sync', completed: false },
    { id: 'compose', label: 'Compose', completed: false },
  ]

  // Mark all phases as completed if project is completed
  if (status === 'completed') {
    phases.forEach(p => p.completed = true)
  }

  return phases
}

function ProjectHeader({
  title,
  status,
  createdAt,
  onStartGeneration,
  isGenerating,
}: {
  title: string
  status: ProjectStatus
  createdAt: string
  onStartGeneration?: () => void
  isGenerating?: boolean
}) {
  const statusStyle = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending
  const canStartGeneration = status === 'pending' && onStartGeneration

  return (
    <div className="space-y-4" role="region" aria-label="Project header">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl md:text-4xl font-bold text-white">{title}</h1>
          <p className="text-gray-400 text-sm">
            <time dateTime={createdAt}>
              Created on {new Date(createdAt).toLocaleDateString()}
            </time>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            className={`${statusStyle.color} border px-4 py-2 text-sm font-medium`}
            aria-label={`Project status: ${statusStyle.label}`}
          >
            {statusStyle.label}
          </Badge>
          {canStartGeneration && (
            <Button
              onClick={onStartGeneration}
              disabled={isGenerating}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              aria-label="Start video generation"
            >
              <Play className="w-4 h-4 mr-2" aria-hidden="true" />
              {isGenerating ? 'Starting...' : 'Start Generation'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function PhaseTracker({ phases }: { phases: Phase[] }) {
  const completedCount = phases.filter(p => p.completed).length

  return (
    <div
      className="bg-gray-800/50 border border-gray-700 rounded-lg p-6"
      role="region"
      aria-label="Generation progress tracker"
    >
      <h2 className="text-xl font-semibold text-white mb-6">
        Project Phases
        <span className="sr-only">
          {completedCount} of {phases.length} phases completed
        </span>
      </h2>
      <div
        className="flex items-center justify-between gap-2 overflow-x-auto pb-2"
        role="progressbar"
        aria-valuenow={completedCount}
        aria-valuemin={0}
        aria-valuemax={phases.length}
        aria-label="Project generation progress"
      >
        {phases.map((phase, index) => (
          <div key={phase.id} className="flex items-center flex-shrink-0">
            <div className="flex flex-col items-center gap-2">
              <div
                className={`flex items-center justify-center w-12 h-12 rounded-full ${
                  phase.completed ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 text-gray-400'
                }`}
                aria-label={`${phase.label} phase: ${phase.completed ? 'completed' : 'pending'}`}
              >
                {phase.completed ? (
                  <CheckCircle2 className="w-6 h-6" aria-hidden="true" />
                ) : (
                  <Circle className="w-6 h-6" aria-hidden="true" />
                )}
              </div>
              <span className={`text-xs md:text-sm font-medium ${
                phase.completed ? 'text-blue-400' : 'text-gray-400'
              }`}>
                {phase.label}
              </span>
            </div>
            {index < phases.length - 1 && (
              <div
                className={`w-12 md:w-24 h-0.5 mx-2 ${
                  phase.completed ? 'bg-blue-500/50' : 'bg-gray-700'
                }`}
                aria-hidden="true"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function SceneCard({
  scene,
  onRegenerateImage,
  onRegenerateVideo,
  onRegenerateLipsync,
  onAddLipsync,
}: {
  scene: ProjectScene
  onRegenerateImage?: (sceneId: number) => void
  onRegenerateVideo?: (sceneId: number) => void
  onRegenerateLipsync?: (sceneId: number) => void
  onAddLipsync?: (sceneId: number) => void
}) {
  const hasVideo = (scene.originalVideoClipUrl || scene.videoClipUrl) && scene.status === 'completed'
  const thumbnail = '/placeholder.svg'

  const sceneStatusConfig = {
    pending: { color: 'bg-gray-500/10 text-gray-400 border-gray-500/20', label: 'Pending' },
    generating: { color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', label: 'Generating' },
    completed: { color: 'bg-green-500/10 text-green-400 border-green-500/20', label: 'Completed' },
    failed: { color: 'bg-red-500/10 text-red-400 border-red-500/20', label: 'Failed' },
  }

  const sceneStatus = scene.status || 'pending'
  const statusStyle = sceneStatusConfig[sceneStatus as keyof typeof sceneStatusConfig] || sceneStatusConfig.pending

  return (
    <Card
      className="bg-gray-800/50 border-gray-700 overflow-hidden group hover:border-blue-500/50 transition-colors"
      role="article"
      aria-label={`Scene ${scene.sequence}: ${scene.prompt}`}
    >
      <div className="relative aspect-video overflow-hidden bg-gray-900/50">
        {hasVideo && (scene.originalVideoClipUrl || scene.videoClipUrl) ? (
          <video
            src={scene.originalVideoClipUrl || scene.videoClipUrl || ''}
            className="object-cover w-full h-full"
            muted
            loop
            playsInline
            aria-label={`Video preview for scene ${scene.sequence}`}
          />
        ) : (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={thumbnail}
            alt={`Scene ${scene.sequence} thumbnail`}
            className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
          />
        )}
        <div className="absolute top-2 right-2">
          <Badge className="bg-gray-900/80 text-white border-gray-700 text-xs">
            Scene {scene.sequence}
          </Badge>
        </div>
      </div>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="text-white font-medium text-sm line-clamp-1">{scene.prompt}</h3>
          <Badge
            className={`text-xs ${statusStyle.color} border flex-shrink-0`}
            aria-label={`Scene status: ${statusStyle.label}`}
          >
            {statusStyle.label}
          </Badge>
        </div>
        <p className="text-gray-400 text-xs mb-3 line-clamp-2">{scene.negativePrompt || 'No negative prompt'}</p>

        {/* Regeneration controls - only show for completed or failed scenes */}
        {(scene.status === 'completed' || scene.status === 'failed') && scene.sequence && (
          <div className="flex gap-2 mt-2" role="group" aria-label="Regeneration controls">
            {onRegenerateImage && (
              <Button
                size="sm"
                variant="outline"
                className="text-xs border-gray-600 hover:bg-gray-700"
                onClick={() => onRegenerateImage(scene.sequence!)}
                aria-label={`Regenerate video for scene ${scene.sequence}`}
              >
                Regen Video
              </Button>
            )}
            {onRegenerateVideo && scene.status === 'completed' && (
              <Button
                size="sm"
                variant="outline"
                className="text-xs border-gray-600 hover:bg-gray-700"
                onClick={() => onRegenerateVideo(scene.sequence!)}
                aria-label={`Regenerate video for scene ${scene.sequence}`}
              >
                Regen Video
              </Button>
            )}
            {onAddLipsync && scene.status === 'completed' && hasVideo && (
              <Button
                size="sm"
                variant="outline"
                className="text-xs border-blue-600 hover:bg-blue-700 text-blue-400"
                onClick={() => onAddLipsync(scene.sequence!)}
                aria-label={`Add lipsync to scene ${scene.sequence}`}
              >
                Add Lipsync
              </Button>
            )}
            {onRegenerateLipsync && scene.status === 'completed' && (
              <Button
                size="sm"
                variant="outline"
                className="text-xs border-gray-600 hover:bg-gray-700"
                onClick={() => onRegenerateLipsync(scene.sequence!)}
                aria-label={`Regenerate lipsync for scene ${scene.sequence}`}
              >
                Regen Lipsync
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function VideoPlayerSection({
  videoUrl,
  projectTitle,
  projectId,
  metadata
}: {
  videoUrl?: string
  projectTitle: string
  projectId: string
  metadata?: {
    duration: number
    fileSize: number
    resolution: string
    format: string
  }
}) {
  if (!videoUrl) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-6">
          <Film className="w-5 h-5 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Final Video</h2>
        </div>
        <div className="aspect-video bg-gray-900/50 rounded-lg border border-gray-700 flex items-center justify-center">
          <div className="text-center space-y-2">
            <Film className="w-12 h-12 text-gray-600 mx-auto" />
            <p className="text-gray-400 text-sm">Video is being generated...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <FinalVideoPlayer
      src={videoUrl}
      metadata={{
        title: projectTitle,
        description: `AI-generated video for project: ${projectId}`,
        duration: metadata?.duration || 0,
        fileSize: metadata?.fileSize,
        resolution: metadata?.resolution,
        format: metadata?.format || 'mp4'
      }}
      showDownload={true}
      showShare={true}
      showMetadata={true}
    />
  )
}

export function ProjectPageClient({ projectId }: { projectId: string }) {
  const { toast } = useToast()
  const { project, loading, error, refetch, isPolling, setOptimisticProject } = useProjectPolling(projectId)

  // Lipsync modal state
  const [lipsyncModalOpen, setLipsyncModalOpen] = useState(false)
  const [lipsyncSceneSequence, setLipsyncSceneSequence] = useState<number | null>(null)
  const [isLipsyncProcessing, setIsLipsyncProcessing] = useState(false)

  // Calculate phases based on project status
  const phases = useMemo(() => {
    return project ? getPhases(project.status) : []
  }, [project])

  // Project title
  const projectTitle = useMemo(() => {
    if (!project) return ''
    return project.conceptPrompt.slice(0, 60) + (project.conceptPrompt.length > 60 ? '...' : '')
  }, [project])

  // Handle start generation
  const handleStartGeneration = useCallback(async () => {
    if (!project) return

    try {
      toast({
        title: 'Starting Generation',
        description: 'Your project generation has been queued.',
      })

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      if (API_KEY) {
        headers['X-API-Key'] = API_KEY
      }

      const response = await fetch(`${API_URL}/api/mv/projects/${projectId}/generate`, {
        method: 'POST',
        headers,
      })

      if (!response.ok) {
        const data = await response.json()
        const errorMessage = data.detail?.message || data.error || data.message || 'Failed to start generation'
        throw new Error(errorMessage)
      }

      // The response contains the updated project with "processing" status
      // Parse the response
      const updatedProject = await response.json()

      // Optimistically update UI immediately with response data
      // This gives instant feedback without waiting for polling
      if (updatedProject && updatedProject.projectId) {
        // Add frontend-only fields
        const optimisticProject = {
          ...updatedProject,
          mode: project?.mode || 'music-video',
          progress: Math.round((updatedProject.completedScenes / Math.max(updatedProject.sceneCount, 1)) * 100),
        }
        setOptimisticProject(optimisticProject)
      }

      toast({
        title: 'Generation Started',
        description: 'Your project is now being generated.',
      })
    } catch (err) {
      toast({
        title: 'Generation Failed',
        description: err instanceof Error ? err.message : 'Failed to start generation',
        variant: 'destructive',
      })
    }
  }, [project, projectId, setOptimisticProject, toast])

  // Handle scene regeneration
  const handleRegenerateImage = useCallback(async (sceneId: number) => {
    try {
      toast({
        title: 'Regenerating Video',
        description: `Regenerating video for scene ${sceneId}...`,
      })

      const response = await fetch(
        `/api/projects/${projectId}/scenes/${sceneId}/regenerate-video`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to regenerate video')
      }

      toast({
        title: 'Regeneration Started',
        description: `Video regeneration for scene ${sceneId} has started.`,
      })

      await refetch()
    } catch (err) {
      toast({
        title: 'Regeneration Failed',
        description: err instanceof Error ? err.message : 'Failed to regenerate video',
        variant: 'destructive',
      })
    }
  }, [projectId, refetch, toast])

  const handleRegenerateVideo = useCallback(async (sceneId: number) => {
    try {
      toast({
        title: 'Regenerating Video',
        description: `Regenerating video for scene ${sceneId}...`,
      })

      const response = await fetch(
        `/api/projects/${projectId}/scenes/${sceneId}/regenerate-video`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to regenerate video')
      }

      toast({
        title: 'Regeneration Started',
        description: `Video regeneration for scene ${sceneId} has started.`,
      })

      await refetch()
    } catch (err) {
      toast({
        title: 'Regeneration Failed',
        description: err instanceof Error ? err.message : 'Failed to regenerate video',
        variant: 'destructive',
      })
    }
  }, [projectId, refetch, toast])

  const handleRegenerateLipsync = useCallback(async (sceneId: number) => {
    try {
      toast({
        title: 'Regenerating Lipsync',
        description: `Regenerating lipsync for scene ${sceneId}...`,
      })

      const response = await fetch(
        `/api/projects/${projectId}/scenes/${sceneId}/regenerate-lipsync`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to regenerate lipsync')
      }

      toast({
        title: 'Regeneration Started',
        description: `Lipsync regeneration for scene ${sceneId} has started.`,
      })

      await refetch()
    } catch (err) {
      toast({
        title: 'Regeneration Failed',
        description: err instanceof Error ? err.message : 'Failed to regenerate lipsync',
        variant: 'destructive',
      })
    }
  }, [projectId, refetch, toast])

  // Handle add lipsync request
  const handleAddLipsync = useCallback((sequence: number) => {
    setLipsyncSceneSequence(sequence)
    setLipsyncModalOpen(true)
  }, [])

  // Handle lipsync modal submit
  const handleLipsyncSubmit = useCallback(async (options: LipsyncOptions) => {
    if (lipsyncSceneSequence === null) return

    try {
      setIsLipsyncProcessing(true)

      toast({
        title: 'Adding Lipsync',
        description: `Adding lipsync to scene ${lipsyncSceneSequence}...`,
      })

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      if (API_KEY) {
        headers['X-API-Key'] = API_KEY
      }

      const response = await fetch(
        `${API_URL}/api/mv/projects/${projectId}/lipsync/${lipsyncSceneSequence}`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify(options)
        }
      )

      if (!response.ok) {
        const data = await response.json()
        const errorMessage = data.detail?.message || data.error || data.message || 'Failed to add lipsync'
        throw new Error(errorMessage)
      }

      toast({
        title: 'Lipsync Added',
        description: `Lipsync successfully added to scene ${lipsyncSceneSequence}.`,
      })

      // Close modal
      setLipsyncModalOpen(false)
      setLipsyncSceneSequence(null)

      // Refetch project to update UI
      await refetch()
    } catch (err) {
      console.error('Lipsync error:', err)
      toast({
        title: 'Lipsync Failed',
        description: err instanceof Error ? err.message : 'Failed to add lipsync',
        variant: 'destructive',
      })
    } finally {
      setIsLipsyncProcessing(false)
    }
  }, [projectId, lipsyncSceneSequence, refetch, toast])

  // Error state
  if (error && !project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-white">Error Loading Project</h1>
          <p className="text-gray-400">{error}</p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => refetch()} variant="outline">
              Try Again
            </Button>
            <Link href="/">
              <Button>Go Back Home</Button>
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Loading state (initial load)
  if (loading && !project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-gray-400">Loading project...</p>
        </div>
      </div>
    )
  }

  // Not found state
  if (!project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-white">Project Not Found</h1>
          <p className="text-gray-400">The project you are looking for does not exist.</p>
          <Link href="/">
            <Button>Go Back Home</Button>
          </Link>
        </div>
      </div>
    )
  }

  // Determine what to show based on status
  const showPhaseTracker = project.status === 'processing'
  const showScenes = project.scenes && project.scenes.length > 0
  const showAssets = project.scenes && project.scenes.some(s => s.originalVideoClipUrl || s.videoClipUrl || s.status === 'completed')
  const showFinalVideo = project.status === 'completed' || project.finalOutputUrl

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header
        className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50"
        role="banner"
      >
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-blue-400">
                <Video className="w-8 h-8" aria-hidden="true" />
                <h1 className="text-xl font-bold text-white">AI Video Generator</h1>
              </div>
            </div>
            <nav className="flex items-center gap-3" aria-label="Project navigation">
              {isPolling && (
                <span
                  className="text-xs text-gray-400 flex items-center gap-2"
                  role="status"
                  aria-live="polite"
                  aria-label="Real-time updates active"
                >
                  <span className="animate-pulse w-2 h-2 bg-blue-500 rounded-full" aria-hidden="true" />
                  Live
                </span>
              )}
              <Link href="/">
                <Button
                  variant="outline"
                  className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
                  aria-label="Go back to home page"
                >
                  <ChevronLeft className="w-4 h-4 mr-2" aria-hidden="true" />
                  Back
                </Button>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 space-y-8" role="main">
        {/* Project Header */}
        <ProjectHeader
          title={projectTitle}
          status={project.status}
          createdAt={project.createdAt}
          onStartGeneration={handleStartGeneration}
          isGenerating={loading}
        />

        {/* Phase Tracker - Only show during generation */}
        {showPhaseTracker && <PhaseTracker phases={phases} />}

        {/* Scenes Section */}
        {showScenes && (
          <section aria-labelledby="scenes-heading">
            <h2 id="scenes-heading" className="text-2xl font-semibold text-white mb-6">
              Scenes ({project.completedScenes}/{project.scenes.length})
            </h2>
            <div
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              role="list"
              aria-label="Project scenes"
            >
              {project.scenes.map((scene) => (
                <SceneCard
                  key={scene.sequence}
                  scene={scene}
                  onRegenerateImage={handleRegenerateImage}
                  onRegenerateVideo={handleRegenerateVideo}
                  onRegenerateLipsync={handleRegenerateLipsync}
                  onAddLipsync={handleAddLipsync}
                />
              ))}
            </div>
          </section>
        )}

        {/* Assets Gallery - Show when we have completed scenes */}
        {showAssets && (
          <AssetGallery
            scenes={project.scenes}
            characterReferenceImageId={project.characterImageUrl}
          />
        )}

        {/* Final Video - Show when project is complete or video is available */}
        {showFinalVideo && (
          <VideoPlayerSection
            videoUrl={project.finalOutputUrl || undefined}
            projectTitle={projectTitle}
            projectId={project.projectId}
            metadata={undefined}
          />
        )}
      </main>

      {/* Lipsync Options Modal */}
      {lipsyncSceneSequence !== null && (
        <LipsyncOptionsModal
          isOpen={lipsyncModalOpen}
          onClose={() => {
            setLipsyncModalOpen(false)
            setLipsyncSceneSequence(null)
          }}
          onSubmit={handleLipsyncSubmit}
          sceneSequence={lipsyncSceneSequence}
          isLoading={isLipsyncProcessing}
        />
      )}
    </div>
  )
}
