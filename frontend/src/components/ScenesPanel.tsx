'use client'

import { useState, memo, useCallback, useMemo, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, Edit, Video, AlertCircle, Plus, Trash2, GripVertical } from 'lucide-react'
import type { Project, ProjectScene } from '@/types/project'
import { useSceneToast } from '@/hooks/useSceneToast'
import { getSceneVideoUrl, getVideoStableId } from '@/lib/utils/video'
import { SceneEditModal } from '@/components/SceneEditModal'
import { AddSceneModal } from '@/components/AddSceneModal'
import { DeleteSceneDialog } from '@/components/DeleteSceneDialog'
import { deleteScene, reorderScenes } from '@/lib/api/client'
import { APIError, getUserFriendlyError } from '@/lib/api/client'
import { useToast } from '@/hooks/useToast'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface VideoThumbnailProps {
  scene: ProjectScene
  status: string
}

/**
 * VideoThumbnail component that prevents unnecessary video reloads
 * when presigned URLs change but S3 keys stay the same.
 */
const VideoThumbnail = memo(function VideoThumbnail({ scene, status }: VideoThumbnailProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const lastStableIdRef = useRef<string | null>(null)
  const videoUrl = getSceneVideoUrl(scene)
  const stableId = getVideoStableId(videoUrl)

  useEffect(() => {
    const video = videoRef.current
    if (!video || !videoUrl) return

    // Only update video src if the S3 key path changed (not just presigned URL)
    if (stableId && stableId !== lastStableIdRef.current) {
      lastStableIdRef.current = stableId
      video.src = videoUrl
      video.load()
    } else if (!stableId && video.src !== videoUrl) {
      // Fallback: if we can't extract stable ID, use URL comparison
      video.src = videoUrl
      video.load()
    }
  }, [videoUrl, stableId])

  if (!videoUrl) {
    if (status === 'processing') {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      )
    }
    if (status === 'error') {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <AlertCircle className="h-8 w-8 text-red-500" />
        </div>
      )
    }
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <Video className="h-8 w-8 text-gray-600" />
      </div>
    )
  }

  return (
    <video
      ref={videoRef}
      className="w-full h-full object-cover pointer-events-none"
      muted
      preload="metadata"
      playsInline
    />
  )
}, (prevProps, nextProps) => {
  // Only re-render if scene sequence or video URL stable ID changed
  const prevUrl = getSceneVideoUrl(prevProps.scene)
  const nextUrl = getSceneVideoUrl(nextProps.scene)
  const prevStableId = getVideoStableId(prevUrl)
  const nextStableId = getVideoStableId(nextUrl)
  
  return (
    prevProps.scene.sequence === nextProps.scene.sequence &&
    prevProps.status === nextProps.status &&
    prevStableId === nextStableId
  )
})

interface SortableSceneCardProps {
  scene: ProjectScene
  isSelected: boolean
  status: string
  onSelect: () => void
  onEdit: () => void
  onDelete: () => void
  getStatusBadge: (status: string) => JSX.Element
}

