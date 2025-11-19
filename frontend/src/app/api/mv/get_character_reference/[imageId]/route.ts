import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const revalidate = 0

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
// Use server-side API key (not exposed to client)
const API_KEY = process.env.API_KEY || ''

export async function GET(
  request: NextRequest,
  { params }: { params: { imageId: string } }
) {
  try {
    const { imageId } = params
    const searchParams = request.nextUrl.searchParams
    const redirect = searchParams.get('redirect') || 'false'

    if (!imageId) {
      return NextResponse.json(
        {
          error: 'ValidationError',
          message: 'Invalid image ID',
          details: 'imageId is required'
        },
        { status: 400 }
      )
    }

    // Proxy the request to backend
    const response = await fetch(`${BACKEND_URL}/api/mv/get_character_reference/${imageId}?redirect=${redirect}`, {
      method: 'GET',
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        error: 'Unknown error',
        message: 'Failed to retrieve character reference image'
      }))
      return NextResponse.json(errorData, { status: response.status })
    }

    // Check if response is JSON (cloud storage) or binary (local storage)
    const contentType = response.headers.get('content-type') || ''
    
    if (contentType.includes('application/json')) {
      // Cloud storage mode - return JSON as-is
      const data = await response.json()
      return NextResponse.json(data)
    } else {
      // Local storage mode - return image blob
      const blob = await response.blob()
      return new NextResponse(blob, {
        status: 200,
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'no-store, no-cache, must-revalidate',
        },
      })
    }
  } catch (error) {
    console.error('Error in get_character_reference API route:', error)
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

