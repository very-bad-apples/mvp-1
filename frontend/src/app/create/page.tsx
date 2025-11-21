'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ImageUploadZone } from '@/components/ImageUploadZone'
import { AudioUploadZone } from '@/components/AudioUploadZone'
import { YouTubeAudioDownloader } from '@/components/YouTubeAudioDownloader'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Sparkles, Video, ChevronLeft, Loader2, ImageIcon, RefreshCw, CheckCircle2, AlertCircle, Zap, ChevronDown, ChevronUp } from 'lucide-react'
import { useToast } from '@/hooks/useToast'
import { createProject, getConfigFlavors, getDirectorConfigs, generateCharacterReference } from '@/lib/api/client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

type Mode = 'ad-creative' | 'music-video'

export default function CreatePage() {
  const router = useRouter()
  const { toast } = useToast()
  const [mode, setMode] = useState<Mode>('music-video')
  const [prompt, setPrompt] = useState('')
  const [characterDescription, setCharacterDescription] = useState('')
  const [uploadedImages, setUploadedImages] = useState<File[]>([])
  const [uploadedAudio, setUploadedAudio] = useState<File | null>(null)
  const [downloadedAudioId, setDownloadedAudioId] = useState<string>('')
  const [downloadedAudioUrl, setDownloadedAudioUrl] = useState<string>('')
  const [audioSource, setAudioSource] = useState<'upload' | 'youtube'>('upload')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [useAICharacter, setUseAICharacter] = useState(true)
  const [generatedImages, setGeneratedImages] = useState<string[]>([])
  const [generatedImageIds, setGeneratedImageIds] = useState<string[]>([])
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null)
  const [isGeneratingImages, setIsGeneratingImages] = useState(false)
  const [imageGenerationError, setImageGenerationError] = useState<string | null>(null)
  const [generationAttempts, setGenerationAttempts] = useState(0)

  // Config flavor state
  const [isConfigExpanded, setIsConfigExpanded] = useState(false)
  const [configFlavor, setConfigFlavor] = useState<string>('default')
  const [availableFlavors, setAvailableFlavors] = useState<string[]>(['default'])
  const [isFetchingFlavors, setIsFetchingFlavors] = useState(false)

  // Director config state
  const [directorConfig, setDirectorConfig] = useState<string>('')
  const [availableDirectorConfigs, setAvailableDirectorConfigs] = useState<string[]>([])
  const [isFetchingDirectorConfigs, setIsFetchingDirectorConfigs] = useState(false)

  // Audio trimming state
  const [startAt, setStartAt] = useState<number>(0)
  const [isTrimming, setIsTrimming] = useState(false)

  // Fetch available config flavors on mount
  useEffect(() => {
    const fetchConfigFlavors = async () => {
      setIsFetchingFlavors(true)
      try {
        const data = await getConfigFlavors()
        if (data.flavors && Array.isArray(data.flavors)) {
          setAvailableFlavors(data.flavors)
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

  // Fetch available director configs on mount
  useEffect(() => {
    const fetchDirectorConfigs = async () => {
      setIsFetchingDirectorConfigs(true)
      try {
        const data = await getDirectorConfigs()
        if (data.configs && Array.isArray(data.configs)) {
          setAvailableDirectorConfigs(data.configs)
        }
      } catch (error) {
        console.error('Failed to fetch director configs:', error)
        // Keep empty array as fallback
      } finally {
        setIsFetchingDirectorConfigs(false)
      }
    }

    fetchDirectorConfigs()
  }, [])

  // Cleanup blob URLs on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      generatedImages.forEach(url => {
        if (url.startsWith('blob:')) {
          URL.revokeObjectURL(url)
        }
      })
    }
  }, [generatedImages])

  // Check if form is valid and ready to submit
  const isFormValid = () => {
    // Check video description
    if (!prompt.trim()) return false

    // Check mode-specific requirements
    if (mode === 'ad-creative' && uploadedImages.length === 0) return false
    if (mode === 'music-video') {
      if (audioSource === 'upload' && !uploadedAudio) return false
      if (audioSource === 'youtube' && !downloadedAudioId) return false
    }

    // Check AI character requirements
    if (useAICharacter && selectedImageIndex === null) return false

    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation with detailed error messages
    if (!prompt.trim()) {
      toast({
        title: "Error",
        description: "Please provide a video description",
        variant: "destructive",
      })
      return
    }

    if (mode === 'ad-creative' && uploadedImages.length === 0) {
      toast({
        title: "Error",
        description: "Please upload at least one product image",
        variant: "destructive",
      })
      return
    }

    if (mode === 'music-video') {
      if (audioSource === 'upload' && !uploadedAudio) {
        toast({
          title: "Error",
          description: "Please upload a music file",
          variant: "destructive",
        })
        return
      }
      if (audioSource === 'youtube' && !downloadedAudioId) {
        toast({
          title: "Error",
          description: "Please download audio from YouTube",
          variant: "destructive",
        })
        return
      }
    }

    if (useAICharacter && selectedImageIndex === null) {
      toast({
        title: "Error",
        description: "Please generate and select a character image",
        variant: "destructive",
      })
      return
    }

    setIsSubmitting(true)

    try {
      // Get character reference image ID if using AI character
      const characterReferenceImageId = useAICharacter && selectedImageIndex !== null && generatedImageIds[selectedImageIndex]
        ? generatedImageIds[selectedImageIndex]
        : null

      // Prepare files for upload
      let audioFile: File | undefined = undefined

      if (mode === 'music-video') {
        if (audioSource === 'upload' && uploadedAudio) {
          // Use uploaded audio file directly
          audioFile = uploadedAudio
        } else if (audioSource === 'youtube' && downloadedAudioId) {
          // Fetch YouTube audio file from backend and convert to File
          try {
            const audioResponse = await fetch(`${API_URL}/api/audio/get/${downloadedAudioId}`, {
              headers: API_KEY ? { 'X-API-Key': API_KEY } : {},
            })

            if (!audioResponse.ok) {
              throw new Error(`Failed to fetch audio file: ${audioResponse.statusText}`)
            }

            const audioBlob = await audioResponse.blob()
            // Create a File from the blob with a proper filename
            audioFile = new File([audioBlob], `${downloadedAudioId}.mp3`, { type: 'audio/mpeg' })
          } catch (error) {
            console.error('Error fetching YouTube audio:', error)
            toast({
              title: "Error",
              description: "Failed to fetch audio file. Please try again.",
              variant: "destructive",
            })
            setIsSubmitting(false)
            return
          }
        }
      }

      // Call the createProject API
      const response = await createProject({
        mode,
        prompt: prompt.trim(),
        characterDescription: characterDescription.trim() || 'No character description provided',
        characterReferenceImageId,
        directorConfig: directorConfig || undefined,
        images: mode === 'ad-creative' ? uploadedImages : undefined,
        audio: audioFile,
      })

      toast({
        title: "Project created successfully!",
        description: response.message,
      })

      // Navigate to the project page
      router.push(`/project/${response.projectId}`)
    } catch (error) {
      console.error('Error submitting form:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create project",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleQuickJob = () => {
    // Get character reference image ID if using AI character and image is selected
    const characterReferenceImageId = useAICharacter && selectedImageIndex !== null && generatedImageIds[selectedImageIndex]
      ? generatedImageIds[selectedImageIndex]
      : undefined

    // Store form data in sessionStorage before navigating
    const quickJobData = {
      videoDescription: prompt,
      characterDescription: characterDescription,
      characterReferenceImageId,
      // Include audio data if YouTube audio was downloaded
      audioId: audioSource === 'youtube' ? downloadedAudioId : undefined,
      audioUrl: audioSource === 'youtube' ? downloadedAudioUrl : undefined,
      configFlavor: configFlavor,
      directorConfig: directorConfig || undefined,
    }
    sessionStorage.setItem('quickJobData', JSON.stringify(quickJobData))
    router.push('/quick-gen-page')
  }

  const handleGenerateImages = async () => {
    if (!characterDescription.trim()) {
      toast({
        title: "Error",
        description: "Please enter or generate a character description first",
        variant: "destructive",
      })
      return
    }

    setIsGeneratingImages(true)
    setSelectedImageIndex(null) // Reset selection
    setImageGenerationError(null) // Clear previous errors

    // Clean up previous blob URLs to prevent memory leaks
    generatedImages.forEach(url => {
      if (url.startsWith('blob:')) {
        URL.revokeObjectURL(url)
      }
    })
    setGeneratedImages([])
    setGeneratedImageIds([])

    try {
      const data = await generateCharacterReference({
        character_description: characterDescription.trim(),
        num_images: 4, // Request 4 images for selection
      })

      // Fetch images using their IDs (backend no longer returns base64 for performance)
      const blobUrls: string[] = []
      const imageIds: string[] = []

      for (const image of data.images) {
        imageIds.push(image.id)
        
        // If cloud_url is available, use it directly
        if (image.cloud_url) {
          blobUrls.push(image.cloud_url)
        } else {
          // Otherwise, fetch the image from the backend
          try {
            const response = await fetch(`${API_URL}/api/mv/get_character_reference/${image.id}?redirect=false`, {
              headers: API_KEY ? { 'X-API-Key': API_KEY } : {},
            })

            if (!response.ok) {
              throw new Error(`Failed to fetch image ${image.id}`)
            }

            const contentType = response.headers.get('content-type')
            
            if (contentType?.includes('application/json')) {
              // Cloud storage mode - get presigned URL from JSON
              const jsonData = await response.json()
              blobUrls.push(jsonData.image_url || jsonData.video_url)
            } else {
              // Local storage mode - create object URL from blob
              const blob = await response.blob()
              const objectUrl = URL.createObjectURL(blob)
              blobUrls.push(objectUrl)
            }
          } catch (fetchError) {
            console.error(`Failed to fetch image ${image.id}:`, fetchError)
            // Continue with other images, but this one will be missing
            blobUrls.push('') // Placeholder to maintain array index alignment
          }
        }
      }

      // Filter out any failed image fetches
      const validPairs = imageIds.map((id, index) => ({ id, url: blobUrls[index] }))
        .filter(pair => pair.url)
      
      const validIds = validPairs.map(pair => pair.id)
      const validUrls = validPairs.map(pair => pair.url)

      if (validIds.length === 0) {
        throw new Error('Failed to fetch any character reference images')
      }

      setGeneratedImages(validUrls)
      setGeneratedImageIds(validIds)
      setGenerationAttempts(prev => prev + 1)

      toast({
        title: "Character Images Generated",
        description: `${validIds.length} character references ready. Click to select one.`,
      })
    } catch (error) {
      console.error('Error generating images:', error)
      const errorMessage = error instanceof Error ? error.message : "Failed to generate character images. Please try again."
      setImageGenerationError(errorMessage)

      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsGeneratingImages(false)
    }
  }

  const handleTrimAudio = async () => {
    // Validate that we have an audio file
    const audioId = downloadedAudioId || uploadedAudio?.name
    if (!downloadedAudioId) {
      toast({
        title: "Error",
        description: "No audio file loaded. Please upload or download audio first.",
        variant: "destructive",
      })
      return
    }

    // Validate start_at value
    if (startAt < 0) {
      toast({
        title: "Error",
        description: "Start position must be 0 or greater",
        variant: "destructive",
      })
      return
    }

    setIsTrimming(true)

    try {
      const response = await fetch(`${API_URL}/api/audio/trim`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { 'X-API-Key': API_KEY } : {})
        },
        body: JSON.stringify({
          audio_id: downloadedAudioId,
          start_at: startAt
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail?.message || `Trim failed: ${response.statusText}`)
      }

      const data = await response.json()

      // Replace audio with trimmed version
      setDownloadedAudioId(data.audio_id)
      setDownloadedAudioUrl(data.audio_url)

      toast({
        title: "Audio Trimmed",
        description: `Audio trimmed from ${startAt}s. New audio ready to use.`,
      })

    } catch (error) {
      console.error("Audio trim error:", error)
      toast({
        title: "Trim Failed",
        description: error instanceof Error ? error.message : "Failed to trim audio",
        variant: "destructive",
      })
    } finally {
      setIsTrimming(false)
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
            <Link href="/">
              <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
                <ChevronLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="min-h-screen p-4 md:p-8 flex items-center justify-center">
        <div className="w-full max-w-3xl">
          <div className="mb-8 text-center">
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
              AI Video Generation
            </h1>
            <p className="text-gray-300">
              Create stunning video content with AI-powered generation
            </p>
          </div>

          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 md:p-8 shadow-lg backdrop-blur-sm">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Mode Toggle */}
              <div className="space-y-3">
                <Label className="text-sm font-medium text-white">Generation Mode</Label>
                <Tabs
                  value={mode}
                  onValueChange={(value) => setMode(value as Mode)}
                  className="w-full"
                >
                  <TabsList className="grid w-full grid-cols-2 h-12 bg-gray-900/50">
                    <TabsTrigger
                      value="music-video"
                      className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                    >
                      Music Video
                    </TabsTrigger>
                    <TabsTrigger
                      value="ad-creative"
                      className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                    >
                      Ad Creative
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>

              {/* Configuration Section - Collapsible */}
              <Collapsible
                open={isConfigExpanded}
                onOpenChange={setIsConfigExpanded}
                className="space-y-3"
              >
                <CollapsibleTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full flex items-center justify-between p-3 bg-gray-900/30 hover:bg-gray-900/50 border border-gray-700 rounded-lg transition-colors"
                  >
                    <span className="text-sm font-medium text-white">Configuration</span>
                    {isConfigExpanded ? (
                      <ChevronUp className="h-4 w-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    )}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 pt-2">
                  <div className="p-4 bg-gray-900/30 border border-gray-700 rounded-lg space-y-3">
                    {/* Config Flavor Select */}
                    <div className="space-y-2">
                      <Label htmlFor="config-flavor" className="text-sm font-medium text-white">
                        Config Flavor
                      </Label>
                      <Select
                        value={configFlavor}
                        onValueChange={setConfigFlavor}
                        disabled={isFetchingFlavors}
                      >
                        <SelectTrigger
                          id="config-flavor"
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
                        Choose the configuration profile for video generation
                      </p>
                    </div>

                    {/* Director Config Selector */}
                    <div className="space-y-2">
                      <Label htmlFor="director-config" className="text-sm font-medium text-white">
                        Director Config (Optional)
                      </Label>
                      <Select
                        value={directorConfig || undefined}
                        onValueChange={(value) => setDirectorConfig(value || '')}
                        disabled={isFetchingDirectorConfigs}
                      >
                        <SelectTrigger
                          id="director-config"
                          className="w-full bg-gray-800 border-gray-600 text-white"
                        >
                          <SelectValue placeholder={isFetchingDirectorConfigs ? "Loading..." : "None (optional)"} />
                        </SelectTrigger>
                        <SelectContent className="bg-gray-800 border-gray-600">
                          {availableDirectorConfigs.length > 0 ? (
                            availableDirectorConfigs.map((config) => (
                              <SelectItem
                                key={config}
                                value={config}
                                className="text-white hover:bg-gray-700"
                              >
                                {config}
                              </SelectItem>
                            ))
                          ) : (
                            <SelectItem
                              value="no-configs"
                              disabled
                              className="text-gray-500"
                            >
                              No configs available
                            </SelectItem>
                          )}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-gray-400">
                        Choose a creative direction template (e.g., Wes-Anderson, David-Lynch)
                      </p>
                    </div>

                    {/* Audio Trim Section - Only show for music-video mode with downloaded audio */}
                    {mode === 'music-video' && audioSource === 'youtube' && downloadedAudioId && (
                      <div className="space-y-2 pt-3 border-t border-gray-700">
                        <Label htmlFor="start-at" className="text-sm font-medium text-white">
                          Audio Start Position (seconds)
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            id="start-at"
                            type="number"
                            min="0"
                            step="1"
                            value={startAt}
                            onChange={(e) => setStartAt(parseInt(e.target.value) || 0)}
                            disabled={isTrimming}
                            className="flex-1 bg-gray-800 border-gray-600 text-white"
                            placeholder="0"
                          />
                          <Button
                            type="button"
                            onClick={handleTrimAudio}
                            disabled={isTrimming || !downloadedAudioId}
                            className="bg-purple-600 hover:bg-purple-700 text-white"
                          >
                            {isTrimming ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Trimming...
                              </>
                            ) : (
                              'Trim Audio'
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-gray-400">
                          Trim audio from this start position (in seconds) to the end. Creates a new audio file.
                        </p>
                      </div>
                    )}
                  </div>
                </CollapsibleContent>
              </Collapsible>

              {/* Mode-Specific Upload Zone */}
              <div className="space-y-3">
                <div className="flex items-center gap-1">
                  <Label className="text-sm font-medium text-white">
                    {mode === 'ad-creative' ? 'Product Images' : 'Music Source'}
                  </Label>
                  <span className="text-red-400 text-sm">*</span>
                </div>
                {mode === 'ad-creative' ? (
                  <div>
                    <ImageUploadZone
                      onFilesChange={setUploadedImages}
                      files={uploadedImages}
                    />
                    {uploadedImages.length === 0 && (
                      <p className="text-xs text-red-400 mt-2">
                        At least one product image is required
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Audio Source Tabs */}
                    <Tabs
                      value={audioSource}
                      onValueChange={(value) => {
                        setAudioSource(value as 'upload' | 'youtube')
                        // Clear the other source when switching
                        if (value === 'upload') {
                          setDownloadedAudioId('')
                          setDownloadedAudioUrl('')
                        } else {
                          setUploadedAudio(null)
                        }
                      }}
                      className="w-full"
                    >
                      <TabsList className="grid w-full grid-cols-2 h-10 bg-gray-900/50">
                        <TabsTrigger
                          value="upload"
                          className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                        >
                          Upload File
                        </TabsTrigger>
                        <TabsTrigger
                          value="youtube"
                          className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                        >
                          YouTube URL
                        </TabsTrigger>
                      </TabsList>
                    </Tabs>

                    {/* Audio Upload Zone */}
                    {audioSource === 'upload' && (
                      <div>
                        <AudioUploadZone
                          onFileChange={setUploadedAudio}
                          file={uploadedAudio}
                        />
                        {!uploadedAudio && (
                          <p className="text-xs text-red-400 mt-2">
                            Music file is required
                          </p>
                        )}
                      </div>
                    )}

                    {/* YouTube Downloader */}
                    {audioSource === 'youtube' && (
                      <div>
                        <YouTubeAudioDownloader
                          onAudioDownloaded={(audioId, audioUrl) => {
                            setDownloadedAudioId(audioId)
                            setDownloadedAudioUrl(audioUrl)
                          }}
                          currentAudioId={downloadedAudioId}
                          currentAudioUrl={downloadedAudioUrl}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* User Prompt */}
              <div className="space-y-3">
                <div className="flex items-center gap-1">
                  <Label htmlFor="prompt" className="text-sm font-medium text-white">
                    Video Description
                  </Label>
                  <span className="text-red-400 text-sm">*</span>
                </div>
                <Textarea
                  id="prompt"
                  placeholder={
                    mode === 'ad-creative'
                      ? 'Describe your product video ad... e.g., "Show the product rotating 360 degrees with dramatic lighting and smooth camera movements"'
                      : 'Describe your music video vision... e.g., "Create a cinematic music video with urban street scenes and dynamic transitions"'
                  }
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[120px] resize-none bg-gray-900/50 border-gray-600 text-white placeholder:text-gray-500"
                  required
                />
                <p className="text-xs text-gray-400">
                  Be specific about scenes, camera angles, and visual style
                </p>
              </div>

              {/* Character Description with AI Toggle */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="character" className="text-sm font-medium text-white">
                    Character & Style
                  </Label>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="ai-toggle" className="text-sm text-gray-400 cursor-pointer">
                      Use AI Generation
                    </Label>
                    <Switch
                      id="ai-toggle"
                      checked={useAICharacter}
                      onCheckedChange={setUseAICharacter}
                      className="data-[state=checked]:bg-blue-600"
                    />
                  </div>
                </div>

                {useAICharacter && (
                  <div className="space-y-4">
                    {/* Character Description Input */}
                    <Textarea
                      id="character"
                      placeholder={
                        mode === 'ad-creative'
                          ? 'Describe visual style, colors, mood... e.g., "Modern minimalist aesthetic with bold colors and clean backgrounds"'
                          : 'Describe performers, setting, atmosphere... e.g., "Solo artist in black and white cinematography with moody lighting"'
                      }
                      value={characterDescription}
                      onChange={(e) => {
                        setCharacterDescription(e.target.value)
                        // Reset generated images when description changes
                        if (generatedImages.length > 0) {
                          setGeneratedImages([])
                          setSelectedImageIndex(null)
                        }
                      }}
                      className="min-h-[100px] resize-none bg-gray-900/50 border-gray-600 text-white placeholder:text-gray-500"
                    />

                    {/* Error Display */}
                    {imageGenerationError && !isGeneratingImages && (
                      <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription className="text-red-300">
                          {imageGenerationError}
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Loading Skeleton */}
                    {isGeneratingImages && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <Skeleton className="aspect-square rounded-lg bg-gray-700/50" />
                          <Skeleton className="aspect-square rounded-lg bg-gray-700/50" />
                          <Skeleton className="aspect-square rounded-lg bg-gray-700/50" />
                          <Skeleton className="aspect-square rounded-lg bg-gray-700/50" />
                        </div>
                        <p className="text-sm text-gray-400 text-center">
                          Generating 4 character images... This may take 30-60 seconds.
                        </p>
                      </div>
                    )}

                    {/* Generated Images Grid - Above the button */}
                    {generatedImages.length > 0 && !isGeneratingImages && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          {generatedImages.map((imageUrl, index) => (
                            <button
                              key={index}
                              type="button"
                              onClick={() => setSelectedImageIndex(index)}
                              className={`relative aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                                selectedImageIndex === index
                                  ? 'border-blue-500 ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-900'
                                  : 'border-gray-600 hover:border-gray-500'
                              }`}
                            >
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img
                                src={imageUrl}
                                alt={`Character option ${index + 1}`}
                                className="w-full h-full object-cover"
                              />
                              {selectedImageIndex === index && (
                                <div className="absolute inset-0 bg-blue-500/20 flex items-center justify-center">
                                  <div className="bg-blue-500 rounded-full p-2">
                                    <CheckCircle2 className="h-6 w-6 text-white" />
                                  </div>
                                </div>
                              )}
                              <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-2 text-center">
                                <span className="text-xs text-white">Option {index + 1}</span>
                              </div>
                            </button>
                          ))}
                        </div>

                        {selectedImageIndex !== null && (
                          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
                            <p className="text-sm text-blue-400 font-medium">
                              Character image selected! You can now generate your video.
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Generate/Regenerate Images Button */}
                    <div>
                      <Button
                        type="button"
                        onClick={handleGenerateImages}
                        disabled={isGeneratingImages || !characterDescription.trim()}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        {isGeneratingImages ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Generating Character Images...
                          </>
                        ) : (
                          <>
                            {generatedImages.length > 0 ? (
                              <>
                                <RefreshCw className="mr-2 h-4 w-4" />
                                Regenerate Character Images
                              </>
                            ) : (
                              <>
                                <ImageIcon className="mr-2 h-4 w-4" />
                                Generate Character Images
                              </>
                            )}
                          </>
                        )}
                      </Button>
                    </div>

                    <p className="text-xs text-gray-400">
                      {!characterDescription.trim()
                        ? "Enter character style details, then click 'Generate Character Images'"
                        : generatedImages.length === 0
                        ? "Click 'Generate Character Images' to create visual options"
                        : "Select an image to proceed, or click the button to regenerate"}
                    </p>
                  </div>
                )}

                {!useAICharacter && (
                  <p className="text-xs text-gray-400">
                    Enable &quot;Use AI Generation&quot; to add character and style details
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <div className="space-y-2">
                <Button
                  type="submit"
                  size="lg"
                  className="w-full h-12 text-base font-medium bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isSubmitting || !isFormValid()}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Generating Video...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-5 w-5" />
                      Generate Video
                    </>
                  )}
                </Button>

                {/* Quick Job Button */}
                <Button
                  type="button"
                  size="lg"
                  onClick={handleQuickJob}
                  className="w-full h-12 text-base font-medium bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Zap className="mr-2 h-5 w-5" />
                  Quick Job
                </Button>

                {/* Validation Messages */}
                {!isFormValid() && !isSubmitting && (
                  <div className="space-y-1">
                    {!prompt.trim() && (
                      <p className="text-xs text-yellow-400 text-center">
                        Video description is required
                      </p>
                    )}
                    {mode === 'ad-creative' && uploadedImages.length === 0 && (
                      <p className="text-xs text-yellow-400 text-center">
                        Please upload at least one product image
                      </p>
                    )}
                    {mode === 'music-video' && (
                      <>
                        {audioSource === 'upload' && !uploadedAudio && (
                          <p className="text-xs text-yellow-400 text-center">
                            Please upload a music file
                          </p>
                        )}
                        {audioSource === 'youtube' && !downloadedAudioId && (
                          <p className="text-xs text-yellow-400 text-center">
                            Audio is required
                          </p>
                        )}
                      </>
                    )}
                    {useAICharacter && selectedImageIndex === null && generatedImages.length > 0 && (
                      <p className="text-xs text-yellow-400 text-center">
                        Please select a character image to continue
                      </p>
                    )}
                    {useAICharacter && generatedImages.length === 0 && characterDescription.trim() && (
                      <p className="text-xs text-yellow-400 text-center">
                        Please generate and select a character image to continue
                      </p>
                    )}
                  </div>
                )}
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}
