"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"

export interface LipsyncOptions {
  temperature?: number
  active_speaker_detection?: boolean
  occlusion_detection_enabled?: boolean
}

export interface LipsyncOptionsModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (options: LipsyncOptions) => Promise<void>
  sceneSequence: number
  isLoading?: boolean
}

export function LipsyncOptionsModal({
  isOpen,
  onClose,
  onSubmit,
  sceneSequence,
  isLoading = false
}: LipsyncOptionsModalProps) {
  const [temperature, setTemperature] = useState<number>(0.5)
  const [activeSpeakerDetection, setActiveSpeakerDetection] = useState<boolean>(false)
  const [occlusionDetection, setOcclusionDetection] = useState<boolean>(false)

  const handleSubmit = async () => {
    const options: LipsyncOptions = {
      temperature,
      active_speaker_detection: activeSpeakerDetection,
      occlusion_detection_enabled: occlusionDetection
    }

    await onSubmit(options)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px] bg-slate-900 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white">Add Lipsync to Scene {sceneSequence}</DialogTitle>
          <DialogDescription className="text-slate-400">
            Configure lipsync parameters for this scene
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Temperature Slider */}
          <div className="grid gap-3">
            <div className="flex justify-between items-center">
              <Label htmlFor="temperature" className="text-white">
                Lip Movement Expressiveness
              </Label>
              <span className="text-sm text-slate-400">{temperature.toFixed(2)}</span>
            </div>
            <Slider
              id="temperature"
              min={0}
              max={1}
              step={0.05}
              value={[temperature]}
              onValueChange={(values) => setTemperature(values[0])}
              disabled={isLoading}
              className="w-full"
            />
            <p className="text-xs text-slate-500">
              0.0 = subtle, 1.0 = exaggerated
            </p>
          </div>

          {/* Active Speaker Detection */}
          <div className="flex items-center justify-between">
            <div className="grid gap-1.5">
              <Label
                htmlFor="active-speaker"
                className="text-white font-medium"
              >
                Active Speaker Detection
              </Label>
              <p className="text-xs text-slate-500">
                Auto-detect speaker in multi-person videos
              </p>
            </div>
            <Switch
              id="active-speaker"
              checked={activeSpeakerDetection}
              onCheckedChange={setActiveSpeakerDetection}
              disabled={isLoading}
            />
          </div>

          {/* Occlusion Detection */}
          <div className="flex items-center justify-between">
            <div className="grid gap-1.5">
              <Label
                htmlFor="occlusion"
                className="text-white font-medium"
              >
                Occlusion Detection
              </Label>
              <p className="text-xs text-slate-500">
                Handle face obstructions (slower processing)
              </p>
            </div>
            <Switch
              id="occlusion"
              checked={occlusionDetection}
              onCheckedChange={setOcclusionDetection}
              disabled={isLoading}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isLoading ? "Processing..." : "Add Lipsync"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
