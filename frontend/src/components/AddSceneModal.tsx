'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Loader2 } from 'lucide-react'
import { addScene } from '@/lib/api/client'
import { APIError, getUserFriendlyError } from '@/lib/api/client'
import { useToast } from '@/hooks/useToast'

interface AddSceneModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  onSceneAdded: () => void
}

export function AddSceneModal({
  open,
  onOpenChange,
  projectId,
  onSceneAdded,
}: AddSceneModalProps) {
  const [sceneConcept, setSceneConcept] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!sceneConcept.trim()) {
      setError('Scene concept is required')
      return
    }

    if (sceneConcept.length < 10 || sceneConcept.length > 1000) {
      setError('Scene concept must be between 10 and 1000 characters')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      // Call API to add scene
      await addScene(projectId, sceneConcept.trim())

      // Show success toast
      toast({
        title: 'Scene Added',
        description: 'New scene has been added successfully.',
      })

      // Reset form and close modal
      setSceneConcept('')
      onOpenChange(false)

      // Refresh the scene list
      onSceneAdded()
    } catch (err) {
      console.error('Failed to add scene:', err)

      // Handle API errors with user-friendly messages
      if (err instanceof APIError) {
        const errorInfo = getUserFriendlyError(err)
        toast({
          title: errorInfo.title,
          description: errorInfo.message,
          variant: 'destructive',
        })
        setError(err.message)
      } else {
        toast({
          title: 'Failed to Add Scene',
          description: err instanceof Error ? err.message : 'An unexpected error occurred',
          variant: 'destructive',
        })
        setError(err instanceof Error ? err.message : 'Failed to add scene')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!isSubmitting) {
      if (!newOpen) {
        // Reset form when closing
        setSceneConcept('')
        setError(null)
      }
      onOpenChange(newOpen)
    }
  }

  const characterCount = sceneConcept.length
  const isValid = characterCount >= 10 && characterCount <= 1000

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px] bg-gray-800 border-gray-700">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-white">Add New Scene</DialogTitle>
            <DialogDescription className="text-gray-400">
              Describe the concept for your new scene. This will be added to the end of your scene list.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="sceneConcept" className="text-white">
                Scene Concept
              </Label>
              <Textarea
                id="sceneConcept"
                value={sceneConcept}
                onChange={(e) => setSceneConcept(e.target.value)}
                placeholder="Describe what happens in this scene..."
                className="min-h-[120px] bg-gray-900 border-gray-600 text-white placeholder:text-gray-500 focus-visible:ring-blue-500"
                disabled={isSubmitting}
                maxLength={1000}
              />
              <div className="flex items-center justify-between text-xs">
                <span className={`${isValid ? 'text-gray-500' : 'text-red-400'}`}>
                  {characterCount}/1000 characters
                </span>
                {!isValid && characterCount > 0 && (
                  <span className="text-red-400">
                    Must be between 10 and 1000 characters
                  </span>
                )}
              </div>
            </div>

            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-md p-3">
                {error}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
              className="border-gray-600 text-white hover:bg-gray-700"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isValid || isSubmitting}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding Scene...
                </>
              ) : (
                'Add Scene'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
