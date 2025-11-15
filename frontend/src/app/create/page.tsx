"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import Link from "next/link"
import { Video, Upload, X, Loader2, ChevronLeft } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/hooks/use-toast"

// Types for model data from backend
interface ModelInfo {
  model_id: string
  display_name: string
  description: string
  cost_per_run: number
  avg_duration: number
  is_default: boolean
}

interface TaskModelsResponse {
  task: string
  default_model: string
  models: ModelInfo[]
}

// Form validation schema
const formSchema = z.object({
  product_name: z.string().min(2, {
    message: "Product name must be at least 2 characters.",
  }).max(100, {
    message: "Product name must not exceed 100 characters.",
  }),
  style: z.enum(["luxury", "energetic", "minimal", "bold"], {
    message: "Please select a video style.",
  }),
  video_model: z.string().min(1, {
    message: "Please select a video model.",
  }),
  cta_text: z.string().min(2, {
    message: "CTA text must be at least 2 characters.",
  }).max(50, {
    message: "CTA text must not exceed 50 characters.",
  }),
  product_image: z.instanceof(File).optional().refine(
    (file) => {
      if (!file) return true;
      return file.size <= 10 * 1024 * 1024; // 10MB
    },
    { message: "File size must be less than 10MB" }
  ).refine(
    (file) => {
      if (!file) return true;
      return ["image/png", "image/jpeg", "image/webp"].includes(file.type);
    },
    { message: "Only PNG, JPG, and WebP formats are supported" }
  ),
})

type FormValues = z.infer<typeof formSchema>

const STYLE_DESCRIPTIONS = {
  luxury: "Elegant and sophisticated with premium visuals",
  energetic: "Dynamic and vibrant with fast-paced action",
  minimal: "Clean and simple with focused messaging",
  bold: "Strong and impactful with dramatic elements",
}

