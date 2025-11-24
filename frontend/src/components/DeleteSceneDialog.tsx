'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { AlertCircle } from 'lucide-react'

interface DeleteSceneDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sceneSequence: number
  isLastScene: boolean
  isComposing: boolean
  onConfirmDelete: () => void
}

export function DeleteSceneDialog({
  open,
  onOpenChange,
  sceneSequence,
  isLastScene,
  isComposing,
  onConfirmDelete,
}: DeleteSceneDialogProps) {
  const canDelete = !isLastScene && !isComposing

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="bg-gray-800 border-gray-700">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-white flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            Delete Scene {sceneSequence}?
          </AlertDialogTitle>
          <AlertDialogDescription className="text-gray-300 space-y-2">
            <p>This action cannot be undone. This will permanently delete the scene.</p>

            {isLastScene && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-md p-3 mt-3">
                <p className="text-yellow-400 text-sm font-medium">
                  Cannot delete the last remaining scene. A project must have at least one scene.
                </p>
              </div>
            )}

            {isComposing && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-md p-3 mt-3">
                <p className="text-yellow-400 text-sm font-medium">
                  Cannot delete scenes while video composition is in progress. Please wait for the composition to complete.
                </p>
              </div>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="border-gray-600 text-white hover:bg-gray-700">
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirmDelete}
            disabled={!canDelete}
            className="bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Delete Scene
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
