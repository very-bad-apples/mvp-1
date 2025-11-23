'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Edit, Save, X, Clock } from 'lucide-react'
import type { ProjectScene } from '@/types/project'

interface SceneDetailPanelProps {
  scene: ProjectScene
  onUpdatePrompt: (sceneSequence: number, newPrompt: string) => Promise<void>
  onUpdateNegativePrompt?: (sceneSequence: number, newNegativePrompt: string) => Promise<void>
}

export function SceneDetailPanel({ scene, onUpdatePrompt, onUpdateNegativePrompt }: SceneDetailPanelProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedPrompt, setEditedPrompt] = useState(scene.prompt)
  const [isEditingNegative, setIsEditingNegative] = useState(false)
  const [editedNegativePrompt, setEditedNegativePrompt] = useState(scene.negativePrompt || '')
  const [isSaving, setIsSaving] = useState(false)

  // Sync local state with prop changes (e.g., after refetch)
  useEffect(() => {
    setEditedPrompt(scene.prompt)
    setEditedNegativePrompt(scene.negativePrompt || '')
  }, [scene.prompt, scene.negativePrompt])

  const handleSave = async () => {
    if (!editedPrompt.trim()) {
      return
    }

    setIsSaving(true)
    try {
      await onUpdatePrompt(scene.sequence, editedPrompt.trim())
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to save prompt:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setEditedPrompt(scene.prompt)
    setIsEditing(false)
  }

  const handleSaveNegative = async () => {
    if (!onUpdateNegativePrompt) {
      return
    }

    setIsSaving(true)
    try {
      await onUpdateNegativePrompt(scene.sequence, editedNegativePrompt.trim())
      setIsEditingNegative(false)
    } catch (error) {
      console.error('Failed to save negative prompt:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancelNegative = () => {
    setEditedNegativePrompt(scene.negativePrompt || '')
    setIsEditingNegative(false)
  }

  const getStatusBadge = () => {
    if (scene.errorMessage) {
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Error</Badge>
    }
    if (scene.originalVideoClipUrl || scene.videoClipUrl) {
      return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Complete</Badge>
    }
    if (scene.status === 'processing') {
      return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Generating</Badge>
    }
    return <Badge className="bg-gray-500/20 text-gray-400 border-gray-500/30">Pending</Badge>
  }

  return (
    <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            Scene {scene.sequence} Details
          </CardTitle>
          <div className="flex items-center gap-2">
            {getStatusBadge()}
            {scene.duration && (
              <Badge variant="outline" className="bg-gray-700/50 text-gray-300 border-gray-600">
                <Clock className="w-3 h-3 mr-1" />
                {scene.duration}s
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Prompt Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-400">Scene Prompt</label>
              {!isEditing && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsEditing(true)}
                  className="text-gray-400 hover:text-white hover:bg-gray-700 h-7"
                >
                  <Edit className="h-3.5 w-3.5 mr-1.5" />
                  Edit
                </Button>
              )}
            </div>

            {isEditing ? (
              <div className="space-y-2">
                <Textarea
                  value={editedPrompt}
                  onChange={(e) => setEditedPrompt(e.target.value)}
                  className="min-h-[120px] bg-gray-900/50 border-gray-600 text-white resize-none"
                  placeholder="Enter scene description..."
                />
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={isSaving || !editedPrompt.trim()}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    <Save className="h-3.5 w-3.5 mr-1.5" />
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCancel}
                    disabled={isSaving}
                    className="text-gray-400 hover:text-white hover:bg-gray-700"
                  >
                    <X className="h-3.5 w-3.5 mr-1.5" />
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="bg-gray-900/50 border border-gray-700 rounded-md p-3 text-sm text-gray-300 leading-relaxed max-h-[200px] overflow-y-auto">
                {scene.prompt || 'No description available'}
              </div>
            )}
          </div>

          {/* Negative Prompt Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-400">Negative Prompt</label>
              {!isEditingNegative && onUpdateNegativePrompt && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsEditingNegative(true)}
                  className="text-gray-400 hover:text-white hover:bg-gray-700 h-7"
                >
                  <Edit className="h-3.5 w-3.5 mr-1.5" />
                  Edit
                </Button>
              )}
            </div>

            {isEditingNegative ? (
              <div className="space-y-2">
                <Textarea
                  value={editedNegativePrompt}
                  onChange={(e) => setEditedNegativePrompt(e.target.value)}
                  className="min-h-[100px] bg-gray-900/50 border-gray-600 text-white resize-none"
                  placeholder="Enter negative prompt (things to avoid)..."
                />
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={handleSaveNegative}
                    disabled={isSaving}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    <Save className="h-3.5 w-3.5 mr-1.5" />
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCancelNegative}
                    disabled={isSaving}
                    className="text-gray-400 hover:text-white hover:bg-gray-700"
                  >
                    <X className="h-3.5 w-3.5 mr-1.5" />
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="bg-gray-900/50 border border-gray-700 rounded-md p-3 text-sm text-gray-400 leading-relaxed max-h-[150px] overflow-y-auto">
                {scene.negativePrompt || 'No negative prompt specified'}
              </div>
            )}
          </div>

          {/* Error Message (if exists) */}
          {scene.errorMessage && (
            <div>
              <label className="text-sm font-medium text-red-400 mb-2 block">
                Error
              </label>
              <div className="bg-red-950/30 border border-red-900/50 rounded-md p-3 text-sm text-red-300 leading-relaxed">
                {scene.errorMessage}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
