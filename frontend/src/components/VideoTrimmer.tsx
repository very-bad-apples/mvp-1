"use client"

import * as React from "react"
import { Card } from "@/components/ui/card"
import { Scissors } from "lucide-react"
import { formatPreciseTime } from '@/lib/utils/time'

export interface VideoTrimmerProps {
  videoDuration: number
  initialTrimPoints: { in: number; out: number }
  onTrimPointsChange: (trimPoints: { in: number; out: number }) => void
  videoUrl?: string
}

export function VideoTrimmer({
  videoDuration,
  initialTrimPoints,
  onTrimPointsChange,
  videoUrl,
}: VideoTrimmerProps) {
  const [trimPoints, setTrimPoints] = React.useState(initialTrimPoints)
  const [isDragging, setIsDragging] = React.useState<'in' | 'out' | null>(null)
  const timelineRef = React.useRef<HTMLDivElement>(null)

  // Ensure trim points are within valid range
  React.useEffect(() => {
    const validatedIn = Math.max(0, Math.min(initialTrimPoints.in, videoDuration))
    const validatedOut = Math.max(
      validatedIn,
      Math.min(initialTrimPoints.out, videoDuration)
    )

    setTrimPoints({ in: validatedIn, out: validatedOut })
  }, [initialTrimPoints, videoDuration])

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current || isDragging) return

    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width
    const time = percentage * videoDuration

    // Snap to closest trim point
    const distanceToIn = Math.abs(time - trimPoints.in)
    const distanceToOut = Math.abs(time - trimPoints.out)

    if (distanceToIn < distanceToOut) {
      const newTrimPoints = { ...trimPoints, in: Math.max(0, Math.min(time, trimPoints.out - 0.1)) }
      setTrimPoints(newTrimPoints)
      onTrimPointsChange(newTrimPoints)
    } else {
      const newTrimPoints = { ...trimPoints, out: Math.min(videoDuration, Math.max(time, trimPoints.in + 0.1)) }
      setTrimPoints(newTrimPoints)
      onTrimPointsChange(newTrimPoints)
    }
  }

  const handleMouseDown = (point: 'in' | 'out') => (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsDragging(point)
  }

  React.useEffect(() => {
    if (!isDragging || !timelineRef.current || typeof window === 'undefined') {
      return undefined
    }

    const handleMouseMove = (e: MouseEvent) => {
      if (!timelineRef.current) return

      const rect = timelineRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const percentage = Math.max(0, Math.min(1, x / rect.width))
      const time = percentage * videoDuration

      if (isDragging === 'in') {
        const newIn = Math.max(0, Math.min(time, trimPoints.out - 0.1))
        const newTrimPoints = { ...trimPoints, in: newIn }
        setTrimPoints(newTrimPoints)
        onTrimPointsChange(newTrimPoints)
      } else if (isDragging === 'out') {
        const newOut = Math.min(videoDuration, Math.max(time, trimPoints.in + 0.1))
        const newTrimPoints = { ...trimPoints, out: newOut }
        setTrimPoints(newTrimPoints)
        onTrimPointsChange(newTrimPoints)
      }
    }

    const handleMouseUp = () => {
      setIsDragging(null)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, trimPoints, videoDuration, onTrimPointsChange])

  const trimDuration = trimPoints.out - trimPoints.in
  const inPercentage = (trimPoints.in / videoDuration) * 100
  const outPercentage = (trimPoints.out / videoDuration) * 100

  return (
    <Card className="bg-gray-900 border-gray-800 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scissors className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-foreground">Video Trimmer</h3>
        </div>
        <div className="text-sm text-muted-foreground">
          Duration: {formatPreciseTime(videoDuration)}
        </div>
      </div>

      <div className="space-y-6">
        {/* Timeline with Video Preview */}
        <div
          ref={timelineRef}
          onClick={handleTimelineClick}
          className="relative w-full h-24 bg-gray-800/50 rounded-lg overflow-hidden cursor-pointer select-none border-2 border-cyan-500/50"
          style={{
            backgroundImage: videoUrl ? 'linear-gradient(to right, rgba(0,0,0,0.3), rgba(0,0,0,0.3))' : undefined,
          }}
        >
          {/* Trimmed overlay - before in point */}
          <div
            className="absolute top-0 bottom-0 left-0 bg-black/70 pointer-events-none z-10"
            style={{ width: `${inPercentage}%` }}
          />

          {/* Trimmed overlay - after out point */}
          <div
            className="absolute top-0 bottom-0 right-0 bg-black/70 pointer-events-none z-10"
            style={{ width: `${100 - outPercentage}%` }}
          />

          {/* In point marker with thick border */}
          <div
            className="absolute top-0 bottom-0 w-1 bg-cyan-500 cursor-ew-resize z-20 hover:w-2 transition-all"
            style={{ left: `${inPercentage}%` }}
            onMouseDown={handleMouseDown('in')}
          >
            {/* Thick border indicator */}
            <div className="absolute top-0 bottom-0 -left-1 w-3 bg-cyan-500/80 rounded-l" />
            {/* Time label */}
            <div className="absolute -top-6 left-0 -translate-x-1/2 bg-cyan-500 text-white text-xs px-2 py-1 rounded whitespace-nowrap font-mono">
              {formatPreciseTime(trimPoints.in)}
            </div>
          </div>

          {/* Out point marker with thick border */}
          <div
            className="absolute top-0 bottom-0 w-1 bg-cyan-500 cursor-ew-resize z-20 hover:w-2 transition-all"
            style={{ left: `${outPercentage}%` }}
            onMouseDown={handleMouseDown('out')}
          >
            {/* Thick border indicator */}
            <div className="absolute top-0 bottom-0 -right-1 w-3 bg-cyan-500/80 rounded-r" />
            {/* Time label */}
            <div className="absolute -top-6 left-0 -translate-x-1/2 bg-cyan-500 text-white text-xs px-2 py-1 rounded whitespace-nowrap font-mono">
              {formatPreciseTime(trimPoints.out)}
            </div>
          </div>

          {/* Filename/duration display */}
          <div className="absolute top-2 left-2 text-white text-xs font-mono bg-black/50 px-2 py-1 rounded z-5">
            {formatPreciseTime(videoDuration)}
          </div>
        </div>

        {/* Trim Range Display */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="bg-gray-800/50 rounded-lg p-3 space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              In Point
            </div>
            <div className="text-lg font-mono font-semibold text-cyan-400">
              {formatPreciseTime(trimPoints.in)}
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-lg p-3 space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Out Point
            </div>
            <div className="text-lg font-mono font-semibold text-cyan-400">
              {formatPreciseTime(trimPoints.out)}
            </div>
          </div>

          <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3 space-y-1">
            <div className="text-xs text-cyan-300/70 uppercase tracking-wide">
              Trim Duration
            </div>
            <div className="text-lg font-mono font-semibold text-cyan-400">
              {formatPreciseTime(trimDuration)}
            </div>
          </div>
        </div>

        {/* Additional Info */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-gray-800">
          <span>
            Range: {formatPreciseTime(trimPoints.in)} - {formatPreciseTime(trimPoints.out)}
          </span>
          <span>
            {((trimDuration / videoDuration) * 100).toFixed(1)}% of video
          </span>
        </div>
      </div>
    </Card>
  )
}
