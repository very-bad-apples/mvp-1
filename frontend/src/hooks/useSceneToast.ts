import { useToast } from '@/hooks/useToast'
import { ProjectScene } from '@/types/project'

/**
 * Custom hook for standardized scene-related toast notifications
 *
 * Provides consistent messaging for scene operations across the application.
 */
export function useSceneToast() {
  const { toast } = useToast()

  return {
    /**
     * Show a success toast for a completed scene operation
     */
    showSuccess: (scene: ProjectScene, action: string, description?: string) => {
      toast({
        title: `${action} Complete`,
        description: description || `Scene ${scene.sequence} ${action.toLowerCase()} successfully.`,
      })
    },

    /**
     * Show an error toast for a failed scene operation
     */
    showError: (scene: ProjectScene, action: string, error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : `Failed to ${action.toLowerCase()}`
      toast({
        title: `${action} Failed`,
        description: errorMessage,
        variant: 'destructive',
      })
    },

    /**
     * Show a progress/loading toast for an ongoing scene operation
     */
    showProgress: (scene: ProjectScene, action: string) => {
      toast({
        title: `${action} in Progress`,
        description: `${action} Scene ${scene.sequence}...`,
      })
    },

    /**
     * Show a generic info toast
     */
    showInfo: (title: string, description?: string) => {
      toast({
        title,
        description,
      })
    },

    /**
     * Show a warning toast
     */
    showWarning: (title: string, description?: string) => {
      toast({
        title,
        description,
        variant: 'destructive',
      })
    },
  }
}
