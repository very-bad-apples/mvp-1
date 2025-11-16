'use client'

import { useCallback } from 'react'
import { Upload, X } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

interface ImageUploadZoneProps {
  onFilesChange: (files: File[]) => void
  files: File[]
}

export function ImageUploadZone({ onFilesChange, files }: ImageUploadZoneProps) {
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      const droppedFiles = Array.from(e.dataTransfer.files).filter((file) =>
        file.type.startsWith('image/')
      )
      if (droppedFiles.length > 0) {
        onFilesChange([...files, ...droppedFiles])
      }
    },
    [files, onFilesChange]
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files
    if (selectedFiles) {
      onFilesChange([...files, ...Array.from(selectedFiles)])
    }
  }

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index)
    onFilesChange(newFiles)
  }

  return (
    <div className="space-y-3">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="relative border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-blue-500/50 transition-colors bg-gray-800/30"
      >
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          id="image-upload"
        />
        <div className="flex flex-col items-center gap-3">
          <div className="rounded-full bg-blue-500/10 p-3">
            <Upload className="h-6 w-6 text-blue-400" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-white">
              Drop product images here or click to browse
            </p>
            <p className="text-xs text-gray-400">
              PNG, JPG, WebP up to 10MB each
            </p>
          </div>
        </div>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-400">
            {files.length} {files.length === 1 ? 'image' : 'images'} uploaded
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {files.map((file, index) => (
              <div
                key={index}
                className="relative group rounded-lg border border-gray-600 overflow-hidden bg-gray-800 aspect-square"
              >
                <img
                  src={URL.createObjectURL(file)}
                  alt={`Upload ${index + 1}`}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <Button
                    type="button"
                    size="icon"
                    variant="destructive"
                    onClick={() => removeFile(index)}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-2">
                  <p className="text-xs text-white truncate">{file.name}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
