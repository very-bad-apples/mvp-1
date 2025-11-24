import { NextRequest, NextResponse } from 'next/server'

// Disable caching for API routes
export const dynamic = 'force-dynamic'
export const revalidate = 0

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
// Use server-side API key (not exposed to client)
const API_KEY = process.env.API_KEY || ''

/**
 * Catch-all proxy for /api/audio/* endpoints
 * This handles all audio API requests that don't have specific proxy routes
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params, 'GET')
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params, 'POST')
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params, 'PATCH')
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params, 'DELETE')
}

async function handleRequest(
  request: NextRequest,
  params: { path: string[] },
  method: string
) {
  try {
    const { path } = params
    const pathString = path.join('/')

    // Get query parameters from the request
    const searchParams = request.nextUrl.searchParams
    const queryString = searchParams.toString()

    // Construct the backend URL
    const backendUrl = `${BACKEND_URL}/api/audio/${pathString}${queryString ? `?${queryString}` : ''}`

    // Prepare headers
    const headers: Record<string, string> = {
      'X-API-Key': API_KEY,
    }

    // Prepare request options
    const requestOptions: RequestInit = {
      method,
      headers,
    }

    // Add body for POST, PATCH, DELETE requests
    if (method !== 'GET' && method !== 'HEAD') {
      const contentType = request.headers.get('content-type')

      if (contentType?.includes('application/json')) {
        // JSON body
        const body = await request.json()
        requestOptions.body = JSON.stringify(body)
        headers['Content-Type'] = 'application/json'
      } else if (contentType?.includes('multipart/form-data')) {
        // FormData body (don't set Content-Type - browser will set with boundary)
        const formData = await request.formData()
        requestOptions.body = formData as any
        delete headers['Content-Type'] // Let fetch set it
      } else if (contentType) {
        // Other content types
        const body = await request.text()
        requestOptions.body = body
        headers['Content-Type'] = contentType
      }
    }

    // Proxy the request to backend
    const response = await fetch(backendUrl, requestOptions)

    // Check if response is JSON or binary
    const responseContentType = response.headers.get('content-type') || ''

    if (responseContentType.includes('application/json')) {
      // JSON response
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          error: 'Unknown error',
          message: 'Request failed'
        }))
        return NextResponse.json(errorData, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data)
    } else {
      // Binary/other response (audio files, etc.)
      const blob = await response.blob()

      return new NextResponse(blob, {
        status: response.status,
        headers: {
          'Content-Type': responseContentType,
          'Content-Disposition': response.headers.get('content-disposition') || '',
          'Cache-Control': 'no-store, no-cache, must-revalidate',
        },
      })
    }
  } catch (error) {
    console.error('Error in catch-all audio API route:', error)
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
