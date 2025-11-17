import { NextRequest, NextResponse } from 'next/server'

// Disable caching for audio download endpoint (dynamic content)
export const dynamic = 'force-dynamic'
export const revalidate = 0

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate request body
    if (!body.url || !body.url.trim()) {
      return NextResponse.json(
        {
          error: 'ValidationError',
          message: 'URL is required',
          details: "The 'url' field cannot be empty"
        },
        { status: 400 }
      )
    }

    // Call backend API
    const response = await fetch(`${BACKEND_URL}/api/audio/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: body.url.trim(),
        audio_quality: body.audio_quality || '192',
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        data,
        { status: response.status }
      )
    }

    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    console.error('Error in audio download API route:', error)
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

