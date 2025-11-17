import { NextRequest, NextResponse } from 'next/server'

// Disable caching for audio info endpoint (dynamic content)
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

    // Call backend API
    const response = await fetch(`${BACKEND_URL}/api/audio/info/${audioId}`, {
      method: 'GET',
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    console.error('Error in audio info API route:', error)
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

