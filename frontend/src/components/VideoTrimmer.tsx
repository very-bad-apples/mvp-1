"use client"

import * as React from "react"
import { Slider } from "@/components/ui/slider"
import { Card } from "@/components/ui/card"
import { Scissors } from "lucide-react"

export interface VideoTrimmerProps {
  videoDuration: number
  initialTrimPoints: { in: number; out: number }
  onTrimPointsChange: (trimPoints: { in: number; out: number }) => void
}

export function VideoTrimmer({
  videoDuration,
  initialTrimPoints,
  onTrimPointsChange,
}: VideoTrimmerProps) {
  const [trimPoints, setTrimPoints] = React.useState(initialTrimPoints)

  // Ensure trim points are within valid range
  React.useEffect(() => {
    const validatedIn = Math.max(0, Math.min(initialTrimPoints.in, videoDuration))
    const validatedOut = Math.max(
      validatedIn,
      Math.min(initialTrimPoints.out, videoDuration)
    )

    setTrimPoints({ in: validatedIn, out: validatedOut })
  }, [initialTrimPoints, videoDuration])

  const handleSliderChange = (values: number[]) => {
    if (values.length !== 2) return

    const newTrimPoints = {
      in: Math.min(values[0], values[1]),
      out: Math.max(values[0], values[1]),
    }

    setTrimPoints(newTrimPoints)
    onTrimPointsChange(newTrimPoints)
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(1)
    return mins > 0 ? `${mins}:${secs.padStart(4, "0")}` : `${secs}s`
  }

  const trimDuration = trimPoints.out - trimPoints.in

  return (
    <Card className="bg-gray-900 border-gray-800 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scissors className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-foreground">Video Trimmer</h3>
        </div>
        <div className="text-sm text-muted-foreground">
          Duration: {formatTime(videoDuration)}
        </div>
      </div>

      <div className="space-y-6">
        {/* Timeline Scrubber with Dual Handles */}
        <div className="space-y-3">
          <Slider
            min={0}
            max={videoDuration}
            step={0.1}
            value={[trimPoints.in, trimPoints.out]}
            onValueChange={handleSliderChange}
            className="w-full"
            aria-label="Video trim points"
          />

          {/* Visual Timeline Markers */}
          <div className="relative h-8 bg-gray-800/50 rounded-md overflow-hidden">
            {/* Full timeline background */}
            <div className="absolute inset-0 bg-gray-700/30" />

            {/* Highlighted trim region */}
            <div
              className="absolute h-full bg-blue-500/30 border-l-2 border-r-2 border-blue-500"
              style={{
                left: `${(trimPoints.in / videoDuration) * 100}%`,
                width: `${(trimDuration / videoDuration) * 100}%`,
              }}
            />

            {/* Time markers */}
            <div className="absolute inset-0 flex items-center justify-between px-3 text-xs text-muted-foreground font-mono">
              <span>0:00</span>
              <span>{formatTime(videoDuration)}</span>
            </div>
          </div>
        </div>

        {/* Trim Range Display */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="bg-gray-800/50 rounded-lg p-3 space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              In Point
            </div>
            <div className="text-lg font-mono font-semibold text-blue-400">
              {formatTime(trimPoints.in)}
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-lg p-3 space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Out Point
            </div>
            <div className="text-lg font-mono font-semibold text-blue-400">
              {formatTime(trimPoints.out)}
            </div>
          </div>

          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 space-y-1">
            <div className="text-xs text-blue-300/70 uppercase tracking-wide">
              Trim Duration
            </div>
            <div className="text-lg font-mono font-semibold text-blue-400">
              {formatTime(trimDuration)}
            </div>
          </div>
        </div>

        {/* Additional Info */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-gray-800">
          <span>
            Range: {formatTime(trimPoints.in)} - {formatTime(trimPoints.out)}
          </span>
          <span>
            {((trimDuration / videoDuration) * 100).toFixed(1)}% of video
          </span>
        </div>
      </div>
    </Card>
  )
}
