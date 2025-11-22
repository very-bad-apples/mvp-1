'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Loader2, MoreVertical, RefreshCw, Edit, Video, AlertCircle } from 'lucide-react'
import type { Project, ProjectScene } from '@/types/project'
import {
  regenerateScenePrompt,
  regenerateVideo,
  regenerateLipSync,
} from '@/lib/orchestration'
import { useToast } from '@/hooks/useToast'

interface ScenesPanelProps {
  project: Project
  selectedSceneId: string | null
  onSceneSelect: (sceneId: string | null) => void
  onProjectUpdate: () => void
}

export function ScenesPanel({
  project,
  selectedSceneId,
  onSceneSelect,
  onProjectUpdate,
}: ScenesPanelProps) {
  const [regeneratingScenes, setRegeneratingScenes] = useState<Set<string>>(new Set())
  const { toast } = useToast()

  const handleRegenerateScene = async (scene: ProjectScene, type: 'prompt' | 'video' | 'all') => {
    const sceneId = `scene-${scene.sequence}`
    setRegeneratingScenes(prev => new Set(prev).add(sceneId))

    try {
      toast({
        title: 'Regenerating Scene',
        description: `Regenerating ${type} for Scene ${scene.sequence}...`,
      })

      const sceneIndex = scene.sequence - 1

      if (type === 'prompt' || type === 'all') {
        await regenerateScenePrompt(
          project.projectId,
          sceneIndex,
          {
            onProgress: (phase, idx, total, message) => {
              console.log(`Regenerate prompt progress: ${message}`)
            },
            onError: (phase, idx, error) => {
              console.error('Regenerate prompt error:', error)
            },
          }
        )
      }

      if (type === 'video' || type === 'all') {
        await regenerateVideo(
          project.projectId,
          sceneIndex,
          {
            onProgress: (phase, idx, total, message) => {
              console.log(`Regenerate video progress: ${message}`)
            },
            onError: (phase, idx, error) => {
              console.error('Regenerate video error:', error)
            },
          }
        )
      }

      toast({
        title: 'Regeneration Complete',
        description: `Scene ${scene.sequence} has been regenerated successfully.`,
      })

      await onProjectUpdate()
    } catch (error) {
      console.error('Regeneration error:', error)
      toast({
        title: 'Regeneration Failed',
        description: error instanceof Error ? error.message : 'Failed to regenerate scene',
        variant: 'destructive',
      })
    } finally {
      setRegeneratingScenes(prev => {
        const next = new Set(prev)
        next.delete(sceneId)
        return next
      })
    }
  }

  const getSceneStatus = (scene: ProjectScene) => {
    if (scene.errorMessage) return 'error'
    if (scene.videoClipUrl) return 'completed'
    if (scene.status === 'processing') return 'processing'
    return 'pending'
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Complete</Badge>
      case 'processing':
        return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Generating</Badge>
      case 'error':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Error</Badge>
      default:
        return <Badge className="bg-gray-500/20 text-gray-400 border-gray-500/30">Pending</Badge>
    }
  }

  const sortedScenes = [...project.scenes].sort((a, b) => a.sequence - b.sequence)

  return (
    <div className="h-full bg-gray-900 border-r border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-800/50">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Video className="h-5 w-5 text-blue-500" />
          Scenes ({sortedScenes.length})
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          Select a scene to preview or edit
        </p>
      </div>

      {/* Scenes List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {sortedScenes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Loader2 className="h-8 w-8 animate-spin mb-2" />
            <p>Generating scenes...</p>
          </div>
        ) : (
          sortedScenes.map((scene) => {
            const sceneId = `scene-${scene.sequence}`
            const isSelected = selectedSceneId === sceneId
            const status = getSceneStatus(scene)
            const isRegenerating = regeneratingScenes.has(sceneId)

            return (
              <Card
                key={sceneId}
                className={`cursor-pointer transition-all hover:border-blue-500/50 ${
                  isSelected
                    ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20'
                    : 'border-gray-700 bg-gray-800/50 hover:bg-gray-800'
                }`}
                onClick={() => onSceneSelect(isSelected ? null : sceneId)}
              >
                <CardContent className="p-3">
                  {/* Scene Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="bg-gray-700/50 text-gray-300 border-gray-600">
                        Scene {scene.sequence}
                      </Badge>
                      {getStatusBadge(status)}
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-gray-400 hover:text-white"
                          disabled={isRegenerating}
                        >
                          {isRegenerating ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <MoreVertical className="h-4 w-4" />
                          )}
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="bg-gray-800 border-gray-700">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRegenerateScene(scene, 'all')
                          }}
                          className="text-gray-200 hover:bg-gray-700"
                        >
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Regenerate All
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRegenerateScene(scene, 'prompt')
                          }}
                          className="text-gray-200 hover:bg-gray-700"
                        >
                          <Edit className="mr-2 h-4 w-4" />
                          Regenerate Prompt
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRegenerateScene(scene, 'video')
                          }}
                          className="text-gray-200 hover:bg-gray-700"
                        >
                          <Video className="mr-2 h-4 w-4" />
                          Regenerate Video
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {/* Video Thumbnail */}
                  <div className="relative aspect-video bg-gray-900 rounded-md overflow-hidden mb-2">
                    {scene.videoClipUrl ? (
                      <video
                        src={scene.videoClipUrl}
                        className="w-full h-full object-cover pointer-events-none"
                        muted
                        preload="metadata"
                        playsInline
                      />
                    ) : status === 'processing' ? (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                      </div>
                    ) : status === 'error' ? (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <AlertCircle className="h-8 w-8 text-red-500" />
                      </div>
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Video className="h-8 w-8 text-gray-600" />
                      </div>
                    )}
                  </div>

                  {/* Scene Prompt */}
                  <p className="text-sm text-gray-300 line-clamp-2 leading-relaxed">
                    {scene.prompt || 'No description available'}
                  </p>

                  {/* Error Message */}
                  {scene.errorMessage && (
                    <p className="text-xs text-red-400 mt-2">
                      {scene.errorMessage}
                    </p>
                  )}

                  {/* Duration */}
                  {scene.duration && (
                    <p className="text-xs text-gray-500 mt-2">
                      Duration: {scene.duration}s
                    </p>
                  )}
                </CardContent>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
