"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize,
  Minimize,
  Share2,
  Download,
  SkipForward,
  SkipBack,
  Loader2,
  Info,
  Film,
  Clock,
  HardDrive,
  Monitor
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/hooks/useToast"
import { FinalVideoPlayerProps, VideoControlState } from "@/types/video-player"

export default function FinalVideoPlayer({
  src,
  poster,
  metadata,
  autoPlay = false,
  muted = false,
  loop = false,
  className = "",
  showDownload = true,
  showShare = true,
  showMetadata = true,
  onEnded,
  onError,
  onPlay,
  onPause,
  onDownload,
  onShare,
}: FinalVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const controlsTimeoutRef = useRef<NodeJS.Timeout>()

  const [controlState, setControlState] = useState<VideoControlState>({
    isPlaying: false,
    isMuted: muted,
    volume: 1,
    currentTime: 0,
    duration: 0,
    isFullscreen: false,
    playbackRate: 1,
    buffered: 0,
    isLoading: true,
    showControls: true,
  })

  const [hasError, setHasError] = useState(false)
  const [isShareModalOpen, setIsShareModalOpen] = useState(false)
  const [showMetadataPanel, setShowMetadataPanel] = useState(false)

  const { toast } = useToast()

  // Get video source URL
  const videoSrc = typeof src === 'string' ? src : src[0]?.url || ''

  // Format time as MM:SS
  const formatTime = (time: number): string => {
    if (!isFinite(time)) return "0:00"
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  // Format file size
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return "Unknown"
    const mb = bytes / (1024 * 1024)
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(2)} GB`
    }
    return `${mb.toFixed(2)} MB`
  }

  // Toggle play/pause
  const togglePlay = useCallback(() => {
    if (!videoRef.current) return

    if (controlState.isPlaying) {
      videoRef.current.pause()
    } else {
      videoRef.current.play()
    }
  }, [controlState.isPlaying])

  // Toggle mute
  const toggleMute = useCallback(() => {
    if (!videoRef.current) return
    const newMuted = !controlState.isMuted
    videoRef.current.muted = newMuted
    setControlState(prev => ({ ...prev, isMuted: newMuted }))
  }, [controlState.isMuted])

  // Change volume
  const handleVolumeChange = useCallback((value: number[]) => {
    if (!videoRef.current) return
    const newVolume = value[0]
    videoRef.current.volume = newVolume

    setControlState(prev => ({
      ...prev,
      volume: newVolume,
      isMuted: newVolume === 0
    }))

    if (newVolume === 0) {
      videoRef.current.muted = true
    } else if (controlState.isMuted) {
      videoRef.current.muted = false
    }
  }, [controlState.isMuted])

  // Seek to position
  const handleSeek = useCallback((value: number[]) => {
    if (!videoRef.current) return
    const newTime = value[0]
    videoRef.current.currentTime = newTime
    setControlState(prev => ({ ...prev, currentTime: newTime }))
  }, [])

  // Skip forward/backward
  const skip = useCallback((seconds: number) => {
    if (!videoRef.current) return
    videoRef.current.currentTime = Math.max(
      0,
      Math.min(controlState.duration, videoRef.current.currentTime + seconds)
    )
  }, [controlState.duration])

  // Toggle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }, [])

  // Change playback speed
  const handlePlaybackRateChange = useCallback((rate: number) => {
    if (!videoRef.current) return
    videoRef.current.playbackRate = rate
    setControlState(prev => ({ ...prev, playbackRate: rate }))
    toast({
      title: "Playback Speed",
      description: `Changed to ${rate}x`,
      duration: 2000,
    })
  }, [toast])

  // Auto-hide controls
  const resetControlsTimeout = useCallback(() => {
    setControlState(prev => ({ ...prev, showControls: true }))
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current)
    }
    if (controlState.isPlaying) {
      controlsTimeoutRef.current = setTimeout(() => {
        setControlState(prev => ({ ...prev, showControls: false }))
      }, 3000)
    }
  }, [controlState.isPlaying])

  // Video event handlers
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handlePlay = () => {
      setControlState(prev => ({ ...prev, isPlaying: true }))
      onPlay?.()
    }

    const handlePause = () => {
      setControlState(prev => ({ ...prev, isPlaying: false }))
      onPause?.()
    }

    const handleTimeUpdate = () => {
      setControlState(prev => ({ ...prev, currentTime: video.currentTime }))
    }

    const handleLoadedMetadata = () => {
      setControlState(prev => ({
        ...prev,
        duration: video.duration,
        isLoading: false
      }))
    }

    const handleWaiting = () => {
      setControlState(prev => ({ ...prev, isLoading: true }))
    }

    const handleCanPlay = () => {
      setControlState(prev => ({ ...prev, isLoading: false }))
    }

    const handleEnded = () => {
      setControlState(prev => ({ ...prev, isPlaying: false }))
      onEnded?.()
    }

    const handleError = () => {
      setHasError(true)
      setControlState(prev => ({ ...prev, isLoading: false }))
      onError?.(new Error("Failed to load video"))
    }

    const handleProgress = () => {
      if (video.buffered.length > 0) {
        const bufferedEnd = video.buffered.end(video.buffered.length - 1)
        const bufferedPercent = (bufferedEnd / video.duration) * 100
        setControlState(prev => ({ ...prev, buffered: bufferedPercent }))
      }
    }

    video.addEventListener("play", handlePlay)
    video.addEventListener("pause", handlePause)
    video.addEventListener("timeupdate", handleTimeUpdate)
    video.addEventListener("loadedmetadata", handleLoadedMetadata)
    video.addEventListener("waiting", handleWaiting)
    video.addEventListener("canplay", handleCanPlay)
    video.addEventListener("ended", handleEnded)
    video.addEventListener("error", handleError)
    video.addEventListener("progress", handleProgress)

    return () => {
      video.removeEventListener("play", handlePlay)
      video.removeEventListener("pause", handlePause)
      video.removeEventListener("timeupdate", handleTimeUpdate)
      video.removeEventListener("loadedmetadata", handleLoadedMetadata)
      video.removeEventListener("waiting", handleWaiting)
      video.removeEventListener("canplay", handleCanPlay)
      video.removeEventListener("ended", handleEnded)
      video.removeEventListener("error", handleError)
      video.removeEventListener("progress", handleProgress)
    }
  }, [onEnded, onError, onPlay, onPause])

  // Fullscreen change handler
  useEffect(() => {
    const handleFullscreenChange = () => {
      setControlState(prev => ({
        ...prev,
        isFullscreen: !!document.fullscreenElement
      }))
    }

    document.addEventListener("fullscreenchange", handleFullscreenChange)
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange)
    }
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!videoRef.current) return

      // Don't trigger if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key.toLowerCase()) {
        case " ":
        case "k":
          e.preventDefault()
          togglePlay()
          break
        case "arrowleft":
        case "j":
          e.preventDefault()
          skip(-5)
          break
        case "arrowright":
        case "l":
          e.preventDefault()
          skip(5)
          break
        case "arrowup":
          e.preventDefault()
          handleVolumeChange([Math.min(1, controlState.volume + 0.1)])
          break
        case "arrowdown":
          e.preventDefault()
          handleVolumeChange([Math.max(0, controlState.volume - 0.1)])
          break
        case "f":
          e.preventDefault()
          toggleFullscreen()
          break
        case "m":
          e.preventDefault()
          toggleMute()
          break
        case "i":
          e.preventDefault()
          setShowMetadataPanel(prev => !prev)
          break
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [togglePlay, skip, toggleMute, toggleFullscreen, controlState.volume, handleVolumeChange])

  // Mouse movement for auto-hide controls
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleMouseMove = () => resetControlsTimeout()
    const handleMouseLeave = () => {
      if (controlState.isPlaying) {
        setControlState(prev => ({ ...prev, showControls: false }))
      }
    }

    container.addEventListener("mousemove", handleMouseMove)
    container.addEventListener("mouseleave", handleMouseLeave)

    return () => {
      container.removeEventListener("mousemove", handleMouseMove)
      container.removeEventListener("mouseleave", handleMouseLeave)
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current)
      }
    }
  }, [controlState.isPlaying, resetControlsTimeout])

  // Download functionality
  const handleDownload = useCallback(async () => {
    try {
      const link = document.createElement('a')
      link.href = videoSrc
      link.download = metadata?.title || 'video.mp4'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      toast({
        title: "Download started",
        description: "Your video download has begun",
      })

      onDownload?.()
    } catch (error) {
      toast({
        title: "Download failed",
        description: "Failed to download video. Please try again.",
        variant: "destructive",
      })
    }
  }, [videoSrc, metadata?.title, toast, onDownload])

  // Share functionality
  const handleShare = async (method: "copy" | "twitter" | "facebook" | "download" | "native") => {
    const url = window.location.href
    const title = metadata?.title || "AI Generated Video"

    switch (method) {
      case "copy":
        try {
          await navigator.clipboard.writeText(url)
          toast({
            title: "Link copied!",
            description: "Video link copied to clipboard",
          })
        } catch (err) {
          toast({
            title: "Failed to copy",
            description: "Please try again",
            variant: "destructive",
          })
        }
        break

      case "twitter":
        window.open(
          `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
          "_blank"
        )
        break

      case "facebook":
        window.open(
          `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
          "_blank"
        )
        break

      case "download":
        handleDownload()
        break

      case "native":
        if (navigator.share) {
          try {
            await navigator.share({
              title: title,
              url: url,
            })
          } catch (err) {
            // User cancelled or error occurred
          }
        }
        break
    }

    onShare?.(method)
    setIsShareModalOpen(false)
  }

  // Loading skeleton
  if (controlState.isLoading && !videoSrc) {
    return (
      <Card className={`bg-gray-800/50 border-gray-700 overflow-hidden ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <Film className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Final Video</h2>
          </div>
          <div className="space-y-4">
            <Skeleton className="aspect-video w-full rounded-lg" />
            <div className="flex gap-2">
              <Skeleton className="h-10 w-20" />
              <Skeleton className="h-10 w-20" />
              <Skeleton className="h-10 flex-1" />
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Error state
  if (hasError) {
    return (
      <Card className={`bg-gray-800/50 border-gray-700 overflow-hidden ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <Film className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Final Video</h2>
          </div>
          <div className="aspect-video bg-gray-900/50 rounded-lg border border-gray-700 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="text-red-500 text-lg font-semibold">Failed to load video</div>
              <Button
                onClick={() => {
                  setHasError(false)
                  setControlState(prev => ({ ...prev, isLoading: true }))
                  videoRef.current?.load()
                }}
                variant="outline"
                className="border-gray-600 text-white hover:bg-gray-800"
              >
                Retry
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card className={`bg-gray-800/50 border-gray-700 overflow-hidden ${className}`}>
        <CardContent className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Film className="w-5 h-5 text-blue-400" />
              <h2 className="text-xl font-semibold text-white">
                {metadata?.title || "Final Video"}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {showMetadata && metadata && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowMetadataPanel(!showMetadataPanel)}
                  className="text-gray-400 hover:text-white hover:bg-gray-700"
                  aria-label="Toggle video information"
                >
                  <Info className="h-5 w-5" />
                </Button>
              )}
              {showDownload && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="border-gray-600 text-white hover:bg-gray-700"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
              )}
              {showShare && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsShareModalOpen(true)}
                  className="border-gray-600 text-white hover:bg-gray-700"
                >
                  <Share2 className="h-4 w-4 mr-2" />
                  Share
                </Button>
              )}
            </div>
          </div>

          {/* Metadata Panel */}
          {showMetadataPanel && metadata && (
            <div className="mb-6 p-4 bg-gray-900/50 border border-gray-700 rounded-lg">
              <h3 className="text-sm font-semibold text-white mb-3">Video Information</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {metadata.duration && (
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-400" />
                    <div>
                      <div className="text-xs text-gray-400">Duration</div>
                      <div className="text-sm text-white">{formatTime(metadata.duration)}</div>
                    </div>
                  </div>
                )}
                {metadata.fileSize && (
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4 text-blue-400" />
                    <div>
                      <div className="text-xs text-gray-400">File Size</div>
                      <div className="text-sm text-white">{formatFileSize(metadata.fileSize)}</div>
                    </div>
                  </div>
                )}
                {metadata.resolution && (
                  <div className="flex items-center gap-2">
                    <Monitor className="w-4 h-4 text-blue-400" />
                    <div>
                      <div className="text-xs text-gray-400">Resolution</div>
                      <div className="text-sm text-white">{metadata.resolution}</div>
                    </div>
                  </div>
                )}
                {metadata.format && (
                  <div className="flex items-center gap-2">
                    <Film className="w-4 h-4 text-blue-400" />
                    <div>
                      <div className="text-xs text-gray-400">Format</div>
                      <div className="text-sm text-white uppercase">{metadata.format}</div>
                    </div>
                  </div>
                )}
              </div>
              {metadata.description && (
                <p className="mt-3 text-sm text-gray-400">{metadata.description}</p>
              )}
            </div>
          )}

          {/* Video Player */}
          <div
            ref={containerRef}
            className="relative bg-black rounded-lg overflow-hidden group"
            role="region"
            aria-label="Video player"
          >
            {/* Video Element */}
            <video
              ref={videoRef}
              src={videoSrc}
              poster={poster}
              autoPlay={autoPlay}
              muted={muted}
              loop={loop}
              className="w-full h-full aspect-video"
              playsInline
              aria-label={metadata?.title || "Video"}
            />

            {/* Loading Spinner */}
            {controlState.isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <Loader2 className="h-12 w-12 text-white animate-spin" />
              </div>
            )}

            {/* Click overlay to play/pause */}
            <div
              className="absolute inset-0 cursor-pointer"
              onClick={togglePlay}
              style={{ zIndex: 1 }}
              aria-label={controlState.isPlaying ? "Pause" : "Play"}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  togglePlay()
                }
              }}
            />

            {/* Controls */}
            <div
              className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/50 to-transparent transition-opacity duration-300 ${
                controlState.showControls ? "opacity-100" : "opacity-0"
              }`}
              style={{ zIndex: 2 }}
              onMouseEnter={() => setControlState(prev => ({ ...prev, showControls: true }))}
            >
              {/* Progress Bar with Buffer */}
              <div className="px-4 pt-4">
                <div className="relative">
                  {/* Buffer indicator */}
                  <div className="absolute top-1/2 -translate-y-1/2 h-1 bg-gray-600 rounded-full w-full">
                    <div
                      className="h-full bg-gray-500 rounded-full transition-all duration-300"
                      style={{ width: `${controlState.buffered}%` }}
                    />
                  </div>
                  {/* Progress slider */}
                  <Slider
                    value={[controlState.currentTime]}
                    max={controlState.duration || 100}
                    step={0.1}
                    onValueChange={handleSeek}
                    className="cursor-pointer relative z-10"
                    aria-label="Video progress"
                  />
                </div>
                <div className="flex justify-between text-xs text-white mt-1">
                  <span>{formatTime(controlState.currentTime)}</span>
                  <span>{formatTime(controlState.duration)}</span>
                </div>
              </div>

              {/* Control Buttons */}
              <div className="flex items-center justify-between px-4 pb-4 pt-2">
                <div className="flex items-center gap-2">
                  {/* Play/Pause */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      togglePlay()
                    }}
                    className="text-white hover:bg-white/20"
                    aria-label={controlState.isPlaying ? "Pause" : "Play"}
                  >
                    {controlState.isPlaying ? (
                      <Pause className="h-5 w-5" />
                    ) : (
                      <Play className="h-5 w-5" />
                    )}
                  </Button>

                  {/* Skip Backward */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      skip(-10)
                    }}
                    className="text-white hover:bg-white/20 hidden sm:flex"
                    aria-label="Skip backward 10 seconds"
                  >
                    <SkipBack className="h-5 w-5" />
                  </Button>

                  {/* Skip Forward */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      skip(10)
                    }}
                    className="text-white hover:bg-white/20 hidden sm:flex"
                    aria-label="Skip forward 10 seconds"
                  >
                    <SkipForward className="h-5 w-5" />
                  </Button>

                  {/* Volume */}
                  <div className="flex items-center gap-2 group/volume">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleMute()
                      }}
                      className="text-white hover:bg-white/20"
                      aria-label={controlState.isMuted ? "Unmute" : "Mute"}
                    >
                      {controlState.isMuted || controlState.volume === 0 ? (
                        <VolumeX className="h-5 w-5" />
                      ) : (
                        <Volume2 className="h-5 w-5" />
                      )}
                    </Button>
                    <div className="w-0 overflow-hidden group-hover/volume:w-20 transition-all duration-300 hidden md:block">
                      <Slider
                        value={[controlState.isMuted ? 0 : controlState.volume]}
                        max={1}
                        step={0.01}
                        onValueChange={handleVolumeChange}
                        className="cursor-pointer"
                        onClick={(e) => e.stopPropagation()}
                        aria-label="Volume"
                      />
                    </div>
                  </div>

                  {/* Playback Speed */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => e.stopPropagation()}
                        className="text-white hover:bg-white/20 text-xs hidden sm:flex"
                        aria-label={`Playback speed: ${controlState.playbackRate}x`}
                      >
                        {controlState.playbackRate}x
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
                      {[0.5, 0.75, 1, 1.25, 1.5, 2].map((rate) => (
                        <DropdownMenuItem
                          key={rate}
                          onClick={() => handlePlaybackRateChange(rate)}
                          className={controlState.playbackRate === rate ? "bg-gray-100" : ""}
                        >
                          {rate}x
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="flex items-center gap-2">
                  {/* Fullscreen */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleFullscreen()
                    }}
                    className="text-white hover:bg-white/20"
                    aria-label={controlState.isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
                  >
                    {controlState.isFullscreen ? (
                      <Minimize className="h-5 w-5" />
                    ) : (
                      <Maximize className="h-5 w-5" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Keyboard Shortcuts Help */}
          <div className="mt-4 text-xs text-gray-400">
            <details className="cursor-pointer">
              <summary className="hover:text-gray-300">Keyboard Shortcuts</summary>
              <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2 p-2 bg-gray-900/50 rounded border border-gray-700">
                <div><Badge variant="outline" className="mr-2">Space/K</Badge>Play/Pause</div>
                <div><Badge variant="outline" className="mr-2">←/J</Badge>Skip back 5s</div>
                <div><Badge variant="outline" className="mr-2">→/L</Badge>Skip forward 5s</div>
                <div><Badge variant="outline" className="mr-2">↑</Badge>Volume up</div>
                <div><Badge variant="outline" className="mr-2">↓</Badge>Volume down</div>
                <div><Badge variant="outline" className="mr-2">M</Badge>Mute/Unmute</div>
                <div><Badge variant="outline" className="mr-2">F</Badge>Fullscreen</div>
                <div><Badge variant="outline" className="mr-2">I</Badge>Toggle info</div>
              </div>
            </details>
          </div>
        </CardContent>
      </Card>

      {/* Share Modal */}
      <Dialog open={isShareModalOpen} onOpenChange={setIsShareModalOpen}>
        <DialogContent className="bg-gray-800 border-gray-700">
          <DialogHeader>
            <DialogTitle className="text-white">Share Video</DialogTitle>
            <DialogDescription className="text-gray-400">
              Share this video with others
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full justify-start border-gray-600 text-white hover:bg-gray-700"
              onClick={() => handleShare("copy")}
            >
              <Share2 className="mr-2 h-4 w-4" />
              Copy Link
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start border-gray-600 text-white hover:bg-gray-700"
              onClick={() => handleShare("twitter")}
            >
              <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
              Share on X (Twitter)
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start border-gray-600 text-white hover:bg-gray-700"
              onClick={() => handleShare("facebook")}
            >
              <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              </svg>
              Share on Facebook
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start border-gray-600 text-white hover:bg-gray-700"
              onClick={() => handleShare("download")}
            >
              <Download className="mr-2 h-4 w-4" />
              Download Video
            </Button>
            {typeof window !== 'undefined' && 'share' in navigator && (
              <Button
                variant="outline"
                className="w-full justify-start border-gray-600 text-white hover:bg-gray-700"
                onClick={() => handleShare("native")}
              >
                <Share2 className="mr-2 h-4 w-4" />
                More Options...
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
