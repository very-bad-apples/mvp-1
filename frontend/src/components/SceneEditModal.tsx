'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { X, Play, Pause, Video, Loader2, Download, Mic, CheckCircle2, AlertCircle, Scissors } from 'lucide-react'
import { ProjectScene } from '@/types/project'
import { cn } from '@/lib/utils'
import { VideoTrimmer } from '@/components/VideoTrimmer'
import { trimScene, downloadSceneVideo, generateLipSync, updateScene, generateSceneVideo } from '@/lib/api/client'
import { formatVideoTime, formatDuration } from '@/lib/utils/time'
import { getSceneVideoUrl } from '@/lib/utils/video'
import { useSceneToast } from '@/hooks/useSceneToast'

interface SceneEditModalProps {
  /** Controls modal visibility */
  open: boolean
  /** Callback when modal state changes */
  onOpenChange: (open: boolean) => void
  /** The scene data to edit */
  scene: ProjectScene
  /** The project ID */
  projectId: string
  /** Callback when scene is updated */
  onSceneUpdate?: (updatedScene: ProjectScene) => void
}

/**
 * SceneEditModal Component
 *
 * A large modal for editing scene details with dark theme styling.
 * Uses a single-pane vertical layout with sections for video preview, prompts, and actions.
 * Supports async operation handling to prevent accidental closes during operations.
 */
