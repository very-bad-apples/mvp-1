'use client'

import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Video, ChevronLeft, Loader2, Download } from 'lucide-react'
import { VideoPreview } from '@/components/timeline/VideoPreview'
import { ScenesPanel } from '@/components/ScenesPanel'
import { useProjectPolling } from '@/hooks/useProjectPolling'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { generateScenes, composeVideo } from '@/lib/api/client'
import { useToast } from '@/hooks/useToast'
import { SceneGenerationOverlay } from '@/components/SceneGenerationOverlay'
import { startFullGeneration } from '@/lib/orchestration'

export default function EditPage({ params }: { params: { id: string } }) {
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isGeneratingScenes, setIsGeneratingScenes] = useState(false)
  const [showOverlay, setShowOverlay] = useState(false)
  const [isComposing, setIsComposing] = useState(false)
  const [compositionJobId, setCompositionJobId] = useState<string | null>(null)
  const [audioVolume, setAudioVolume] = useState(1)
  const [audioMuted, setAudioMuted] = useState(false)
  const sceneGenerationTriggered = useRef(false)
  const overlayDismissed = useRef(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  const lastAutoSelectedSceneRef = useRef<string | null>(null)
  const { toast } = useToast()

  // Fetch project data using the API client hook
  const { project, loading, error, refetch, isPolling } = useProjectPolling(params.id)

  // Calculate total duration from scenes
  const duration = useMemo(() => {
    if (!project?.scenes || project.scenes.length === 0) {
      return 180 // Default 3 minutes if no scenes yet
    }
    // Sum up all scene durations
    return project.scenes.reduce((total, scene) => total + (scene.duration || 0), 0)
  }, [project?.scenes])

  // Check if all SCENE TEXTS are generated (not videos)
  // This is used for the scene generation overlay only
  const allSceneTextsGenerated = useMemo(() => {
    if (!project?.scenes || project.scenes.length === 0) return false
    return project.scenes.every(scene => scene.prompt && scene.prompt.length > 0)
  }, [project?.scenes])

  // Check if all VIDEOS are complete (for export functionality)
  const allVideosComplete = useMemo(() => {
    if (!project?.scenes || project.scenes.length === 0) return false
    return project.scenes.every(scene => scene.videoClipUrl !== null && scene.videoClipUrl !== undefined)
  }, [project?.scenes])

  // Auto-select the currently playing scene based on currentTime
  useEffect(() => {
    if (!project?.scenes) return

    // Get scenes with videos, sorted by sequence
    const scenesWithVideos = project.scenes
      .filter(scene => scene.videoClipUrl)
      .sort((a, b) => a.sequence - b.sequence)

    if (scenesWithVideos.length === 0) return

    // Find the scene that should be playing at current time
    let targetSceneId: string | null = null
    let accumulatedTime = 0

    for (const scene of scenesWithVideos) {
      const sceneDuration = scene.duration || 0
      if (currentTime >= accumulatedTime && currentTime < accumulatedTime + sceneDuration) {
        targetSceneId = `scene-${scene.sequence}`
        break
      }
      accumulatedTime += sceneDuration
    }

    // If we're beyond all scenes, select the last scene
    if (!targetSceneId && currentTime >= accumulatedTime && scenesWithVideos.length > 0) {
      const lastScene = scenesWithVideos[scenesWithVideos.length - 1]
      targetSceneId = `scene-${lastScene.sequence}`
    }

    // Only update if the target scene changed
    if (targetSceneId && targetSceneId !== lastAutoSelectedSceneRef.current) {
      lastAutoSelectedSceneRef.current = targetSceneId
      setSelectedSceneId(targetSceneId)
    }
  }, [currentTime, project?.scenes])

  // Get the selected scene object from the ID
  const selectedScene = useMemo(() => {
    if (!selectedSceneId || !project?.scenes) return null
    const sequence = parseInt(selectedSceneId.replace('scene-', ''))
    return project.scenes.find(scene => scene.sequence === sequence) || null
  }, [selectedSceneId, project?.scenes])

  // Handle scene selection - jump to scene's start time in timeline
  const handleSceneSelect = (sceneId: string | null) => {
    if (!sceneId || !project?.scenes) {
      return
    }

    // Reset auto-selection tracking when user manually selects
    lastAutoSelectedSceneRef.current = null

    // Parse scene sequence from ID
    const sequence = parseInt(sceneId.replace('scene-', ''))

    // Get all scenes with videos, sorted by sequence
    const scenesWithVideos = project.scenes
      .filter(scene => scene.videoClipUrl)
      .sort((a, b) => a.sequence - b.sequence)

    // Find the clicked scene in the sorted list
    const sceneIndex = scenesWithVideos.findIndex(scene => scene.sequence === sequence)
    if (sceneIndex === -1) {
      console.warn(`Scene ${sequence} not found or has no video`)
      return
    }

    // Calculate the scene's start time in the global timeline
    const startTime = scenesWithVideos
      .slice(0, sceneIndex)
      .reduce((total, scene) => total + (scene.duration || 0), 0)

    // Jump to the scene's start time (auto-selection will update the detail panel)
    setCurrentTime(startTime)
    setIsPlaying(true) // Auto-play when jumping to a scene
  }

  // Handle overlay visibility - show only for new projects that haven't dismissed it
  useEffect(() => {
    if (project && project.scenes.length > 0 && !overlayDismissed.current && isGeneratingScenes) {
      setShowOverlay(true)
    }
  }, [project, isGeneratingScenes])

  // Auto-trigger scene generation and video generation
  useEffect(() => {
    const triggerGeneration = async () => {
      if (!project || loading || sceneGenerationTriggered.current) {
        return
      }

      // Case 1: Project has no scenes - generate scenes first, then videos
      if (project.scenes.length === 0 && !isGeneratingScenes) {
        sceneGenerationTriggered.current = true
        setIsGeneratingScenes(true)

        toast({
          title: "Generating Scenes",
          description: "Creating scene descriptions for your project...",
        })

        try {
          // Use productDescription for ad-creative mode, characterDescription for music-video mode
          const description = project.mode === 'ad-creative'
            ? project.productDescription
            : project.characterDescription

          if (!description) {
            throw new Error(`Missing ${project.mode === 'ad-creative' ? 'product' : 'character'} description`)
          }

          await generateScenes({
            idea: project.conceptPrompt,
            character_description: description,
            config_flavor: 'default',
            project_id: params.id,
          })

          toast({
            title: "Scenes Generated!",
            description: "Scene descriptions have been created.",
          })

          // Refresh project data to get the new scenes
          await refetch()

          // Show overlay now that we have scenes
          setShowOverlay(true)
          setIsGeneratingScenes(false)

          // Start video generation in the BACKGROUND
          toast({
            title: "Starting Video Generation",
            description: "Videos will generate in the background.",
          })

          startFullGeneration(params.id, {
            onProgress: (phase, sceneIndex, total, message) => {
              console.log(`[Generation] ${phase}: ${sceneIndex}/${total}`, message)
            },
            onError: (phase, sceneIndex, error) => {
              console.error(`[Generation Error] ${phase}:`, error)
              toast({
                title: "Generation Error",
                description: `Failed during ${phase} phase: ${error.message}`,
                variant: "destructive",
              })
            },
          }).catch((err) => {
            console.error('Background generation error:', err)
            toast({
              title: "Video Generation Failed",
              description: err instanceof Error ? err.message : "Failed to generate videos",
              variant: "destructive",
            })
          })

        } catch (err) {
          console.error('Scene generation error:', err)
          toast({
            title: "Scene Generation Failed",
            description: err instanceof Error ? err.message : "Failed to generate scenes",
            variant: "destructive",
          })
          sceneGenerationTriggered.current = false
          setIsGeneratingScenes(false)
        }
        return
      }

      // Case 2: Project has scenes but some/all are missing videos - trigger video generation only
      const scenesWithoutVideos = project.scenes.filter(scene => !scene.videoClipUrl)
      if (scenesWithoutVideos.length > 0 && !isGeneratingScenes) {
        sceneGenerationTriggered.current = true

        console.log(`[Editor] Detected ${scenesWithoutVideos.length} scenes without videos, triggering generation`)

        toast({
          title: "Generating Missing Videos",
          description: `Starting video generation for ${scenesWithoutVideos.length} scenes...`,
        })

        // Start video generation in the BACKGROUND (non-blocking)
        startFullGeneration(params.id, {
          onProgress: (phase, sceneIndex, total, message) => {
            console.log(`[Generation] ${phase}: ${sceneIndex}/${total}`, message)
          },
          onError: (phase, sceneIndex, error) => {
            console.error(`[Generation Error] ${phase}:`, error)
            toast({
              title: "Generation Error",
              description: `Failed during ${phase} phase: ${error.message}`,
              variant: "destructive",
            })
          },
        }).catch((err) => {
          console.error('Background generation error:', err)
          toast({
            title: "Video Generation Failed",
            description: err instanceof Error ? err.message : "Failed to generate videos",
            variant: "destructive",
          })
        })
      }
    }

    triggerGeneration()
  }, [project, loading, isGeneratingScenes, params.id, refetch, toast])

  // Poll for composition completion
  useEffect(() => {
    if (!isComposing || !compositionJobId) return

    // Check if already complete (in case of re-render)
    if (project?.finalOutputUrl) {
      setIsComposing(false)
      return
    }

    // Set up polling interval to check for completion
    const pollInterval = setInterval(async () => {
      // Trigger a refetch to get latest project data
      await refetch()

      // Note: The check for finalOutputUrl happens in a separate effect
      // that watches the project state, to avoid including project in deps here
    }, 3000) // Poll every 3 seconds

    return () => {
      clearInterval(pollInterval)
    }
  }, [isComposing, compositionJobId, refetch])

  // Separate effect to detect composition completion
  useEffect(() => {
    if (isComposing && project?.finalOutputUrl) {
      setIsComposing(false)
      toast({
        title: "Video Composition Complete!",
        description: "Your final video is ready. You can download it.",
      })
    }
  }, [project?.finalOutputUrl, isComposing, toast])

  // Load audio backing track when project is available
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !project?.audioBackingTrackUrl) return

    const handleError = () => {
      console.warn('Failed to load audio backing track:', project.audioBackingTrackUrl)
    }

    audio.addEventListener('error', handleError)

    // Only update src if it changed
    if (audio.src !== project.audioBackingTrackUrl) {
      audio.src = project.audioBackingTrackUrl
      audio.load()
    }

    return () => {
      audio.removeEventListener('error', handleError)
    }
  }, [project?.audioBackingTrackUrl])

  // Sync audio play/pause with video playback
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !project?.audioBackingTrackUrl) return

    if (isPlaying) {
      audio.play().catch(err => {
        console.warn('Failed to play audio backing track:', err)
        // Don't break video playback if audio fails
      })
    } else {
      audio.pause()
    }
  }, [isPlaying, project?.audioBackingTrackUrl])

  // Sync audio currentTime with video currentTime
  // Sync when paused, when playback starts, or when user seeks during playback
  // During normal playback, let audio play naturally without constant syncing to avoid choppiness
  const lastSyncedTimeRef = useRef<number>(0)
  const wasPlayingRef = useRef<boolean>(false)
  const prevCurrentTimeRef = useRef<number>(0)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !project?.audioBackingTrackUrl) return

    // Calculate the change in currentTime to detect seek operations
    const timeDelta = Math.abs(currentTime - prevCurrentTimeRef.current)

    // Detect if this is a seek operation (large jump in time)
    // Normal playback updates happen in small increments (< 0.5s)
    // Seeks typically jump by larger amounts
    const isSeekOperation = timeDelta > 0.5

    // Sync when playback starts (to ensure audio starts at correct position)
    if (isPlaying && !wasPlayingRef.current) {
      audio.currentTime = currentTime
      lastSyncedTimeRef.current = currentTime
      wasPlayingRef.current = true
      prevCurrentTimeRef.current = currentTime
      return
    }

    // Update ref when playback stops
    if (!isPlaying) {
      wasPlayingRef.current = false
    }

    // Sync when paused OR when a seek operation is detected while playing
    if (!isPlaying || isSeekOperation) {
      const diff = Math.abs(audio.currentTime - currentTime)
      if (diff > 0.1) {
        audio.currentTime = currentTime
        lastSyncedTimeRef.current = currentTime
      }
    }

    // Update previous time for next comparison
    prevCurrentTimeRef.current = currentTime

    // During normal playback (no seek), don't sync - let audio play naturally
  }, [currentTime, isPlaying, project?.audioBackingTrackUrl])

  // Sync audio volume with state
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !project?.audioBackingTrackUrl) return
    audio.volume = audioMuted ? 0 : audioVolume
  }, [audioVolume, audioMuted, project?.audioBackingTrackUrl])

  // Sync audio muted state with state
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !project?.audioBackingTrackUrl) return
    audio.muted = audioMuted
  }, [audioMuted, project?.audioBackingTrackUrl])

  // Callbacks for VideoPreview to control audio
  const handleAudioVolumeChange = useCallback((volume: number) => {
    setAudioVolume(volume)
  }, [])

  const handleAudioMuteChange = useCallback((muted: boolean) => {
    setAudioMuted(muted)
  }, [])

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      const audio = audioRef.current
      if (audio) {
        audio.pause()
        audio.src = ''
        audio.load()
      }
    }
  }, [])

  // Handle Continue button click
  const handleContinue = () => {
    setShowOverlay(false)
    overlayDismissed.current = true
    setIsGeneratingScenes(false)
  }

  // Handle Export Final Video button click
  const handleExportVideo = async () => {
    // If final video is already available, download it
    if (project?.finalOutputUrl) {
      window.open(project.finalOutputUrl, '_blank')
      toast({
        title: "Downloading Video",
        description: "Your final video is being downloaded.",
      })
      return
    }

    // Otherwise, start the composition process
    if (!project || !allVideosComplete) {
      toast({
        title: "Cannot Export",
        description: "All video clips must be generated before exporting the final video.",
        variant: "destructive",
      })
      return
    }

    setIsComposing(true)

    try {
      toast({
        title: "Starting Video Composition",
        description: "Stitching all scenes together into the final video...",
      })

      const response = await composeVideo(params.id)
      setCompositionJobId(response.jobId)

      toast({
        title: "Composition Started!",
        description: "Your final video is being composed. This may take a few minutes.",
      })
    } catch (err) {
      console.error('Composition error:', err)
      toast({
        title: "Composition Failed",
        description: err instanceof Error ? err.message : "Failed to start video composition",
        variant: "destructive",
      })
      setIsComposing(false)
    }
  }

  // Loading state
  if (loading && !project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
          <p className="text-white text-lg">Loading project...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error && !project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription className="flex flex-col gap-4">
            <p>{error}</p>
            <Button onClick={refetch} variant="outline">
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  // Project not found
  if (!project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-white text-lg mb-4">Project not found</p>
          <Link href="/create">
            <Button>Create New Project</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <nav className="border-b border-gray-700/50 backdrop-blur-sm bg-gray-900/50 sticky top-0 z-50">
        <div className="w-full px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <Video className="h-8 w-8 text-blue-500" />
              <span className="text-xl font-bold text-white">AI Video Generator</span>
            </Link>
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                className="border-gray-600 text-white hover:bg-gray-800"
                onClick={() => window.location.href = `/result/${params.id}`}
              >
                <ChevronLeft className="mr-2 h-4 w-4" />
                Back to Result
              </Button>
              <Button
                className="bg-blue-600 hover:bg-blue-700 text-white"
                onClick={handleExportVideo}
                disabled={!allVideosComplete || isComposing || !!project?.finalOutputUrl}
              >
                {isComposing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Composing...
                  </>
                ) : project?.finalOutputUrl ? (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Download Video
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Export Final Video
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Video Editor - Panel Layout */}
      <div className="h-[calc(100vh-73px)] flex">
        {/* Left Panel - Scenes (30%) */}
        <div className="w-[30%] min-w-[320px] max-w-[400px]">
          <ScenesPanel
            project={project}
            selectedSceneId={selectedSceneId}
            onSceneSelect={handleSceneSelect}
            onProjectUpdate={refetch}
          />
        </div>

        {/* Main Panel - Video Preview (70%) */}
        <div className="flex-1 bg-gray-800/50 p-6 overflow-y-auto">
          <div className="max-w-5xl mx-auto space-y-4">
            {/* Video Preview */}
            <div className="flex items-center justify-center">
              <VideoPreview
                jobId={params.id}
                project={project}
                currentTime={currentTime}
                duration={duration}
                isPlaying={isPlaying}
                onPlayPause={() => setIsPlaying(!isPlaying)}
                onSeek={setCurrentTime}
                showFinalVideo={!!project?.finalOutputUrl}
                isComposing={isComposing}
                selectedScene={selectedScene}
                muted={!!project?.audioBackingTrackUrl}
                onAudioVolumeChange={project?.audioBackingTrackUrl ? handleAudioVolumeChange : undefined}
                onAudioMuteChange={project?.audioBackingTrackUrl ? handleAudioMuteChange : undefined}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Scene Generation Overlay */}
      <SceneGenerationOverlay
        isVisible={showOverlay}
        scenes={project.scenes}
        totalScenes={project.sceneCount || project.scenes.length}
        onContinue={handleContinue}
        isComplete={allSceneTextsGenerated}
      />

      {/* Hidden Audio Element for Backing Track */}
      {project?.audioBackingTrackUrl && (
        <audio
          ref={audioRef}
          className="hidden"
          preload="auto"
          aria-hidden="true"
        />
      )}
    </div>
  )
}
