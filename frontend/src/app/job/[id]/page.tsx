"use client"

import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { Video, ChevronLeft, CheckCircle, XCircle, Clock, Loader2, Wifi, WifiOff, Download, RotateCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import VideoPlayer from "@/components/VideoPlayer"

// Types
interface Stage {
  stage: string
  progress: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
}

interface Job {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  stages: Stage[]
  video_url?: string
  error_message?: string
  created_at: string
  prompt?: string
  voice_id?: string
  background_music?: string
}

interface WebSocketMessage {
  type: 'connected' | 'progress_update' | 'status_update' | 'error'
  job_id: string
  message?: string
  progress?: number
  status?: string
  stages?: Stage[]
  video_url?: string
  error_message?: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

const STAGE_NAMES = {
  script_gen: 'Script Generation',
  voice_gen: 'Voiceover Generation',
  video_gen: 'Video Generation',
  compositing: 'Video Compositing'
}

const STATUS_COLORS = {
  pending: 'bg-gray-500',
  processing: 'bg-blue-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500'
}

const STATUS_ICONS = {
  pending: Clock,
  processing: Loader2,
  completed: CheckCircle,
  failed: XCircle
}

export default function JobStatusPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string

  const [job, setJob] = useState<Job | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [wsError, setWsError] = useState(false)
  const [ws, setWs] = useState<WebSocket | null>(null)

  // Fetch initial job data
  const fetchJobData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
        headers: {
          'X-API-Key': API_KEY,
        },
      })

      if (!response.ok) {
        if (response.status === 404) {
          setError('Job not found. Please check the job ID.')
        } else {
          setError('Failed to fetch job data. Please try again.')
        }
        return
      }

      const data = await response.json()
      setJob(data)
    } catch (err) {
      console.error('Error fetching job data:', err)
      setError('Network error. Please check your connection.')
    } finally {
      setIsLoading(false)
    }
  }, [jobId])

  // WebSocket connection
  useEffect(() => {
    if (!jobId) return

    // Fetch initial data
    fetchJobData()

    // Setup WebSocket
    let websocket: WebSocket | null = null
    let reconnectTimeout: NodeJS.Timeout | null = null
    let isMounted = true
    let shouldReconnect = true

    const connectWebSocket = () => {
      try {
        websocket = new WebSocket(`${WS_URL}/ws/jobs/${jobId}`)

        websocket.onopen = () => {
          console.log('WebSocket connected')
          if (isMounted) {
            setIsConnected(true)
            setWsError(false)
          }
        }

        websocket.onclose = () => {
          console.log('WebSocket disconnected')
          if (isMounted && shouldReconnect) {
            setIsConnected(false)
            // Try to reconnect after 3 seconds
            reconnectTimeout = setTimeout(() => {
              if (isMounted && shouldReconnect) {
                connectWebSocket()
              }
            }, 3000)
          }
        }

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error)
          if (isMounted) {
            setWsError(true)
            setIsConnected(false)
          }
        }

        websocket.onmessage = (event) => {
          if (!isMounted) return

          try {
            const data: WebSocketMessage = JSON.parse(event.data)

            if (data.type === 'connected') {
              console.log('WebSocket connected:', data.message)
            } else if (data.type === 'progress_update' || data.type === 'status_update') {
              if (!isMounted) return
              setJob(prevJob => {
                if (!prevJob) return prevJob

                return {
                  ...prevJob,
                  progress: data.progress ?? prevJob.progress,
                  status: (data.status as Job['status']) ?? prevJob.status,
                  stages: data.stages ?? prevJob.stages,
                  video_url: data.video_url ?? prevJob.video_url
                }
              })
            } else if (data.type === 'error') {
              if (!isMounted) return
              setJob(prevJob => {
                if (!prevJob) return prevJob

                return {
                  ...prevJob,
                  status: 'failed',
                  error_message: data.error_message
                }
              })
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err)
          }
        }

        setWs(websocket)
      } catch (err) {
        console.error('Error creating WebSocket:', err)
        if (isMounted) {
          setWsError(true)
        }
      }
    }

    connectWebSocket()

    return () => {
      isMounted = false
      shouldReconnect = false
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (websocket) {
        websocket.close()
      }
    }
  }, [jobId, fetchJobData])

  // Calculate overall progress from stages
  const calculateOverallProgress = (stages: Stage[]) => {
    if (!stages || stages.length === 0) return 0
    const totalProgress = stages.reduce((sum, stage) => sum + stage.progress, 0)
    return Math.round(totalProgress / stages.length)
  }

  // Handle retry
  const handleRetry = () => {
    router.push('/create')
  }

  // Render loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
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

        <div className="container mx-auto px-4 py-12">
          <div className="max-w-4xl mx-auto space-y-6">
            <Skeleton className="h-12 w-3/4 mx-auto" />
            <Skeleton className="h-6 w-1/2 mx-auto" />
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-4 w-2/3" />
              </CardHeader>
              <CardContent className="space-y-4">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  // Render error state
  if (error || !job) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
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

        <div className="container mx-auto px-4 py-12">
          <div className="max-w-4xl mx-auto">
            <Alert variant="destructive" className="bg-red-900/20 border-red-500">
              <XCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error || 'Job not found'}</AlertDescription>
            </Alert>

            <div className="mt-6 flex gap-4 justify-center">
              <Button onClick={fetchJobData} variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
                <RotateCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
              <Link href="/create">
                <Button className="bg-blue-600 hover:bg-blue-700">
                  Create New Video
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const overallProgress = job.stages && job.stages.length > 0
    ? calculateOverallProgress(job.stages)
    : job.progress

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
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-3 mb-4">
              <h1 className="text-3xl md:text-4xl font-bold text-white">
                {job.status === 'completed' ? 'Video Ready!' :
                 job.status === 'failed' ? 'Generation Failed' :
                 'Generating Your Video'}
              </h1>
              {(job.status === 'processing' || job.status === 'pending') && (
                <Badge variant={isConnected ? "default" : "secondary"} className="gap-1">
                  {isConnected ? (
                    <>
                      <Wifi className="h-3 w-3" />
                      Live
                    </>
                  ) : (
                    <>
                      <WifiOff className="h-3 w-3" />
                      Disconnected
                    </>
                  )}
                </Badge>
              )}
            </div>
            <p className="text-gray-400">Job ID: {job.job_id}</p>
            {job.prompt && (
              <p className="text-gray-300 mt-2 italic">&quot;{job.prompt}&quot;</p>
            )}
          </div>

          {/* Overall Status Card */}
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">Overall Progress</CardTitle>
                <Badge className={STATUS_COLORS[job.status]}>
                  {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                </Badge>
              </div>
              <CardDescription className="text-gray-400">
                {new Date(job.created_at).toLocaleString()}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300">Progress</span>
                  <span className="text-white font-semibold">{overallProgress}%</span>
                </div>
                <Progress value={overallProgress} className="h-3" />
              </div>

              {/* Failed Job Error */}
              {job.status === 'failed' && job.error_message && (
                <Alert variant="destructive" className="bg-red-900/20 border-red-500">
                  <XCircle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{job.error_message}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Stage Progress Cards */}
          {job.stages && job.stages.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-semibold text-white">Generation Stages</h2>
              <div className="grid gap-4">
                {job.stages.map((stage, index) => {
                  const StatusIcon = STATUS_ICONS[stage.status]

                  return (
                    <Card key={`${stage.stage}-${index}`} className="bg-gray-800/50 border-gray-700">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-full ${STATUS_COLORS[stage.status]}`}>
                              <StatusIcon className={`h-5 w-5 text-white ${stage.status === 'processing' ? 'animate-spin' : ''}`} />
                            </div>
                            <div>
                              <CardTitle className="text-white text-lg">
                                {STAGE_NAMES[stage.stage as keyof typeof STAGE_NAMES] || stage.stage}
                              </CardTitle>
                              <CardDescription className="text-gray-400">
                                Stage {index + 1} of {job.stages.length}
                              </CardDescription>
                            </div>
                          </div>
                          <Badge className={STATUS_COLORS[stage.status]}>
                            {stage.status}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-300">Progress</span>
                            <span className="text-white font-semibold">{stage.progress}%</span>
                          </div>
                          <Progress value={stage.progress} className="h-2" />
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}

          {/* Video Player for Completed Jobs */}
          {job.status === 'completed' && job.video_url && (
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Your Video is Ready!</CardTitle>
                <CardDescription className="text-gray-400">
                  Watch and download your generated video
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <VideoPlayer
                  src={job.video_url}
                  onEnded={() => console.log('Video playback ended')}
                  onError={(error) => console.error('Video error:', error)}
                />

                <div className="flex gap-4">
                  <Link href="/create" className="flex-1">
                    <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-800 w-full">
                      Create Another Video
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Failed Job Actions */}
          {job.status === 'failed' && (
            <div className="flex gap-4 justify-center">
              <Button onClick={handleRetry} className="bg-blue-600 hover:bg-blue-700">
                <RotateCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
              <Link href="/">
                <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
                  Back to Home
                </Button>
              </Link>
            </div>
          )}

          {/* Connection Status Warning */}
          {wsError && !isConnected && (job.status === 'processing' || job.status === 'pending') && (
            <Alert className="bg-yellow-900/20 border-yellow-500">
              <WifiOff className="h-4 w-4" />
              <AlertTitle>Connection Issue</AlertTitle>
              <AlertDescription>
                Live updates are unavailable. The page will continue to show status but may not update in real-time.
              </AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </div>
  )
}
