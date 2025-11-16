'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Video, ChevronLeft } from 'lucide-react'
import { VideoPreview } from '@/components/timeline/VideoPreview'
import { Timeline } from '@/components/timeline/Timeline'

export default function EditPage({ params }: { params: { id: string } }) {
  const [currentTime, setCurrentTime] = useState(0)
  const [duration] = useState(180) // Total duration: 5 segments × 36 seconds = 180 seconds
  const [isPlaying, setIsPlaying] = useState(false)
  const [zoom, setZoom] = useState(1)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <nav className="border-b border-gray-700/50 backdrop-blur-sm bg-gray-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <Video className="h-8 w-8 text-blue-500" />
              <span className="text-xl font-bold text-white">AI Video Generator</span>
            </Link>
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                className="border-gray-600 text-white hover:bg-gray-800"
                onClick={() => window.location.href = `/result/${params.id}`}
              >
                <ChevronLeft className="mr-2 h-4 w-4" />
                Back to Result
              </Button>
              <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                Export Video
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Video Editor */}
      <div className="h-[calc(100vh-73px)] flex flex-col">
        {/* Top Section - Video Preview (60%) */}
        <div className="h-[60%] flex items-center justify-center border-b border-gray-700 bg-gray-800/50 p-6">
          <VideoPreview
            jobId={params.id}
            currentTime={currentTime}
            duration={duration}
            isPlaying={isPlaying}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onSeek={setCurrentTime}
          />
        </div>

        {/* Bottom Section - Timeline (40%) */}
        <div className="h-[40%] overflow-hidden bg-gray-900">
          <Timeline
            jobId={params.id}
            currentTime={currentTime}
            duration={duration}
            zoom={zoom}
            onSeek={setCurrentTime}
            onZoomChange={setZoom}
          />
        </div>
      </div>
    </div>
  )
}
