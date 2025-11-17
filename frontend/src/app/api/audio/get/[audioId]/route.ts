import { NextRequest, NextResponse } from 'next/server'

// Disable caching for audio files (they're large and dynamic)
export const dynamic = 'force-dynamic'
export const revalidate = 0

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: { audioId: string } }
) {
  try {
    const { audioId } = params

    if (!audioId || audioId.length < 10) {
      return NextResponse.json(
        {
          error: 'ValidationError',
          message: 'Invalid audio_id format',
          details: 'audio_id must be a valid identifier'
        },
        { status: 400 }
      )
    }

    // Proxy the request to backend
    const response = await fetch(`${BACKEND_URL}/api/audio/get/${audioId}`, {
      method: 'GET',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        error: 'Unknown error',
        message: 'Failed to retrieve audio file'
      }))
      return NextResponse.json(errorData, { status: response.status })
    }

    // Get the audio file as a blob
    const blob = await response.blob()
    const contentType = response.headers.get('content-type') || 'audio/mpeg'
    
    // Get filename from backend response if available, otherwise use audioId.mp3
    const contentDisposition = response.headers.get('content-disposition') || ''
    let filename = `${audioId}.mp3` // Default to MP3 since we always convert to MP3
    
    // Try to extract filename from Content-Disposition header
    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1]
      // Ensure it's .mp3 (since we always convert to MP3)
      if (!filename.endsWith('.mp3')) {
        filename = filename.replace(/\.[^.]+$/, '.mp3')
      }
    }

    // Return the audio file (stream, don't cache)
    return new NextResponse(blob, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      },
    })
  } catch (error) {
    console.error('Error in audio get API route:', error)
    return NextResponse.json(
      {
        error: 'InternalError',
        message: 'An unexpected error occurred',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}

