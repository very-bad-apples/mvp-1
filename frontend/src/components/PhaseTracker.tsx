"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { FileText, Image, Video, Mic, Package, Check, Loader2, AlertCircle } from "lucide-react"

// Type definitions
export type PhaseStatus = "pending" | "in-progress" | "completed" | "error"

export interface PhaseData {
  id: string
  name: string
  status: PhaseStatus
  progress: number
  estimatedTime?: string
}

export interface PhaseTrackerProps {
  currentPhase: string
  overallProgress: number
  phases?: PhaseData[]
  className?: string
}

// Default phases configuration
const DEFAULT_PHASES: PhaseData[] = [
  {
    id: "scenes",
    name: "Scenes",
    status: "pending",
    progress: 0,
    estimatedTime: "2-3 min"
  },
  {
    id: "images",
    name: "Images",
    status: "pending",
    progress: 0,
    estimatedTime: "3-5 min"
  },
  {
    id: "videos",
    name: "Videos",
    status: "pending",
    progress: 0,
    estimatedTime: "5-8 min"
  },
  {
    id: "lipsync",
    name: "Lip-sync",
    status: "pending",
    progress: 0,
    estimatedTime: "2-4 min"
  },
  {
    id: "compose",
    name: "Compose",
    status: "pending",
    progress: 0,
    estimatedTime: "1-2 min"
  }
]

// Icon mapping for each phase
const PHASE_ICONS = {
  scenes: FileText,
  images: Image,
  videos: Video,
  lipsync: Mic,
  compose: Package
}

// Status badge configuration
const STATUS_BADGE_CONFIG = {
  pending: {
    variant: "outline" as const,
    label: "Pending",
    className: "bg-gray-800 border-gray-700 text-gray-400"
  },
  "in-progress": {
    variant: "default" as const,
    label: "In Progress",
    className: "bg-blue-600 border-blue-500 text-white animate-pulse"
  },
  completed: {
    variant: "default" as const,
    label: "Completed",
    className: "bg-green-600 border-green-500 text-white"
  },
  error: {
    variant: "destructive" as const,
    label: "Error",
    className: "bg-red-600 border-red-500 text-white"
  }
}

// Status icon component
function StatusIcon({ status }: { status: PhaseStatus }) {
  switch (status) {
    case "completed":
      return <Check className="w-4 h-4 text-green-500" />
    case "in-progress":
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
    case "error":
      return <AlertCircle className="w-4 h-4 text-red-500" />
    default:
      return null
  }
}

// Phase step component
interface PhaseStepProps {
  phase: PhaseData
  index: number
  isLast: boolean
  isVertical: boolean
}