export function SceneEditModal({
  open,
  onOpenChange,
  scene,
  projectId,
  onSceneUpdate,
}: SceneEditModalProps) {
  // Track if an async operation is in progress (e.g., saving, regenerating video)
  const [isOperationInProgress, setIsOperationInProgress] = useState(false)

  // Local state for edited prompts
  const [editedPrompt, setEditedPrompt] = useState(scene.prompt || '')
  const [editedNegativePrompt, setEditedNegativePrompt] = useState(scene.negativePrompt || '')

  // Video preview state
  const [isPlaying, setIsPlaying] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)
  const [originalVideoDuration, setOriginalVideoDuration] = useState<number>(0)
  const [trimPoints, setTrimPoints] = useState<{ in: number; out: number }>(
    scene.trimPoints || { in: 0, out: scene.duration || 0 }
  )
  const [isApplyingTrim, setIsApplyingTrim] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const sceneToast = useSceneToast()

  // Lip-sync state
  const [lipSyncStatus, setLipSyncStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  // Save prompts state
  const [isSavingPrompts, setIsSavingPrompts] = useState(false)
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false)

  // Track if prompts have been modified
  const promptsModified =
    editedPrompt !== (scene.prompt || '') ||
    editedNegativePrompt !== (scene.negativePrompt || '')

  // For trimming, ALWAYS use the original video (so users see the full clip)
  // Priority: originalVideoClipUrl first (true original), then videoClipUrl (may be working version)
  const originalVideoUrl = scene.originalVideoClipUrl || scene.videoClipUrl

  // For the toggle: default shows original (for trimming), toggle shows working result
  const currentVideoUrl = showOriginal ? getSceneVideoUrl(scene, false) : originalVideoUrl

  // Sync local state when scene changes
  useEffect(() => {
    setEditedPrompt(scene.prompt || '')
    setEditedNegativePrompt(scene.negativePrompt || '')
    // Don't initialize trim points here - wait for video metadata to load
    // This ensures we use the original video duration, not the trimmed duration
    setShowOriginal(false)
    setIsPlaying(false)
    // Reset any error states when scene changes
    setLipSyncStatus('idle')
    // Reset original video duration
    setOriginalVideoDuration(0)
  }, [scene.sequence, scene.duration, open]) // Re-sync when modal opens

  /**
   * Handle video metadata loaded - sets up trimmer with original video duration
   */
  const handleVideoLoadedMetadata = () => {
    const video = videoRef.current
    if (!video || !video.duration || !isFinite(video.duration)) return

    setOriginalVideoDuration(video.duration)

    // Initialize trim points: use saved points or default to full video
    setTrimPoints(scene.trimPoints || { in: 0, out: video.duration })
  }

  /**
   * Handle video load errors
   */
  const handleVideoError = () => {
    const video = videoRef.current
    if (video?.error) {
      console.error('Video load error:', video.error.message)
    }
  }

  // Use the original video duration for the trimmer (not the trimmed duration)
  // Don't use scene.duration as fallback - it's the TRIMMED duration and will break the trimmer
  const videoDuration = originalVideoDuration

  // Check if scene is actually trimmed (not just default trim points)
  const isTrimmed = scene.trimPoints &&
    originalVideoDuration > 0 &&
    (scene.trimPoints.in > 0 || scene.trimPoints.out < originalVideoDuration)

  /**
   * Handle modal close with operation check
   * Prevents closing if an operation is in progress
   */
  const handleOpenChange = (newOpen: boolean) => {
    // If trying to close but operation in progress, do nothing
    if (!newOpen && isOperationInProgress) {
      return
    }
    onOpenChange(newOpen)
  }

  /**
   * Handle lip-sync generation
   * Generates lip-synced video from scene's video and audio clips
   */
  const handleGenerateLipSync = async () => {
    const videoUrl = scene.originalVideoClipUrl ?? scene.videoClipUrl
    if (!videoUrl || !scene.audioClipUrl) {
      sceneToast.showWarning(
        'Missing Required Media',
        'Both video and audio clips are required for lip-sync generation.'
      )
      return
    }

    setIsOperationInProgress(true)
    setLipSyncStatus('loading')

    sceneToast.showProgress(scene, 'Lip-Sync Generation')

    try {
      // Call the lip-sync API
      await generateLipSync({
        video_url: videoUrl,
        audio_url: scene.audioClipUrl,
      })

      // Success - the backend will update the scene automatically
      setLipSyncStatus('success')
      sceneToast.showSuccess(scene, 'Lip-Sync Generation')

      // Call the callback to trigger a refresh in parent component
      if (onSceneUpdate) {
        onSceneUpdate(scene)
      }

    } catch (error) {
      console.error('Lip-sync generation failed:', error)
      setLipSyncStatus('error')
      sceneToast.showError(scene, 'Lip-Sync Generation', error)
    } finally {
      setIsOperationInProgress(false)
    }
  }

  /**
   * Get badge variant based on scene status
   */
  const getStatusVariant = (status: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
    const statusLower = status.toLowerCase()

    if (statusLower.includes('complete') || statusLower.includes('done')) {
      return 'default' // Blue/primary color
    }
    if (statusLower.includes('fail') || statusLower.includes('error')) {
      return 'destructive' // Red color
    }
    if (statusLower.includes('processing') || statusLower.includes('progress')) {
      return 'secondary' // Gray color
    }
    return 'outline' // Default outline
  }

  /**
   * Video player controls
   */
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  /**
   * Enforce trim boundaries during playback
   */
  useEffect(() => {
    const video = videoRef.current
    if (!video || !scene.trimPoints) return

    const handleTimeUpdate = () => {
      if (video.currentTime < scene.trimPoints!.in) {
        video.currentTime = scene.trimPoints!.in
      } else if (video.currentTime > scene.trimPoints!.out) {
        video.currentTime = scene.trimPoints!.in
        video.pause()
        setIsPlaying(false)
      }
    }

    const handleSeeking = () => {
      if (video.currentTime < scene.trimPoints!.in) {
        video.currentTime = scene.trimPoints!.in
      } else if (video.currentTime > scene.trimPoints!.out) {
        video.currentTime = scene.trimPoints!.out
      }
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('seeking', handleSeeking)

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('seeking', handleSeeking)
    }
  }, [scene.trimPoints])

  /**
   * Apply trim points by calling the API
   */
  const handleApplyTrim = async () => {
    setIsApplyingTrim(true)
    setIsOperationInProgress(true)

    try {
      await trimScene(projectId, scene.sequence, trimPoints)
      sceneToast.showSuccess(scene, 'Trim Application')

      // Call the callback to trigger a refresh in parent component
      if (onSceneUpdate) {
        onSceneUpdate(scene)
      }
    } catch (error) {
      console.error('Failed to apply trim:', error)
      sceneToast.showError(scene, 'Trim Application', error)
    } finally {
      setIsApplyingTrim(false)
      setIsOperationInProgress(false)
    }
  }

  /**
   * Save edited prompts and trigger video regeneration
   */
  const handleSavePrompts = async () => {
    if (!promptsModified) return

    setIsSavingPrompts(true)
    setIsOperationInProgress(true)

    try {
      // Step 1: Update prompts in database
      await updateScene(projectId, scene.sequence, {
        prompt: editedPrompt,
        negativePrompt: editedNegativePrompt,
      })

      sceneToast.showSuccess(scene, 'Prompt Update')

      // Step 2: Trigger video regeneration with updated prompts
      setIsGeneratingVideo(true)
      sceneToast.showProgress(scene, 'Video Regeneration')

      try {
        await generateSceneVideo(projectId, scene.sequence, 'replicate')
        sceneToast.showSuccess(scene, 'Video Regeneration')
      } catch (videoError) {
        console.error('Failed to regenerate video:', videoError)
        sceneToast.showError(scene, 'Video Regeneration', videoError)
        // Don't fail the whole operation - prompts were saved successfully
      } finally {
        setIsGeneratingVideo(false)
      }

      // Call the callback to trigger a refresh in parent component
      if (onSceneUpdate) {
        onSceneUpdate({
          ...scene,
          prompt: editedPrompt,
          negativePrompt: editedNegativePrompt,
        })
      }
    } catch (error) {
      console.error('Failed to save prompts:', error)
      sceneToast.showError(scene, 'Prompt Update', error)
    } finally {
      setIsSavingPrompts(false)
      setIsOperationInProgress(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {/* Custom DialogContent with max-w-4xl and max-h-[90vh] */}
      <DialogContent
        className={cn(
          "max-w-4xl max-h-[90vh] flex flex-col p-0 gap-0",
          "bg-card text-card-foreground border-border",
          // Prevent backdrop click when operation in progress
          isOperationInProgress && "pointer-events-auto"
        )}
        // Prevent escape key from closing during operations
        onEscapeKeyDown={(e) => {
          if (isOperationInProgress) {
            e.preventDefault()
          }
        }}
        // Prevent pointer down outside from closing during operations
        onPointerDownOutside={(e) => {
          if (isOperationInProgress) {
            e.preventDefault()
          }
        }}
        // Prevent interact outside from closing during operations
        onInteractOutside={(e) => {
          if (isOperationInProgress) {
            e.preventDefault()
          }
        }}
      >
        {/* Header - Fixed at top */}
        <DialogHeader className="px-6 py-4 border-b border-border shrink-0">
          <DialogTitle className="text-xl font-semibold">
            Edit Scene {scene.sequence}
          </DialogTitle>
        </DialogHeader>

        {/* Scrollable Content Area - Grows to fill available space */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">

          {/* Video Preview & Trimmer Section */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Video Preview & Editing
            </h3>
            <div className="border border-border rounded-lg p-6 bg-muted/20 space-y-4">
              {currentVideoUrl ? (
                <>
                  {/* Header with status and toggle */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Video className="h-4 w-4 text-cyan-500" />
                      <span className="text-sm font-medium">
                        {showOriginal ? 'Working Video (Preview)' : 'Original Video (Trimming)'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getStatusVariant(scene.status)} className="text-xs">
                        {scene.status}
                      </Badge>
                      {isTrimmed && (
                        <Badge variant="outline" className="text-xs bg-cyan-500/10 border-cyan-500/30 text-cyan-400">
                          <Scissors className="h-3 w-3 mr-1" />
                          Trimmed
                        </Badge>
                      )}
                      {(scene.workingVideoClipUrl || scene.lipSyncedVideoClipUrl) && scene.videoClipUrl && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowOriginal(!showOriginal)}
                          className="text-xs"
                        >
                          {showOriginal ? 'Show Original' : 'Preview Result'}
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Full-width Video Container */}
                  <div className="relative bg-black rounded-lg overflow-hidden w-full" style={{ aspectRatio: '16/9' }}>
                    <video
                      ref={videoRef}
                      src={currentVideoUrl}
                      className="w-full h-full object-contain"
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => setIsPlaying(false)}
                      onLoadedMetadata={handleVideoLoadedMetadata}
                      onError={handleVideoError}
                    />

                    {/* Play/Pause Overlay */}
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black/30">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-16 w-16 rounded-full bg-black/50 hover:bg-black/70"
                        onClick={togglePlayPause}
                      >
                        {isPlaying ? (
                          <Pause className="h-8 w-8 text-white" />
                        ) : (
                          <Play className="h-8 w-8 text-white" />
                        )}
                      </Button>
                    </div>

                    {/* Trim indicator overlay - only show when previewing working video */}
                    {isTrimmed && showOriginal && (
                      <div className="absolute top-2 left-2 bg-cyan-500/90 text-white text-xs px-2 py-1 rounded">
                        Trimmed: {formatVideoTime(scene.trimPoints!.in)} - {formatVideoTime(scene.trimPoints!.out)}
                      </div>
                    )}
                  </div>

                  {/* Video Controls */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Duration: {formatVideoTime(videoDuration)}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={togglePlayPause}
                      className="text-xs"
                    >
                      {isPlaying ? 'Pause' : 'Play'}
                    </Button>
                  </div>

                  {/* Video Trimmer */}
                  <div className="space-y-3 pt-4 border-t border-border">
                    {videoDuration > 0 ? (
                      <>
                        <VideoTrimmer
                          key={`trimmer-${scene.sequence}-${open}`} // Force re-mount when scene/modal changes
                          videoDuration={videoDuration}
                          initialTrimPoints={trimPoints}
                          onTrimPointsChange={setTrimPoints}
                          videoUrl={currentVideoUrl}
                        />

                        {/* Apply Trim Button */}
                        <div className="flex items-center justify-end gap-3">
                          <p className="text-xs text-muted-foreground">
                            Trim points: {formatVideoTime(trimPoints.in)} - {formatVideoTime(trimPoints.out)}
                          </p>
                          <Button
                            onClick={handleApplyTrim}
                            disabled={isApplyingTrim || isOperationInProgress}
                            size="sm"
                            className="bg-cyan-600 hover:bg-cyan-700"
                          >
                            {isApplyingTrim && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {isApplyingTrim ? 'Applying...' : 'Apply Trim Points'}
                          </Button>
                        </div>
                      </>
                    ) : (
                      <div className="flex items-center justify-center py-8 text-muted-foreground">
                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                        <span className="text-sm">Loading video metadata...</span>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground space-y-2">
                  <Video className="h-12 w-12 opacity-50" />
                  <p className="text-sm">No video available for this scene</p>
                  <p className="text-xs">Generate video to see preview</p>
                </div>
              )}
            </div>
          </div>

          {/* Prompts Section */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Prompts
            </h3>
            <div className="border border-border rounded-lg p-6 bg-muted/20 space-y-6">
              {/* Scene Prompt */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="scene-prompt" className="text-sm font-medium">
                    Scene Prompt
                  </Label>
                  <span className={cn(
                    "text-xs",
                    editedPrompt.length > 450 ? "text-destructive" : "text-muted-foreground"
                  )}>
                    {editedPrompt.length} / 500 characters
                  </span>
                </div>
                <Textarea
                  id="scene-prompt"
                  value={editedPrompt}
                  onChange={(e) => setEditedPrompt(e.target.value)}
                  placeholder="Enter scene description, visual details, camera angles, lighting, mood..."
                  className="min-h-[120px] resize-none"
                  maxLength={500}
                  aria-describedby="scene-prompt-help"
                />
                <p id="scene-prompt-help" className="text-xs text-muted-foreground">
                  Saving will update the prompt and automatically regenerate the video
                </p>
              </div>

              {/* Negative Prompt */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="negative-prompt" className="text-sm font-medium">
                    Negative Prompt
                  </Label>
                  <span className={cn(
                    "text-xs",
                    editedNegativePrompt.length > 450 ? "text-destructive" : "text-muted-foreground"
                  )}>
                    {editedNegativePrompt.length} / 500 characters
                  </span>
                </div>
                <Textarea
                  id="negative-prompt"
                  value={editedNegativePrompt}
                  onChange={(e) => setEditedNegativePrompt(e.target.value)}
                  placeholder="Enter elements to avoid in the scene (e.g., blur, distortion, low quality)..."
                  className="min-h-[100px] resize-none"
                  maxLength={500}
                  aria-describedby="negative-prompt-help"
                />
                <p id="negative-prompt-help" className="text-xs text-muted-foreground">
                  Saving will update the negative prompt and automatically regenerate the video
                </p>
              </div>

              {/* Save Prompts Button */}
              <div className="flex items-center justify-end gap-3 pt-2">
                {promptsModified && (
                  <p className="text-xs text-amber-500">Unsaved changes</p>
                )}
                <Button
                  onClick={handleSavePrompts}
                  disabled={!promptsModified || isSavingPrompts || isGeneratingVideo || isOperationInProgress}
                  size="sm"
                  className="bg-cyan-600 hover:bg-cyan-700"
                >
                  {(isSavingPrompts || isGeneratingVideo) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {isSavingPrompts ? 'Saving...' : isGeneratingVideo ? 'Regenerating Video...' : 'Save Prompts'}
                </Button>
              </div>
            </div>
          </div>

          {/* Actions Section */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Actions
            </h3>
            <div className="border border-border rounded-lg p-6 bg-muted/20">
              <div className="flex flex-wrap gap-3">
                {/* Generate Lip-Sync Button */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        onClick={handleGenerateLipSync}
                        disabled={
                          !scene.needsLipSync ||
                          !scene.audioClipUrl ||
                          !!scene.lipSyncedVideoClipUrl ||
                          lipSyncStatus === 'loading'
                        }
                        variant={lipSyncStatus === 'success' ? 'default' : lipSyncStatus === 'error' ? 'destructive' : 'outline'}
                        size="default"
                        className={cn(
                          "min-w-[180px]",
                          lipSyncStatus === 'loading' && "cursor-not-allowed"
                        )}
                      >
                        {lipSyncStatus === 'loading' ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Generating...
                          </>
                        ) : lipSyncStatus === 'success' ? (
                          <>
                            <CheckCircle2 className="h-4 w-4 mr-2" />
                            Lip-Sync Complete
                          </>
                        ) : lipSyncStatus === 'error' ? (
                          <>
                            <AlertCircle className="h-4 w-4 mr-2" />
                            Retry Lip-Sync
                          </>
                        ) : (
                          <>
                            <Mic className="h-4 w-4 mr-2" />
                            Generate Lip-Sync
                          </>
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {!scene.needsLipSync ? (
                        <p>Lip-sync is not needed for this scene</p>
                      ) : !scene.audioClipUrl ? (
                        <p>Audio clip required for lip-sync generation</p>
                      ) : scene.lipSyncedVideoClipUrl ? (
                        <p>Lip-sync already generated for this scene</p>
                      ) : lipSyncStatus === 'loading' ? (
                        <p>Generating lip-synced video... Please wait</p>
                      ) : (
                        <p>Generate lip-synced video from audio and video clips</p>
                      )}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                {/* Download Scene Button */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        onClick={() => {
                          try {
                            const videoUrl = getSceneVideoUrl(scene)

                            if (!videoUrl) {
                              sceneToast.showWarning(
                                "No video available",
                                "This scene doesn't have a video to download yet."
                              )
                              return
                            }

                            downloadSceneVideo(videoUrl, scene.sequence, projectId)
                            sceneToast.showSuccess(scene, 'Download Started')
                          } catch (error) {
                            console.error('Download error:', error)
                            sceneToast.showError(scene, 'Download', error)
                          }
                        }}
                        disabled={!scene.workingVideoClipUrl && !scene.lipSyncedVideoClipUrl && !scene.originalVideoClipUrl && !scene.videoClipUrl}
                        variant="outline"
                        size="default"
                        className="min-w-[180px]"
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Download Video
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {!scene.workingVideoClipUrl && !scene.lipSyncedVideoClipUrl && !scene.originalVideoClipUrl && !scene.videoClipUrl ? (
                        <p>No video available for this scene</p>
                      ) : (
                        <p>Download scene video to your device</p>
                      )}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>
          </div>

        </div>

        {/* Footer - Fixed at bottom */}
        <DialogFooter className="px-6 py-4 border-t border-border shrink-0 flex-row justify-between items-center">
          <div className="flex items-center gap-3">
            {/* Scene Status Badge */}
            <Badge variant={getStatusVariant(scene.status)}>
              {scene.status}
            </Badge>

            {/* Retry count if applicable */}
            {scene.retryCount > 0 && (
              <span className="text-xs text-muted-foreground">
                Retries: {scene.retryCount}
              </span>
            )}
          </div>

          {/* Scene Duration */}
          <div className="text-sm text-muted-foreground">
            Duration: {formatDuration(scene.duration)}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
