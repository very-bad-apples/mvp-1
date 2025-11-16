'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { ZoomIn, ZoomOut, RefreshCw, Edit3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

interface TimelineProps {
  jobId: string
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

export function Timeline({
  jobId,
  currentTime,
  duration,
  zoom,
  onSeek,
  onZoomChange,
}: TimelineProps) {
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null)
  const [segments, setSegments] = useState<VideoSegment[]>(mockSegments)
  const [isRegenerating, setIsRegenerating] = useState<string | null>(null)
  const [isEditPromptOpen, setIsEditPromptOpen] = useState(false)
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null)
  const [editPromptValue, setEditPromptValue] = useState('')
  const timelineRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const { toast } = useToast()

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
    setIsRegenerating(segmentId)
    toast({
      title: "Regenerating Scene",
      description: "Creating new version of this scene...",
    })

    // Simulate API call to regenerate scene
    await new Promise(resolve => setTimeout(resolve, 3000))

    // Update segment with new data (in production, this would come from API)
    setSegments(prev => prev.map(seg =>
      seg.id === segmentId
        ? { ...seg, thumbnail: seg.thumbnail + '&v=' + Date.now() }
        : seg
    ))

    setIsRegenerating(null)
    toast({
      title: "Scene Regenerated",
      description: "New version has been created successfully!",
    })
  }

  const handleOpenEditPrompt = (segmentId: string) => {
    const segment = segments.find(s => s.id === segmentId)
    if (segment) {
      setEditingSegmentId(segmentId)
      setEditPromptValue(segment.prompt)
      setIsEditPromptOpen(true)
    }
  }

  const handleSavePrompt = () => {
    if (editingSegmentId) {
      setSegments(prev => prev.map(seg =>
        seg.id === editingSegmentId
          ? { ...seg, prompt: editPromptValue }
          : seg
      ))
      toast({
        title: "Prompt Updated",
        description: "Scene prompt has been updated successfully!",
      })
    }
    setIsEditPromptOpen(false)
    setEditingSegmentId(null)
    setEditPromptValue('')
  }

  const handleCancelEdit = () => {
    setIsEditPromptOpen(false)
    setEditingSegmentId(null)
    setEditPromptValue('')
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

                    {/* Hover overlay with info */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/75 opacity-0 transition-opacity group-hover:opacity-100 p-2">
                      <span className="text-sm font-medium text-white mb-1">
                        Scene {segment.sceneNumber}
                      </span>
                      <span className="text-xs text-gray-300 mb-2">
                        {formatTime(segment.duration)}
                      </span>
                      <div className="flex flex-col gap-1.5 w-full px-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 text-xs border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white w-full"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleOpenEditPrompt(segment.id)
                          }}
                        >
                          <Edit3 className="mr-1.5 h-3.5 w-3.5" />
                          Edit Prompt
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 text-xs border-green-500 text-green-400 hover:bg-green-500 hover:text-white w-full"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRegenerateSegment(segment.id)
                          }}
                          disabled={isRegenerating === segment.id}
                        >
                          {isRegenerating === segment.id ? (
                            <>
                              <RefreshCw className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                              Regenerating...
                            </>
                          ) : (
                            <>
                              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                              Regenerate
                            </>
                          )}
                        </Button>
                      </div>
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
                onClick={() => selectedSegmentId && handleOpenEditPrompt(selectedSegmentId)}
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

      {/* Edit Prompt Modal */}
      <Dialog open={isEditPromptOpen} onOpenChange={setIsEditPromptOpen}>
        <DialogContent className="sm:max-w-[525px] bg-gray-800 border-gray-700">
          <DialogHeader>
            <DialogTitle className="text-white">
              Edit Scene {segments.find(s => s.id === editingSegmentId)?.sceneNumber} Prompt
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              Modify the text prompt for this scene. This will be used when regenerating the scene.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="prompt" className="text-white">
                Scene Prompt
              </Label>
              <Textarea
                id="prompt"
                value={editPromptValue}
                onChange={(e) => setEditPromptValue(e.target.value)}
                placeholder="Enter scene description..."
                className="bg-gray-900 border-gray-600 text-white placeholder:text-gray-500 min-h-[120px] resize-none"
                rows={5}
              />
              <p className="text-xs text-gray-400">
                Describe what you want to see in this scene. Be specific about the visuals, actions, and atmosphere.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleCancelEdit}
              className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-white"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSavePrompt}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Save Prompt
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
