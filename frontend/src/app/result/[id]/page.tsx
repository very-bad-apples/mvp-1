'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Video, ChevronLeft, CheckCircle, Loader2, XCircle, Download, Play } from 'lucide-react'
import { Logo } from '@/components/Logo'

type JobStatus = 'pending' | 'processing' | 'completed' | 'failed'

interface MockJobData {
  jobId: string
  status: JobStatus
  progress: number
  createdAt: string
  completedAt?: string
  videoUrl?: string
  error?: string
}

interface VideoSegment {
  url: string
  sceneNumber: number
  isReady: boolean
}

export default function ResultPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [jobData, setJobData] = useState<MockJobData>({
    jobId: params.id,
    status: 'pending',
    progress: 0,
    createdAt: new Date().toISOString(),
  })

  // Video composition state
  const [videoSegments, setVideoSegments] = useState<VideoSegment[]>([])
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0)
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null)
  const [currentSceneNumber, setCurrentSceneNumber] = useState(1)
  const [totalScenes, setTotalScenes] = useState(5)

  // Refs for canvas and video elements
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const animationFrameRef = useRef<number | null>(null)

  // Simulate receiving video segments over time
  useEffect(() => {
    const timeouts: NodeJS.Timeout[] = []

    // Start after 2 seconds, receive segments every 3 seconds
    const scheduleSegments = () => {
      const segments = [
        { delay: 2000, sceneNumber: 1, url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' },
        { delay: 5000, sceneNumber: 2, url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4' },
        { delay: 8000, sceneNumber: 3, url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4' },
        { delay: 11000, sceneNumber: 4, url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4' },
        { delay: 14000, sceneNumber: 5, url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4' },
      ]

      segments.forEach(({ delay, sceneNumber, url }) => {
        const timeout = setTimeout(() => {
          setVideoSegments((prev) => [
            ...prev,
            { url, sceneNumber, isReady: true }
          ])
          setJobData((prev) => ({
            ...prev,
            status: 'processing',
            progress: (sceneNumber / totalScenes) * 100
          }))
        }, delay)
        timeouts.push(timeout)
      })

      // After all segments, set final video URL
      const finalTimeout = setTimeout(() => {
        setFinalVideoUrl('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4')
        setJobData((prev) => ({
          ...prev,
          status: 'completed',
          progress: 100,
          completedAt: new Date().toISOString(),
          videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
        }))
      }, 17000)
      timeouts.push(finalTimeout)
    }

    if (jobData.status === 'pending') {
      scheduleSegments()
    }

    return () => {
      timeouts.forEach(timeout => clearTimeout(timeout))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  // Load and play current video segment
  useEffect(() => {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas || videoSegments.length === 0) return

    const currentSegment = videoSegments[currentSegmentIndex]
    if (!currentSegment) return

    // Load the current segment
    video.src = currentSegment.url
    video.load()

    const handleCanPlay = () => {
      video.play().catch(err => console.error('Error playing video:', err))
      setCurrentSceneNumber(currentSegment.sceneNumber)
    }

    video.addEventListener('canplay', handleCanPlay)

    return () => {
      video.removeEventListener('canplay', handleCanPlay)
    }
  }, [currentSegmentIndex, videoSegments])

  // Draw video frames to canvas
  useEffect(() => {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const drawFrame = () => {
      if (video.paused || video.ended) {
        animationFrameRef.current = requestAnimationFrame(drawFrame)
        return
      }

      // Set canvas size to match video dimensions
      canvas.width = video.videoWidth || 1280
      canvas.height = video.videoHeight || 720

      // Draw current video frame to canvas
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

      animationFrameRef.current = requestAnimationFrame(drawFrame)
    }

    // Start drawing loop
    animationFrameRef.current = requestAnimationFrame(drawFrame)

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [videoSegments])

  // Handle video end - transition to next segment or loop
  const handleVideoEnded = () => {
    const nextIndex = currentSegmentIndex + 1

    if (nextIndex < videoSegments.length) {
      // Next segment is ready, transition to it
      setCurrentSegmentIndex(nextIndex)
    } else if (finalVideoUrl) {
      // All segments done, final video is ready
      // Canvas will be replaced by final video in UI
    } else {
      // Next segment not ready, loop current segment
      const video = videoRef.current
      if (video) {
        video.currentTime = 0
        video.play().catch(err => console.error('Error looping video:', err))
      }
    }
  }

  const getStatusBadge = () => {
    switch (jobData.status) {
      case 'pending':
        return <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20">Pending</Badge>
      case 'processing':
        return <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Processing</Badge>
      case 'completed':
        return <Badge className="bg-green-500/10 text-green-400 border-green-500/20">Completed</Badge>
      case 'failed':
        return <Badge className="bg-red-500/10 text-red-400 border-red-500/20">Failed</Badge>
    }
  }

  const getStatusIcon = () => {
    switch (jobData.status) {
      case 'pending':
      case 'processing':
        return <Loader2 className="h-12 w-12 text-blue-400 animate-spin" />
      case 'completed':
        return <CheckCircle className="h-12 w-12 text-green-400" />
      case 'failed':
        return <XCircle className="h-12 w-12 text-red-400" />
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <nav className="border-b border-gray-700/50 backdrop-blur-sm bg-gray-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3">
              <Logo size="sm" className="text-blue-500" />
              <span className="text-2xl font-bold text-white">Bad Apple</span>
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
              Video Generation Status
            </h1>
            <p className="text-xl text-gray-300">
              Track your video generation progress
            </p>
          </div>

          <div className="space-y-6">
            {/* Status Card */}
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white">Job Status</CardTitle>
                  {getStatusBadge()}
                </div>
                <CardDescription className="text-gray-400">
                  Job ID: {jobData.jobId}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Status Icon */}
                  <div className="flex justify-center">
                    {getStatusIcon()}
                  </div>

                  {/* Progress Bar */}
                  {(jobData.status === 'pending' || jobData.status === 'processing') && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm text-gray-400">
                        <span>Progress</span>
                        <span>{Math.round(jobData.progress)}%</span>
                      </div>
                      <Progress value={jobData.progress} className="h-2" />
                    </div>
                  )}

                  {/* Job Details */}
                  <div className="border-t border-gray-700 pt-4 space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Created</span>
                      <span className="text-white">{formatDate(jobData.createdAt)}</span>
                    </div>
                    {jobData.completedAt && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Completed</span>
                        <span className="text-white">{formatDate(jobData.completedAt)}</span>
                      </div>
                    )}
                  </div>

                  {/* Completion Message */}
                  {jobData.status === 'completed' && (
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center">
                      <p className="text-green-400 font-medium">
                        Your video has been generated successfully!
                      </p>
                    </div>
                  )}

                  {/* Error Message */}
                  {jobData.status === 'failed' && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                      <p className="text-red-400 font-medium mb-2">
                        Video generation failed
                      </p>
                      <p className="text-sm text-gray-400">
                        {jobData.error || 'An unknown error occurred. Please try again.'}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Video Preview Card (shown when processing or completed) */}
            {(jobData.status === 'processing' || jobData.status === 'completed') && (
              <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white">
                      {finalVideoUrl ? 'Final Video' : 'Live Preview'}
                    </CardTitle>
                    {!finalVideoUrl && (
                      <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                        Scene {currentSceneNumber} of {totalScenes}
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-gray-400">
                    {finalVideoUrl
                      ? 'Your generated video is ready'
                      : 'Compositing video segments as they arrive'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Live Canvas Preview or Final Video */}
                    <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                      {finalVideoUrl ? (
                        // Final complete video
                        <video
                          src={finalVideoUrl}
                          controls
                          className="w-full h-full"
                          autoPlay
                        />
                      ) : (
                        // Live canvas composition
                        <div className="relative w-full h-full">
                          <canvas
                            ref={canvasRef}
                            className="w-full h-full object-contain"
                          />
                          {videoSegments.length === 0 && (
                            <div className="absolute inset-0 flex items-center justify-center">
                              <div className="text-center space-y-4">
                                <Loader2 className="h-16 w-16 text-blue-400 animate-spin mx-auto" />
                                <p className="text-gray-400">Waiting for first scene...</p>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Hidden video element for loading segments */}
                    <video
                      ref={videoRef}
                      className="hidden"
                      onEnded={handleVideoEnded}
                      playsInline
                      muted
                    />

                    {/* Action Buttons */}
                    {finalVideoUrl && (
                      <div className="flex gap-4">
                        <Button
                          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                          onClick={() => {
                            const link = document.createElement('a')
                            link.href = finalVideoUrl
                            link.download = `video-${jobData.jobId}.mp4`
                            link.click()
                          }}
                        >
                          <Download className="mr-2 h-4 w-4" />
                          Download Video
                        </Button>
                        <Button
                          variant="outline"
                          className="flex-1 border-gray-600 text-white hover:bg-gray-800"
                          onClick={() => router.push(`/edit/${jobData.jobId}`)}
                        >
                          Edit Video
                        </Button>
                      </div>
                    )}

                    {/* Live composition info */}
                    {!finalVideoUrl && videoSegments.length > 0 && (
                      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                        <p className="text-sm text-blue-400 text-center">
                          {videoSegments.length === totalScenes
                            ? 'All scenes received! Finalizing video...'
                            : `Received ${videoSegments.length} of ${totalScenes} scenes`}
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Action Buttons for Pending/Failed States */}
            {(jobData.status === 'pending' || jobData.status === 'failed') && (
              <div className="flex gap-4">
                <Button
                  variant="outline"
                  className="flex-1 border-gray-600 text-white hover:bg-gray-800"
                  onClick={() => router.push('/create')}
                >
                  Create New Video
                </Button>
                <Button
                  variant="outline"
                  className="flex-1 border-gray-600 text-white hover:bg-gray-800"
                  onClick={() => router.push('/')}
                >
                  Back to Home
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
