"use client"

import { useState, useEffect, useRef } from "react"
import { Loader2, RefreshCw, AlertCircle, Play, Film, Mic } from "lucide-react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import type { ProjectScene } from "@/types/project"

/**
 * Scene generation status
 */
export type SceneGenerationStatus =
  | 'pending'
  | 'generating-image'
  | 'generating-video'
  | 'generating-lipsync'
  | 'completed'
  | 'error'

/**
 * Scene generation step for progress tracking
 */
export interface GenerationStep {
  /** Current step name */
  step: 'image' | 'video' | 'lipsync' | 'complete'
  /** Progress percentage for current step (0-100) */
  progress: number
  /** Optional status message */
  message?: string
}

/**
 * Extended scene data with generation status
 */
export interface SceneWithStatus extends Partial<ProjectScene> {
  /** Scene sequence number */
  sequence: number
  /** Scene prompt/description */
  prompt: string
  /** Current generation status */
  status: SceneGenerationStatus
  /** Current generation step details */
  generationStep?: GenerationStep
  /** Error message if status is 'error' */
  errorMessage?: string
  /** Generated image URL (if available) */
  imageUrl?: string
  /** Generated video URL (if available) */
  videoUrl?: string
  /** Lip-synced video URL (if available) */
  lipSyncUrl?: string
}

export interface ProjectSceneCardProps {
  /** Scene data with generation status */
  scene: SceneWithStatus
  /** Callback when regenerate is requested */
  onRegenerate?: (type: 'image' | 'video' | 'lipsync') => void
  /** Callback when retry is requested after error */
  onRetry?: () => void
  /** Additional CSS classes */
  className?: string
}

/**
 * Custom hook for typewriter animation effect
 */
function useTypewriter(text: string, speed: number = 30, enabled: boolean = true) {
  const [displayedText, setDisplayedText] = useState("")
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(text)
      setIsComplete(true)
      return
    }

    setDisplayedText("")
    setIsComplete(false)
    let currentIndex = 0

    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1))
        currentIndex++
      } else {
        setIsComplete(true)
        clearInterval(interval)
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed, enabled])

  return { displayedText, isComplete }
}

/**
 * Get status badge variant based on scene status
 */
function getStatusBadgeVariant(status: SceneGenerationStatus): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case 'completed':
      return 'default'
    case 'error':
      return 'destructive'
    case 'pending':
      return 'outline'
    default:
      return 'secondary'
  }
}

/**
 * Get status display text
 */
function getStatusText(status: SceneGenerationStatus): string {
  switch (status) {
    case 'pending':
      return 'Pending'
    case 'generating-image':
      return 'Generating Image'
    case 'generating-video':
      return 'Generating Video'
    case 'generating-lipsync':
      return 'Generating Lip-Sync'
    case 'completed':
      return 'Completed'
    case 'error':
      return 'Error'
  }
}

/**
 * ProjectSceneCard component
 *
 * Displays a scene card with generation status, media previews, and regeneration options.
 * Features teletype animation for scene prompts and smooth loading transitions.
 */
