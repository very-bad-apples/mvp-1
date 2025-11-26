'use client'

import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Maximize, Gauge, Keyboard } from 'lucide-react'
import { Project, ProjectScene } from '@/types/project'
import { Badge } from '@/components/ui/badge'
import { useEffect, useRef, useState } from 'react'
import { getVideoStableId } from '@/lib/utils/video'

interface VideoPreviewProps {
  jobId: string
  project: Project
  currentTime: number
  duration: number
  isPlaying: boolean
  onPlayPause: () => void
  onSeek: (time: number) => void
  showFinalVideo?: boolean
  isComposing?: boolean
  selectedScene?: ProjectScene | null
  isScenePreviewMode?: boolean // When true, locks to selectedScene; when false, shows details for currently playing scene
  muted?: boolean // When true, video element is muted (for audio backing track playback)
  onAudioVolumeChange?: (volume: number) => void // Callback for audio volume changes when muted is true
  onAudioMuteChange?: (muted: boolean) => void // Callback for audio mute changes when muted is true
}

export function VideoPreview({
  jobId,
  project,
  currentTime,
  duration,
  isPlaying,
  onPlayPause,
  onSeek,
  showFinalVideo = false,
  isComposing = false,
  selectedScene = null,
  isScenePreviewMode = false,
  muted = false,
  onAudioVolumeChange,
  onAudioMuteChange,
}: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0)
  const [videoError, setVideoError] = useState<string | null>(null)
  const [isVideoLoaded, setIsVideoLoaded] = useState(false)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false)
  const [showSpeedIndicator, setShowSpeedIndicator] = useState(false)
  const lastSeekTimeRef = useRef<number>(0)
  const isSeekingRef = useRef(false)
  const isTransitioningRef = useRef(false)
  const speedIndicatorTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  // Track the last stable video ID to prevent reloads when only presigned URL changes
  const lastVideoStableIdRef = useRef<string | null>(null)
  const lastSceneIndexRef = useRef<number>(-1)

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/10 text-green-400 border-green-500/20'
      case 'processing':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
      case 'failed':
        return 'bg-red-500/10 text-red-400 border-red-500/20'
      default:
        return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
    }
  }

  // Get scenes with valid video URLs, sorted by displaySequence for correct playback order
  const validScenes = project.scenes
    .filter(scene => scene.originalVideoClipUrl || scene.videoClipUrl)
    .sort((a, b) => a.displaySequence - b.displaySequence)

  // Calculate cumulative scene start times for seeking
  const sceneTimings = validScenes.map((scene, index) => {
    const startTime = validScenes
      .slice(0, index)
      .reduce((total, s) => total + (s.duration || 0), 0)
    return {
      scene,
      startTime,
      endTime: startTime + (scene.duration || 0),
    }
  })

  // Find which scene should be playing at the current time
  const getCurrentSceneInfo = (time: number) => {
    for (let i = 0; i < sceneTimings.length; i++) {
      const timing = sceneTimings[i]
      if (time >= timing.startTime && time < timing.endTime) {
        // Calculate local time within the scene (0 to scene.duration)
        const sceneLocalTime = time - timing.startTime

        // If scene has trim points, add the trim offset to get actual video time
        const trimOffset = timing.scene.trimPoints?.in || 0
        const videoTime = sceneLocalTime + trimOffset

        return {
          index: i,
          timing,
          localTime: videoTime, // This is the actual video time including trim offset
        }
      }
    }
    // If beyond all scenes, return last scene
    if (sceneTimings.length > 0) {
      const lastTiming = sceneTimings[sceneTimings.length - 1]
      const trimOffset = lastTiming.scene.trimPoints?.in || 0
      return {
        index: sceneTimings.length - 1,
        timing: lastTiming,
        localTime: (lastTiming.scene.duration || 0) + trimOffset,
      }
    }
    return null
  }

  // Handle scene changes when currentTime updates (from external seek)
  useEffect(() => {
    const sceneInfo = getCurrentSceneInfo(currentTime)
    if (!sceneInfo) return

    // If scene changed, update the current scene index
    if (sceneInfo.index !== currentSceneIndex) {
      console.log('[VideoPreview] Scene change detected:', {
        currentTime,
        oldSceneIndex: currentSceneIndex,
        newSceneIndex: sceneInfo.index,
        timing: sceneInfo.timing
      })
      setCurrentSceneIndex(sceneInfo.index)
      setIsVideoLoaded(false)
      setVideoError(null)
    }
  }, [currentTime, currentSceneIndex])

  // Load video when scene changes OR when final video becomes available OR when selected scene changes
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    // MODE 1: If in scene preview mode, show only that scene's video
    if (isScenePreviewMode && selectedScene && (selectedScene.originalVideoClipUrl || selectedScene.videoClipUrl)) {
      const videoUrl = selectedScene.lipSyncedVideoClipUrl || selectedScene.originalVideoClipUrl || selectedScene.videoClipUrl
      const videoStableId = getVideoStableId(videoUrl)

      const handleLoadedMetadata = () => {
        setIsVideoLoaded(true)
        setVideoError(null)
        video.currentTime = 0 // Start from beginning of selected scene
        // Enforce muted state when muted prop is true
        if (muted) {
          video.muted = true
        }
      }

      const handleLoadedData = () => {
        // Playback handled by separate play/pause effect
      }

      const handleError = (e: Event) => {
        console.error('Selected scene video loading error:', e)
        setVideoError('Failed to load selected scene video')
        setIsVideoLoaded(false)
      }

      video.addEventListener('loadedmetadata', handleLoadedMetadata)
      video.addEventListener('loadeddata', handleLoadedData)
      video.addEventListener('error', handleError)

      // Only reload if the S3 key path changed (not just presigned URL)
      if (videoUrl && videoStableId && videoStableId !== lastVideoStableIdRef.current) {
        lastVideoStableIdRef.current = videoStableId
        video.src = videoUrl
        video.load()
      } else if (videoUrl && !videoStableId) {
        // Fallback: if we can't extract stable ID, use URL comparison (less efficient but safe)
        if (video.src !== videoUrl) {
          video.src = videoUrl
          video.load()
        }
      }

      return () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata)
        video.removeEventListener('loadeddata', handleLoadedData)
        video.removeEventListener('error', handleError)
      }
    }

    // MODE 2: If showing final video and it's available, load that instead
    if (showFinalVideo && project.finalOutputUrl) {
      const videoStableId = getVideoStableId(project.finalOutputUrl)

      const handleLoadedMetadata = () => {
        setIsVideoLoaded(true)
        setVideoError(null)
        // Seeking handled by separate sync effect
        // Enforce muted state when muted prop is true
        if (muted) {
          video.muted = true
        }
      }

      const handleLoadedData = () => {
        // Playback handled by separate play/pause effect
      }

      const handleError = (e: Event) => {
        console.error('Final video loading error:', e)
        setVideoError('Failed to load final video')
        setIsVideoLoaded(false)
      }

      video.addEventListener('loadedmetadata', handleLoadedMetadata)
      video.addEventListener('loadeddata', handleLoadedData)
      video.addEventListener('error', handleError)

      // Only reload if the S3 key path changed (not just presigned URL)
      if (videoStableId && videoStableId !== lastVideoStableIdRef.current) {
        lastVideoStableIdRef.current = videoStableId
        video.src = project.finalOutputUrl
        video.load()
      } else if (!videoStableId) {
        // Fallback: if we can't extract stable ID, use URL comparison (less efficient but safe)
        if (video.src !== project.finalOutputUrl) {
          video.src = project.finalOutputUrl
          video.load()
        }
      }

      return () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata)
        video.removeEventListener('loadeddata', handleLoadedData)
        video.removeEventListener('error', handleError)
      }
    }

    // MODE 3: Otherwise, load scene videos as normal (sequential playback)
    if (validScenes.length === 0) return

    const currentScene = validScenes[currentSceneIndex]
    const currentVideoUrl = currentScene?.originalVideoClipUrl ?? currentScene?.videoClipUrl
    if (!currentVideoUrl) return

    const videoStableId = getVideoStableId(currentVideoUrl)

    const handleLoadedMetadata = () => {
      setIsVideoLoaded(true)
      setVideoError(null)
      // Clear transitioning flag now that new video has loaded
      isTransitioningRef.current = false
      console.log('[VideoPreview] Video loaded, cleared transitioning flag')
      // Initial seek will be handled by the sync effect
      // Enforce muted state when muted prop is true
      if (muted) {
        video.muted = true
      }
    }

    const handleLoadedData = () => {
      // Video loaded - playback will be handled by play/pause effect
    }

    const handleError = (e: Event) => {
      console.error('Video loading error:', e)
      setVideoError('Failed to load video')
      setIsVideoLoaded(false)
    }

    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('loadeddata', handleLoadedData)
    video.addEventListener('error', handleError)

    // Only reload video when the S3 key path changed (not just presigned URL)
    // Also reload if scene index changed (different scene)
    const sceneChanged = currentSceneIndex !== lastSceneIndexRef.current
    if (videoStableId && (videoStableId !== lastVideoStableIdRef.current || sceneChanged)) {
      lastVideoStableIdRef.current = videoStableId
      lastSceneIndexRef.current = currentSceneIndex
      video.src = currentVideoUrl
      video.load()
    } else if (!videoStableId) {
      // Fallback: if we can't extract stable ID, use URL comparison (less efficient but safe)
      if (video.src !== currentVideoUrl || sceneChanged) {
        lastSceneIndexRef.current = currentSceneIndex
        video.src = currentVideoUrl
        video.load()
      }
    }

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('loadeddata', handleLoadedData)
      video.removeEventListener('error', handleError)
    }
  }, [isScenePreviewMode, selectedScene, currentSceneIndex, validScenes, showFinalVideo, project.finalOutputUrl, muted])

  // Handle play/pause state changes
  useEffect(() => {
    const video = videoRef.current
    if (!video || !isVideoLoaded) return

    if (isPlaying) {
      video.play().catch(err => {
        console.error('Error playing video:', err)
        setVideoError('Failed to play video')
      })
    } else {
      video.pause()
    }
  }, [isPlaying, isVideoLoaded])

  // Sync video playback time with parent currentTime (only for normal sequential playback)
  useEffect(() => {
    const video = videoRef.current
    if (!video || !isVideoLoaded || isSeekingRef.current) return

    // Skip sync when in scene preview mode or viewing final video - they manage their own playback
    if ((isScenePreviewMode && selectedScene) || (showFinalVideo && project.finalOutputUrl)) return

    const sceneInfo = getCurrentSceneInfo(currentTime)
    if (!sceneInfo || sceneInfo.index !== currentSceneIndex) return

    const currentScene = validScenes[currentSceneIndex]

    // Only seek if there's a significant difference (>0.1s) to avoid micro-adjustments
    const diff = Math.abs(video.currentTime - sceneInfo.localTime)
    if (diff > 0.1) {
      console.log('[VideoPreview] Syncing video time:', {
        currentTime,
        sceneIndex: currentSceneIndex,
        videoCurrentTime: video.currentTime,
        targetTime: sceneInfo.localTime,
        trimPoints: currentScene?.trimPoints,
        diff
      })
      video.currentTime = sceneInfo.localTime
    }
  }, [currentTime, currentSceneIndex, isVideoLoaded, isScenePreviewMode, selectedScene, showFinalVideo, project.finalOutputUrl, validScenes])

  // Handle video timeupdate event to sync parent currentTime (only for normal sequential playback)
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      if (isSeekingRef.current || isTransitioningRef.current) return

      // Skip updating parent timeline when in scene preview mode or viewing final video
      if ((isScenePreviewMode && selectedScene) || (showFinalVideo && project.finalOutputUrl)) return

      const sceneInfo = sceneTimings[currentSceneIndex]
      if (!sceneInfo) return

      // Calculate scene-local time by subtracting trim offset from video time
      const trimOffset = sceneInfo.scene.trimPoints?.in || 0
      const sceneLocalTime = video.currentTime - trimOffset
      const globalTime = sceneInfo.startTime + sceneLocalTime

      // Only update if there's a meaningful difference to avoid excessive updates
      if (Math.abs(globalTime - currentTime) > 0.05) {
        onSeek(globalTime)
      }
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    return () => video.removeEventListener('timeupdate', handleTimeUpdate)
  }, [currentSceneIndex, currentTime, onSeek, sceneTimings, isScenePreviewMode, selectedScene, showFinalVideo, project.finalOutputUrl])

  // Enforce trim boundaries during playback (only for normal sequential playback)
  useEffect(() => {
    const video = videoRef.current
    if (!video || !isVideoLoaded) return

    // Skip when in scene preview mode or viewing final video
    if ((isScenePreviewMode && selectedScene) || (showFinalVideo && project.finalOutputUrl)) return

    const sceneInfo = sceneTimings[currentSceneIndex]
    if (!sceneInfo || !sceneInfo.scene.trimPoints) return

    const trimPoints = sceneInfo.scene.trimPoints

    const handleTimeUpdate = () => {
      // Only enforce the OUT boundary - if video goes past trim out point, transition to next scene
      // Don't enforce IN boundary here since that's handled by the initial seek in getCurrentSceneInfo
      if (video.currentTime >= trimPoints.out - 0.1) {
        console.log('[VideoPreview] Trim boundary reached:', {
          sceneIndex: currentSceneIndex,
          videoTime: video.currentTime,
          trimOut: trimPoints.out,
          hasNextScene: currentSceneIndex < validScenes.length - 1
        })

        // Set transitioning flag to prevent timeupdate handler from interfering
        isTransitioningRef.current = true

        // Remove the event listener immediately to prevent multiple triggers
        video.removeEventListener('timeupdate', handleTimeUpdate)

        // Reached end of trim, move to next scene
        if (currentSceneIndex < validScenes.length - 1) {
          const nextSceneIndex = currentSceneIndex + 1
          const nextSceneTiming = sceneTimings[nextSceneIndex]
          console.log('[VideoPreview] Transitioning to next scene:', {
            from: currentSceneIndex,
            to: nextSceneIndex,
            nextStartTime: nextSceneTiming.startTime
          })
          setCurrentSceneIndex(nextSceneIndex)
          setIsVideoLoaded(false)
          onSeek(nextSceneTiming.startTime)
        } else {
          // End of all scenes - stop playback
          console.log('[VideoPreview] End of all scenes, stopping playback')
          onPlayPause()
          setCurrentSceneIndex(0)
          onSeek(0)
        }
      }
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    return () => video.removeEventListener('timeupdate', handleTimeUpdate)
  }, [currentSceneIndex, isVideoLoaded, sceneTimings, validScenes.length, onSeek, onPlayPause, isScenePreviewMode, selectedScene, showFinalVideo, project.finalOutputUrl])

  // Handle automatic scene transitions when video ends
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleEnded = () => {
      // Check if there's a next scene
      if (currentSceneIndex < validScenes.length - 1) {
        // Move to next scene
        const nextSceneIndex = currentSceneIndex + 1
        const nextSceneTiming = sceneTimings[nextSceneIndex]

        setCurrentSceneIndex(nextSceneIndex)
        setIsVideoLoaded(false)
        onSeek(nextSceneTiming.startTime)
      } else {
        // End of all scenes - stop playback
        onPlayPause() // This will set isPlaying to false

        // Reset to beginning
        setCurrentSceneIndex(0)
        onSeek(0)
      }
    }

    video.addEventListener('ended', handleEnded)
    return () => video.removeEventListener('ended', handleEnded)
  }, [currentSceneIndex, validScenes.length, onSeek, onPlayPause, sceneTimings])

  // Handle volume changes
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    // If muted prop is true, video must stay muted and volume must not be changed
    // Only control audio element via callbacks
    if (muted) {
      // Enforce video muted state (must always be true)
      video.muted = true
      // Never modify video volume when muted prop is true
      if (onAudioVolumeChange && onAudioMuteChange) {
        onAudioVolumeChange(volume)
        onAudioMuteChange(isMuted)
      }
      return
    }

    // Otherwise, control video volume as normal
    video.volume = isMuted ? 0 : volume
  }, [volume, isMuted, muted, onAudioVolumeChange, onAudioMuteChange])

  // Handle muted prop (for audio backing track playback)
  // This effect ensures video stays muted when muted prop is true
  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    if (muted) {
      video.muted = true
    }
  }, [muted, isVideoLoaded]) // Also run when video loads to enforce muted state

  // Handle playback speed changes
  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    video.playbackRate = playbackSpeed
  }, [playbackSpeed])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (speedIndicatorTimeoutRef.current) {
        clearTimeout(speedIndicatorTimeoutRef.current)
      }
    }
  }, [])

  // Handle scene navigation
  const skipToNextScene = () => {
    // Safety check: ensure we have valid scene timings
    if (sceneTimings.length === 0) {
      return
    }

    if (currentSceneIndex < sceneTimings.length - 1) {
      const nextSceneIndex = currentSceneIndex + 1
      const nextSceneTiming = sceneTimings[nextSceneIndex]
      if (!nextSceneTiming) return

      setCurrentSceneIndex(nextSceneIndex)
      setIsVideoLoaded(false)
      onSeek(nextSceneTiming.startTime)
    }
  }

  const skipToPreviousScene = () => {
    // Safety check: ensure we have valid scene timings
    if (sceneTimings.length === 0 || currentSceneIndex < 0) {
      return
    }

    // If we're more than 2 seconds into current scene, restart it
    const currentSceneTiming = sceneTimings[currentSceneIndex]
    if (!currentSceneTiming) return

    const localTime = currentTime - currentSceneTiming.startTime

    if (localTime > 2 && currentSceneIndex >= 0) {
      // Restart current scene
      onSeek(currentSceneTiming.startTime)
    } else if (currentSceneIndex > 0) {
      // Go to previous scene
      const prevSceneIndex = currentSceneIndex - 1
      const prevSceneTiming = sceneTimings[prevSceneIndex]
      if (!prevSceneTiming) return

      setCurrentSceneIndex(prevSceneIndex)
      setIsVideoLoaded(false)
      onSeek(prevSceneTiming.startTime)
    }
  }

  const toggleMute = () => {
    const newMutedState = !isMuted
    setIsMuted(newMutedState)
    
    // If muted prop is true and audio callback exists, notify parent
    if (muted && onAudioMuteChange) {
      onAudioMuteChange(newMutedState)
    }
  }

  const cyclePlaybackSpeed = () => {
    const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2]
    const currentIndex = speeds.indexOf(playbackSpeed)
    const nextIndex = (currentIndex + 1) % speeds.length
    setPlaybackSpeed(speeds[nextIndex])

    // Show speed indicator feedback
    setShowSpeedIndicator(true)
    if (speedIndicatorTimeoutRef.current) {
      clearTimeout(speedIndicatorTimeoutRef.current)
    }
    speedIndicatorTimeoutRef.current = setTimeout(() => {
      setShowSpeedIndicator(false)
    }, 1500)
  }

  // Handle fullscreen
  const handleFullscreen = () => {
    const video = videoRef.current
    if (!video) return

    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      video.requestFullscreen().catch(err => {
        console.error('Error entering fullscreen:', err)
      })
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle shortcuts if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key.toLowerCase()) {
        case ' ':
        case 'k':
          // Space or K: Play/Pause
          e.preventDefault()
          onPlayPause()
          break
        case 'arrowleft':
          // Left Arrow: Previous scene (or seek back 5s if Shift held)
          e.preventDefault()
          if (e.shiftKey) {
            onSeek(Math.max(0, currentTime - 5))
          } else {
            skipToPreviousScene()
          }
          break
        case 'arrowright':
          // Right Arrow: Next scene (or seek forward 5s if Shift held)
          e.preventDefault()
          if (e.shiftKey) {
            onSeek(Math.min(duration, currentTime + 5))
          } else {
            skipToNextScene()
          }
          break
        case 'arrowup':
          // Up Arrow: Increase volume
          e.preventDefault()
          setVolume(prev => {
            const newVolume = Math.min(1, prev + 0.1)
            if (muted && onAudioVolumeChange) {
              onAudioVolumeChange(newVolume)
            }
            return newVolume
          })
          if (isMuted) {
            setIsMuted(false)
            if (muted && onAudioMuteChange) {
              onAudioMuteChange(false)
            }
          }
          break
        case 'arrowdown':
          // Down Arrow: Decrease volume
          e.preventDefault()
          setVolume(prev => {
            const newVolume = Math.max(0, prev - 0.1)
            if (muted && onAudioVolumeChange) {
              onAudioVolumeChange(newVolume)
            }
            return newVolume
          })
          break
        case 'm':
          // M: Toggle mute
          e.preventDefault()
          toggleMute()
          break
        case 'f':
          // F: Toggle fullscreen
          e.preventDefault()
          handleFullscreen()
          break
        case '>':
        case '.':
          // > or .: Cycle playback speed
          if (e.shiftKey || e.key === '>') {
            e.preventDefault()
            cyclePlaybackSpeed()
          }
          break
        case 'j':
          // J: Seek backward 10s
          e.preventDefault()
          onSeek(Math.max(0, currentTime - 10))
          break
        case 'l':
          // L: Seek forward 10s
          e.preventDefault()
          onSeek(Math.min(duration, currentTime + 10))
          break
        case '0':
        case 'home':
          // 0 or Home: Seek to start
          e.preventDefault()
          onSeek(0)
          setCurrentSceneIndex(0)
          break
        case 'end':
          // End: Seek to end
          e.preventDefault()
          onSeek(duration)
          break
        case '?':
          // ?: Toggle keyboard shortcuts help
          e.preventDefault()
          setShowKeyboardHelp(prev => !prev)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentTime, duration, isMuted, onPlayPause, onSeek, skipToNextScene, skipToPreviousScene, cyclePlaybackSpeed, handleFullscreen, toggleMute, muted, onAudioVolumeChange, onAudioMuteChange])

  return (
    <div className="flex w-full max-w-5xl flex-col gap-4">
      {/* Video Player */}
      <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-gray-700 bg-gray-900">
        {validScenes.length > 0 ? (
          <>
            {/* HTML5 Video Element */}
            <video
              ref={videoRef}
              className="w-full h-full object-contain"
              playsInline
              aria-label="Video preview player"
              onError={() => setVideoError('Failed to load video')}
            />

            {/* Composing Overlay */}
            {isComposing && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 backdrop-blur-sm">
                <div className="text-center space-y-3">
                  <div className="flex justify-center">
                    <svg className="animate-spin h-12 w-12 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <div className="text-white font-medium">Composing Final Video</div>
                  <div className="text-sm text-gray-400">Stitching all scenes together...</div>
                </div>
              </div>
            )}

            {/* Loading Overlay */}
            {!isVideoLoaded && !videoError && !isComposing && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
                <div className="text-center space-y-2">
                  <div className="text-gray-400 animate-pulse">
                    {selectedScene
                      ? `Loading scene ${selectedScene.sequence}...`
                      : showFinalVideo
                      ? 'Loading final video...'
                      : 'Loading video...'}
                  </div>
                  {!showFinalVideo && !selectedScene && (
                    <div className="text-sm text-gray-500">
                      Scene {currentSceneIndex + 1} of {validScenes.length}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Overlay */}
            {videoError && !isComposing && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/90">
                <div className="text-center space-y-2">
                  <div className="text-red-400">{videoError}</div>
                  {!showFinalVideo && validScenes[currentSceneIndex] && (
                    <div className="text-sm text-gray-400">
                      Scene {currentSceneIndex + 1}: {validScenes[currentSceneIndex]?.prompt}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Scene Info Overlay */}
            {isVideoLoaded && !isComposing && (
              <div className="absolute top-4 left-4 right-4 flex items-start justify-between pointer-events-none">
                <div className="bg-gray-900/80 backdrop-blur-sm rounded-lg px-3 py-2 border border-gray-700">
                  {selectedScene ? (
                    <>
                      <div className="text-xs text-gray-400 mb-1">Selected Scene</div>
                      <div className="text-sm text-white font-medium">
                        Scene {selectedScene.sequence}
                      </div>
                    </>
                  ) : showFinalVideo && project.finalOutputUrl ? (
                    <>
                      <div className="text-xs text-gray-400 mb-1">Final Video</div>
                      <div className="text-sm text-white font-medium">Composed</div>
                    </>
                  ) : (
                    <>
                      <div className="text-xs text-gray-400 mb-1">Current Scene</div>
                      <div className="text-sm text-white font-medium">
                        {currentSceneIndex + 1} / {validScenes.length}
                      </div>
                    </>
                  )}
                </div>
                <div className="flex gap-2">
                  <Badge variant="outline" className={getStatusColor(project.status)}>
                    {project.status}
                  </Badge>
                  {selectedScene && (
                    <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                      Scene Preview
                    </Badge>
                  )}
                  {showFinalVideo && project.finalOutputUrl && (
                    <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20">
                      Final Video
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {/* Playback Speed Indicator */}
            {showSpeedIndicator && (
              <div className="absolute bottom-20 left-1/2 -translate-x-1/2 pointer-events-none animate-in fade-in slide-in-from-bottom-4 duration-200">
                <div className="bg-gray-900/95 backdrop-blur-sm rounded-lg px-6 py-4 border border-gray-700 shadow-2xl">
                  <div className="flex items-center gap-3">
                    <Gauge className="h-6 w-6 text-blue-400" />
                    <div>
                      <div className="text-xs text-gray-400 mb-0.5">Playback Speed</div>
                      <div className="text-2xl font-bold text-white font-mono">{playbackSpeed}x</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Placeholder when no videos available */
          <div className="flex h-full items-center justify-center">
            <div className="text-center space-y-4">
              <div className="mb-2 text-gray-400">No Videos Available</div>
              <div className="text-4xl font-mono text-blue-400">
                {formatTime(currentTime)}
              </div>
              <div className="space-y-2">
                <div className="text-sm text-gray-400 max-w-md mx-auto">
                  {project.conceptPrompt}
                </div>
                <div className="flex items-center justify-center gap-2">
                  <Badge variant="outline" className={getStatusColor(project.status)}>
                    {project.status}
                  </Badge>
                  <Badge variant="outline" className="bg-gray-500/10 text-gray-400 border-gray-500/20">
                    {project.scenes.length} scenes
                  </Badge>
                  {project.progress !== undefined && (
                    <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                      {project.progress}% complete
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Playback Controls */}
      <div className="flex flex-col gap-3">
        {/* Progress Bar with Scene Markers */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-gray-400">
            {formatTime(currentTime)}
          </span>
          <div className="flex-1 relative">
            {/* Scene Markers - positioned on the slider track */}
            {duration > 0 && sceneTimings.length > 0 && (
              <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-2 pointer-events-none">
                {sceneTimings.map((timing, index) => {
                  const position = (timing.startTime / duration) * 100
                  const isCurrentScene = index === currentSceneIndex

                  return (
                    <div
                      key={`marker-${index}`}
                      className="absolute top-0 h-full w-0.5 pointer-events-auto cursor-pointer group"
                      style={{ left: `${position}%` }}
                      onClick={() => {
                        onSeek(timing.startTime)
                        setCurrentSceneIndex(index)
                        setIsVideoLoaded(false)
                      }}
                    >
                      {/* Marker Line */}
                      <div
                        className={`w-full h-full transition-all ${
                          isCurrentScene
                            ? 'bg-blue-300'
                            : 'bg-gray-300 group-hover:bg-white'
                        }`}
                      />
                    </div>
                  )
                })}
              </div>
            )}
            <Slider
              value={[currentTime]}
              max={duration}
              step={0.1}
              onValueChange={([value]) => onSeek(value)}
              className="flex-1"
            />
          </div>
          <span className="text-sm font-mono text-gray-400">
            {formatTime(duration)}
          </span>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={skipToPreviousScene}
              disabled={currentSceneIndex === 0 && currentTime <= 2}
              className="text-gray-300 hover:text-white hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              aria-label="Previous scene (Left Arrow)"
              title="Previous scene (Left Arrow)"
            >
              <SkipBack className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              onClick={onPlayPause}
              className="bg-blue-600 hover:bg-blue-700 text-white transition-all"
              aria-label={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
              title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
            >
              {isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={skipToNextScene}
              disabled={currentSceneIndex >= validScenes.length - 1}
              className="text-gray-300 hover:text-white hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              aria-label="Next scene (Right Arrow)"
              title="Next scene (Right Arrow)"
            >
              <SkipForward className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2">
            {/* Playback Speed Control */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-gray-800/50 border border-gray-700 hover:border-gray-600 transition-all">
              <Gauge className="h-3.5 w-3.5 text-gray-400" />
              <button
                onClick={cyclePlaybackSpeed}
                className="text-xs font-mono text-gray-300 hover:text-white transition-colors min-w-[2.5rem] text-center"
                aria-label={`Playback speed: ${playbackSpeed}x (Press > to change)`}
                title="Cycle playback speed (>)"
              >
                {playbackSpeed}x
              </button>
            </div>

            {/* Volume Control */}
            <div className="flex items-center gap-2 group">
              <Button
                size="sm"
                variant="ghost"
                onClick={toggleMute}
                className="text-gray-300 hover:text-white hover:bg-gray-700 transition-all"
                aria-label={isMuted ? 'Unmute (M)' : 'Mute (M)'}
                title={isMuted ? 'Unmute (M)' : 'Mute (M)'}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </Button>
              <div className="w-0 group-hover:w-20 transition-all duration-200 overflow-hidden">
                <Slider
                  value={[isMuted ? 0 : volume * 100]}
                  max={100}
                  step={1}
                  onValueChange={([value]) => {
                    const newVolume = value / 100
                    const wasMuted = isMuted
                    setVolume(newVolume)
                    if (value > 0 && isMuted) {
                      setIsMuted(false)
                    }
                    
                    // If muted prop is true and audio callbacks exist, notify parent
                    if (muted && onAudioVolumeChange) {
                      onAudioVolumeChange(newVolume)
                      if (value > 0 && wasMuted && onAudioMuteChange) {
                        onAudioMuteChange(false)
                      }
                    }
                  }}
                  className="w-20"
                  aria-label="Volume (Arrow Up/Down)"
                />
              </div>
            </div>

            {/* Fullscreen Control */}
            <Button
              size="sm"
              variant="ghost"
              onClick={handleFullscreen}
              className="text-gray-300 hover:text-white hover:bg-gray-700 transition-all"
              aria-label="Toggle fullscreen (F)"
              title="Toggle fullscreen (F)"
            >
              <Maximize className="h-4 w-4" />
            </Button>

            {/* Keyboard Shortcuts Help */}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowKeyboardHelp(!showKeyboardHelp)}
              className="text-gray-300 hover:text-white hover:bg-gray-700 transition-all"
              aria-label="Show keyboard shortcuts (?)"
              title="Show keyboard shortcuts (?)"
            >
              <Keyboard className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Help Overlay */}
      {showKeyboardHelp && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center animate-in fade-in duration-200"
          onClick={() => setShowKeyboardHelp(false)}
        >
          <div
            className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-2xl mx-4 shadow-2xl animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                <Keyboard className="h-5 w-5" />
                Keyboard Shortcuts
              </h3>
              <button
                onClick={() => setShowKeyboardHelp(false)}
                className="text-gray-400 hover:text-white transition-colors"
                aria-label="Close"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-blue-400 mb-2">Playback</h4>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Play/Pause</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">Space</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Play/Pause</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">K</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Previous Scene</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">←</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Next Scene</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">→</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Seek Back 5s</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">Shift + ←</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Seek Forward 5s</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">Shift + →</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Seek Back 10s</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">J</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Seek Forward 10s</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">L</kbd>
                </div>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-blue-400 mb-2">Audio & Display</h4>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Volume Up</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">↑</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Volume Down</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">↓</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Mute/Unmute</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">M</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Fullscreen</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">F</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Playback Speed</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">Shift + &gt;</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Go to Start</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">0</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Go to Start</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">Home</kbd>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Go to End</span>
                  <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono text-xs">End</kbd>
                </div>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-400">
              Press <kbd className="px-1.5 py-0.5 bg-gray-800 border border-gray-600 rounded text-gray-300 font-mono">?</kbd> or click the keyboard icon to toggle this help
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
