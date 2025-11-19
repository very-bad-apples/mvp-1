'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { ImageUploadZone } from '@/components/ImageUploadZone'
import { AudioUploadZone } from '@/components/AudioUploadZone'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Sparkles, Video, ChevronLeft, Loader2, ImageIcon, RefreshCw, CheckCircle2, AlertCircle, Zap } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

type Mode = 'ad-creative' | 'music-video'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

export default function CreatePage() {
  const router = useRouter()
  const { toast } = useToast()
  const [mode, setMode] = useState<Mode>('music-video')
  const [prompt, setPrompt] = useState('')
  const [characterDescription, setCharacterDescription] = useState('')
  const [uploadedImages, setUploadedImages] = useState<File[]>([])
  const [uploadedAudio, setUploadedAudio] = useState<File | null>(null)
  const [youtubeUrl, setYoutubeUrl] = useState<string>('')
  const [convertedAudioFile, setConvertedAudioFile] = useState<File | null>(null)
  const [isConvertingAudio, setIsConvertingAudio] = useState(false)
  const [audioSource, setAudioSource] = useState<'upload' | 'youtube'>('youtube')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [useAICharacter, setUseAICharacter] = useState(true)
  const [generatedImages, setGeneratedImages] = useState<string[]>([])
  const [generatedImageIds, setGeneratedImageIds] = useState<string[]>([])
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null)
  const [isGeneratingImages, setIsGeneratingImages] = useState(false)
  const [imageGenerationError, setImageGenerationError] = useState<string | null>(null)
  const [generationAttempts, setGenerationAttempts] = useState(0)
  const [imageLoadingStates, setImageLoadingStates] = useState<{ [imageId: string]: 'loading' | 'loaded' | 'error' }>({})

  // Update useAICharacter default when mode changes
  useEffect(() => {
    if (mode === 'music-video') {
      setUseAICharacter(true)
    } else if (mode === 'ad-creative') {
      setUseAICharacter(false)
    }
  }, [mode])

  // Note: Blob URL cleanup removed in v10 - images now fetched directly from backend

  // Check if form is valid and ready to submit
  const isFormValid = () => {
    // Check video description
    if (!prompt.trim()) return false

    // Check mode-specific requirements
    if (mode === 'ad-creative' && uploadedImages.length === 0) return false
    if (mode === 'music-video') {
      if (audioSource === 'upload' && !uploadedAudio) return false
      if (audioSource === 'youtube' && !convertedAudioFile) return false
    }

    // Check AI character requirements - only required for ad-creative mode
    if (mode === 'ad-creative' && useAICharacter && selectedImageIndex === null) return false

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
      if (audioSource === 'youtube' && !convertedAudioFile) {
        toast({
          title: "Error",
          description: "Please convert YouTube audio first",
          variant: "destructive",
        })
        return
      }
    }

    // Character image selection only required for ad-creative mode
    if (mode === 'ad-creative' && useAICharacter && selectedImageIndex === null) {
      toast({
        title: "Error",
        description: "Please generate and select a character image",
        variant: "destructive",
      })
      return
    }

    setIsSubmitting(true)

    try {
      // Prepare FormData for the API
      const formData = new FormData()
      formData.append('mode', mode)
      formData.append('prompt', prompt)
      formData.append('characterDescription', characterDescription)

      if (mode === 'ad-creative') {
        uploadedImages.forEach((image, index) => {
          formData.append(`images`, image)
        })
      } else {
        // Music video mode - send audio file (either uploaded or converted from YouTube)
        const audioFile = audioSource === 'upload' ? uploadedAudio : convertedAudioFile
        if (audioFile) {
          formData.append('audio', audioFile)
        }
      }

      // Add selected character reference image ID if using AI character
      if (useAICharacter && selectedImageIndex !== null && generatedImageIds[selectedImageIndex]) {
        formData.append('characterReferenceImageId', generatedImageIds[selectedImageIndex])
      }

      // Call the real API endpoint
      const response = await fetch(`${API_URL}/api/mv/projects`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_KEY,
        },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        const errorMessage = errorData.detail?.message || errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        throw new Error(errorMessage)
      }

      const data = await response.json()
      const projectId = data.projectId

      toast({
        title: "Project created successfully!",
        description: `Project ID: ${projectId}`,
      })

      // Navigate to the project result page
      router.push(`/result/${projectId}`)
    } catch (error) {
      console.error('Error submitting form:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start video generation",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleQuickJob = () => {
    // Store form data in sessionStorage before navigating
    const quickJobData = {
      videoDescription: prompt,
      characterDescription: characterDescription,
      characterReferenceImageId: selectedImageIndex !== null ? generatedImageIds[selectedImageIndex] : '',
      // Include YouTube URL for music-video mode
      youtubeUrl: audioSource === 'youtube' ? youtubeUrl : undefined,
    }
    sessionStorage.setItem('quickJobData', JSON.stringify(quickJobData))
    router.push('/quick-gen-page')
  }

  /**
   * Fetch a single character reference image by ID.
   * Uses redirect=false to get JSON response (cloud) or direct file (local).
   */
  const fetchCharacterImage = async (imageId: string): Promise<string> => {
    const response = await fetch(`${API_URL}/api/mv/get_character_reference/${imageId}?redirect=false`, {
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch image ${imageId}`)
    }

    // For cloud storage: response is JSON with image_url
    // For local storage: response is the image file directly
    const contentType = response.headers.get('content-type')

    if (contentType?.includes('application/json')) {
      // Cloud storage mode - get presigned URL from JSON
      const data = await response.json()
      return data.image_url || data.video_url // video_url is legacy field name
    } else {
      // Local storage mode - create object URL from blob
      const blob = await response.blob()
      return URL.createObjectURL(blob)
    }
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
    setGeneratedImages([])
    setGeneratedImageIds([])
    setImageLoadingStates({})

    try {
      // Step 1: Generate images and get image IDs (no base64 in v10)
      const response = await fetch(`${API_URL}/api/mv/generate_character_reference`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          character_description: characterDescription.trim(),
          num_images: 4, // Request 4 images for selection
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
        throw new Error(errorData.detail?.message || errorData.error || 'Failed to generate character images')
      }

      const data = await response.json()
      const imageIds = data.images.map((img: any) => img.id)

      // Initialize image IDs and placeholder URLs
      setGeneratedImageIds(imageIds)
      setGeneratedImages(new Array(imageIds.length).fill('')) // Placeholder empty strings

      // Initialize all images as loading
      const initialLoadingStates: { [key: string]: 'loading' | 'loaded' | 'error' } = {}
      imageIds.forEach((id: string) => {
        initialLoadingStates[id] = 'loading'
      })
      setImageLoadingStates(initialLoadingStates)

      // Step 2: Fetch all images in parallel
      const fetchPromises = imageIds.map(async (imageId: string, index: number) => {
        try {
          const imageUrl = await fetchCharacterImage(imageId)

          // Update the specific image URL
          setGeneratedImages(prev => {
            const newImages = [...prev]
            newImages[index] = imageUrl
            return newImages
          })

          // Update loading state to loaded
          setImageLoadingStates(prev => ({
            ...prev,
            [imageId]: 'loaded'
          }))
        } catch (error) {
          console.error(`Failed to fetch image ${imageId}:`, error)

          // Update loading state to error
          setImageLoadingStates(prev => ({
            ...prev,
            [imageId]: 'error'
          }))
        }
      })

      // Wait for all fetches to complete
      await Promise.allSettled(fetchPromises)

      setGenerationAttempts(prev => prev + 1)

      toast({
        title: "Character Images Generated",
        description: `${imageIds.length} character references ready. Click to select one.`,
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
                      value="ad-creative"
                      className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                    >
                      Ad Creative
                    </TabsTrigger>
                    <TabsTrigger
                      value="music-video"
                      className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                    >
                      Music Video
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>

              {/* Mode-Specific Upload Zone */}
              {mode === 'ad-creative' && (
                <div className="space-y-3">
                  <div className="flex items-center gap-1">
                    <Label className="text-sm font-medium text-white">
                      Product Images
                    </Label>
                    <span className="text-red-400 text-sm">*</span>
                  </div>
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
                </div>
              )}

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
                    Character & Style{mode === 'music-video' ? ' (Optional)' : ''}
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

                {(useAICharacter || mode === 'music-video') && (
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
                    {generatedImageIds.length > 0 && !isGeneratingImages && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          {generatedImageIds.map((imageId, index) => {
                            const imageUrl = generatedImages[index]
                            const loadingState = imageLoadingStates[imageId]

                            return (
                              <button
                                key={imageId}
                                type="button"
                                onClick={() => {
                                  if (loadingState === 'loaded') {
                                    setSelectedImageIndex(index)
                                  }
                                }}
                                disabled={loadingState !== 'loaded'}
                                className={`relative aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                                  selectedImageIndex === index && loadingState === 'loaded'
                                    ? 'border-blue-500 ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-900'
                                    : 'border-gray-600 hover:border-gray-500'
                                } ${loadingState !== 'loaded' ? 'cursor-not-allowed' : ''}`}
                              >
                                {/* Loading State */}
                                {loadingState === 'loading' && (
                                  <div className="absolute inset-0 bg-gray-800/50 flex items-center justify-center">
                                    <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
                                  </div>
                                )}

                                {/* Error State */}
                                {loadingState === 'error' && (
                                  <div className="absolute inset-0 bg-gray-900/90 flex flex-col items-center justify-center p-4">
                                    <AlertCircle className="h-8 w-8 text-red-400 mb-2" />
                                    <span className="text-xs text-red-300 text-center">Failed to load image</span>
                                  </div>
                                )}

                                {/* Loaded Image */}
                                {loadingState === 'loaded' && imageUrl && (
                                  <>
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
                                  </>
                                )}

                                {/* Image Label */}
                                <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-2 text-center">
                                  <span className="text-xs text-white">Option {index + 1}</span>
                                </div>
                              </button>
                            )
                          })}
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

                {!useAICharacter && mode === 'ad-creative' && (
                  <p className="text-xs text-gray-400">
                    Enable &quot;Use AI Generation&quot; to add character and style details
                  </p>
                )}
              </div>

              {/* Music Source for Music Video Mode */}
              {mode === 'music-video' && (
                <div className="space-y-3">
                  <div className="flex items-center gap-1">
                    <Label className="text-sm font-medium text-white">
                      Music Source
                    </Label>
                    <span className="text-red-400 text-sm">*</span>
                  </div>
                  <div className="space-y-4">
                    {/* Audio Source Tabs */}
                    <Tabs
                      value={audioSource}
                      onValueChange={(value) => {
                        setAudioSource(value as 'upload' | 'youtube')
                        // Clear the other source when switching
                        if (value === 'upload') {
                          setYoutubeUrl('')
                          setConvertedAudioFile(null)
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

                    {/* YouTube URL Input */}
                    {audioSource === 'youtube' && (
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="youtube-url" className="text-white">
                            YouTube URL
                          </Label>
                          <div className="flex gap-2">
                            <Input
                              id="youtube-url"
                              type="url"
                              placeholder="https://www.youtube.com/watch?v=..."
                              value={youtubeUrl}
                              onChange={(e) => setYoutubeUrl(e.target.value)}
                              className="bg-gray-800 border-gray-700 text-white placeholder-gray-500 flex-1"
                              disabled={isConvertingAudio}
                            />
                            <Button
                              type="button"
                              onClick={async () => {
                                if (!youtubeUrl.trim()) {
                                  toast({
                                    title: "Error",
                                    description: "Please enter a YouTube URL",
                                    variant: "destructive",
                                  })
                                  return
                                }

                                setIsConvertingAudio(true)
                                try {
                                  const response = await fetch(`${API_URL}/api/audio/convert-youtube`, {
                                    method: 'POST',
                                    headers: {
                                      'Content-Type': 'application/json',
                                      'X-API-Key': API_KEY,
                                    },
                                    body: JSON.stringify({ url: youtubeUrl }),
                                  })

                                  if (!response.ok) {
                                    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
                                    throw new Error(errorData.detail?.message || errorData.detail || 'Failed to convert audio')
                                  }

                                  const blob = await response.blob()
                                  const audioFile = new File([blob], "audio.mp3", { type: "audio/mpeg" })
                                  setConvertedAudioFile(audioFile)

                                  toast({
                                    title: "Success",
                                    description: "Audio converted successfully!",
                                  })
                                } catch (error) {
                                  console.error('Error converting audio:', error)
                                  toast({
                                    title: "Error",
                                    description: error instanceof Error ? error.message : "Failed to convert audio",
                                    variant: "destructive",
                                  })
                                } finally {
                                  setIsConvertingAudio(false)
                                }
                              }}
                              disabled={isConvertingAudio || !youtubeUrl.trim()}
                              className="bg-blue-600 hover:bg-blue-700"
                            >
                              {isConvertingAudio ? (
                                <>
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                  Converting...
                                </>
                              ) : (
                                'Convert'
                              )}
                            </Button>
                          </div>
                        </div>

                        {/* Show converted audio file */}
                        {convertedAudioFile && (
                          <div className="border border-gray-600 rounded-lg p-4 bg-gray-800/30">
                            <div className="flex items-center gap-4">
                              <div className="rounded-lg bg-green-500/10 p-3 flex-shrink-0">
                                <CheckCircle2 className="h-6 w-6 text-green-400" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-white">{convertedAudioFile.name}</p>
                                <p className="text-xs text-gray-400">
                                  {(convertedAudioFile.size / (1024 * 1024)).toFixed(2)} MB
                                </p>
                              </div>
                            </div>

                            {/* Audio Preview */}
                            <div className="mt-4">
                              <audio
                                controls
                                src={URL.createObjectURL(convertedAudioFile)}
                                className="w-full h-10"
                              />
                            </div>
                          </div>
                        )}

                        {!convertedAudioFile && !isConvertingAudio && (
                          <p className="text-xs text-red-400">
                            Click &quot;Convert&quot; to download audio from YouTube
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

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
                        {audioSource === 'youtube' && !convertedAudioFile && (
                          <p className="text-xs text-yellow-400 text-center">
                            Convert YouTube audio first
                          </p>
                        )}
                      </>
                    )}
                    {mode === 'ad-creative' && useAICharacter && selectedImageIndex === null && generatedImages.length > 0 && (
                      <p className="text-xs text-yellow-400 text-center">
                        Please select a character image to continue
                      </p>
                    )}
                    {mode === 'ad-creative' && useAICharacter && generatedImages.length === 0 && characterDescription.trim() && (
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
