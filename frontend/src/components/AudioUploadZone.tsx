'use client'

import { useCallback } from 'react'
import { Music, X, FileAudio } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

interface AudioUploadZoneProps {
  onFileChange: (file: File | null) => void
  file: File | null
}

export function AudioUploadZone({ onFileChange, file }: AudioUploadZoneProps) {
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile && droppedFile.type.startsWith('audio/')) {
        onFileChange(droppedFile)
      }
    },
    [onFileChange]
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      onFileChange(selectedFile)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="space-y-3">
      {!file ? (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="relative border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-blue-500/50 transition-colors bg-gray-800/30"
        >
          <input
            type="file"
            accept="audio/*"
            onChange={handleFileInput}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            id="audio-upload"
          />
          <div className="flex flex-col items-center gap-3">
            <div className="rounded-full bg-blue-500/10 p-3">
              <Music className="h-6 w-6 text-blue-400" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-white">
                Drop music file here or click to browse
              </p>
              <p className="text-xs text-gray-400">
                MP3, WAV, OGG up to 50MB
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="border border-gray-600 rounded-lg p-4 bg-gray-800/30">
          <div className="flex items-center gap-4">
            <div className="rounded-lg bg-blue-500/10 p-3 flex-shrink-0">
              <FileAudio className="h-6 w-6 text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate text-white">{file.name}</p>
              <p className="text-xs text-gray-400">
                {formatFileSize(file.size)}
              </p>
            </div>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => onFileChange(null)}
              className="flex-shrink-0 text-gray-400 hover:text-white hover:bg-gray-700"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Audio Preview */}
          <div className="mt-4">
            <audio
              controls
              src={URL.createObjectURL(file)}
              className="w-full h-10"
            />
          </div>
        </div>
      )}
    </div>
  )
}
