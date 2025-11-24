'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ImageUploadZone } from '@/components/ImageUploadZone'
import { AudioUploadZone } from '@/components/AudioUploadZone'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Sparkles,
  Video,
  ChevronLeft,
  ChevronRight,
  Loader2,
  ImageIcon,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Upload,
  Youtube,
  Music,
  Check,
  Zap
} from 'lucide-react'
import { useToast } from '@/hooks/useToast'
import { createProject, getDirectorConfigs, generateCharacterReference, uploadCharacterReference } from '@/lib/api/client'
import { Logo } from '@/components/Logo'

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

interface WizardStep {
  id: number
  title: string
  description: string
}

const WIZARD_STEPS: WizardStep[] = [
  { id: 1, title: 'Video Type', description: 'Choose your format' },
  { id: 2, title: 'Basic Info', description: 'Describe your vision' },
  { id: 3, title: 'Reference Image', description: 'Upload or generate' },
  { id: 4, title: 'Audio Source', description: 'Add your music' },
  { id: 5, title: 'Director Style', description: 'Optional styling' },
  { id: 6, title: 'Review', description: 'Finalize & submit' },
]

const STORAGE_KEY = 'video-wizard-data'

export default function CreatePage() {
  const router = useRouter()
  const { toast } = useToast()

  // Wizard state
  const [currentStep, setCurrentStep] = useState(1)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])

  // Form state
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

  // Load saved data from localStorage on mount
  useEffect(() => {
    const savedData = localStorage.getItem(STORAGE_KEY)
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData)
        setMode(parsed.mode || 'music-video')
        setPrompt(parsed.prompt || '')
        setPersonality(parsed.personality || '')
        setCharacterDescription(parsed.characterDescription || '')
        setYoutubeUrl(parsed.youtubeUrl || '')
        setAudioSource(parsed.audioSource || 'upload')
        setImageSource(parsed.imageSource || 'generate')
        setDirectorConfig(parsed.directorConfig || '')
        setCurrentStep(parsed.currentStep || 1)
        setCompletedSteps(parsed.completedSteps || [])
        setAiMusicPrompt(parsed.aiMusicPrompt || '')
        setAiMusicLyrics(parsed.aiMusicLyrics || '')
      } catch (error) {
        console.error('Failed to load saved data:', error)
      }
    }
  }, [])

  // Save data to localStorage whenever it changes
  useEffect(() => {
    const dataToSave = {
      mode,
      prompt,
      personality,
      characterDescription,
      youtubeUrl,
      audioSource,
      imageSource,
      directorConfig,
      currentStep,
      completedSteps,
      aiMusicPrompt,
      aiMusicLyrics,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave))
  }, [mode, prompt, personality, characterDescription, youtubeUrl, audioSource, imageSource, directorConfig, currentStep, completedSteps, aiMusicPrompt, aiMusicLyrics])

  // Fetch available director configs on mount
  useEffect(() => {
    const fetchDirectorConfigs = async () => {
      setIsFetchingDirectorConfigs(true)
      try {
        const data = await getDirectorConfigs()
        if (data.configs && Array.isArray(data.configs)) {
          setAvailableDirectorConfigs(data.configs)
        } else {
          setAvailableDirectorConfigs([])
        }
      } catch (error) {
        console.error('Failed to fetch director configs:', error)
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

  // Step validation
  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 1:
        return true // Video type always valid (has default)
      case 2:
        return prompt.trim().length >= 10 && personality.trim() !== ''
      case 3:
        if (imageSource === 'upload') {
          return uploadedCharacterImage !== null
        }
        if (imageSource === 'generate') {
          return characterDescription.trim() !== '' && selectedImageIndex !== null
        }
        return false
      case 4:
        if (audioSource === 'upload') {
          return uploadedAudio !== null
        }
        if (audioSource === 'youtube') {
          return convertedAudioFile !== null
        }
        if (audioSource === 'ai-music') {
          return generatedAiMusicFile !== null
        }
        return false
      case 5:
        return true // Director style is optional
      case 6:
        return true // Review step
      default:
        return false
    }
  }

  const canProceedToStep = (step: number): boolean => {
    // Can always go back
    if (step <= currentStep) return true

    // Can only proceed if previous step is valid
    return isStepValid(currentStep)
  }

  const goToStep = (step: number) => {
    if (canProceedToStep(step)) {
      // Mark current step as completed if valid
      if (isStepValid(currentStep) && !completedSteps.includes(currentStep)) {
        setCompletedSteps([...completedSteps, currentStep])
      }
      setCurrentStep(step)
    }
  }

  const nextStep = () => {
    if (currentStep < WIZARD_STEPS.length && isStepValid(currentStep)) {
      if (!completedSteps.includes(currentStep)) {
        setCompletedSteps([...completedSteps, currentStep])
      }
      setCurrentStep(currentStep + 1)
    } else if (!isStepValid(currentStep)) {
      toast({
        title: "Incomplete Step",
        description: "Please complete all required fields before proceeding.",
        variant: "destructive",
      })
    }
  }

  const previousStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
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
    setSelectedImageIndex(null)
    setImageGenerationError(null)

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
        num_images: 4,
      })

      const blobUrls: string[] = []
      const imageIds: string[] = []

      for (const image of data.images) {
        imageIds.push(image.id)

        if (image.cloud_url) {
          blobUrls.push(image.cloud_url)
        } else {
          try {
            const response = await fetch(`${API_URL}/api/mv/get_character_reference/${image.id}?redirect=false`, {
              headers: API_KEY ? { 'X-API-Key': API_KEY } : {},
            })

            if (!response.ok) {
              throw new Error(`Failed to fetch image ${image.id}`)
            }

            const contentType = response.headers.get('content-type')

            if (contentType?.includes('application/json')) {
              const jsonData = await response.json()
              blobUrls.push(jsonData.image_url || jsonData.video_url)
            } else {
              const blob = await response.blob()
              const objectUrl = URL.createObjectURL(blob)
              blobUrls.push(objectUrl)
            }
          } catch (fetchError) {
            console.error(`Failed to fetch image ${image.id}:`, fetchError)
            blobUrls.push('')
          }
        }
      }

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

  const handleSubmit = async () => {
    setIsSubmitting(true)

    try {
      let characterReferenceImageId: string | null = null

      if (imageSource === 'generate') {
        characterReferenceImageId = selectedImageIndex !== null && generatedImageIds[selectedImageIndex]
          ? generatedImageIds[selectedImageIndex]
          : null
      } else if (imageSource === 'upload' && uploadedCharacterImage) {
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

      let audioFile: File | undefined = undefined

      if (audioSource === 'upload' && uploadedAudio) {
        audioFile = uploadedAudio
      } else if (audioSource === 'youtube' && convertedAudioFile) {
        audioFile = convertedAudioFile
      } else if (audioSource === 'ai-music' && generatedAiMusicFile) {
        audioFile = generatedAiMusicFile
      }

      const combinedDescription = [
        personality.trim(),
        characterDescription.trim()
      ].filter(Boolean).join('\n\n') || 'No description provided'

      const response = await createProject({
        mode,
        prompt: prompt.trim(),
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

      // Clear saved data
      localStorage.removeItem(STORAGE_KEY)

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

  const progressPercentage = (completedSteps.length / WIZARD_STEPS.length) * 100

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Left Sidebar - Steps Navigation */}
      <aside className="w-80 border-r border-gray-800 bg-gray-900/50 p-6 flex flex-col">
        <div className="mb-8">
          <Link href="/" className="flex items-center gap-3 mb-6">
            <Logo size="sm" className="text-blue-500" />
            <span className="text-xl font-bold text-white">Bad Apple</span>
          </Link>

          {/* Progress */}
          <div className="space-y-2 mb-8">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Progress</span>
              <span className="text-white font-medium">{completedSteps.length} / {WIZARD_STEPS.length}</span>
            </div>
            <Progress value={progressPercentage} className="h-2" />
          </div>
        </div>

        {/* Steps */}
        <nav className="flex-1 space-y-1">
          {WIZARD_STEPS.map((step) => {
            const isActive = currentStep === step.id
            const isCompleted = completedSteps.includes(step.id)
            const isAccessible = step.id === 1 || completedSteps.includes(step.id - 1) || step.id <= currentStep

            return (
              <button
                key={step.id}
                onClick={() => isAccessible && goToStep(step.id)}
                disabled={!isAccessible}
                className={`
                  w-full text-left px-4 py-3 rounded-lg transition-all
                  ${isActive
                    ? 'bg-blue-500/10 border border-blue-500/50 text-white'
                    : isCompleted
                    ? 'bg-gray-800/50 text-gray-300 hover:bg-gray-800'
                    : isAccessible
                    ? 'text-gray-400 hover:bg-gray-800/30'
                    : 'text-gray-600 cursor-not-allowed'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <div className={`
                    shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                    ${isActive
                      ? 'bg-blue-500 text-white'
                      : isCompleted
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-700 text-gray-400'
                    }
                  `}>
                    {isCompleted ? <Check className="h-3 w-3" /> : step.id}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{step.title}</div>
                    <div className="text-xs text-gray-500">{step.description}</div>
                  </div>
                </div>
              </button>
            )
          })}
        </nav>

        {/* Back to Home */}
        <div className="mt-8 pt-6 border-t border-gray-800">
          <Link href="/">
            <Button variant="outline" className="w-full border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white">
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back to Home
            </Button>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-12">
          {/* Mode Badge - Show on steps 2-6 */}
          {currentStep > 1 && (
            <div className="mb-6">
              <Badge variant="outline" className="border-blue-500/50 text-blue-400 bg-blue-500/10">
                {mode === 'music-video' ? (
                  <>
                    <Music className="w-3 h-3 mr-1" />
                    Music Video
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3 h-3 mr-1" />
                    Ad Creative
                  </>
                )}
              </Badge>
            </div>
          )}

          {/* Step Content */}
          <div className="space-y-6">
            {/* Step 1: Video Type */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Choose Your Video Type</h1>
                  <p className="text-gray-400">Select the format that best fits your project</p>
                </div>

                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="pt-6">
                    <Tabs
                      value={mode}
                      onValueChange={(value) => setMode(value as Mode)}
                      className="w-full"
                    >
                      <TabsList className="grid w-full grid-cols-2 bg-gray-800 h-auto p-2">
                        <TabsTrigger
                          value="music-video"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white py-4"
                        >
                          <div className="flex flex-col items-center gap-2">
                            <Music className="w-6 h-6" />
                            <div className="text-center">
                              <div className="font-medium">Music Video</div>
                              <div className="text-xs text-gray-400">Create cinematic music videos</div>
                            </div>
                          </div>
                        </TabsTrigger>
                        <TabsTrigger
                          value="ad-creative"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white py-4"
                        >
                          <div className="flex flex-col items-center gap-2">
                            <Sparkles className="w-6 h-6" />
                            <div className="text-center">
                              <div className="font-medium">Ad Creative</div>
                              <div className="text-xs text-gray-400">Generate product advertisements</div>
                            </div>
                          </div>
                        </TabsTrigger>
                      </TabsList>
                    </Tabs>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 2: Basic Information */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Basic Information</h1>
                  <p className="text-gray-400">Describe your video concept and style</p>
                </div>

                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="pt-6 space-y-6">
                    {/* Video Description */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-1">
                        <Label htmlFor="prompt" className="text-gray-200">
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
                        className="min-h-32 bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 focus:border-gray-600"
                        maxLength={1000}
                        required
                      />
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-gray-400">
                          Be specific about scenes, camera angles, and visual style
                        </p>
                        <span className={`text-xs ${prompt.length < 10 || prompt.length > 900 ? 'text-red-400' : 'text-gray-500'}`}>
                          {prompt.length}/1000 characters {prompt.length > 0 && prompt.length < 10 && '(min: 10)'}
                        </span>
                      </div>
                    </div>

                    {/* Personality */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-1">
                        <Label htmlFor="personality" className="text-gray-200">
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
                        className="min-h-24 bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 focus:border-gray-600"
                      />
                      <p className="text-xs text-gray-400">
                        {mode === 'ad-creative'
                          ? 'Describe the brand personality, target audience, and overall vibe'
                          : 'Describe the artist personality, mood, and overall vibe'}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 3: Reference Image */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">
                    {mode === 'ad-creative' ? 'Product/Brand Reference Image' : 'Character Reference Image'}
                  </h1>
                  <p className="text-gray-400">Upload or generate a reference image for your video</p>
                </div>

                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="pt-6">
                    <Tabs
                      value={imageSource}
                      onValueChange={(value) => {
                        setImageSource(value as 'upload' | 'generate')
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
                      <TabsList className="grid w-full grid-cols-2 bg-gray-800 mb-6">
                        <TabsTrigger
                          value="upload"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white"
                        >
                          <Upload className="w-4 h-4 mr-2" />
                          Upload
                        </TabsTrigger>
                        <TabsTrigger
                          value="generate"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white"
                        >
                          <Sparkles className="w-4 h-4 mr-2" />
                          Generate
                        </TabsTrigger>
                      </TabsList>

                      {/* Upload Image Tab */}
                      <TabsContent value="upload" className="space-y-4 mt-0">
                        <ImageUploadZone
                          onFilesChange={(files) => {
                            setUploadedCharacterImage(files.length > 0 ? files[0] : null)
                          }}
                          files={uploadedCharacterImage ? [uploadedCharacterImage] : []}
                        />
                        {!uploadedCharacterImage && (
                          <p className="text-xs text-gray-400">
                            {mode === 'ad-creative'
                              ? 'Upload a product/brand reference image'
                              : 'Upload a character reference image'}
                          </p>
                        )}
                      </TabsContent>

                      {/* Generate Image Tab */}
                      <TabsContent value="generate" className="space-y-4 mt-0">
                        <div className="space-y-2">
                          <div className="flex items-center gap-1">
                            <Label htmlFor="character" className="text-gray-200">
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
                              if (generatedImages.length > 0) {
                                setGeneratedImages([])
                                setSelectedImageIndex(null)
                              }
                            }}
                            className="min-h-24 bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 focus:border-gray-600"
                          />
                        </div>

                        {imageGenerationError && !isGeneratingImages && (
                          <Alert variant="destructive" className="bg-red-950/50 border-red-900">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="text-red-300">
                              {imageGenerationError}
                            </AlertDescription>
                          </Alert>
                        )}

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
                                    ? 'Product reference image selected!'
                                    : 'Character image selected!'}
                                </p>
                              </div>
                            )}
                          </div>
                        )}

                        <Button
                          type="button"
                          onClick={handleGenerateImages}
                          disabled={isGeneratingImages || !characterDescription.trim()}
                          className="w-full bg-gray-700 hover:bg-gray-600 text-white"
                        >
                          {isGeneratingImages ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Generating Images...
                            </>
                          ) : (
                            <>
                              {generatedImages.length > 0 ? (
                                <>
                                  <RefreshCw className="mr-2 h-4 w-4" />
                                  Regenerate Images
                                </>
                              ) : (
                                <>
                                  <ImageIcon className="mr-2 h-4 w-4" />
                                  Generate Images
                                </>
                              )}
                            </>
                          )}
                        </Button>

                        <p className="text-xs text-gray-400">
                          {!characterDescription.trim()
                            ? `Enter visual details, then click 'Generate Images'`
                            : generatedImages.length === 0
                              ? `Click 'Generate Images' to create visual options`
                              : "Select an image to proceed, or regenerate for new options"}
                        </p>
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 4: Audio Source */}
            {currentStep === 4 && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">
                    {mode === 'ad-creative' ? 'Background Music' : 'Music Source'}
                  </h1>
                  <p className="text-gray-400">
                    {mode === 'ad-creative'
                      ? 'Add background music to your ad creative'
                      : 'Upload audio, provide a YouTube URL, or generate AI music'}
                  </p>
                </div>

                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="pt-6">
                    <Tabs
                      value={audioSource}
                      onValueChange={(value) => {
                        setAudioSource(value as 'upload' | 'youtube' | 'ai-music')
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
                      <TabsList className="grid w-full grid-cols-3 bg-gray-800 mb-6">
                        <TabsTrigger
                          value="upload"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white"
                        >
                          <Upload className="w-4 h-4 mr-2" />
                          Upload Audio
                        </TabsTrigger>
                        <TabsTrigger
                          value="youtube"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white"
                        >
                          <Youtube className="w-4 h-4 mr-2" />
                          YouTube URL
                        </TabsTrigger>
                        <TabsTrigger
                          value="ai-music"
                          className="data-[state=active]:bg-gray-700 text-gray-300 data-[state=active]:text-white"
                        >
                          <Music className="w-4 h-4 mr-2" />
                          AI Music
                        </TabsTrigger>
                      </TabsList>

                      {/* Audio Upload Tab */}
                      <TabsContent value="upload" className="space-y-3 mt-0">
                        <AudioUploadZone
                          onFileChange={setUploadedAudio}
                          file={uploadedAudio}
                        />
                        {!uploadedAudio && (
                          <p className="text-xs text-red-400">
                            Audio file is required
                          </p>
                        )}
                      </TabsContent>

                      {/* YouTube URL Tab */}
                      <TabsContent value="youtube" className="space-y-3 mt-0">
                        <div className="space-y-2">
                          <Label htmlFor="youtube-url" className="text-gray-200">
                            YouTube URL
                          </Label>
                          <div className="flex gap-2">
                            <Input
                              id="youtube-url"
                              type="url"
                              placeholder="https://www.youtube.com/watch?v=..."
                              value={youtubeUrl}
                              onChange={(e) => setYoutubeUrl(e.target.value)}
                              className="bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:border-gray-600 flex-1"
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
                              className="bg-gray-700 hover:bg-gray-600"
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

                        {convertedAudioFile && (
                          <div className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
                            <div className="flex items-center gap-4">
                              <div className="rounded-lg bg-green-500/10 p-3 shrink-0">
                                <CheckCircle2 className="h-6 w-6 text-green-400" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-white">{convertedAudioFile.name}</p>
                                <p className="text-xs text-gray-400">
                                  {(convertedAudioFile.size / (1024 * 1024)).toFixed(2)} MB
                                </p>
                              </div>
                            </div>

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
                          <p className="text-xs text-gray-400">
                            Click &quot;Convert&quot; to download audio from YouTube
                          </p>
                        )}
                      </TabsContent>

                      {/* AI Music Tab */}
                      <TabsContent value="ai-music" className="space-y-4 mt-0">
                        <div className="space-y-3">
                          <div>
                            <Label htmlFor="ai-music-prompt" className="text-gray-200 flex items-center gap-1">
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
                            <Label htmlFor="ai-music-lyrics" className="text-gray-200 flex items-center gap-1">
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
                                const parameters: Record<string, any> = {
                                  prompt: aiMusicPrompt,
                                  sample_rate: aiMusicSampleRate,
                                  bitrate: aiMusicBitrate,
                                  audio_format: 'mp3',
                                }

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
                            className="w-full bg-purple-600 hover:bg-purple-700 text-white"
                          >
                            {isGeneratingAiMusic ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Generating AI Music (1-2 minutes)...
                              </>
                            ) : (
                              <>
                                <Sparkles className="mr-2 h-4 w-4" />
                                Generate AI Music
                              </>
                            )}
                          </Button>
                        </div>

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
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 5: Director Style */}
            {currentStep === 5 && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Director Style</h1>
                  <p className="text-gray-400">Choose a creative direction template (optional)</p>
                </div>

                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="pt-6">
                    <div className="space-y-2">
                      <Label htmlFor="director-config" className="text-gray-200">
                        Select a Style
                      </Label>
                      <Select
                        value={directorConfig || undefined}
                        onValueChange={(value) => {
                          setDirectorConfig(value === "none" ? '' : value)
                        }}
                        disabled={isFetchingDirectorConfigs}
                      >
                        <SelectTrigger
                          id="director-config"
                          className="w-full bg-gray-800 border-gray-700 text-white focus:border-gray-600"
                        >
                          <SelectValue placeholder={isFetchingDirectorConfigs ? "Loading..." : "Select a style (optional)"} />
                        </SelectTrigger>
                        <SelectContent className="bg-gray-800 border-gray-700">
                          {isFetchingDirectorConfigs ? (
                            <SelectItem value="loading" disabled className="text-gray-500">
                              Loading...
                            </SelectItem>
                          ) : availableDirectorConfigs.length > 0 ? (
                            availableDirectorConfigs.map((config) => (
                              <SelectItem
                                key={config}
                                value={config}
                                className="text-white hover:bg-gray-700 focus:bg-gray-700"
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
                        Optional: Select a preset creative direction for your video
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 6: Review */}
            {currentStep === 6 && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Review & Submit</h1>
                  <p className="text-gray-400">Review your settings before generating</p>
                </div>

                <div className="space-y-4">
                  {/* Video Type */}
                  <Card className="bg-gray-900 border-gray-800">
                    <CardHeader>
                      <CardTitle className="text-white text-lg">Video Type</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Badge variant="outline" className="border-blue-500/50 text-blue-400 bg-blue-500/10">
                        {mode === 'music-video' ? (
                          <>
                            <Music className="w-3 h-3 mr-1" />
                            Music Video
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3 mr-1" />
                            Ad Creative
                          </>
                        )}
                      </Badge>
                    </CardContent>
                  </Card>

                  {/* Basic Information */}
                  <Card className="bg-gray-900 border-gray-800">
                    <CardHeader>
                      <CardTitle className="text-white text-lg">Basic Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <Label className="text-gray-400 text-sm">Video Description</Label>
                        <p className="text-white mt-1">{prompt}</p>
                      </div>
                      <div>
                        <Label className="text-gray-400 text-sm">
                          {mode === 'ad-creative' ? 'Brand Personality' : 'Artist/Band Personality'}
                        </Label>
                        <p className="text-white mt-1">{personality}</p>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Reference Image */}
                  <Card className="bg-gray-900 border-gray-800">
                    <CardHeader>
                      <CardTitle className="text-white text-lg">Reference Image</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle2 className="h-4 w-4 text-green-400" />
                        <span className="text-white">
                          {imageSource === 'upload' ? 'Uploaded image' : 'Generated image selected'}
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Audio */}
                  <Card className="bg-gray-900 border-gray-800">
                    <CardHeader>
                      <CardTitle className="text-white text-lg">Audio</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle2 className="h-4 w-4 text-green-400" />
                        <span className="text-white">
                          {audioSource === 'upload'
                            ? `Uploaded: ${uploadedAudio?.name}`
                            : audioSource === 'youtube'
                            ? 'YouTube audio converted'
                            : 'AI-generated music ready'}
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Director Style */}
                  {directorConfig && (
                    <Card className="bg-gray-900 border-gray-800">
                      <CardHeader>
                        <CardTitle className="text-white text-lg">Director Style</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-white">{directorConfig}</p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-800">
            <Button
              type="button"
              variant="outline"
              onClick={previousStep}
              disabled={currentStep === 1}
              className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white disabled:opacity-50"
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>

            {currentStep < WIZARD_STEPS.length ? (
              <Button
                type="button"
                onClick={nextStep}
                disabled={!isStepValid(currentStep)}
                className="bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting || !isStepValid(currentStep)}
                className="bg-white text-gray-900 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
