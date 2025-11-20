'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { ZoomIn, ZoomOut, RefreshCw, Edit3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { TimelineItemSheet, TimelineItem } from './TimelineItemSheet'
import { Project } from '@/types/project'

interface TimelineProps {
  jobId: string
  project: Project
  currentTime: number
  duration: number
  zoom: number
  onSeek: (time: number) => void
  onZoomChange: (zoom: number) => void
}

interface VideoSegment {
  id: string
  sceneNumber: number
  startTime: number
  duration: number
  url: string
  thumbnail: string
  color: string
  prompt: string
}

// Mock video segments - in production, this would come from the API
// Segments are continuous and connected - startTime is calculated cumulatively
const generateMockSegments = (): VideoSegment[] => {
  const segmentData = [
    {
      id: '1',
      sceneNumber: 1,
      duration: 36,
      url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
      thumbnail: 'https://placehold.co/120x80/1e40af/ffffff?text=Scene+1',
      color: 'from-blue-500/20 to-blue-600/20',
      prompt: 'A serene landscape with rolling hills and blue skies',
    },
    {
      id: '2',
      sceneNumber: 2,
      duration: 36,
      url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
      thumbnail: 'https://placehold.co/120x80/7c3aed/ffffff?text=Scene+2',
      color: 'from-purple-500/20 to-purple-600/20',
      prompt: 'A character walking through a vibrant city street',
    },
    {
      id: '3',
      sceneNumber: 3,
      duration: 36,
      url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
      thumbnail: 'https://placehold.co/120x80/0891b2/ffffff?text=Scene+3',
      color: 'from-cyan-500/20 to-cyan-600/20',
      prompt: 'Product showcase with dynamic camera movements',
    },
    {
      id: '4',
      sceneNumber: 4,
      duration: 36,
      url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
      thumbnail: 'https://placehold.co/120x80/059669/ffffff?text=Scene+4',
      color: 'from-green-500/20 to-green-600/20',
      prompt: 'Close-up shots highlighting product features',
    },
    {
      id: '5',
      sceneNumber: 5,
      duration: 36,
      url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
      thumbnail: 'https://placehold.co/120x80/dc2626/ffffff?text=Scene+5',
      color: 'from-red-500/20 to-red-600/20',
      prompt: 'Ending scene with call-to-action and branding',
    },
  ]

  // Calculate cumulative start times for continuous video
  let cumulativeTime = 0
  return segmentData.map(seg => {
    const segment = {
      ...seg,
      startTime: cumulativeTime
    }
    cumulativeTime += seg.duration
    return segment
  })
}

const mockSegments: VideoSegment[] = generateMockSegments()

// Color palette for scenes
const sceneColors = [
  'from-blue-500/20 to-blue-600/20',
  'from-purple-500/20 to-purple-600/20',
  'from-cyan-500/20 to-cyan-600/20',
  'from-green-500/20 to-green-600/20',
  'from-red-500/20 to-red-600/20',
  'from-orange-500/20 to-orange-600/20',
  'from-pink-500/20 to-pink-600/20',
  'from-yellow-500/20 to-yellow-600/20',
]

