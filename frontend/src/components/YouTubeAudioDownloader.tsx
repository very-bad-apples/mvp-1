'use client'

import { useState } from 'react'
import { Youtube, Download, Loader2, CheckCircle2, X, Music } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useToast } from '@/hooks/use-toast'

// Use Next.js API route instead of direct backend call
const API_URL = '/api/audio'

interface AudioDownloadResult {
  audio_id: string
  audio_url: string
  filename: string
  format: string
  title: string
  duration?: number
  file_size_bytes: number
}

interface YouTubeAudioDownloaderProps {
  onAudioDownloaded?: (audioId: string, audioUrl: string) => void
  downloadedAudio?: AudioDownloadResult | null
}

export function YouTubeAudioDownloader({ 
  onAudioDownloaded, 
  downloadedAudio 
}: YouTubeAudioDownloaderProps) {
  const { toast } = useToast()
  const [url, setUrl] = useState('')
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadResult, setDownloadResult] = useState<AudioDownloadResult | null>(downloadedAudio || null)
  const [error, setError] = useState<string | null>(null)

  const isValidYouTubeUrl = (url: string): boolean => {
    const patterns = [
      /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+/,
      /^https?:\/\/youtube\.com\/watch\?v=[\w-]+/,
      /^https?:\/\/youtu\.be\/[\w-]+/
    ]
    return patterns.some(pattern => pattern.test(url))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleDownload = async () => {
    if (!url.trim()) {
      toast({
        title: "Error",
        description: "Please enter a YouTube URL",
        variant: "destructive",
      })
      return
    }

    if (!isValidYouTubeUrl(url)) {
      toast({
        title: "Invalid URL",
        description: "Please enter a valid YouTube URL",
        variant: "destructive",
      })
      return
    }

    setIsDownloading(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url.trim(),
          audio_quality: '192', // Default quality
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
        throw new Error(errorData.message || errorData.detail?.message || errorData.error || 'Failed to download audio')
      }

      const data: AudioDownloadResult = await response.json()
      setDownloadResult(data)
      setUrl('') // Clear URL after successful download

      // Notify parent component
      if (onAudioDownloaded) {
        onAudioDownloaded(data.audio_id, data.audio_url)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to download audio'
      setError(errorMessage)
      toast({
        title: "Download Failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsDownloading(false)
    }
  }

  const handleClear = () => {
    setDownloadResult(null)
    setUrl('')
    setError(null)
    if (onAudioDownloaded) {
      onAudioDownloaded('', '')
    }
  }

  return (
    <div className="space-y-3">
      {!downloadResult ? (
        <div className="space-y-3">
          <div className="border-2 border-dashed border-gray-600 rounded-lg p-6 bg-gray-800/30">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full bg-red-500/10 p-3">
                <Youtube className="h-6 w-6 text-red-400" />
              </div>
              <div className="w-full space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="youtube-url" className="text-sm font-medium text-white">
                    YouTube URL
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      id="youtube-url"
                      type="url"
                      placeholder="https://www.youtube.com/watch?v=..."
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !isDownloading) {
                          handleDownload()
                        }
                      }}
                      className="flex-1 bg-gray-900/50 border-gray-600 text-white placeholder:text-gray-500"
                      disabled={isDownloading}
                    />
                    <Button
                      type="button"
                      onClick={handleDownload}
                      disabled={isDownloading || !url.trim()}
                      className="bg-red-600 hover:bg-red-700 text-white"
                    >
                      {isDownloading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4" />
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-gray-400 text-center">
                  Paste a YouTube URL to download audio as MP3
                </p>
              </div>
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="bg-red-950/50 border-red-900">
              <AlertDescription className="text-red-300">{error}</AlertDescription>
            </Alert>
          )}

          {isDownloading && (
            <Alert className="bg-blue-950/50 border-blue-900">
              <Loader2 className="h-4 w-4 animate-spin" />
              <AlertDescription className="text-blue-300">
                Downloading and converting audio... This may take 10-60 seconds.
              </AlertDescription>
            </Alert>
          )}
        </div>
      ) : (
        <div className="border border-gray-600 rounded-lg p-4 bg-gray-800/30">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-red-500/10 p-3 flex-shrink-0">
              <Music className="h-6 w-6 text-red-400" />
            </div>
            <div className="flex-1 min-w-0 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {downloadResult.title}
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>{formatFileSize(downloadResult.file_size_bytes)}</span>
                    <span>•</span>
                    <span>{downloadResult.format.toUpperCase()}</span>
                    {downloadResult.duration && (
                      <>
                        <span>•</span>
                        <span>{formatDuration(downloadResult.duration)}</span>
                      </>
                    )}
                  </div>
                </div>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  onClick={handleClear}
                  className="flex-shrink-0 text-gray-400 hover:text-white hover:bg-gray-700"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {/* Audio Preview */}
              <div className="mt-3">
                <audio
                  controls
                  src={`${API_URL}/get/${downloadResult.audio_id}`}
                  className="w-full h-10"
                />
              </div>

              {/* Download Button */}
              <div className="flex gap-2 mt-3">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    window.open(`${API_URL}/get/${downloadResult.audio_id}`, '_blank')
                  }}
                  className="flex-1 border-gray-600 text-white hover:bg-gray-700"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download MP3
                </Button>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-md">
                  <CheckCircle2 className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-400">Ready</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

