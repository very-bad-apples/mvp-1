'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Video, ChevronLeft, Loader2, CheckCircle, AlertCircle, Film } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Configuration
const VIDEO_EXPECTED_LOAD_TIME_SECONDS = 7 // Expected time for video generation

/**
 * Resolves video URL to handle both local and S3 storage backends.
 * - If URL is absolute (starts with http), use directly (S3 presigned URL)
 * - If URL is relative (starts with /), prepend API_URL (local backend)
 */
const resolveVideoUrl = (videoUrl: string): string => {
  if (videoUrl.startsWith('http://') || videoUrl.startsWith('https://')) {
    // Absolute URL (S3 presigned URL) - use directly
    return videoUrl
  }
  // Relative URL (local backend) - prepend API_URL
  return `${API_URL}${videoUrl}`
}

interface QuickJobData {
  videoDescription: string
  characterDescription: string
  characterReferenceImageId: string
}

interface Scene {
  description: string
  negative_description: string
}

interface VideoState {
  sceneIndex: number
  status: 'loading' | 'completed' | 'error'
  videoId?: string
  videoUrl?: string
  error?: string
}

type GenerationStatus = 'idle' | 'loading' | 'completed' | 'error'

export default function QuickGenPage() {
  const router = useRouter()
  const [jobData, setJobData] = useState<QuickJobData>({
    videoDescription: '',
    characterDescription: '',
    characterReferenceImageId: '',
  })

  // Scene generation state
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>('idle')
  const [progress, setProgress] = useState(0)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [error, setError] = useState<string | null>(null)
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const hasStartedRef = useRef(false)

  // Video generation state
  const [videoStates, setVideoStates] = useState<VideoState[]>([])
  const hasStartedVideoGenRef = useRef(false)

  // Load job data from sessionStorage
  useEffect(() => {
    const storedData = sessionStorage.getItem('quickJobData')
    if (storedData) {
      try {
        const parsed = JSON.parse(storedData) as QuickJobData
        setJobData({
          videoDescription: parsed.videoDescription || '',
          characterDescription: parsed.characterDescription || '',
          characterReferenceImageId: parsed.characterReferenceImageId || '',
        })
      } catch (error) {
        console.error('Failed to parse quickJobData from sessionStorage:', error)
      }
    }
  }, [])

  // Start scene generation when jobData is loaded
  useEffect(() => {
    // Only start once and only if we have the required data
    if (
      hasStartedRef.current ||
      !jobData.videoDescription ||
      !jobData.characterDescription
    ) {
      return
    }

    hasStartedRef.current = true
    generateScenes()

    // Cleanup interval on unmount
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
      }
    }
  }, [jobData])

  // Start video generation when scenes are ready
  useEffect(() => {
    if (
      hasStartedVideoGenRef.current ||
      scenes.length === 0 ||
      generationStatus !== 'completed'
    ) {
      return
    }

    hasStartedVideoGenRef.current = true
    generateVideos()
  }, [scenes, generationStatus])

  const generateScenes = async () => {
    setGenerationStatus('loading')
    setProgress(0)
    setError(null)
    setScenes([])

    // Start simulated progress (0% to ~90% over 25 seconds)
    const startTime = Date.now()
    const maxDuration = 25000 // 25 seconds to reach ~90%

    progressIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime
      const targetProgress = Math.min(90, (elapsed / maxDuration) * 90)
      setProgress(targetProgress)
    }, 200)

    try {
      const response = await fetch(`${API_URL}/api/mv/create_scenes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          idea: jobData.videoDescription,
          character_description: jobData.characterDescription,
        }),
      })

      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
        progressIntervalRef.current = null
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to generate scenes')
      }

      const data = await response.json()

      // Jump to 100% and set completed
      setProgress(100)
      setScenes(data.scenes || [])
      setGenerationStatus('completed')
    } catch (err) {
      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
        progressIntervalRef.current = null
      }

      const errorMessage = err instanceof Error ? err.message : 'Failed to generate scenes'
      setError(errorMessage)
      setGenerationStatus('error')
      console.error('Scene generation error:', err)
    }
  }

  const generateVideos = async () => {
    // Initialize video states with loading status
    const initialStates: VideoState[] = scenes.map((_, index) => ({
      sceneIndex: index,
      status: 'loading',
    }))
    setVideoStates(initialStates)

    // Generate videos in parallel
    // LIMITATION: Character reference image is not passed to generate_video
    // This would require fetching the image by ID and converting to base64
    // Deferred for future implementation
    const videoPromises = scenes.map((scene, index) =>
      generateSingleVideo(scene, index)
    )

    await Promise.allSettled(videoPromises)
  }

  const generateSingleVideo = async (scene: Scene, sceneIndex: number) => {
    try {
      const response = await fetch(`${API_URL}/api/mv/generate_video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: scene.description,
          negative_prompt: scene.negative_description,
          // LIMITATION: reference_image_base64 is omitted
          // Character reference image integration deferred
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to generate video')
      }

      const data = await response.json()

      // Update state for this specific video
      // Resolve video URL (handles both S3 presigned URLs and local backend paths)
      const resolvedVideoUrl = resolveVideoUrl(data.video_url)
      setVideoStates(prev =>
        prev.map(state =>
          state.sceneIndex === sceneIndex
            ? {
                ...state,
                status: 'completed',
                videoId: data.video_id,
                videoUrl: resolvedVideoUrl,
              }
            : state
        )
      )
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate video'
      console.error(`Video generation error for scene ${sceneIndex + 1}:`, err)

      // Update state with error for this specific video
      setVideoStates(prev =>
        prev.map(state =>
          state.sceneIndex === sceneIndex
            ? {
                ...state,
                status: 'error',
                error: errorMessage,
              }
            : state
        )
      )
    }
  }

  // Calculate video generation summary stats
  const videoSummary = {
    loading: videoStates.filter(v => v.status === 'loading').length,
    succeeded: videoStates.filter(v => v.status === 'completed').length,
    failed: videoStates.filter(v => v.status === 'error').length,
  }

  const getStatusBadge = () => {
    switch (generationStatus) {
      case 'idle':
        return <Badge className="bg-gray-500/10 text-gray-400 border-gray-500/20">Idle</Badge>
      case 'loading':
        return <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Generating</Badge>
      case 'completed':
        return <Badge className="bg-green-500/10 text-green-400 border-green-500/20">Completed</Badge>
      case 'error':
        return <Badge className="bg-red-500/10 text-red-400 border-red-500/20">Error</Badge>
    }
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
            <Link href="/create">
              <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
                <ChevronLeft className="mr-2 h-4 w-4" />
                Back to Create
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Quick Job
            </h1>
            <p className="text-xl text-gray-300">
              Generate and review scenes
            </p>
          </div>

          <div className="space-y-6">
            {/* Input Data Card */}
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white">Input Data</CardTitle>
                <CardDescription className="text-gray-400">
                  Data received from the create page
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Video Description */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-400">
                      Video Description
                    </label>
                    <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3 min-h-[60px]">
                      <p className="text-white text-sm whitespace-pre-wrap">
                        {jobData.videoDescription || <span className="text-gray-500 italic">Empty</span>}
                      </p>
                    </div>
                  </div>

                  {/* Character and Style */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-400">
                      Character and Style
                    </label>
                    <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3 min-h-[60px]">
                      <p className="text-white text-sm whitespace-pre-wrap">
                        {jobData.characterDescription || <span className="text-gray-500 italic">Empty</span>}
                      </p>
                    </div>
                  </div>

                  {/* Character Reference Image ID */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-400">
                      Character Reference Image ID
                    </label>
                    <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                      <p className="text-white text-sm font-mono">
                        {jobData.characterReferenceImageId || <span className="text-gray-500 italic">Empty</span>}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Scene Generation Status Card */}
            {generationStatus !== 'idle' && (
              <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white">Scene Generation</CardTitle>
                    {getStatusBadge()}
                  </div>
                  <CardDescription className="text-gray-400">
                    {generationStatus === 'loading' && 'Generating scenes with AI...'}
                    {generationStatus === 'completed' && `Generated ${scenes.length} scenes`}
                    {generationStatus === 'error' && 'Failed to generate scenes'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* Progress Bar (shown while loading) */}
                    {generationStatus === 'loading' && (
                      <div className="space-y-4">
                        <div className="flex justify-center">
                          <Loader2 className="h-12 w-12 text-blue-400 animate-spin" />
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm text-gray-400">
                            <span>Progress</span>
                            <span>{Math.round(progress)}%</span>
                          </div>
                          <Progress value={progress} className="h-2" />
                        </div>
                        <p className="text-sm text-gray-400 text-center">
                          This may take 10-30 seconds...
                        </p>
                      </div>
                    )}

                    {/* Completed Status */}
                    {generationStatus === 'completed' && (
                      <div className="flex justify-center">
                        <CheckCircle className="h-12 w-12 text-green-400" />
                      </div>
                    )}

                    {/* Error Display */}
                    {generationStatus === 'error' && error && (
                      <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription className="text-red-300">
                          {error}
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Generated Scenes Cards */}
            {scenes.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-white">Generated Scenes</h2>
                {scenes.map((scene, index) => (
                  <Card key={index} className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
                    <CardHeader>
                      <CardTitle className="text-white text-lg">
                        Scene {index + 1}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {/* Scene Description */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-gray-400">
                            Description
                          </label>
                          <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                            <p className="text-white text-sm whitespace-pre-wrap">
                              {scene.description}
                            </p>
                          </div>
                        </div>

                        {/* Negative Description */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-gray-400">
                            Negative Description
                          </label>
                          <div className="bg-gray-900/50 border border-red-900/30 rounded-lg p-3">
                            <p className="text-gray-300 text-sm whitespace-pre-wrap">
                              {scene.negative_description}
                            </p>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Video Generation Section */}
            {videoStates.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white">Generated Videos</h2>
                  {/* Status Summary Bar */}
                  <div className="flex items-center gap-2">
                    {videoSummary.loading > 0 && (
                      <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                        {videoSummary.loading} loading
                      </Badge>
                    )}
                    {videoSummary.succeeded > 0 && (
                      <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                        {videoSummary.succeeded} succeeded
                      </Badge>
                    )}
                    {videoSummary.failed > 0 && (
                      <Badge className="bg-red-500/10 text-red-400 border-red-500/20">
                        {videoSummary.failed} failed
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Video Cards */}
                {videoStates.map((videoState) => (
                  <Card key={videoState.sceneIndex} className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-white text-lg">
                          Video {videoState.sceneIndex + 1}
                        </CardTitle>
                        {videoState.status === 'loading' && (
                          <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                            Generating
                          </Badge>
                        )}
                        {videoState.status === 'completed' && (
                          <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                            Ready
                          </Badge>
                        )}
                        {videoState.status === 'error' && (
                          <Badge className="bg-red-500/10 text-red-400 border-red-500/20">
                            Failed
                          </Badge>
                        )}
                      </div>
                      {videoState.videoId && (
                        <CardDescription className="text-gray-400 font-mono text-xs">
                          ID: {videoState.videoId}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent>
                      {/* Loading State */}
                      {videoState.status === 'loading' && (
                        <div className="space-y-4">
                          <div className="aspect-video bg-gray-900/50 rounded-lg flex items-center justify-center border border-gray-700">
                            <div className="text-center space-y-3">
                              <Loader2 className="h-12 w-12 text-blue-400 animate-spin mx-auto" />
                              <p className="text-gray-400 text-sm">
                                Generating video... (expected ~{VIDEO_EXPECTED_LOAD_TIME_SECONDS}s)
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Completed State - Video Player */}
                      {videoState.status === 'completed' && videoState.videoUrl && (
                        <div className="space-y-2">
                          <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                            <video
                              src={videoState.videoUrl}
                              controls
                              className="w-full h-full"
                              preload="metadata"
                            >
                              Your browser does not support the video tag.
                            </video>
                          </div>
                        </div>
                      )}

                      {/* Error State */}
                      {videoState.status === 'error' && videoState.error && (
                        <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription className="text-red-300">
                            Scene {videoState.sceneIndex + 1} failed: {videoState.error}
                          </AlertDescription>
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
