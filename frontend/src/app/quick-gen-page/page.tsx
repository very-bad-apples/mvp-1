'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import {
  Video,
  ChevronLeft,
  Loader2,
  AlertCircle,
  Film,
  Edit,
  RefreshCw,
  Save,
  X,
  ChevronDown,
  ChevronUp,
  Music,
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

// Configuration Constants
const VIDEO_EXPECTED_LOAD_TIME_SECONDS = 7 * 60 // 7 minutes in seconds
const SCENE_EXPECTED_LOAD_TIME_SECONDS = 25 // 25 seconds
const STITCH_EXPECTED_TIME_PER_VIDEO_SECONDS = 5 // 5 seconds per video
const TELETYPE_TOTAL_DURATION_MS = 10000 // 10 seconds for all scenes to complete typing

// Loading snippets for scene generation (rotate every 3-5 seconds)
const SCENE_LOADING_SNIPPETS = [
  'Analyzing video concept...',
  'Crafting scene narratives...',
  'Optimizing character integration...',
  'Generating creative directions...',
  'Finalizing scene structure...',
]

// Loading snippets for video generation (rotate every 10-15 seconds)
const VIDEO_LOADING_SNIPPETS = [
  'Rendering scene visuals...',
  'Applying character style...',
  'Processing video effects...',
  'Enhancing video quality...',
  'Almost there...',
]

/**
 * Resolves video URL to handle both local and S3 storage backends.
 */
const resolveVideoUrl = (videoUrl: string): string => {
  if (videoUrl.startsWith('http://') || videoUrl.startsWith('https://')) {
    return videoUrl // S3 presigned URL
  }
  return `${API_URL}${videoUrl}` // Local backend
}

interface QuickJobData {
  videoDescription: string
  characterDescription: string
  characterReferenceImageId: string
  audioId?: string
  audioUrl?: string
  audioTitle?: string
  configFlavor?: string
}

interface Scene {
  description: string
  negative_description: string
}

interface SceneVideoState {
  sceneIndex: number
  scene: {
    description: string
    negative_description: string
    status: 'loading' | 'completed' | 'error'
    error?: string
    isEditing?: boolean
    editedDescription?: string
  }
  video: {
    videoId?: string
    videoUrl?: string
    status: 'idle' | 'loading' | 'completed' | 'error'
    error?: string
  }
}

interface StitchedVideo {
  videoId: string
  videoUrl: string
  metadata?: {
    num_clips?: number
    total_duration?: number
  }
}

type StitchingStatus = 'idle' | 'loading' | 'completed' | 'error'

