'use client'

import { useState, useRef, useEffect } from 'react'

interface TimelinePromptTooltipProps {
  sceneNumber: number
  prompt: string
  children: React.ReactNode
  disabled?: boolean
}

export function TimelinePromptTooltip({
  sceneNumber,
  prompt,
  children,
  disabled = false,
}: TimelinePromptTooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const triggerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect()
      const tooltipRect = tooltipRef.current.getBoundingClientRect()

      // Position above the trigger element
      let top = triggerRect.top - tooltipRect.height - 12
      let left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2

      // Ensure tooltip stays within viewport bounds
      const padding = 16
      if (left < padding) {
        left = padding
      } else if (left + tooltipRect.width > window.innerWidth - padding) {
        left = window.innerWidth - tooltipRect.width - padding
      }

      // If tooltip would go off top of screen, show below instead
      if (top < padding) {
        top = triggerRect.bottom + 12
      }

      setPosition({ top, left })
    }
  }, [isVisible])

  const handleMouseEnter = () => {
    if (disabled) return

    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Show tooltip after brief delay
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true)
    }, 300)
  }

  const handleMouseLeave = () => {
    // Clear timeout if user leaves before delay completes
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    setIsVisible(false)
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="relative"
      >
        {children}
      </div>

      {isVisible && (
        <div
          ref={tooltipRef}
          className="fixed z-50 pointer-events-none animate-in fade-in-0 zoom-in-95 duration-200"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
          }}
        >
          <div className="relative">
            {/* Tooltip content */}
            <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl px-4 py-3 max-w-md">
              {/* Scene number badge */}
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-semibold bg-blue-500/20 text-blue-400 rounded border border-blue-500/30">
                  Scene {sceneNumber}
                </span>
              </div>

              {/* Prompt text */}
              <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                {prompt}
              </p>
            </div>

            {/* Arrow pointer */}
            <div className="absolute left-1/2 -translate-x-1/2 -bottom-2">
              <div className="w-0 h-0 border-l-8 border-l-transparent border-r-8 border-r-transparent border-t-8 border-t-gray-700" />
              <div className="absolute w-0 h-0 border-l-[7px] border-l-transparent border-r-[7px] border-r-transparent border-t-[7px] border-t-gray-900 left-1/2 -translate-x-1/2 -top-[7px]" />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
