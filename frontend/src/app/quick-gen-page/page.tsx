'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Video, ChevronLeft } from 'lucide-react'

interface QuickJobData {
  videoDescription: string
  characterDescription: string
  characterReferenceImageId: string
}

export default function QuickGenPage() {
  const router = useRouter()
  const [jobData, setJobData] = useState<QuickJobData>({
    videoDescription: '',
    characterDescription: '',
    characterReferenceImageId: '',
  })

  useEffect(() => {
    // Retrieve state from sessionStorage
    const storedData = sessionStorage.getItem('quickJobData')
    if (storedData) {
      try {
        const parsed = JSON.parse(storedData) as QuickJobData
        setJobData({
          videoDescription: parsed.videoDescription || '',
          characterDescription: parsed.characterDescription || '',
          characterReferenceImageId: parsed.characterReferenceImageId || '',
        })
      } catch (error) {
        console.error('Failed to parse quickJobData from sessionStorage:', error)
      }
    }
  }, [])

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
            <Link href="/create">
              <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
                <ChevronLeft className="mr-2 h-4 w-4" />
                Back to Create
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Quick Job
            </h1>
            <p className="text-xl text-gray-300">
              Review your input data
            </p>
          </div>

          <div className="space-y-6">
            {/* Input Data Card */}
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white">Input Data</CardTitle>
                <CardDescription className="text-gray-400">
                  Data received from the create page
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Video Description */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-400">
                      Video Description
                    </label>
                    <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3 min-h-[60px]">
                      <p className="text-white text-sm whitespace-pre-wrap">
                        {jobData.videoDescription || <span className="text-gray-500 italic">Empty</span>}
                      </p>
                    </div>
                  </div>

                  {/* Character and Style */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-400">
                      Character and Style
                    </label>
                    <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3 min-h-[60px]">
                      <p className="text-white text-sm whitespace-pre-wrap">
                        {jobData.characterDescription || <span className="text-gray-500 italic">Empty</span>}
                      </p>
                    </div>
                  </div>

                  {/* Character Reference Image ID */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-400">
                      Character Reference Image ID
                    </label>
                    <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                      <p className="text-white text-sm font-mono">
                        {jobData.characterReferenceImageId || <span className="text-gray-500 italic">Empty</span>}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
