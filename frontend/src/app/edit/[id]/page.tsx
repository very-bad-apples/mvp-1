'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
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
  const sceneGenerationTriggered = useRef(false)
  const overlayDismissed = useRef(false)
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

  // Get the selected scene object from the ID
  const selectedScene = useMemo(() => {
    if (!selectedSceneId || !project?.scenes) return null
    const sequence = parseInt(selectedSceneId.replace('scene-', ''))
    return project.scenes.find(scene => scene.sequence === sequence) || null
  }, [selectedSceneId, project?.scenes])

  // Handle overlay visibility - show only for new projects that haven't dismissed it
  useEffect(() => {
    if (project && project.scenes.length > 0 && !overlayDismissed.current && isGeneratingScenes) {
      setShowOverlay(true)
    }
  }, [project, isGeneratingScenes])

  // Auto-trigger scene generation for new projects
  useEffect(() => {
    const triggerSceneGeneration = async () => {
      // Only trigger if:
      // 1. Project is loaded
      // 2. Project has no scenes
      // 3. We haven't already triggered generation
      // 4. Not currently loading or generating
      if (
        project &&
        project.scenes.length === 0 &&
        !sceneGenerationTriggered.current &&
        !loading &&
        !isGeneratingScenes
      ) {
        sceneGenerationTriggered.current = true
        setIsGeneratingScenes(true)

        toast({
          title: "Generating Scenes",
          description: "Creating scene descriptions for your project...",
        })

        try {
          await generateScenes({
            idea: project.conceptPrompt,
            character_description: project.characterDescription,
            config_flavor: 'default',
            project_id: params.id,
          })

          toast({
            title: "Scenes Generated!",
            description: "Scene descriptions have been created. You can now continue to the editor.",
          })

          // Refresh project data to get the new scenes
          await refetch()

          // Show overlay now that we have scenes
          setShowOverlay(true)

          // Scene generation is complete - allow user to continue
          setIsGeneratingScenes(false)

          // Start video generation in the BACKGROUND (non-blocking)
          toast({
            title: "Starting Video Generation",
            description: "Videos will generate in the background. You can continue editing.",
          })

          // Start the full generation orchestration WITHOUT awaiting
          // This runs in the background while user can interact with the editor
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

          toast({
            title: "Background Generation Started!",
            description: "Video assets are being generated. Check the timeline for progress.",
          })
        } catch (err) {
          console.error('Scene generation error:', err)
          toast({
            title: "Scene Generation Failed",
            description: err instanceof Error ? err.message : "Failed to generate scenes",
            variant: "destructive",
          })
          sceneGenerationTriggered.current = false // Allow retry
          setIsGeneratingScenes(false)
        }
      }
    }

    triggerSceneGeneration()
  }, [project, loading, isGeneratingScenes, params.id, refetch, toast])

  // Poll for composition completion
  useEffect(() => {
    if (!isComposing || !compositionJobId) return

    // Check if composition is complete by checking if finalOutputUrl is available
    if (project?.finalOutputUrl) {
      setIsComposing(false)
      toast({
        title: "Video Composition Complete!",
        description: "Your final video is ready. You can now download it.",
      })
      return
    }

    // Set up polling interval to check for completion
    const pollInterval = setInterval(async () => {
      // Trigger a refetch to get latest project data
      await refetch()
    }, 3000) // Poll every 3 seconds

    return () => {
      clearInterval(pollInterval)
    }
  }, [isComposing, compositionJobId, project?.finalOutputUrl, refetch, toast])

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
        <div className="container mx-auto px-4 py-4">
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
            onSceneSelect={setSelectedSceneId}
            onProjectUpdate={refetch}
          />
        </div>

        {/* Main Panel - Video Preview (70%) */}
        <div className="flex-1 flex items-center justify-center bg-gray-800/50 p-6">
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
          />
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
    </div>
  )
}
