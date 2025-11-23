import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.API_KEY || ''

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId

    const response = await fetch(`${BACKEND_URL}/api/mv/get_video/${videoId}`, {
      method: 'GET',
      headers: {
        'X-API-Key': API_KEY,
      },
    })

    // Stream the video response
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch video' },
        { status: response.status }
      )
    }

    // Pass through video content with appropriate headers
    const blob = await response.blob()
    return new NextResponse(blob, {
      status: 200,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'video/mp4',
        'Content-Length': response.headers.get('Content-Length') || '',
      },
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch video' },
      { status: 500 }
    )
  }
}