function PhaseStep({ phase, index, isLast, isVertical }: PhaseStepProps) {
  const Icon = PHASE_ICONS[phase.id as keyof typeof PHASE_ICONS] || FileText
  const statusConfig = STATUS_BADGE_CONFIG[phase.status]

  return (
    <div
      className={cn(
        "flex gap-4",
        isVertical ? "flex-row items-start" : "flex-col items-center"
      )}
      role="listitem"
      aria-label={`Phase ${index + 1}: ${phase.name}`}
    >
      {/* Phase icon and connector */}
      <div className={cn("flex items-center", isVertical ? "flex-col" : "flex-row")}>
        {/* Icon container */}
        <div
          className={cn(
            "relative z-10 flex items-center justify-center rounded-full border-2 transition-all duration-300",
            phase.status === "completed" && "bg-green-600 border-green-500",
            phase.status === "in-progress" && "bg-blue-600 border-blue-500 ring-4 ring-blue-500/20",
            phase.status === "error" && "bg-red-600 border-red-500",
            phase.status === "pending" && "bg-gray-800 border-gray-700",
            isVertical ? "w-12 h-12" : "w-14 h-14"
          )}
          aria-hidden="true"
        >
          <Icon className={cn("transition-colors", isVertical ? "w-5 h-5" : "w-6 h-6")} />

          {/* Status indicator overlay */}
          {phase.status !== "pending" && (
            <div className="absolute -top-1 -right-1 bg-gray-900 rounded-full p-0.5">
              <StatusIcon status={phase.status} />
            </div>
          )}
        </div>

        {/* Connector line */}
        {!isLast && (
          <div
            className={cn(
              "transition-colors duration-300",
              isVertical
                ? "w-0.5 h-16 my-2"
                : "h-0.5 w-full min-w-[60px] mx-2",
              phase.status === "completed" ? "bg-green-500" : "bg-gray-700"
            )}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Phase details */}
      <div
        className={cn(
          "flex-1 space-y-2",
          isVertical ? "pb-4" : "text-center min-w-[120px]"
        )}
      >
        {/* Phase name */}
        <h3
          className={cn(
            "font-semibold transition-colors",
            phase.status === "in-progress" && "text-blue-400",
            phase.status === "completed" && "text-green-400",
            phase.status === "error" && "text-red-400",
            phase.status === "pending" && "text-gray-400",
            isVertical ? "text-base" : "text-sm"
          )}
        >
          {phase.name}
        </h3>

        {/* Status badge */}
        <Badge
          variant={statusConfig.variant}
          className={cn(statusConfig.className, "text-xs")}
        >
          {statusConfig.label}
        </Badge>

        {/* Progress bar (shown for in-progress and completed phases) */}
        {(phase.status === "in-progress" || phase.status === "completed") && (
          <div className="space-y-1">
            <Progress
              value={phase.progress}
              className="h-1.5"
              aria-label={`${phase.name} progress: ${phase.progress}%`}
            />
            <p className="text-xs text-gray-500">{phase.progress}%</p>
          </div>
        )}

        {/* Estimated time */}
        {phase.estimatedTime && phase.status === "pending" && (
          <p className="text-xs text-gray-500">
            Est: {phase.estimatedTime}
          </p>
        )}
      </div>
    </div>
  )
}

// Main PhaseTracker component
export function PhaseTracker({
  currentPhase,
  overallProgress,
  phases = DEFAULT_PHASES,
  className
}: PhaseTrackerProps) {
  // Update phases based on currentPhase prop
  const updatedPhases = React.useMemo(() => {
    return phases.map(phase => {
      if (phase.id === currentPhase) {
        return { ...phase, status: "in-progress" as PhaseStatus }
      }
      const currentIndex = phases.findIndex(p => p.id === currentPhase)
      const phaseIndex = phases.findIndex(p => p.id === phase.id)
      if (phaseIndex < currentIndex) {
        return { ...phase, status: "completed" as PhaseStatus, progress: 100 }
      }
      return phase
    })
  }, [phases, currentPhase])

  return (
    <div
      className={cn(
        "bg-gray-900 border border-gray-800 rounded-lg p-6 shadow-xl",
        className
      )}
      role="region"
      aria-label="Video generation progress tracker"
    >
      {/* Header */}
      <div className="mb-6 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Generation Pipeline</h2>
          <Badge className="bg-blue-600 border-blue-500 text-white">
            {overallProgress}% Complete
          </Badge>
        </div>
        <Progress value={overallProgress} className="h-2" aria-label={`Overall progress: ${overallProgress}%`} />
      </div>

      {/* Phase steps - responsive layout */}
      <div
        className={cn(
          "flex",
          // Vertical on mobile (< md), horizontal on desktop (>= md)
          "flex-col md:flex-row md:items-start md:justify-between"
        )}
        role="list"
        aria-label="Generation phases"
      >
        {updatedPhases.map((phase, index) => (
          <PhaseStep
            key={phase.id}
            phase={phase}
            index={index}
            isLast={index === updatedPhases.length - 1}
            isVertical={false} // Will be vertical on mobile via CSS
            // Using CSS classes for responsive behavior instead of JS
          />
        ))}
      </div>

      {/* Keyboard navigation hint */}
      <div className="sr-only" role="status" aria-live="polite">
        Currently on phase: {currentPhase}. Overall progress: {overallProgress}%
      </div>
    </div>
  )
}
