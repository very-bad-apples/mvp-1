import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const revalidate = 0

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
// Use server-side API key (not exposed to client)
const API_KEY = process.env.API_KEY || ''

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params

    if (!id) {
      return NextResponse.json(
        {
          error: 'ValidationError',
          message: 'Invalid job ID',
          details: 'Job ID is required'
        },
        { status: 400 }
      )
    }

    // Proxy the request to backend
    const response = await fetch(`${BACKEND_URL}/api/jobs/${id}`, {
      method: 'GET',
      headers: {
        'X-API-Key': API_KEY,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        error: 'Unknown error',
        message: 'Failed to retrieve job'
      }))
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error in jobs API route:', error)
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

