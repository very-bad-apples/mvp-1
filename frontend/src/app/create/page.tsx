'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ImageUploadZone } from '@/components/ImageUploadZone'
import { AudioUploadZone } from '@/components/AudioUploadZone'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Sparkles, Video, ChevronLeft, Loader2, ImageIcon, RefreshCw, CheckCircle2, AlertCircle, Zap } from 'lucide-react'
import { useToast } from '@/hooks/useToast'
import { createProject, getDirectorConfigs, generateCharacterReference, uploadCharacterReference } from '@/lib/api/client'

// Use relative paths to proxy routes (API key handled server-side)
const API_BASE = '/api/mv'
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

type Mode = 'ad-creative' | 'music-video'

type AudioModelParameter = {
  name: string
  type: string
  required: boolean
  description: string
  control?: 'text' | 'textarea' | 'number' | 'select' | 'boolean'
  options?: { label: string; value: string }[]
  min?: number
  max?: number
  step?: number
  placeholder?: string
}

type AudioModelMetadata = {
  key: string
  model_id: string
  display_name: string
  provider: string
  description: string
  docs_url: string
  max_duration_seconds: number
  parameters: AudioModelParameter[]
  default_params: Record<string, unknown>
}

export default function CreatePage() {
  const router = useRouter()
  const { toast } = useToast()
  const [mode, setMode] = useState<Mode>('music-video')
  const [prompt, setPrompt] = useState('')
  const [personality, setPersonality] = useState('')
  const [characterDescription, setCharacterDescription] = useState('')
  const [uploadedCharacterImage, setUploadedCharacterImage] = useState<File | null>(null)
  const [uploadedAudio, setUploadedAudio] = useState<File | null>(null)
  const [downloadedAudioId, setDownloadedAudioId] = useState<string>('')
  const [downloadedAudioUrl, setDownloadedAudioUrl] = useState<string>('')
  const [convertedAudioFile, setConvertedAudioFile] = useState<File | null>(null)
  const [isConvertingAudio, setIsConvertingAudio] = useState(false)
  const [youtubeUrl, setYoutubeUrl] = useState<string>('')
  const [audioSource, setAudioSource] = useState<'upload' | 'youtube' | 'ai-music'>('upload')
  const [aiMusicPrompt, setAiMusicPrompt] = useState<string>('')
  const [aiMusicLyrics, setAiMusicLyrics] = useState<string>('')
  const [showAdvancedAudioOptions, setShowAdvancedAudioOptions] = useState(false)
  const [aiMusicSampleRate, setAiMusicSampleRate] = useState<number>(44100)
  const [aiMusicBitrate, setAiMusicBitrate] = useState<number>(256000)
  const [isGeneratingAiMusic, setIsGeneratingAiMusic] = useState(false)
  const [generatedAiMusicFile, setGeneratedAiMusicFile] = useState<File | null>(null)
  const [imageSource, setImageSource] = useState<'upload' | 'generate'>('generate')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [generatedImages, setGeneratedImages] = useState<string[]>([])
  const [generatedImageIds, setGeneratedImageIds] = useState<string[]>([])
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null)
  const [isGeneratingImages, setIsGeneratingImages] = useState(false)
  const [imageGenerationError, setImageGenerationError] = useState<string | null>(null)
  const [generationAttempts, setGenerationAttempts] = useState(0)

  // Director config state
  const [directorConfig, setDirectorConfig] = useState<string>('')
  const [availableDirectorConfigs, setAvailableDirectorConfigs] = useState<string[]>([])
  const [isFetchingDirectorConfigs, setIsFetchingDirectorConfigs] = useState(false)

  // Fetch available director configs on mount
  useEffect(() => {
    const fetchDirectorConfigs = async () => {
      setIsFetchingDirectorConfigs(true)
      try {
        const data = await getDirectorConfigs()
        if (data.configs && Array.isArray(data.configs)) {
          setAvailableDirectorConfigs(data.configs)
        } else {
          console.warn('Director configs response missing or invalid:', data)
          setAvailableDirectorConfigs([])
        }
      } catch (error) {
        console.error('Failed to fetch director configs:', error)
        // Keep empty array as fallback - backend may not be running
        // This is non-critical, so we silently fail
        setAvailableDirectorConfigs([])
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
    // Check video description (required)
    if (!prompt.trim()) return false

    // Check personality (required)
    if (!personality.trim()) return false

    // Check reference image (required)
    if (imageSource === 'upload' && !uploadedCharacterImage) return false
    if (imageSource === 'generate') {
      // Must have character description and selected image
      if (!characterDescription.trim()) return false
      if (selectedImageIndex === null) return false
    }

    // Check audio (required for both modes)
    if (audioSource === 'upload' && !uploadedAudio) return false
    if (audioSource === 'youtube' && !downloadedAudioId) return false

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

    if (!personality.trim()) {
      toast({
        title: "Error",
        description: mode === 'ad-creative'
          ? "Please provide brand personality"
          : "Please provide artist/band personality",
        variant: "destructive",
      })
      return
    }

    // Check reference image (required)
    if (imageSource === 'upload' && !uploadedCharacterImage) {
      toast({
        title: "Error",
        description: mode === 'ad-creative'
          ? "Please upload a product/brand reference image"
          : "Please upload a character reference image",
        variant: "destructive",
      })
      return
    }

    if (imageSource === 'generate') {
      if (!characterDescription.trim()) {
        toast({
          title: "Error",
          description: mode === 'ad-creative'
            ? "Please provide product/brand visual style description"
            : "Please provide artist/band visual appearance description",
          variant: "destructive",
        })
        return
      }
      if (selectedImageIndex === null) {
        toast({
          title: "Error",
          description: mode === 'ad-creative'
            ? "Please select a generated product image"
            : "Please select a generated character image",
          variant: "destructive",
        })
        return
      }
    }

    // Check audio (required for both modes)
    if (audioSource === 'upload' && !uploadedAudio) {
      toast({
        title: "Error",
        description: mode === 'ad-creative'
          ? "Please upload background music"
          : "Please upload a music file",
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
    if (audioSource === 'ai-music' && !generatedAiMusicFile) {
      toast({
        title: "Error",
        description: "Please generate AI music first",
        variant: "destructive",
      })
      return
    }

    setIsSubmitting(true)

    try {
      // Get character reference image ID based on image source
      let characterReferenceImageId: string | null = null

      if (imageSource === 'generate') {
        // Use generated character image if selected
        characterReferenceImageId = selectedImageIndex !== null && generatedImageIds[selectedImageIndex]
          ? generatedImageIds[selectedImageIndex]
          : null
      } else if (imageSource === 'upload' && uploadedCharacterImage) {
        // Upload character image to get an ID
        try {
          const uploadResponse = await uploadCharacterReference(uploadedCharacterImage)
          characterReferenceImageId = uploadResponse.image_id

          toast({
            title: "Image uploaded",
            description: "Character reference image uploaded successfully",
          })
        } catch (error) {
          console.error('Error uploading character image:', error)
          toast({
            title: "Upload failed",
            description: error instanceof Error ? error.message : "Failed to upload character image. Please try again.",
            variant: "destructive",
          })
          setIsSubmitting(false)
          return
        }
      }

      // Prepare files for upload (for both modes - music-video requires it, ad-creative optional)
      let audioFile: File | undefined = undefined

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
      } else if (audioSource === 'ai-music' && generatedAiMusicFile) {
        // Use AI-generated music file
        audioFile = generatedAiMusicFile
      }

      // Call the createProject API
      // Combine personality and visual appearance for the description field
      const combinedDescription = [
        personality.trim(),
        characterDescription.trim()
      ].filter(Boolean).join('\n\n') || 'No description provided'

      // Route data to correct database fields based on mode
      const response = await createProject({
        mode,
        prompt: prompt.trim(),
        // For music-video: use characterDescription + characterImageUrl
        // For ad-creative: use productDescription + productImageUrl
        characterDescription: mode === 'music-video' ? combinedDescription : undefined,
        productDescription: mode === 'ad-creative' ? combinedDescription : undefined,
        characterReferenceImageId: mode === 'music-video' ? characterReferenceImageId : undefined,
        productReferenceImageId: mode === 'ad-creative' ? characterReferenceImageId : undefined,
        directorConfig: directorConfig || undefined,
        audio: audioFile,
      })


      toast({
        title: "Project created successfully!",
        description: response.message,
      })

      // Navigate to the edit page
      router.push(`/edit/${response.projectId}`)
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
    // Get character reference image ID if character image is selected
    const characterReferenceImageId = selectedImageIndex !== null && generatedImageIds[selectedImageIndex]
      ? generatedImageIds[selectedImageIndex]
      : undefined

    // Store form data in sessionStorage before navigating
    const quickJobData = {
      videoDescription: prompt,
      personality: personality,
      characterDescription: characterDescription,
      characterReferenceImageId,
      // Include audio data if YouTube audio was downloaded
      audioId: audioSource === 'youtube' ? downloadedAudioId : undefined,
      audioUrl: audioSource === 'youtube' ? downloadedAudioUrl : undefined,
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

              {/* Personality Field */}
              <div className="space-y-3">
                <div className="flex items-center gap-1">
                  <Label htmlFor="personality" className="text-sm font-medium text-white">
                    {mode === 'ad-creative' ? 'Brand Personality' : 'Artist/Band Personality'}
                  </Label>
                  <span className="text-red-400 text-sm">*</span>
                </div>
                <Textarea
                  id="personality"
                  placeholder={
                    mode === 'ad-creative'
                      ? 'Describe the brand personality and vibe... e.g., "Bold, innovative, and eco-conscious. Appeals to millennials who value sustainability and style"'
                      : 'Describe the artist/band personality and vibe... e.g., "Moody and introspective, with a dreamy, ethereal atmosphere"'
                  }
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  className="min-h-[100px] resize-none bg-gray-900/50 border-gray-600 text-white placeholder:text-gray-500"
                />
                <p className="text-xs text-gray-400">
                  {mode === 'ad-creative'
                    ? 'Describe the brand personality, target audience, and overall vibe'
                    : 'Describe the artist personality, mood, and overall vibe'}
                </p>
              </div>

              {/* Image Source */}
              <div className="space-y-3">
                <div className="flex items-center gap-1">
                  <Label className="text-sm font-medium text-white">
                    {mode === 'ad-creative' ? 'Product/Brand Reference Image' : 'Character Reference Image'}
                  </Label>
                  <span className="text-red-400 text-sm">*</span>
                </div>

                {/* Image Source Tabs */}
                <Tabs
                  value={imageSource}
                  onValueChange={(value) => {
                    setImageSource(value as 'upload' | 'generate')
                    // Clear the other source when switching
                    if (value === 'upload') {
                      setGeneratedImages([])
                      setSelectedImageIndex(null)
                      setCharacterDescription('')
                    } else {
                      setUploadedCharacterImage(null)
                    }
                  }}
                  className="w-full"
                >
                  <TabsList className="grid w-full grid-cols-2 h-10 bg-gray-900/50">
                    <TabsTrigger
                      value="upload"
                      className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                    >
                      Upload Image
                    </TabsTrigger>
                    <TabsTrigger
                      value="generate"
                      className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                    >
                      Generate Image
                    </TabsTrigger>
                  </TabsList>
                </Tabs>

                {/* Upload Image Option */}
                {imageSource === 'upload' && (
                  <div>
                    <ImageUploadZone
                      onFilesChange={(files) => {
                        // Only take the first file for character image
                        setUploadedCharacterImage(files.length > 0 ? files[0] : null)
                      }}
                      files={uploadedCharacterImage ? [uploadedCharacterImage] : []}
                    />
                    {!uploadedCharacterImage && (
                      <p className="text-xs text-gray-400 mt-2">
                        {mode === 'ad-creative'
                          ? 'Upload a product/brand reference image'
                          : 'Upload a character reference image'}
                      </p>
                    )}
                  </div>
                )}

                {/* Generate Image Option */}
                {imageSource === 'generate' && (
                  <div className="space-y-4">
                    {/* Visual Appearance Input */}
                    <div>
                      <div className="flex items-center gap-1 mb-2">
                        <Label htmlFor="character" className="text-sm font-medium text-white">
                          {mode === 'ad-creative' ? 'Product/Brand Visual Style' : 'Artist/Band Visual Appearance'}
                        </Label>
                        <span className="text-red-400 text-sm">*</span>
                      </div>
                      <Textarea
                        id="character"
                        placeholder={
                          mode === 'ad-creative'
                            ? 'Describe product appearance, colors, packaging... e.g., "Sleek aluminum bottle with minimalist label, shot against natural backgrounds with soft lighting"'
                            : 'Describe visual appearance of performers, setting, atmosphere... e.g., "Solo artist in black and white cinematography with moody lighting"'
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
                    </div>

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
                              className={`relative aspect-square rounded-lg overflow-hidden border-2 transition-all ${selectedImageIndex === index
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
                              {mode === 'ad-creative'
                                ? 'Product reference image selected! You can now generate your video.'
                                : 'Character image selected! You can now generate your video.'}
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
                                {mode === 'ad-creative' ? 'Regenerate Product Images' : 'Regenerate Character Images'}
                              </>
                            ) : (
                              <>
                                <ImageIcon className="mr-2 h-4 w-4" />
                                {mode === 'ad-creative' ? 'Generate Product Images' : 'Generate Character Images'}
                              </>
                            )}
                          </>
                        )}
                      </Button>
                    </div>

                    <p className="text-xs text-gray-400">
                      {!characterDescription.trim()
                        ? `Enter visual appearance details, then click 'Generate ${mode === 'ad-creative' ? 'Product' : 'Character'} Images'`
                        : generatedImages.length === 0
                          ? `Click 'Generate ${mode === 'ad-creative' ? 'Product' : 'Character'} Images' to create visual options`
                          : "Select an image to proceed, or click the button to regenerate"}
                    </p>
                  </div>
                )}
              </div>

              {/* Music Source - Available for Both Modes */}
              <div className="space-y-3">
                <div className="flex items-center gap-1">
                  <Label className="text-sm font-medium text-white">
                    {mode === 'ad-creative' ? 'Background Music' : 'Music Source'}
                  </Label>
                  <span className="text-red-400 text-sm">*</span>
                </div>
                {mode === 'ad-creative' && (
                  <p className="text-xs text-gray-400">
                    Add background music to your ad creative
                  </p>
                )}
                <div className="space-y-4">
                  {/* Audio Source Tabs */}
                  <Tabs
                    value={audioSource}
                    onValueChange={(value) => {
                      setAudioSource(value as 'upload' | 'youtube' | 'ai-music')
                      // Clear the other sources when switching
                      if (value === 'upload') {
                        setYoutubeUrl('')
                        setConvertedAudioFile(null)
                        setGeneratedAiMusicFile(null)
                      } else if (value === 'youtube') {
                        setUploadedAudio(null)
                        setGeneratedAiMusicFile(null)
                      } else if (value === 'ai-music') {
                        setUploadedAudio(null)
                        setYoutubeUrl('')
                        setConvertedAudioFile(null)
                      }
                    }}
                    className="w-full"
                  >
                    <TabsList className="grid w-full grid-cols-3 h-10 bg-gray-900/50">
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
                      <TabsTrigger
                        value="ai-music"
                        className="text-sm font-medium data-[state=active]:bg-blue-600 data-[state=active]:text-white"
                      >
                        AI Music
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
                      {!uploadedAudio && mode === 'music-video' && (
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

                  {/* AI Music Generation */}
                  {audioSource === 'ai-music' && (
                    <div className="space-y-4">
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="ai-music-prompt" className="text-white flex items-center gap-1">
                            Music Prompt
                            <span className="text-red-400">*</span>
                          </Label>
                          <Textarea
                            id="ai-music-prompt"
                            placeholder="Energetic electro-pop track with soaring synths and pulsing bass..."
                            value={aiMusicPrompt}
                            onChange={(e) => setAiMusicPrompt(e.target.value)}
                            className="bg-gray-800 border-gray-700 text-white placeholder-gray-500 mt-2 min-h-[100px]"
                            disabled={isGeneratingAiMusic}
                          />
                          <p className="text-xs text-gray-400 mt-1">
                            Describe the music you want to generate (10-300 characters)
                          </p>
                        </div>

                        <div>
                          <Label htmlFor="ai-music-lyrics" className="text-white flex items-center gap-1">
                            Lyrics
                            <span className="text-xs text-gray-500 ml-1">(Optional - leave blank for instrumental)</span>
                          </Label>
                          <Textarea
                            id="ai-music-lyrics"
                            placeholder="[Verse]&#10;Dancing under starlight&#10;[Chorus]&#10;Feel the rhythm tonight..."
                            value={aiMusicLyrics}
                            onChange={(e) => setAiMusicLyrics(e.target.value)}
                            className="bg-gray-800 border-gray-700 text-white placeholder-gray-500 mt-2 min-h-[120px]"
                            disabled={isGeneratingAiMusic}
                          />
                          <p className="text-xs text-gray-400 mt-1">
                            Use tags like [Verse], [Chorus], [Bridge], [Outro] (10-600 characters, or leave empty for instrumental)
                          </p>
                        </div>

                        {/* Advanced Options */}
                        <div className="border border-gray-700 rounded-lg">
                          <button
                            type="button"
                            onClick={() => setShowAdvancedAudioOptions(!showAdvancedAudioOptions)}
                            className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-800/30 transition-colors"
                          >
                            <span className="text-sm font-medium text-white">Advanced Audio Options</span>
                            <span className="text-gray-400">{showAdvancedAudioOptions ? '−' : '+'}</span>
                          </button>
                          
                          {showAdvancedAudioOptions && (
                            <div className="p-4 pt-0 space-y-4 border-t border-gray-700">
                              <div>
                                <Label htmlFor="ai-music-sample-rate" className="text-white text-sm flex items-center gap-2">
                                  Sample Rate
                                  <span className="text-xs text-gray-500 font-normal">
                                    (Higher = better quality)
                                  </span>
                                </Label>
                                <Select
                                  value={String(aiMusicSampleRate)}
                                  onValueChange={(value) => setAiMusicSampleRate(Number(value))}
                                  disabled={isGeneratingAiMusic}
                                >
                                  <SelectTrigger id="ai-music-sample-rate" className="bg-gray-800 border-gray-700 text-white mt-2">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent className="bg-gray-800 border-gray-700 text-white">
                                    <SelectItem value="16000">16 kHz (Phone quality)</SelectItem>
                                    <SelectItem value="24000">24 kHz (Acceptable)</SelectItem>
                                    <SelectItem value="32000">32 kHz (Good)</SelectItem>
                                    <SelectItem value="44100">44.1 kHz (CD quality - Recommended)</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>

                              <div>
                                <Label htmlFor="ai-music-bitrate" className="text-white text-sm flex items-center gap-2">
                                  Bitrate
                                  <span className="text-xs text-gray-500 font-normal">
                                    (Higher = better sound)
                                  </span>
                                </Label>
                                <Select
                                  value={String(aiMusicBitrate)}
                                  onValueChange={(value) => setAiMusicBitrate(Number(value))}
                                  disabled={isGeneratingAiMusic}
                                >
                                  <SelectTrigger id="ai-music-bitrate" className="bg-gray-800 border-gray-700 text-white mt-2">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent className="bg-gray-800 border-gray-700 text-white">
                                    <SelectItem value="32000">32 kbps (Very compressed)</SelectItem>
                                    <SelectItem value="64000">64 kbps (Low quality)</SelectItem>
                                    <SelectItem value="128000">128 kbps (Acceptable)</SelectItem>
                                    <SelectItem value="256000">256 kbps (High quality - Recommended)</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                          )}
                        </div>

                        <Button
                          type="button"
                          onClick={async () => {
                            if (!aiMusicPrompt.trim()) {
                              toast({
                                title: "Error",
                                description: "Please enter a music prompt",
                                variant: "destructive",
                              })
                              return
                            }

                            if (aiMusicPrompt.trim().length < 10) {
                              toast({
                                title: "Error",
                                description: "Prompt must be at least 10 characters",
                                variant: "destructive",
                              })
                              return
                            }

                            if (aiMusicLyrics.trim() && aiMusicLyrics.trim().length < 10) {
                              toast({
                                title: "Error",
                                description: "Lyrics must be at least 10 characters or left empty",
                                variant: "destructive",
                              })
                              return
                            }

                            setIsGeneratingAiMusic(true)
                            try {
                              // Build parameters object - only include lyrics if provided
                              const parameters: Record<string, any> = {
                                prompt: aiMusicPrompt,
                                sample_rate: aiMusicSampleRate,
                                bitrate: aiMusicBitrate,
                                audio_format: 'mp3',
                              }
                              
                              // Only add lyrics if user provided them (for instrumental, omit this field)
                              if (aiMusicLyrics.trim()) {
                                parameters.lyrics = aiMusicLyrics
                              }

                              const response = await fetch(`${API_URL}/api/audio/models/run`, {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                  ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
                                },
                                body: JSON.stringify({
                                  model_key: 'minimax_music_1_5',
                                  parameters,
                                }),
                              })

                              if (!response.ok) {
                                const errorData = await response.json().catch(() => ({}))
                                throw new Error(errorData.detail?.message || errorData.message || 'Failed to generate music')
                              }

                              const data = await response.json()
                              const audioUrl = data.outputs?.[0]

                              if (!audioUrl) {
                                throw new Error('No audio generated')
                              }

                              // Download the audio file
                              const audioResponse = await fetch(audioUrl)
                              const audioBlob = await audioResponse.blob()
                              const audioFile = new File([audioBlob], 'ai-generated-music.mp3', { type: 'audio/mpeg' })
                              setGeneratedAiMusicFile(audioFile)

                              toast({
                                title: "Success",
                                description: "AI music generated successfully!",
                              })
                            } catch (error) {
                              console.error('AI music generation failed:', error)
                              toast({
                                title: "Generation Failed",
                                description: error instanceof Error ? error.message : "Unable to generate AI music",
                                variant: "destructive",
                              })
                            } finally {
                              setIsGeneratingAiMusic(false)
                            }
                          }}
                          disabled={isGeneratingAiMusic || !aiMusicPrompt.trim()}
                          className="w-full bg-purple-600 hover:bg-purple-700"
                        >
                          {isGeneratingAiMusic ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Generating AI Music (this may take 1-2 minutes)...
                            </>
                          ) : (
                            <>
                              <Sparkles className="mr-2 h-4 w-4" />
                              Generate AI Music
                            </>
                          )}
                        </Button>
                      </div>

                      {/* Show generated AI music file */}
                      {generatedAiMusicFile && (
                        <div className="border border-gray-600 rounded-lg p-4 bg-gray-800/30">
                          <div className="flex items-center gap-4">
                            <div className="rounded-lg bg-purple-500/10 p-3 flex-shrink-0">
                              <CheckCircle2 className="h-6 w-6 text-purple-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-white">{generatedAiMusicFile.name}</p>
                              <p className="text-xs text-gray-400">
                                {(generatedAiMusicFile.size / (1024 * 1024)).toFixed(2)} MB • AI Generated
                              </p>
                            </div>
                          </div>

                          {/* Audio Preview */}
                          <div className="mt-4">
                            <audio
                              controls
                              src={URL.createObjectURL(generatedAiMusicFile)}
                              className="w-full h-10"
                            />
                          </div>
                        </div>
                      )}

                      {!generatedAiMusicFile && !isGeneratingAiMusic && (
                        <p className="text-xs text-gray-400">
                          Fill in the prompt and click &quot;Generate AI Music&quot; to create your track
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Director Style Selector */}
              <div className="space-y-2">
                <Label htmlFor="director-config" className="text-sm font-medium text-white">
                  Director Style (Optional)
                </Label>
                <Select
                  value={directorConfig || undefined}
                  onValueChange={(value) => {
                    // Allow clearing selection by setting to empty string
                    setDirectorConfig(value === "none" ? '' : value)
                  }}
                  disabled={isFetchingDirectorConfigs}
                >
                  <SelectTrigger
                    id="director-config"
                    className="w-full bg-gray-800 border-gray-600 text-white"
                  >
                    <SelectValue placeholder={isFetchingDirectorConfigs ? "Loading..." : "None (optional)"} />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-600">
                    {isFetchingDirectorConfigs ? (
                      <SelectItem value="loading" disabled className="text-gray-500">
                        Loading...
                      </SelectItem>
                    ) : availableDirectorConfigs.length > 0 ? (
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
                    {mode === 'music-video' && (
                      <>
                        {audioSource === 'upload' && !uploadedAudio && (
                          <p className="text-xs text-yellow-400 text-center">
                            Please upload a music file
                          </p>
                        )}
                        {audioSource === 'youtube' && !convertedAudioFile && (
                          <p className="text-xs text-yellow-400 text-center">
                            Please download audio from YouTube
                          </p>
                        )}
                      </>
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
