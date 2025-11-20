'use client'

import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Play, Pause, SkipBack, SkipForward, Volume2, Maximize } from 'lucide-react'
import { Project } from '@/types/project'
import { Badge } from '@/components/ui/badge'

interface VideoPreviewProps {
  jobId: string
  project: Project
  currentTime: number
  duration: number
  isPlaying: boolean
  onPlayPause: () => void
  onSeek: (time: number) => void
}

export function VideoPreview({
  jobId,
  project,
  currentTime,
  duration,
  isPlaying,
  onPlayPause,
  onSeek,
}: VideoPreviewProps) {
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

  return (
    <div className="flex w-full max-w-5xl flex-col gap-4">
      {/* Video Player */}
      <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-gray-700 bg-gray-900">
        {/* Placeholder video preview - will be replaced with actual canvas */}
        <div className="flex h-full items-center justify-center">
          <div className="text-center space-y-4">
            <div className="mb-2 text-gray-400">Video Preview</div>
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
      </div>

      {/* Playback Controls */}
      <div className="flex flex-col gap-3">
        {/* Progress Bar */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-gray-400">
            {formatTime(currentTime)}
          </span>
          <Slider
            value={[currentTime]}
            max={duration}
            step={0.1}
            onValueChange={([value]) => onSeek(value)}
            className="flex-1"
          />
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
              onClick={() => onSeek(Math.max(0, currentTime - 5))}
              className="text-gray-300 hover:text-white hover:bg-gray-700"
            >
              <SkipBack className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              onClick={onPlayPause}
              className="bg-blue-600 hover:bg-blue-700 text-white"
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
              onClick={() => onSeek(Math.min(duration, currentTime + 5))}
              className="text-gray-300 hover:text-white hover:bg-gray-700"
            >
              <SkipForward className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-300 hover:text-white hover:bg-gray-700"
            >
              <Volume2 className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-300 hover:text-white hover:bg-gray-700"
            >
              <Maximize className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