export default function CreatePage() {
  const router = useRouter()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [videoModels, setVideoModels] = useState<ModelInfo[]>([])
  const [isLoadingModels, setIsLoadingModels] = useState(true)

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      product_name: "",
      style: undefined,
      video_model: "",
      cta_text: "",
      product_image: undefined,
    },
  })

  // Fetch available video models from backend
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const response = await fetch(`${apiUrl}/api/models/tasks/video_scene/models`)

        if (!response.ok) {
          throw new Error("Failed to fetch models")
        }

        const data: TaskModelsResponse = await response.json()
        setVideoModels(data.models)

        // Set default model (the one marked as default from backend)
        const defaultModel = data.models.find(m => m.is_default)
        if (defaultModel) {
          form.setValue("video_model", defaultModel.model_id)
        } else if (data.models.length > 0) {
          // Fallback to first model if no default is set
          form.setValue("video_model", data.models[0].model_id)
        }
      } catch (error) {
        console.error("Error fetching models:", error)
        toast({
          title: "Warning",
          description: "Failed to load video models. Please refresh the page.",
          variant: "destructive",
        })
      } finally {
        setIsLoadingModels(false)
      }
    }

    fetchModels()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleFileChange = useCallback((file: File | null) => {
    if (file) {
      // Validate file
      const isValidType = ["image/png", "image/jpeg", "image/webp"].includes(file.type)
      const isValidSize = file.size <= 10 * 1024 * 1024

      if (!isValidType) {
        toast({
          title: "Invalid file type",
          description: "Please upload a PNG, JPG, or WebP image.",
          variant: "destructive",
        })
        return
      }

      if (!isValidSize) {
        toast({
          title: "File too large",
          description: "Please upload an image smaller than 10MB.",
          variant: "destructive",
        })
        return
      }

      // Set the file in the form
      form.setValue("product_image", file, { shouldValidate: true })

      // Create preview URL
      const url = URL.createObjectURL(file)
      setPreviewUrl(url)
    } else {
      form.setValue("product_image", undefined)
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
        setPreviewUrl(null)
      }
    }
  }, [form, toast, previewUrl])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileChange(files[0])
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileChange(files[0])
    }
  }

  const clearImage = () => {
    handleFileChange(null)
  }

  async function onSubmit(values: FormValues) {
    setIsSubmitting(true)

    try {
      const formData = new FormData()
      formData.append("product_name", values.product_name)
      formData.append("style", values.style)
      formData.append("video_model", values.video_model)
      formData.append("cta_text", values.cta_text)

      if (values.product_image) {
        formData.append("product_image", values.product_image)
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const response = await fetch(`${apiUrl}/api/generate`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to create video job")
      }

      const data = await response.json()

      toast({
        title: "Video generation started!",
        description: `Job ID: ${data.job_id}. Estimated time: ${data.estimated_completion_time}s`,
      })

      // Redirect to job status page
      router.push(`/job/${data.job_id}`)
    } catch (error) {
      console.error("Error submitting form:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start video generation",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
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
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Create Your Video
            </h1>
            <p className="text-xl text-gray-300">
              Upload your product image and customize your AI-generated video
            </p>
          </div>

          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-white">Video Details</CardTitle>
              <CardDescription className="text-gray-400">
                Fill in the details below to generate your video
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                  {/* Product Image Upload */}
                  <FormField
                    control={form.control}
                    name="product_image"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white">Product Image (Optional)</FormLabel>
                        <FormControl>
                          <div>
                            {previewUrl ? (
                              <div className="relative">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={previewUrl}
                                  alt="Preview"
                                  className="w-full h-64 object-contain rounded-lg border-2 border-gray-600 bg-gray-900/50"
                                />
                                <Button
                                  type="button"
                                  variant="destructive"
                                  size="icon"
                                  className="absolute top-2 right-2"
                                  onClick={clearImage}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            ) : (
                              <div
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                                  isDragging
                                    ? "border-blue-500 bg-blue-500/10"
                                    : "border-gray-600 hover:border-gray-500"
                                }`}
                              >
                                <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                                <p className="text-gray-300 mb-2">
                                  Drag and drop your image here, or
                                </p>
                                <label htmlFor="file-upload">
                                  <Button
                                    type="button"
                                    variant="outline"
                                    className="border-gray-600 text-white hover:bg-gray-700"
                                    onClick={() => document.getElementById("file-upload")?.click()}
                                  >
                                    Browse Files
                                  </Button>
                                </label>
                                <input
                                  id="file-upload"
                                  type="file"
                                  accept="image/png,image/jpeg,image/webp"
                                  className="hidden"
                                  onChange={handleFileInputChange}
                                />
                                <p className="text-sm text-gray-500 mt-4">
                                  PNG, JPG, or WebP (max 10MB)
                                </p>
                              </div>
                            )}
                          </div>
                        </FormControl>
                        <FormDescription className="text-gray-400">
                          Upload a clear image of your product for best results
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Product Name */}
                  <FormField
                    control={form.control}
                    name="product_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white">Product Name *</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="e.g., Premium Wireless Headphones"
                            className="bg-gray-900/50 border-gray-600 text-white placeholder:text-gray-500"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription className="text-gray-400">
                          The name of your product or service
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Style Selector */}
                  <FormField
                    control={form.control}
                    name="style"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white">Video Style *</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger className="bg-gray-900/50 border-gray-600 text-white">
                              <SelectValue placeholder="Select a style" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="bg-gray-800 border-gray-700">
                            {Object.entries(STYLE_DESCRIPTIONS).map(([value, description]) => (
                              <SelectItem
                                key={value}
                                value={value}
                                className="text-white focus:bg-gray-700 focus:text-white"
                              >
                                <div className="flex flex-col">
                                  <span className="font-medium capitalize">{value}</span>
                                  <span className="text-sm text-gray-400">{description}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormDescription className="text-gray-400">
                          Choose the visual style for your video
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Video Model Selector */}
                  <FormField
                    control={form.control}
                    name="video_model"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white">Video Generation Model *</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value} disabled={isLoadingModels}>
                          <FormControl>
                            <SelectTrigger className="bg-gray-900/50 border-gray-600 text-white">
                              <SelectValue placeholder={isLoadingModels ? "Loading models..." : "Select a model"} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="bg-gray-800 border-gray-700 max-h-[300px]">
                            {videoModels.length === 0 && !isLoadingModels && (
                              <div className="text-gray-400 px-2 py-8 text-center text-sm">
                                No models available. Please check backend connection.
                              </div>
                            )}
                            {videoModels.map((model) => (
                              <SelectItem
                                key={model.model_id}
                                value={model.model_id}
                                className="text-white focus:bg-gray-700 focus:text-white"
                              >
                                <div className="flex flex-col py-1">
                                  <span className="font-medium">{model.display_name}</span>
                                  <span className="text-xs text-gray-400">{model.description}</span>
                                  <span className="text-xs text-blue-400 mt-1">
                                    ${model.cost_per_run.toFixed(4)} • ~{Math.round(model.avg_duration)}s
                                  </span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormDescription className="text-gray-400">
                          Choose the AI model for video generation. Costs and generation times shown below each option.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* CTA Text */}
                  <FormField
                    control={form.control}
                    name="cta_text"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white">Call-to-Action Text *</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="e.g., Shop Now, Learn More, Get Started"
                            className="bg-gray-900/50 border-gray-600 text-white placeholder:text-gray-500"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription className="text-gray-400">
                          The action you want viewers to take
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Submit Button */}
                  <div className="flex gap-4 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      className="flex-1 border-gray-600 text-white hover:bg-gray-700"
                      onClick={() => router.push("/")}
                      disabled={isSubmitting}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Creating Video...
                        </>
                      ) : (
                        "Create Video"
                      )}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
