'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { RefreshCw, Trash2, Save, X, Clock, Film } from 'lucide-react'
import { cn } from '@/lib/utils'

// Generic timeline item type - can be extended for different item types
export interface TimelineItem {
  id: string
  type: 'scene' | 'transition' | 'audio' // Extensible for future item types
  sceneNumber?: number
  startTime: number
  duration: number
  thumbnail?: string
  prompt?: string
  [key: string]: unknown // Allow additional properties
}

interface TimelineItemSheetProps {
  item: TimelineItem | null
  isOpen: boolean
  onClose: () => void
  onSave: (itemId: string, updates: Partial<TimelineItem>) => void
  onRegenerate?: (itemId: string) => void
  onDelete?: (itemId: string) => void
  isRegenerating?: boolean
}

export function TimelineItemSheet({
  item,
  isOpen,
  onClose,
  onSave,
  onRegenerate,
  onDelete,
  isRegenerating = false,
}: TimelineItemSheetProps) {
  const [promptValue, setPromptValue] = useState('')
  const [hasChanges, setHasChanges] = useState(false)

  // Sync prompt value when item changes
  useEffect(() => {
    if (item?.prompt) {
      setPromptValue(item.prompt)
      setHasChanges(false)
    } else {
      setPromptValue('')
      setHasChanges(false)
    }
  }, [item?.id, item?.prompt])

  const handlePromptChange = (value: string) => {
    setPromptValue(value)
    setHasChanges(value !== item?.prompt)
  }

  const handleSave = () => {
    if (item && hasChanges) {
      onSave(item.id, { prompt: promptValue })
      setHasChanges(false)
    }
  }

  const handleCancel = () => {
    if (item?.prompt) {
      setPromptValue(item.prompt)
    }
    setHasChanges(false)
  }

  const handleRegenerate = () => {
    if (item && onRegenerate) {
      onRegenerate(item.id)
    }
  }

  const handleDelete = () => {
    if (item && onDelete) {
      if (confirm('Are you sure you want to delete this scene? This action cannot be undone.')) {
        onDelete(item.id)
        onClose()
      }
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Render empty state when no item is selected
  if (!item) {
    return (
      <Sheet open={isOpen} onOpenChange={onClose}>
        <SheetContent side="right" className="w-[500px] bg-gray-900 border-gray-700">
          <div className="flex h-full items-center justify-center text-gray-500">
            <div className="text-center">
              <Film className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p className="text-sm">Select a scene to view details</p>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    )
  }

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[500px] bg-gray-900 border-gray-700 overflow-y-auto">
        <SheetHeader className="space-y-4">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-white text-xl">
              Scene Details
            </SheetTitle>
            <Badge
              variant="outline"
              className="bg-blue-500/20 text-blue-400 border-blue-500/30"
            >
              Scene {item.sceneNumber}
            </Badge>
          </div>
          <SheetDescription className="text-gray-400">
            Edit the prompt and settings for this scene
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Thumbnail Preview */}
          {item.thumbnail && (
            <div className="space-y-2">
              <Label className="text-gray-300 text-sm font-medium">Preview</Label>
              <div className="relative aspect-video rounded-lg overflow-hidden border border-gray-700 bg-gray-800">
                <img
                  src={item.thumbnail}
                  alt={`Scene ${item.sceneNumber}`}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          )}

          {/* Scene Info */}
          <div className="space-y-3 rounded-lg bg-gray-800/50 p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Scene Information
            </h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-500 mb-1">Start Time</p>
                <p className="text-white font-medium">{formatTime(item.startTime)}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-1">Duration</p>
                <p className="text-white font-medium">{formatTime(item.duration)}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-1">End Time</p>
                <p className="text-white font-medium">
                  {formatTime(item.startTime + item.duration)}
                </p>
              </div>
              <div>
                <p className="text-gray-500 mb-1">Scene ID</p>
                <p className="text-white font-medium font-mono text-xs">
                  {item.id}
                </p>
              </div>
            </div>
          </div>

          <Separator className="bg-gray-700" />

          {/* Prompt Editor */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="prompt" className="text-gray-300 text-sm font-medium">
                Scene Prompt
              </Label>
              <span className="text-xs text-gray-500">
                {promptValue.length} characters
              </span>
            </div>
            <Textarea
              id="prompt"
              value={promptValue}
              onChange={(e) => handlePromptChange(e.target.value)}
              placeholder="Describe what you want to see in this scene..."
              className="bg-gray-800 border-gray-600 text-white placeholder:text-gray-500 min-h-[180px] resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={8}
            />
            <p className="text-xs text-gray-400">
              Describe the visuals, actions, and atmosphere for this scene. Be specific and detailed.
            </p>
          </div>

          {/* Action Buttons */}
          {hasChanges && (
            <div className="flex gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <Button
                onClick={handleSave}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
              <Button
                onClick={handleCancel}
                variant="outline"
                className="flex-1 border-gray-600 text-gray-300 hover:bg-gray-800 hover:text-white"
              >
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </div>
          )}

          <Separator className="bg-gray-700" />

          {/* Scene Actions */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300">Scene Actions</h3>
            <div className="space-y-2">
              {onRegenerate && (
                <Button
                  onClick={handleRegenerate}
                  disabled={isRegenerating || hasChanges}
                  variant="outline"
                  className={cn(
                    'w-full justify-start',
                    'border-green-500/50 text-green-400 hover:bg-green-500/10 hover:text-green-300',
                    isRegenerating && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  <RefreshCw className={cn('mr-2 h-4 w-4', isRegenerating && 'animate-spin')} />
                  {isRegenerating ? 'Regenerating Scene...' : 'Regenerate Scene'}
                </Button>
              )}
              {onDelete && (
                <Button
                  onClick={handleDelete}
                  disabled={hasChanges}
                  variant="outline"
                  className={cn(
                    'w-full justify-start',
                    'border-red-500/50 text-red-400 hover:bg-red-500/10 hover:text-red-300'
                  )}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Scene
                </Button>
              )}
            </div>
            {hasChanges && (
              <p className="text-xs text-yellow-400 flex items-center gap-1">
                <span>⚠</span>
                Save or cancel changes before performing actions
              </p>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