export default function ProjectSceneCard({
  scene,
  onRegenerate,
  onRetry,
  className,
}: ProjectSceneCardProps) {
  const [videoPlaying, setVideoPlaying] = useState(false)
  const [lipSyncPlaying, setLipSyncPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const lipSyncRef = useRef<HTMLVideoElement>(null)

  // Typewriter effect for scene prompt
  const { displayedText, isComplete } = useTypewriter(
    scene.prompt,
    30,
    scene.status !== 'pending'
  )

  // Calculate overall progress based on generation step
  const getOverallProgress = (): number => {
    if (!scene.generationStep) return 0

    const stepWeights = {
      image: 33,
      video: 33,
      lipsync: 33,
      complete: 1,
    }

    const stepOffsets = {
      image: 0,
      video: 33,
      lipsync: 66,
      complete: 99,
    }

    const offset = stepOffsets[scene.generationStep.step]
    const weight = stepWeights[scene.generationStep.step]
    const stepProgress = (scene.generationStep.progress / 100) * weight

    return offset + stepProgress
  }

  // Handle video play/pause
  const toggleVideoPlay = () => {
    if (videoRef.current) {
      if (videoPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setVideoPlaying(!videoPlaying)
    }
  }

  const toggleLipSyncPlay = () => {
    if (lipSyncRef.current) {
      if (lipSyncPlaying) {
        lipSyncRef.current.pause()
      } else {
        lipSyncRef.current.play()
      }
      setLipSyncPlaying(!lipSyncPlaying)
    }
  }

  return (
    <Card
      className={cn(
        "overflow-hidden transition-all duration-300 hover:shadow-lg border-blue-900/20 bg-gradient-to-br from-slate-900 to-slate-800",
        className
      )}
    >
      {/* Header */}
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
              <span className="text-blue-400">Scene {scene.sequence}</span>
              <Badge variant={getStatusBadgeVariant(scene.status)} className="ml-2">
                {getStatusText(scene.status)}
              </Badge>
            </CardTitle>
          </div>

          {/* Regenerate Dropdown */}
          {scene.status !== 'pending' && scene.status !== 'error' && onRegenerate && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-blue-700 text-blue-400 hover:bg-blue-950 hover:text-blue-300"
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Regenerate
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 bg-slate-800 border-slate-700">
                <DropdownMenuLabel className="text-slate-400">Regenerate Options</DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-slate-700" />
                <DropdownMenuItem
                  onClick={() => onRegenerate('image')}
                  disabled={!scene.imageUrl}
                  className="text-white hover:bg-slate-700 focus:bg-slate-700"
                >
                  <Film className="h-4 w-4 mr-2" />
                  Regenerate Image
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onRegenerate('video')}
                  disabled={!scene.videoClipUrl}
                  className="text-white hover:bg-slate-700 focus:bg-slate-700"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Regenerate Video
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onRegenerate('lipsync')}
                  disabled={!scene.lipSyncUrl}
                  className="text-white hover:bg-slate-700 focus:bg-slate-700"
                >
                  <Mic className="h-4 w-4 mr-2" />
                  Regenerate Lip-Sync
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        {/* Scene Prompt with Teletype Animation */}
        <div className="mt-3">
          <p className="text-sm text-slate-300 leading-relaxed min-h-[3rem]">
            {displayedText}
            {!isComplete && (
              <span className="inline-block w-0.5 h-4 bg-blue-400 ml-0.5 animate-pulse" />
            )}
          </p>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Error Display */}
        {scene.status === 'error' && (
          <div className="p-4 bg-red-950/30 border border-red-900/50 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-red-300">Generation Failed</p>
                {scene.errorMessage && (
                  <p className="text-sm text-red-400 mt-1">{scene.errorMessage}</p>
                )}
                {onRetry && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onRetry}
                    className="mt-3 border-red-700 text-red-400 hover:bg-red-950 hover:text-red-300"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Progress Indicator */}
        {scene.generationStep && scene.status !== 'completed' && scene.status !== 'error' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">
                {scene.generationStep.message || `Generating ${scene.generationStep.step}...`}
              </span>
              <span className="text-blue-400 font-medium">
                {Math.round(getOverallProgress())}%
              </span>
            </div>
            <Progress value={getOverallProgress()} className="h-2 bg-slate-700" />
          </div>
        )}

        {/* Media Previews Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Image Preview */}
          <div className="space-y-2">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Image
            </div>
            <div className="relative aspect-video bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
              {!scene.imageUrl && scene.status === 'pending' && (
                <Skeleton className="w-full h-full" />
              )}
              {!scene.imageUrl && (scene.status === 'generating-image' || scene.status === 'generating-video' || scene.status === 'generating-lipsync') && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
                  <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
                </div>
              )}
              {scene.imageUrl && (
                <img
                  src={scene.imageUrl}
                  alt={`Scene ${scene.sequence}`}
                  className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
                  loading="lazy"
                />
              )}
            </div>
          </div>

          {/* Video Preview */}
          <div className="space-y-2">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Video
            </div>
            <div className="relative aspect-video bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
              {!scene.videoClipUrl && (scene.status === 'pending' || scene.status === 'generating-image') && (
                <Skeleton className="w-full h-full" />
              )}
              {!scene.videoClipUrl && (scene.status === 'generating-video' || scene.status === 'generating-lipsync') && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
                  <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
                </div>
              )}
              {scene.videoClipUrl && (
                <div className="relative w-full h-full group">
                  <video
                    ref={videoRef}
                    src={scene.videoClipUrl}
                    className="w-full h-full object-cover"
                    loop
                    muted
                    playsInline
                    onPlay={() => setVideoPlaying(true)}
                    onPause={() => setVideoPlaying(false)}
                  />
                  <button
                    onClick={toggleVideoPlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    aria-label={videoPlaying ? "Pause video" : "Play video"}
                  >
                    {!videoPlaying && (
                      <Play className="h-12 w-12 text-white drop-shadow-lg" />
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Lip-Sync Video Preview */}
          <div className="space-y-2">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Lip-Sync
            </div>
            <div className="relative aspect-video bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
              {!scene.lipSyncUrl && (scene.status === 'pending' || scene.status === 'generating-image' || scene.status === 'generating-video') && (
                <Skeleton className="w-full h-full" />
              )}
              {!scene.lipSyncUrl && scene.status === 'generating-lipsync' && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
                  <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
                </div>
              )}
              {scene.lipSyncUrl && (
                <div className="relative w-full h-full group">
                  <video
                    ref={lipSyncRef}
                    src={scene.lipSyncUrl}
                    className="w-full h-full object-cover"
                    loop
                    muted
                    playsInline
                    onPlay={() => setLipSyncPlaying(true)}
                    onPause={() => setLipSyncPlaying(false)}
                  />
                  <button
                    onClick={toggleLipSyncPlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    aria-label={lipSyncPlaying ? "Pause lip-sync video" : "Play lip-sync video"}
                  >
                    {!lipSyncPlaying && (
                      <Play className="h-12 w-12 text-white drop-shadow-lg" />
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