export function Timeline({
  jobId,
  project,
  currentTime,
  duration,
  zoom,
  onSeek,
  onZoomChange,
}: TimelineProps) {
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null)
  const [isRegenerating, setIsRegenerating] = useState<string | null>(null)
  const [isSheetOpen, setIsSheetOpen] = useState(false)
  const timelineRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const { toast } = useToast()

  // Convert project scenes to VideoSegments
  const segments = useMemo(() => {
    if (!project.scenes || project.scenes.length === 0) {
      return mockSegments // Fallback to mock data if no scenes
    }

    let cumulativeTime = 0
    return project.scenes
      .sort((a, b) => a.sequence - b.sequence) // Ensure scenes are in order
      .map((scene, index) => {
        const segment: VideoSegment = {
          id: `scene-${scene.sequence}`,
          sceneNumber: scene.sequence,
          startTime: cumulativeTime,
          duration: scene.duration || 0,
          url: scene.lipSyncedVideoClipUrl || scene.videoClipUrl || '',
          thumbnail: scene.videoClipUrl || `https://placehold.co/120x80/666/fff?text=Scene+${scene.sequence}`,
          color: sceneColors[index % sceneColors.length],
          prompt: scene.prompt,
        }
        cumulativeTime += scene.duration || 0
        return segment
      })
  }, [project.scenes])

  const pixelsPerSecond = 10 * zoom
  const timelineWidth = duration * pixelsPerSecond

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return
    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left + timelineRef.current.scrollLeft
    const time = Math.max(0, Math.min(duration, x / pixelsPerSecond))
    onSeek(time)
  }

  const handlePlayheadDrag = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return
    handleTimelineClick(e)
  }

  const handleRegenerateSegment = async (segmentId: string) => {
    // TODO: Implement API call to regenerate scene
    toast({
      title: "Coming Soon",
      description: "Scene regeneration will be available soon!",
    })
  }

  const handleOpenSheet = (segmentId: string) => {
    setSelectedSegmentId(segmentId)
    setIsSheetOpen(true)
  }

  const handleCloseSheet = () => {
    setIsSheetOpen(false)
    // Keep the segment selected briefly so the sheet can animate out
    setTimeout(() => setSelectedSegmentId(null), 300)
  }

  const handleSaveSegment = (segmentId: string, updates: Partial<TimelineItem>) => {
    // TODO: Implement API call to update scene
    toast({
      title: "Coming Soon",
      description: "Scene editing will be available soon!",
    })
  }

  const handleDeleteSegment = (segmentId: string) => {
    // TODO: Implement API call to delete scene
    toast({
      title: "Coming Soon",
      description: "Scene deletion will be available soon!",
    })
  }

  useEffect(() => {
    const handleMouseUp = () => setIsDragging(false)
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && timelineRef.current) {
        const rect = timelineRef.current.getBoundingClientRect()
        const x = e.clientX - rect.left + timelineRef.current.scrollLeft
        const time = Math.max(0, Math.min(duration, x / pixelsPerSecond))
        onSeek(time)
      }
    }

    window.addEventListener('mouseup', handleMouseUp)
    window.addEventListener('mousemove', handleMouseMove)
    return () => {
      window.removeEventListener('mouseup', handleMouseUp)
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [isDragging, duration, pixelsPerSecond, onSeek])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const timeMarkers = []
  const markerInterval = 10 // Every 10 seconds
  for (let i = 0; i <= duration; i += markerInterval) {
    timeMarkers.push(i)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Timeline Header */}
      <div className="flex items-center justify-between border-b border-gray-700 bg-gray-800/50 px-4 py-2">
        <div className="text-sm font-medium text-white">Timeline</div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onZoomChange(Math.max(0.5, zoom - 0.5))}
            className="text-gray-300 hover:text-white hover:bg-gray-700"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm font-mono text-gray-400">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onZoomChange(Math.min(5, zoom + 0.5))}
            className="text-gray-300 hover:text-white hover:bg-gray-700"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Timeline Content */}
      <div className="relative flex-1 overflow-x-auto overflow-y-hidden">
        <div
          ref={timelineRef}
          className="relative h-full cursor-pointer"
          style={{ width: `${timelineWidth}px` }}
          onClick={handleTimelineClick}
          onMouseMove={handlePlayheadDrag}
        >
          {/* Time Markers */}
          <div className="sticky top-0 z-10 flex h-10 items-end border-b border-gray-700 bg-gray-800/50">
            {timeMarkers.map((time) => (
              <div
                key={time}
                className="absolute flex flex-col items-center"
                style={{ left: `${time * pixelsPerSecond}px` }}
              >
                <span className="text-xs font-mono text-gray-400">
                  {formatTime(time)}
                </span>
                <div className="h-2 w-px bg-gray-600" />
              </div>
            ))}
          </div>

          {/* Video Track - Continuous Segments */}
          <div className="p-4">
            {/* Single continuous video track - Increased height to h-32 for better button visibility */}
            <div className="relative h-32 rounded-md border border-gray-700 bg-gray-800/30">
              <div className="absolute left-0 top-0 flex h-full">
                {segments.map((segment, index) => (
                  <div
                    key={segment.id}
                    className={cn(
                      'group relative h-full cursor-pointer overflow-hidden transition-all',
                      selectedSegmentId === segment.id
                        ? 'border-t-4 border-b-4 border-blue-500 shadow-lg shadow-blue-500/20 z-10'
                        : 'border-r border-gray-600 hover:border-r-2 hover:border-blue-400'
                    )}
                    style={{
                      width: `${segment.duration * pixelsPerSecond}px`,
                    }}
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedSegmentId(segment.id)
                    }}
                  >
                    <div
                      className={cn(
                        'absolute inset-0 bg-gradient-to-r',
                        segment.color
                      )}
                    />
                    <img
                      src={segment.thumbnail}
                      alt={`Scene ${segment.sceneNumber}`}
                      className="h-full w-full object-cover opacity-60"
                    />

                    {/* Hover overlay with prompt */}
                    <div className="absolute inset-0 flex flex-col items-start justify-center bg-black/85 backdrop-blur-sm opacity-0 transition-opacity group-hover:opacity-100 p-3 overflow-hidden">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-semibold bg-blue-500/20 text-blue-400 rounded border border-blue-500/30">
                          Scene {segment.sceneNumber}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatTime(segment.duration)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-200 leading-relaxed line-clamp-4">
                        {segment.prompt}
                      </p>
                      <p className="text-xs text-gray-400 mt-2 italic">
                        Click to edit
                      </p>
                    </div>

                    {/* Scene number label */}
                    <div className="absolute top-1 left-1 bg-black/70 px-1.5 py-0.5 rounded text-xs text-white">
                      {segment.sceneNumber}
                    </div>

                    {/* Segment separator line (except for last segment) */}
                    {index < segments.length - 1 && (
                      <div className="absolute top-0 right-0 h-full w-px bg-gray-500/50" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Playhead */}
          <div
            className="absolute top-0 z-20 flex h-full flex-col items-center pointer-events-none"
            style={{ left: `${currentTime * pixelsPerSecond}px` }}
          >
            <div
              className="cursor-ew-resize rounded-sm bg-blue-500 px-1 py-0.5 pointer-events-auto"
              onMouseDown={(e) => {
                e.stopPropagation()
                setIsDragging(true)
              }}
            >
              <div className="h-3 w-3 rounded-sm bg-white" />
            </div>
            <div className="h-full w-0.5 bg-blue-500 shadow-lg shadow-blue-500/50" />
          </div>
        </div>
      </div>

      {/* Selected Segment Info */}
      {selectedSegmentId && (
        <div className="border-t border-gray-700 bg-gray-800/50 px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-white">
                Scene {segments.find(s => s.id === selectedSegmentId)?.sceneNumber} Selected
              </div>
              <div className="text-xs text-gray-400">
                Duration: {formatTime(segments.find(s => s.id === selectedSegmentId)?.duration || 0)}
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => selectedSegmentId && handleOpenSheet(selectedSegmentId)}
                className="border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white"
              >
                <Edit3 className="mr-2 h-4 w-4" />
                Edit Prompt
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => selectedSegmentId && handleRegenerateSegment(selectedSegmentId)}
                disabled={isRegenerating === selectedSegmentId}
                className="border-green-500 text-green-400 hover:bg-green-500 hover:text-white"
              >
                {isRegenerating === selectedSegmentId ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Regenerating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Regenerate
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Timeline Item Sheet */}
      <TimelineItemSheet
        item={
          selectedSegmentId
            ? {
                ...segments.find(s => s.id === selectedSegmentId)!,
                type: 'scene' as const,
              }
            : null
        }
        isOpen={isSheetOpen}
        onClose={handleCloseSheet}
        onSave={handleSaveSegment}
        onRegenerate={handleRegenerateSegment}
        onDelete={handleDeleteSegment}
        isRegenerating={isRegenerating === selectedSegmentId}
      />
    </div>
  )
}