export default function QuickGenPage() {
  const router = useRouter()
  const [jobData, setJobData] = useState<QuickJobData>({
    videoDescription: '',
    characterDescription: '',
    characterReferenceImageId: '',
    audioId: undefined,
    audioUrl: undefined,
    audioTitle: undefined,
  })

  // Combined scene/video state
  const [sceneVideoStates, setSceneVideoStates] = useState<SceneVideoState[]>([])
  const hasStartedRef = useRef(false)
  const hasStartedVideoGenRef = useRef(false)

  // Input data collapse state
  const [isInputDataExpanded, setIsInputDataExpanded] = useState(true)

  // Config flavor state
  const [isConfigExpanded, setIsConfigExpanded] = useState(false)
  const [configFlavor, setConfigFlavor] = useState<string>('default')
  const [availableFlavors, setAvailableFlavors] = useState<string[]>(['default'])
  const [isFetchingFlavors, setIsFetchingFlavors] = useState(false)

  // Character reference image state
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null)
  const [characterImageLoading, setCharacterImageLoading] = useState(false)
  const [characterImageError, setCharacterImageError] = useState(false)

  // Video stitching state
  const [stitchingStatus, setStitchingStatus] = useState<StitchingStatus>('idle')
  const [stitchedVideo, setStitchedVideo] = useState<StitchedVideo | null>(null)
  const [stitchingError, setStitchingError] = useState<string | null>(null)
  const [estimatedStitchTime, setEstimatedStitchTime] = useState(0)
  const hasStartedStitchingRef = useRef(false)
  const stitchedVideoRef = useRef<HTMLDivElement>(null)

  // Teletype animation state
  const [teletypeStates, setTeletypeStates] = useState<{ [key: number]: string }>({})
  const teletypeTimersRef = useRef<{ [key: number]: NodeJS.Timeout }>({})

  // Fetch available config flavors on mount
  useEffect(() => {
    const fetchConfigFlavors = async () => {
      setIsFetchingFlavors(true)
      try {
        const response = await fetch(`${API_URL}/api/mv/get_config_flavors`, {
          headers: API_KEY ? { 'X-API-Key': API_KEY } : {},
        })
        if (response.ok) {
          const data = await response.json()
          if (data.flavors && Array.isArray(data.flavors)) {
            setAvailableFlavors(data.flavors)
          }
        }
      } catch (error) {
        console.error('Failed to fetch config flavors:', error)
        // Keep default fallback
      } finally {
        setIsFetchingFlavors(false)
      }
    }

    fetchConfigFlavors()
  }, [])

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
          audioId: parsed.audioId || undefined,
          audioUrl: parsed.audioUrl || undefined,
          audioTitle: parsed.audioTitle || undefined,
          configFlavor: parsed.configFlavor,
        })
        // Initialize configFlavor from sessionStorage
        if (parsed.configFlavor) {
          setConfigFlavor(parsed.configFlavor)
        }
      } catch (error) {
        console.error('Failed to parse quickJobData from sessionStorage:', error)
      }
    }
  }, [])

  // Fetch character reference image
  useEffect(() => {
    const fetchCharacterImage = async (imageId: string) => {
      setCharacterImageLoading(true)
      setCharacterImageError(false)

      try {
        const response = await fetch(`${API_URL}/api/mv/get_character_reference/${imageId}?redirect=false`, {
          headers: {
            'X-API-Key': API_KEY,
            'Content-Type': 'application/json'
          },
        })

        if (!response.ok) {
          throw new Error(`Failed to fetch image ${imageId}`)
        }

        const contentType = response.headers.get('content-type')

        if (contentType?.includes('application/json')) {
          // Cloud storage mode - get presigned URL from JSON
          const data = await response.json()
          setCharacterImageUrl(data.image_url || data.video_url)
        } else {
          // Local storage mode - create object URL from blob
          const blob = await response.blob()
          const objectUrl = URL.createObjectURL(blob)
          setCharacterImageUrl(objectUrl)
        }

        setCharacterImageLoading(false)
      } catch (error) {
        console.error('Failed to fetch character image:', error)
        setCharacterImageError(true)
        setCharacterImageLoading(false)
      }
    }

    if (jobData.characterReferenceImageId) {
      fetchCharacterImage(jobData.characterReferenceImageId)
    }

    // Cleanup function to revoke object URLs
    return () => {
      if (characterImageUrl && characterImageUrl.startsWith('blob:')) {
        URL.revokeObjectURL(characterImageUrl)
      }
    }
  }, [jobData.characterReferenceImageId])

  // Initialize placeholder cards and start scene generation
  useEffect(() => {
    if (
      hasStartedRef.current ||
      !jobData.videoDescription ||
      !jobData.characterDescription
    ) {
      return
    }

    hasStartedRef.current = true

    // Create 4 placeholder cards (assuming 4 scenes by default)
    const placeholders: SceneVideoState[] = Array.from({ length: 4 }, (_, i) => ({
      sceneIndex: i,
      scene: {
        description: '',
        negative_description: '',
        status: 'loading',
      },
      video: {
        status: 'idle',
      },
    }))
    setSceneVideoStates(placeholders)

    // Start scene generation
    generateScenes()
  }, [jobData])

  // Start video generation when all scenes are ready
  useEffect(() => {
    if (hasStartedVideoGenRef.current) return

    const allScenesComplete = sceneVideoStates.length > 0 &&
      sceneVideoStates.every(s => s.scene.status === 'completed')

    if (allScenesComplete) {
      hasStartedVideoGenRef.current = true
      generateVideos()
    }
  }, [sceneVideoStates])

  // Start video stitching when all videos complete
  useEffect(() => {
    if (
      hasStartedStitchingRef.current ||
      sceneVideoStates.length === 0 ||
      stitchingStatus !== 'idle'
    ) {
      return
    }

    const allVideosFinished = sceneVideoStates.every(
      s => s.video.status === 'completed' || s.video.status === 'error'
    )
    const hasSuccessful = sceneVideoStates.some(s => s.video.status === 'completed')

    if (allVideosFinished && hasSuccessful) {
      hasStartedStitchingRef.current = true
      stitchVideos()
    }
  }, [sceneVideoStates, stitchingStatus])

  // Auto-scroll to stitched video when completed
  useEffect(() => {
    if (stitchingStatus === 'completed' && stitchedVideoRef.current) {
      setTimeout(() => {
        stitchedVideoRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }, 300)
    }
  }, [stitchingStatus])

  // Auto-collapse input data when all scenes complete
  useEffect(() => {
    const allScenesComplete = sceneVideoStates.length > 0 &&
      sceneVideoStates.every(s => s.scene.status === 'completed')

    if (allScenesComplete && isInputDataExpanded) {
      setTimeout(() => {
        setIsInputDataExpanded(false)
      }, 500)
    }
  }, [sceneVideoStates])

  const generateScenes = async () => {
    try {
      const response = await fetch(`${API_URL}/api/mv/create_scenes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          idea: jobData.videoDescription,
          character_description: jobData.characterDescription,
          config_flavor: configFlavor,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to generate scenes')
      }

      const data = await response.json()
      const scenes: Scene[] = data.scenes || []

      // Update states with actual scene data
      const updatedStates: SceneVideoState[] = scenes.map((scene, index) => ({
        sceneIndex: index,
        scene: {
          description: scene.description,
          negative_description: scene.negative_description,
          status: 'completed',
        },
        video: {
          status: 'idle',
        },
      }))

      setSceneVideoStates(updatedStates)

      // Start teletype animation for all scenes in parallel
      startTeletypeAnimations(scenes)
    } catch (err) {
      console.error('Scene generation error:', err)
      // Mark all placeholder scenes as error
      setSceneVideoStates(prev =>
        prev.map(s => ({
          ...s,
          scene: {
            ...s.scene,
            status: 'error',
            error: err instanceof Error ? err.message : 'Failed to generate scenes',
          },
        }))
      )
    }
  }

  const startTeletypeAnimations = (scenes: Scene[]) => {
    // Calculate total characters across all scenes
    const totalChars = scenes.reduce((sum, scene) => sum + scene.description.length, 0)
    const charDelay = TELETYPE_TOTAL_DURATION_MS / totalChars

    scenes.forEach((scene, index) => {
      let currentIndex = 0
      const text = scene.description

      const typeNextChar = () => {
        if (currentIndex < text.length) {
          setTeletypeStates(prev => ({
            ...prev,
            [index]: text.substring(0, currentIndex + 1),
          }))
          currentIndex++
          teletypeTimersRef.current[index] = setTimeout(typeNextChar, charDelay)
        } else {
          // Animation complete for this scene
          delete teletypeTimersRef.current[index]
        }
      }

      // Start typing
      typeNextChar()
    })
  }

  const skipTeletype = (sceneIndex: number) => {
    // Clear timer and show full text immediately
    if (teletypeTimersRef.current[sceneIndex]) {
      clearTimeout(teletypeTimersRef.current[sceneIndex])
      delete teletypeTimersRef.current[sceneIndex]
    }

    const fullText = sceneVideoStates[sceneIndex]?.scene.description || ''
    setTeletypeStates(prev => ({
      ...prev,
      [sceneIndex]: fullText,
    }))
  }

  const generateVideos = async () => {
    // Set all videos to loading
    setSceneVideoStates(prev =>
      prev.map(s => ({
        ...s,
        video: { ...s.video, status: 'loading' },
      }))
    )

    // Generate videos in parallel
    const videoPromises = sceneVideoStates.map((state) =>
      generateSingleVideo(state.scene.description, state.scene.negative_description, state.sceneIndex)
    )

    await Promise.allSettled(videoPromises)
  }

  const generateSingleVideo = async (
    prompt: string,
    negativePrompt: string,
    sceneIndex: number
  ) => {
    try {
      const response = await fetch(`${API_URL}/api/mv/generate_video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          prompt,
          negative_prompt: negativePrompt,
          character_reference_id: jobData.characterReferenceImageId,
          config_flavor: configFlavor,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to generate video')
      }

      const data = await response.json()
      const resolvedVideoUrl = resolveVideoUrl(data.video_url)

      setSceneVideoStates(prev =>
        prev.map(s =>
          s.sceneIndex === sceneIndex
            ? {
                ...s,
                video: {
                  ...s.video,
                  status: 'completed',
                  videoId: data.video_id,
                  videoUrl: resolvedVideoUrl,
                },
              }
            : s
        )
      )
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate video'
      console.error(`Video generation error for scene ${sceneIndex + 1}:`, err)

      setSceneVideoStates(prev =>
        prev.map(s =>
          s.sceneIndex === sceneIndex
            ? {
                ...s,
                video: {
                  ...s.video,
                  status: 'error',
                  error: errorMessage,
                },
              }
            : s
        )
      )
    }
  }

  const regenerateScene = async (sceneIndex: number) => {
    // Set scene to loading
    setSceneVideoStates(prev =>
      prev.map(s =>
        s.sceneIndex === sceneIndex
          ? {
              ...s,
              scene: { ...s.scene, status: 'loading', error: undefined },
            }
          : s
      )
    )

    try {
      const response = await fetch(`${API_URL}/api/mv/create_scenes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          idea: jobData.videoDescription,
          character_description: jobData.characterDescription,
          config_flavor: configFlavor,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to regenerate scene')
      }

      const data = await response.json()
      const scenes: Scene[] = data.scenes || []

      // Use the scene at the same index
      if (scenes[sceneIndex]) {
        const newScene = scenes[sceneIndex]
        setSceneVideoStates(prev =>
          prev.map(s =>
            s.sceneIndex === sceneIndex
              ? {
                  ...s,
                  scene: {
                    description: newScene.description,
                    negative_description: newScene.negative_description,
                    status: 'completed',
                  },
                }
              : s
          )
        )

        // Start teletype for this scene
        startTeletypeAnimations([newScene])
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to regenerate scene'
      console.error(`Scene regeneration error for scene ${sceneIndex + 1}:`, err)

      setSceneVideoStates(prev =>
        prev.map(s =>
          s.sceneIndex === sceneIndex
            ? {
                ...s,
                scene: {
                  ...s.scene,
                  status: 'error',
                  error: errorMessage,
                },
              }
            : s
        )
      )
    }
  }

  const regenerateVideo = async (sceneIndex: number) => {
    const state = sceneVideoStates[sceneIndex]
    if (!state) return

    // Set video to loading
    setSceneVideoStates(prev =>
      prev.map(s =>
        s.sceneIndex === sceneIndex
          ? {
              ...s,
              video: { ...s.video, status: 'loading', error: undefined },
            }
          : s
      )
    )

    // Use current (possibly edited) scene description
    await generateSingleVideo(
      state.scene.description,
      state.scene.negative_description,
      sceneIndex
    )
  }

  const startEditingScene = (sceneIndex: number) => {
    setSceneVideoStates(prev =>
      prev.map(s =>
        s.sceneIndex === sceneIndex
          ? {
              ...s,
              scene: {
                ...s.scene,
                isEditing: true,
                editedDescription: s.scene.description,
              },
            }
          : s
      )
    )
  }

  const saveEditedScene = (sceneIndex: number) => {
    const state = sceneVideoStates[sceneIndex]
    if (!state?.scene.editedDescription?.trim()) return

    setSceneVideoStates(prev =>
      prev.map(s =>
        s.sceneIndex === sceneIndex
          ? {
              ...s,
              scene: {
                ...s.scene,
                description: s.scene.editedDescription || s.scene.description,
                isEditing: false,
                editedDescription: undefined,
              },
            }
          : s
      )
    )
  }

  const cancelEditingScene = (sceneIndex: number) => {
    setSceneVideoStates(prev =>
      prev.map(s =>
        s.sceneIndex === sceneIndex
          ? {
              ...s,
              scene: {
                ...s.scene,
                isEditing: false,
                editedDescription: undefined,
              },
            }
          : s
      )
    )
  }

  const updateEditedDescription = (sceneIndex: number, value: string) => {
    setSceneVideoStates(prev =>
      prev.map(s =>
        s.sceneIndex === sceneIndex
          ? {
              ...s,
              scene: {
                ...s.scene,
                editedDescription: value,
              },
            }
          : s
      )
    )
  }

  const stitchVideos = async () => {
    const successfulVideoIds = sceneVideoStates
      .filter(s => s.video.status === 'completed' && s.video.videoId)
      .sort((a, b) => a.sceneIndex - b.sceneIndex)
      .map(s => s.video.videoId!)

    if (successfulVideoIds.length === 0) {
      console.error('No successful videos to stitch')
      return
    }

    const estimatedTime = successfulVideoIds.length * STITCH_EXPECTED_TIME_PER_VIDEO_SECONDS
    setEstimatedStitchTime(estimatedTime)
    setStitchingStatus('loading')
    setStitchingError(null)
    setStitchedVideo(null)

    try {
      // Build request body with optional audio parameters
      const requestBody: {
        video_ids: string[]
        audio_overlay_id?: string
        suppress_video_audio?: boolean
      } = {
        video_ids: successfulVideoIds,
      }

      // Add audio overlay parameters if audio is available
      if (jobData.audioId) {
        requestBody.audio_overlay_id = jobData.audioId
        requestBody.suppress_video_audio = true
      }

      const response = await fetch(`${API_URL}/api/mv/stitch-videos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to stitch videos')
      }

      const data = await response.json()
      const resolvedVideoUrl = resolveVideoUrl(data.video_url)

      setStitchedVideo({
        videoId: data.video_id,
        videoUrl: resolvedVideoUrl,
        metadata: data.metadata,
      })
      setStitchingStatus('completed')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to stitch videos'
      setStitchingError(errorMessage)
      setStitchingStatus('error')
      console.error('Video stitching error:', err)
    }
  }

  const retryStitching = () => {
    hasStartedStitchingRef.current = false
    setStitchingStatus('idle')
    setStitchingError(null)
    setStitchedVideo(null)
  }

  // Calculate video generation summary stats
  const videoSummary = {
    loading: sceneVideoStates.filter(s => s.video.status === 'loading').length,
    succeeded: sceneVideoStates.filter(s => s.video.status === 'completed').length,
    failed: sceneVideoStates.filter(s => s.video.status === 'error').length,
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
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Quick Job
            </h1>
            <p className="text-xl text-gray-300">
              Generate and review scenes
            </p>
          </div>

          <div className="space-y-6">
            {/* Configuration Card - Collapsible */}
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
              <CardHeader className="cursor-pointer" onClick={() => setIsConfigExpanded(!isConfigExpanded)}>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white">Configuration</CardTitle>
                    <CardDescription className="text-gray-400">
                      Adjust generation settings
                    </CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                    {isConfigExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </Button>
                </div>
              </CardHeader>
              {isConfigExpanded && (
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="quick-config-flavor" className="text-sm font-medium text-white">
                      Config Flavor
                    </Label>
                    <Select
                      value={configFlavor}
                      onValueChange={setConfigFlavor}
                      disabled={isFetchingFlavors}
                    >
                      <SelectTrigger
                        id="quick-config-flavor"
                        className="w-full bg-gray-800 border-gray-600 text-white"
                      >
                        <SelectValue placeholder={isFetchingFlavors ? "Loading..." : "Select flavor"} />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-800 border-gray-600">
                        {availableFlavors.map((flavor) => (
                          <SelectItem
                            key={flavor}
                            value={flavor}
                            className="text-white hover:bg-gray-700"
                          >
                            {flavor}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-400">
                      Config flavor affects prompts and generation parameters
                    </p>
                  </div>
                </CardContent>
              )}
            </Card>

            {/* Input Data Card - Collapsible */}
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
              <CardHeader className="cursor-pointer" onClick={() => setIsInputDataExpanded(!isInputDataExpanded)}>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white">Input Data</CardTitle>
                    <CardDescription className="text-gray-400">
                      Data received from the create page
                    </CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                    {isInputDataExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </Button>
                </div>
              </CardHeader>
              {isInputDataExpanded && (
                <CardContent>
                  <div className="space-y-4">
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

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-400">
                        Character Reference Image
                      </label>
                      <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                        {!jobData.characterReferenceImageId && (
                          <p className="text-gray-500 italic text-sm">No image selected</p>
                        )}

                        {jobData.characterReferenceImageId && characterImageLoading && (
                          <div className="flex items-center justify-center aspect-square max-w-[200px] bg-gray-800 rounded-lg">
                            <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
                          </div>
                        )}

                        {jobData.characterReferenceImageId && characterImageError && (
                          <div className="flex flex-col items-center justify-center aspect-square max-w-[200px] bg-gray-800 rounded-lg p-4">
                            <AlertCircle className="h-8 w-8 text-red-400 mb-2" />
                            <p className="text-xs text-red-300 text-center">Failed to load image</p>
                            <p className="text-xs text-gray-500 font-mono mt-2">ID: {jobData.characterReferenceImageId}</p>
                          </div>
                        )}

                        {jobData.characterReferenceImageId && characterImageUrl && !characterImageLoading && !characterImageError && (
                          <div className="space-y-2">
                            <img
                              src={characterImageUrl}
                              alt="Character reference"
                              className="max-w-[200px] rounded-lg border border-gray-600"
                            />
                            <p className="text-xs text-gray-500 font-mono">ID: {jobData.characterReferenceImageId}</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Config Flavor Display */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-400">
                        Config Flavor
                      </label>
                      <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                        <p className="text-white text-sm">
                          {jobData.configFlavor || configFlavor || 'default'}
                        </p>
                      </div>
                    </div>

                    {/* Audio Track Section */}
                    {jobData.audioId && (
                      <div>
                        <label className="text-sm font-medium text-white block mb-2">
                          Audio Track
                        </label>
                        <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <Music className="h-4 w-4 text-red-400" />
                            <span className="text-xs text-gray-400">Audio from YouTube</span>
                          </div>
                          {jobData.audioTitle && (
                            <p className="text-sm text-white mb-2 truncate">{jobData.audioTitle}</p>
                          )}
                          <audio
                            controls
                            src={`${API_URL}/api/audio/get/${jobData.audioId}`}
                            className="w-full h-10"
                          />
                          <p className="text-xs text-gray-500 font-mono mt-2">ID: {jobData.audioId}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>

            {/* Scene/Video Combined Cards */}
            {sceneVideoStates.length > 0 && (
              <div className="space-y-6">
                {/* Status Summary */}
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white">Scenes & Videos</h2>
                  <div className="flex items-center gap-2">
                    {videoSummary.loading > 0 && (
                      <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                        {videoSummary.loading} generating
                      </Badge>
                    )}
                    {videoSummary.succeeded > 0 && (
                      <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                        {videoSummary.succeeded} ready
                      </Badge>
                    )}
                    {videoSummary.failed > 0 && (
                      <Badge className="bg-red-500/10 text-red-400 border-red-500/20">
                        {videoSummary.failed} failed
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Combined Scene/Video Cards */}
                {sceneVideoStates.map((state) => (
                  <SceneVideoCard
                    key={state.sceneIndex}
                    state={state}
                    jobData={jobData}
                    teletypeText={teletypeStates[state.sceneIndex]}
                    onSkipTeletype={() => skipTeletype(state.sceneIndex)}
                    onRegenerateScene={() => regenerateScene(state.sceneIndex)}
                    onRegenerateVideo={() => regenerateVideo(state.sceneIndex)}
                    onStartEditing={() => startEditingScene(state.sceneIndex)}
                    onSaveEditing={() => saveEditedScene(state.sceneIndex)}
                    onCancelEditing={() => cancelEditingScene(state.sceneIndex)}
                    onUpdateEditing={(value) => updateEditedDescription(state.sceneIndex, value)}
                  />
                ))}
              </div>
            )}

            {/* Full Video Section - Stitched Video */}
            {stitchingStatus !== 'idle' && (
              <div ref={stitchedVideoRef} className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Film className="h-6 w-6" />
                    Full Video
                  </h2>
                  {stitchingStatus === 'loading' && (
                    <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                      Stitching
                    </Badge>
                  )}
                  {stitchingStatus === 'completed' && (
                    <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                      Ready
                    </Badge>
                  )}
                  {stitchingStatus === 'error' && (
                    <Badge className="bg-red-500/10 text-red-400 border-red-500/20">
                      Failed
                    </Badge>
                  )}
                </div>

                <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="text-white">Stitched Video</CardTitle>
                    {stitchedVideo?.videoId && (
                      <CardDescription className="text-gray-400 font-mono text-xs">
                        ID: {stitchedVideo.videoId}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    {stitchingStatus === 'loading' && (
                      <div className="space-y-4">
                        <div className="aspect-video bg-gray-900/50 rounded-lg flex items-center justify-center border border-gray-700">
                          <div className="text-center space-y-3">
                            <Loader2 className="h-12 w-12 text-blue-400 animate-spin mx-auto" />
                            <div className="space-y-1">
                              <p className="text-gray-400 text-sm font-medium">
                                Stitching videos...
                              </p>
                              <p className="text-gray-500 text-xs">
                                Estimated time: {estimatedStitchTime} seconds
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {stitchingStatus === 'completed' && stitchedVideo?.videoUrl && (
                      <div className="space-y-4">
                        <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                          <video
                            src={stitchedVideo.videoUrl}
                            controls
                            className="w-full h-full"
                            preload="metadata"
                          >
                            Your browser does not support the video tag.
                          </video>
                        </div>

                        {stitchedVideo.metadata && (
                          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                            {stitchedVideo.metadata.num_clips !== undefined && (
                              <div className="space-y-1">
                                <p className="text-xs text-gray-500">Clips Stitched</p>
                                <p className="text-sm text-white font-medium">
                                  {stitchedVideo.metadata.num_clips}
                                </p>
                              </div>
                            )}
                            {stitchedVideo.metadata.total_duration !== undefined && (
                              <div className="space-y-1">
                                <p className="text-xs text-gray-500">Total Duration</p>
                                <p className="text-sm text-white font-medium">
                                  {stitchedVideo.metadata.total_duration.toFixed(1)}s
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {stitchingStatus === 'error' && stitchingError && (
                      <div className="space-y-4">
                        <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription className="text-red-300">
                            Failed to stitch videos. Please try again.
                            {stitchingError && (
                              <span className="block mt-1 text-xs text-red-400">
                                Error: {stitchingError}
                              </span>
                            )}
                          </AlertDescription>
                        </Alert>
                        <div className="flex justify-center">
                          <Button
                            onClick={retryStitching}
                            variant="outline"
                            className="border-gray-600 text-white hover:bg-gray-800"
                          >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Retry Stitching
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// SceneVideoCard Component
// ============================================================================

interface SceneVideoCardProps {
  state: SceneVideoState
  jobData: QuickJobData
  teletypeText?: string
  onSkipTeletype: () => void
  onRegenerateScene: () => void
  onRegenerateVideo: () => void
  onStartEditing: () => void
  onSaveEditing: () => void
  onCancelEditing: () => void
  onUpdateEditing: (value: string) => void
}

function SceneVideoCard({
  state,
  jobData,
  teletypeText,
  onSkipTeletype,
  onRegenerateScene,
  onRegenerateVideo,
  onStartEditing,
  onSaveEditing,
  onCancelEditing,
  onUpdateEditing,
}: SceneVideoCardProps) {
  const [isNegativeExpanded, setIsNegativeExpanded] = useState(false)
  const [sceneSnippetIndex, setSceneSnippetIndex] = useState(0)
  const [videoSnippetIndex, setVideoSnippetIndex] = useState(0)

  // Rotate scene loading snippets every 4 seconds
  useEffect(() => {
    if (state.scene.status === 'loading') {
      const interval = setInterval(() => {
        setSceneSnippetIndex(prev => (prev + 1) % SCENE_LOADING_SNIPPETS.length)
      }, 4000)
      return () => clearInterval(interval)
    }
  }, [state.scene.status])

  // Rotate video loading snippets every 12 seconds
  useEffect(() => {
    if (state.video.status === 'loading') {
      const interval = setInterval(() => {
        setVideoSnippetIndex(prev => (prev + 1) % VIDEO_LOADING_SNIPPETS.length)
      }, 12000)
      return () => clearInterval(interval)
    }
  }, [state.video.status])

  const displayDescription = teletypeText !== undefined ? teletypeText : state.scene.description
  const isTeletypeComplete = teletypeText === state.scene.description
  const showCursor = teletypeText !== undefined && !isTeletypeComplete

  return (
    <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-white text-lg">
          Scene {state.sceneIndex + 1}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Responsive Layout: Side-by-side on desktop, stacked on mobile */}
        <div className="flex flex-col md:flex-row gap-6">
          {/* Scene Prompt Section (Left/Top) */}
          <div className="flex-1 space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-gray-300">Scene Prompt</label>
                {state.scene.status === 'completed' && (
                  <div className="flex items-center gap-2">
                    {!state.scene.isEditing && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={onStartEditing}
                          className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-white"
                        >
                          <Edit className="h-3 w-3 mr-1" />
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={onRegenerateScene}
                          className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-white"
                        >
                          <RefreshCw className="h-3 w-3 mr-1" />
                          Regenerate
                        </Button>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Scene Loading State */}
              {state.scene.status === 'loading' && (
                <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-6 min-h-[120px] flex flex-col items-center justify-center">
                  <Loader2 className="h-8 w-8 text-blue-400 animate-spin mb-3" />
                  <p className="text-gray-400 text-sm font-medium mb-1">
                    {SCENE_LOADING_SNIPPETS[sceneSnippetIndex]}
                  </p>
                  <p className="text-gray-500 text-xs">
                    Estimated ~{SCENE_EXPECTED_LOAD_TIME_SECONDS}s
                  </p>
                  <div className="mt-3 text-xs text-gray-600">
                    <p>Context: {jobData.videoDescription.substring(0, 50)}...</p>
                  </div>
                </div>
              )}

              {/* Scene Description (Completed) */}
              {state.scene.status === 'completed' && (
                <>
                  {state.scene.isEditing ? (
                    <div className="space-y-2">
                      <Textarea
                        value={state.scene.editedDescription}
                        onChange={(e) => onUpdateEditing(e.target.value)}
                        className="bg-gray-900/50 border-blue-500/50 text-white min-h-[120px] focus:border-blue-400"
                        placeholder="Edit scene description..."
                      />
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={onSaveEditing}
                          disabled={!state.scene.editedDescription?.trim()}
                          className="bg-green-600 hover:bg-green-700 text-white"
                        >
                          <Save className="h-3 w-3 mr-1" />
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={onCancelEditing}
                          className="border-gray-600 text-gray-300 hover:bg-gray-700"
                        >
                          <X className="h-3 w-3 mr-1" />
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div
                      className="bg-gray-900/50 border border-gray-700 rounded-lg p-4 min-h-[120px] cursor-pointer hover:border-gray-600 transition-colors"
                      onClick={isTeletypeComplete ? undefined : onSkipTeletype}
                    >
                      <p className="text-white text-base leading-relaxed whitespace-pre-wrap">
                        {displayDescription}
                        {showCursor && <span className="animate-pulse">|</span>}
                      </p>
                      {!isTeletypeComplete && (
                        <p className="text-xs text-gray-500 mt-2">Click to skip animation</p>
                      )}
                    </div>
                  )}

                  {/* Negative Description - Collapsible */}
                  <div className="space-y-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setIsNegativeExpanded(!isNegativeExpanded)}
                      className="text-gray-400 hover:text-white p-0 h-auto"
                    >
                      <span className="text-xs font-medium">Negative Prompt</span>
                      {isNegativeExpanded ? (
                        <ChevronUp className="h-3 w-3 ml-1" />
                      ) : (
                        <ChevronDown className="h-3 w-3 ml-1" />
                      )}
                    </Button>
                    {isNegativeExpanded && (
                      <div className="bg-gray-900/50 border border-red-900/30 rounded-lg p-3">
                        <p className="text-gray-300 text-sm whitespace-pre-wrap">
                          {state.scene.negative_description}
                        </p>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Scene Error State */}
              {state.scene.status === 'error' && state.scene.error && (
                <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-300">
                    {state.scene.error}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </div>

          {/* Video Section (Right/Bottom) */}
          <div className="flex-1 space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-gray-300">Video Clip</label>
                {state.video.status === 'completed' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onRegenerateVideo}
                    className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-white"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Regenerate
                  </Button>
                )}
              </div>

              {/* Video Idle State */}
              {state.video.status === 'idle' && (
                <div className="aspect-video bg-gray-900/50 rounded-lg flex items-center justify-center border border-gray-700/50">
                  <p className="text-gray-500 text-sm">Waiting for scene...</p>
                </div>
              )}

              {/* Video Loading State */}
              {state.video.status === 'loading' && (
                <div className="aspect-video bg-gray-900/50 rounded-lg flex items-center justify-center border border-gray-700">
                  <div className="text-center space-y-3 px-4">
                    <Loader2 className="h-10 w-10 text-blue-400 animate-spin mx-auto" />
                    <p className="text-gray-400 text-sm font-medium">
                      {VIDEO_LOADING_SNIPPETS[videoSnippetIndex]}
                    </p>
                    <p className="text-gray-500 text-xs">
                      Estimated ~{Math.floor(VIDEO_EXPECTED_LOAD_TIME_SECONDS / 60)} min
                    </p>
                    <div className="text-xs text-gray-600">
                      <p className="line-clamp-2">
                        Generating: {state.scene.description.substring(0, 60)}...
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Video Completed State */}
              {state.video.status === 'completed' && state.video.videoUrl && (
                <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                  <video
                    src={state.video.videoUrl}
                    controls
                    className="w-full h-full"
                    preload="metadata"
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
              )}

              {/* Video Error State */}
              {state.video.status === 'error' && state.video.error && (
                <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-300">
                    {state.video.error}
                  </AlertDescription>
                </Alert>
              )}

              {state.video.videoId && (
                <p className="text-xs text-gray-500 font-mono">ID: {state.video.videoId}</p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