const SortableSceneCard = memo(function SortableSceneCard({
  scene,
  isSelected,
  status,
  onSelect,
  onEdit,
  onDelete,
  getStatusBadge,
}: SortableSceneCardProps) {
  const sceneId = `scene-${scene.sequence}`
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: sceneId })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={`cursor-pointer transition-all hover:border-blue-500/50 ${
        isSelected
          ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20'
          : 'border-gray-700 bg-gray-800/50 hover:bg-gray-800'
      } ${isDragging ? 'z-50' : ''}`}
      onClick={onSelect}
    >
      <CardContent className="p-3">
        {/* Scene Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            {/* Drag Handle */}
            <button
              {...attributes}
              {...listeners}
              className="cursor-grab active:cursor-grabbing touch-none p-1 hover:bg-gray-700/50 rounded"
              onClick={(e) => e.stopPropagation()}
            >
              <GripVertical className="h-4 w-4 text-gray-400" />
            </button>
            <Badge variant="outline" className="bg-gray-700/50 text-gray-300 border-gray-600">
              Scene {scene.sequence}
            </Badge>
            {getStatusBadge(status)}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="h-8 w-8 p-0 hover:bg-red-500/20 hover:text-red-400 text-gray-400 cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Video Thumbnail */}
        <div className="relative aspect-video bg-gray-900 rounded-md overflow-hidden mb-2">
          <VideoThumbnail scene={scene} status={status} />
        </div>

        {/* Scene Prompt */}
        <p className="text-sm text-gray-300 line-clamp-2 leading-relaxed">
          {scene.prompt || 'No description available'}
        </p>

        {/* Edit Scene Button */}
        <Button
          onClick={(e) => {
            e.stopPropagation()
            onEdit()
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
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if these specific props change
  return (
    prevProps.scene.sequence === nextProps.scene.sequence &&
    prevProps.scene.status === nextProps.scene.status &&
    prevProps.scene.originalVideoClipUrl === nextProps.scene.originalVideoClipUrl &&
    prevProps.scene.videoClipUrl === nextProps.scene.videoClipUrl &&
    prevProps.scene.prompt === nextProps.scene.prompt &&
    prevProps.scene.errorMessage === nextProps.scene.errorMessage &&
    prevProps.scene.duration === nextProps.scene.duration &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.status === nextProps.status
  )
})

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
  const { toast } = useToast()
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [selectedSceneForEdit, setSelectedSceneForEdit] = useState<ProjectScene | null>(null)
  const [addSceneModalOpen, setAddSceneModalOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sceneToDelete, setSceneToDelete] = useState<ProjectScene | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Drag and drop state
  const [activeId, setActiveId] = useState<string | null>(null)
  const [localScenes, setLocalScenes] = useState<ProjectScene[]>([])
  const [isReordering, setIsReordering] = useState(false)

  // Initialize local scenes from project
  // Filter out scenes with invalid sequences and sort by displaySequence for UI ordering
  // Memoize to avoid unnecessary recalculations on every render
  const sortedScenes = useMemo(() => {
    return [...project.scenes]
      .filter(scene => {
        const isValid = scene.sequence != null && scene.sequence >= 1 && Number.isInteger(scene.sequence)
        if (!isValid) {
          console.warn('Scene with invalid sequence detected:', scene)
        }
        return isValid
      })
      .sort((a, b) => a.displaySequence - b.displaySequence)  // Sort by displaySequence for UI
  }, [project.scenes])

  // Use local scenes if reordering, otherwise use sorted project scenes
  const displayScenes = isReordering ? localScenes : sortedScenes

  // Configure drag sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleEditScene = (scene: ProjectScene) => {
    setSelectedSceneForEdit(scene)
    setEditModalOpen(true)
  }

  const handleSceneUpdate = () => {
    // Refresh the project data when a scene is updated
    onProjectUpdate()
  }

  // Get the fresh scene data from the project when it updates
  // This ensures the modal always shows the latest scene data including newly generated videos
  const freshSceneForEdit = selectedSceneForEdit
    ? project.scenes.find(s => s.sequence === selectedSceneForEdit.sequence) || selectedSceneForEdit
    : null

  const handleDeleteClick = (scene: ProjectScene) => {
    setSceneToDelete(scene)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!sceneToDelete) return

    setIsDeleting(true)
    try {
      await deleteScene(project.projectId, sceneToDelete.sequence)

      // Show success toast
      toast({
        title: 'Scene Deleted',
        description: `Scene ${sceneToDelete.sequence} has been deleted successfully.`,
      })

      // Close dialog
      setDeleteDialogOpen(false)
      setSceneToDelete(null)

      // Refresh the scene list
      onProjectUpdate()
    } catch (err) {
      console.error('Failed to delete scene:', err)

      // Handle API errors with user-friendly messages
      if (err instanceof APIError) {
        const errorInfo = getUserFriendlyError(err)
        toast({
          title: errorInfo.title,
          description: errorInfo.message,
          variant: 'destructive',
        })
      } else {
        toast({
          title: 'Failed to Delete Scene',
          description: err instanceof Error ? err.message : 'An unexpected error occurred',
          variant: 'destructive',
        })
      }
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    setActiveId(active.id as string)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event

    if (!over || active.id === over.id) {
      setActiveId(null)
      return
    }

    // Find the scenes being moved
    const oldIndex = displayScenes.findIndex((s) => `scene-${s.sequence}` === active.id)
    const newIndex = displayScenes.findIndex((s) => `scene-${s.sequence}` === over.id)

    if (oldIndex === -1 || newIndex === -1) {
      setActiveId(null)
      return
    }

    // Create the new order optimistically
    const newScenes = arrayMove(displayScenes, oldIndex, newIndex)
    setLocalScenes(newScenes)
    setIsReordering(true)
    setActiveId(null)

    // Calculate the new scene order (array of current displaySequence values in new display order)
    // The backend expects the CURRENT displaySequence values (scene identifiers) in the desired new order
    // After the reorder, the backend will assign new displaySequence values 1, 2, 3, etc. based on this order
    const sceneOrder = newScenes.map((s) => s.displaySequence)

    // Debug logging
    console.log('Reordering scenes:')
    console.log('  displayScenes:', displayScenes.map(s => ({ seq: s.sequence, displaySeq: s.displaySequence })))
    console.log('  newScenes:', newScenes.map(s => ({ seq: s.sequence, displaySeq: s.displaySequence })))
    console.log('  sceneOrder to send:', sceneOrder)

    // Validate sceneOrder before sending
    if (sceneOrder.length === 0) {
      console.error('sceneOrder is empty!')
      toast({
        title: 'Reorder Failed',
        description: 'No scenes to reorder',
        variant: 'destructive',
      })
      setIsReordering(false)
      setLocalScenes([])
      return
    }

    if (sceneOrder.some((seq) => seq < 1 || !Number.isInteger(seq))) {
      console.error('sceneOrder contains invalid sequence:', sceneOrder)
      toast({
        title: 'Reorder Failed',
        description: 'Invalid scene sequence numbers detected',
        variant: 'destructive',
      })
      setIsReordering(false)
      setLocalScenes([])
      return
    }

    if (new Set(sceneOrder).size !== sceneOrder.length) {
      console.error('sceneOrder contains duplicates:', sceneOrder)
      toast({
        title: 'Reorder Failed',
        description: 'Duplicate scene sequences detected',
        variant: 'destructive',
      })
      setIsReordering(false)
      setLocalScenes([])
      return
    }

    try {
      // Call the API to reorder
      await reorderScenes(project.projectId, sceneOrder)

      // Show success toast
      toast({
        title: 'Scenes Reordered',
        description: 'Scene order has been updated successfully.',
      })

      // Refresh the project to get the updated sequences
      onProjectUpdate()
    } catch (err) {
      console.error('Failed to reorder scenes:', err)

      // Rollback to original order
      setIsReordering(false)
      setLocalScenes([])

      // Handle API errors with user-friendly messages
      if (err instanceof APIError) {
        const errorInfo = getUserFriendlyError(err)
        toast({
          title: errorInfo.title,
          description: errorInfo.message,
          variant: 'destructive',
        })
      } else {
        toast({
          title: 'Failed to Reorder Scenes',
          description: err instanceof Error ? err.message : 'An unexpected error occurred',
          variant: 'destructive',
        })
      }
    } finally {
      // Clear the reordering state after API completes
      setIsReordering(false)
      setLocalScenes([])
    }
  }

  const handleDragCancel = () => {
    setActiveId(null)
  }

  const getSceneStatus = useCallback((scene: ProjectScene) => {
    if (scene.errorMessage) return 'error'
    if (scene.originalVideoClipUrl || scene.videoClipUrl) return 'completed'
    if (scene.status === 'processing') return 'processing'
    return 'pending'
  }, [])

  const getStatusBadge = useCallback((status: string) => {
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
  }, [])

  return (
    <div className="h-full bg-gray-900 border-r border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Video className="h-5 w-5 text-blue-500" />
            Scenes ({displayScenes.length})
          </h2>
          <Button
            onClick={() => setAddSceneModalOpen(true)}
            size="sm"
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Scene
          </Button>
        </div>
        <p className="text-sm text-gray-400">
          Select a scene to preview or edit. Drag scenes to reorder.
        </p>
      </div>

      {/* Scenes List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {displayScenes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Loader2 className="h-8 w-8 animate-spin mb-2" />
            <p>Generating scenes...</p>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
          >
            <SortableContext
              items={displayScenes.map((s) => `scene-${s.sequence}`)}
              strategy={verticalListSortingStrategy}
            >
              {displayScenes.map((scene) => {
                const sceneId = `scene-${scene.sequence}`
                const isSelected = selectedSceneId === sceneId
                const status = getSceneStatus(scene)

                return (
                  <SortableSceneCard
                    key={sceneId}
                    scene={scene}
                    isSelected={isSelected}
                    status={status}
                    onSelect={() => onSceneSelect(isSelected ? null : sceneId)}
                    onEdit={() => handleEditScene(scene)}
                    onDelete={() => handleDeleteClick(scene)}
                    getStatusBadge={getStatusBadge}
                  />
                )
              })}
            </SortableContext>
            <DragOverlay>
              {activeId ? (
                <div className="opacity-80">
                  <Card className="border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20">
                    <CardContent className="p-3">
                      <div className="flex items-center gap-2">
                        <GripVertical className="h-4 w-4 text-gray-400" />
                        <Badge variant="outline" className="bg-gray-700/50 text-gray-300 border-gray-600">
                          Scene {displayScenes.find(s => `scene-${s.sequence}` === activeId)?.sequence}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        )}
      </div>

      {/* Scene Edit Modal */}
      {freshSceneForEdit && (
        <SceneEditModal
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          scene={freshSceneForEdit}
          projectId={project.projectId}
          onSceneUpdate={handleSceneUpdate}
        />
      )}

      {/* Add Scene Modal */}
      <AddSceneModal
        open={addSceneModalOpen}
        onOpenChange={setAddSceneModalOpen}
        projectId={project.projectId}
        onSceneAdded={handleSceneUpdate}
      />

      {/* Delete Scene Dialog */}
      {sceneToDelete && (
        <DeleteSceneDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          sceneSequence={sceneToDelete.sequence}
          isLastScene={sortedScenes.length === 1}
          isComposing={false} // TODO: Add compositionStatus to Project type
          onConfirmDelete={handleConfirmDelete}
        />
      )}
    </div>
  )
}
