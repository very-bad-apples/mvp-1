'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react'
import { ProjectScene } from '@/types/project'

interface SceneGenerationOverlayProps {
  /** Whether the overlay is visible */
  isVisible: boolean
  /** Array of scenes being generated */
  scenes: ProjectScene[]
  /** Total number of scenes expected */
  totalScenes: number
  /** Callback when Continue button is clicked */
  onContinue: () => void
  /** Whether all scenes are complete */
  isComplete: boolean
}

/**
 * Cinematic overlay displaying scene generation progress with bottom-up animations
 */
export function SceneGenerationOverlay({
  isVisible,
  scenes,
  totalScenes,
  onContinue,
  isComplete,
}: SceneGenerationOverlayProps) {
  // Animation variants for the overlay
  const overlayVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.5,
      }
    },
    exit: {
      opacity: 0,
      transition: {
        duration: 0.5,
      }
    },
  }

  // Animation variants for the container holding scene cards
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.3,
      }
    }
  }

  // Animation variants for individual scene cards (bottom-up slide)
  const sceneCardVariants = {
    hidden: {
      opacity: 0,
      y: 50,
      scale: 0.9,
    },
    show: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: 'spring' as const,
        stiffness: 100,
        damping: 15,
      }
    }
  }

  // Determine scene status
  // NOTE: This overlay tracks SCENE TEXT generation only, not video generation
  const getSceneStatus = (scene: ProjectScene) => {
    if (scene.errorMessage) return 'error'
    // A scene is complete when it has a prompt (text description), NOT when it has a video
    if (scene.prompt && scene.prompt.length > 0) return 'complete'
    if (scene.status === 'processing') return 'generating'
    return 'pending'
  }

  // Get status badge component
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'complete':
        return (
          <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Complete
          </Badge>
        )
      case 'generating':
        return (
          <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            Generating
          </Badge>
        )
      case 'error':
        return (
          <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
            <XCircle className="w-3 h-3 mr-1" />
            Error
          </Badge>
        )
      default:
        return (
          <Badge className="bg-gray-500/20 text-gray-400 border-gray-500/30">
            <Clock className="w-3 h-3 mr-1" />
            Pending
          </Badge>
        )
    }
  }

  // Calculate overall progress based on scene TEXT generation, not video generation
  const completedScenes = scenes.filter(s => s.prompt && s.prompt.length > 0).length
  const progress = totalScenes > 0 ? (completedScenes / totalScenes) * 100 : 0

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          variants={overlayVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90 backdrop-blur-lg p-6 overflow-y-auto"
        >
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-center mb-8"
          >
            <h1 className="text-4xl font-bold text-white mb-2">
              Creating Your Scenes
            </h1>
            <p className="text-gray-400 text-lg">
              {completedScenes} of {totalScenes} scenes completed
            </p>

            {/* Overall progress bar */}
            <div className="mt-4 max-w-md mx-auto">
              <Progress value={progress} className="h-2 bg-gray-700">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </Progress>
            </div>
          </motion.div>

          {/* Scene Cards - Rendered in reverse to show Scene 1 at bottom */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="w-full max-w-4xl space-y-4 mb-8"
          >
            {[...scenes].reverse().map((scene) => {
              const status = getSceneStatus(scene)
              const sceneProgress = status === 'complete' ? 100 : status === 'generating' ? 50 : 0

              return (
                <motion.div
                  key={scene.sequence}
                  variants={sceneCardVariants}
                >
                  <Card className="bg-gray-800/50 border-gray-700 p-6 backdrop-blur-sm">
                    <div className="flex items-start gap-4">
                      {/* Scene Number */}
                      <div className="flex-shrink-0 w-16 h-16 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                        <span className="text-2xl font-bold text-white">
                          {scene.sequence}
                        </span>
                      </div>

                      {/* Scene Details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-lg font-semibold text-white truncate">
                            Scene {scene.sequence}
                          </h3>
                          {getStatusBadge(status)}
                        </div>

                        <p className="text-gray-400 text-sm mb-3 line-clamp-2">
                          {scene.prompt}
                        </p>

                        {/* Progress bar for this scene */}
                        <Progress value={sceneProgress} className="h-1.5 bg-gray-700">
                          <div
                            className="h-full bg-blue-500 transition-all duration-500"
                            style={{ width: `${sceneProgress}%` }}
                          />
                        </Progress>

                        {/* Error message if any */}
                        {scene.errorMessage && (
                          <p className="text-red-400 text-xs mt-2">
                            {scene.errorMessage}
                          </p>
                        )}
                      </div>

                      {/* Scene icon placeholder - NO VIDEO PREVIEW since this is scene text generation only */}
                      <div className="flex-shrink-0 w-32 h-20 rounded-lg bg-gray-700/50 overflow-hidden border border-gray-600">
                        <div className="w-full h-full flex items-center justify-center">
                          {status === 'complete' ? (
                            <CheckCircle2 className="w-10 h-10 text-green-400" />
                          ) : status === 'generating' ? (
                            <Loader2 className="w-10 h-10 text-blue-400 animate-spin" />
                          ) : (
                            <Clock className="w-10 h-10 text-gray-500" />
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </motion.div>

          {/* Continue Button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{
              opacity: 1,
              scale: 1,
            }}
            transition={{ delay: 0.5 }}
          >
            <Button
              size="lg"
              onClick={onContinue}
              disabled={!isComplete}
              className={`
                px-8 py-6 text-lg font-semibold
                ${isComplete
                  ? 'bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700'
                  : 'bg-gray-700 cursor-not-allowed'
                }
                text-white transition-all duration-300
                ${isComplete ? 'animate-pulse' : ''}
              `}
            >
              {isComplete ? 'Continue to Timeline' : 'Generating Scenes...'}
            </Button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
