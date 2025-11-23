'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, Edit, Video, AlertCircle } from 'lucide-react'
import type { Project, ProjectScene } from '@/types/project'
import { useSceneToast } from '@/hooks/useSceneToast'
import { getSceneVideoUrl } from '@/lib/utils/video'
import { SceneEditModal } from '@/components/SceneEditModal'

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
  const sceneToast = useSceneToast()
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [selectedSceneForEdit, setSelectedSceneForEdit] = useState<ProjectScene | null>(null)

  const handleEditScene = (scene: ProjectScene) => {
    setSelectedSceneForEdit(scene)
    setEditModalOpen(true)
  }

  const handleSceneUpdate = () => {
    // Refresh the project data when a scene is updated
    onProjectUpdate()
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
                  </div>

                  {/* Video Thumbnail */}
                  <div className="relative aspect-video bg-gray-900 rounded-md overflow-hidden mb-2">
                    {getSceneVideoUrl(scene) ? (
                      <video
                        src={getSceneVideoUrl(scene)}
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

                  {/* Edit Scene Button */}
                  <Button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleEditScene(scene)
                    }}
                    className="w-full mt-3 bg-blue-600 hover:bg-blue-700 text-white border-blue-500/50"
                    size="sm"
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Edit Scene
                  </Button>

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

      {/* Scene Edit Modal */}
      {selectedSceneForEdit && (
        <SceneEditModal
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          scene={selectedSceneForEdit}
          projectId={project.projectId}
          onSceneUpdate={handleSceneUpdate}
        />
      )}
    </div>
  )
}
