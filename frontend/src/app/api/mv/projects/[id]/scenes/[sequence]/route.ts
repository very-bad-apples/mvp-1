import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.API_KEY || ''

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string; sequence: string } }
) {
  try {
    const { id: projectId, sequence } = params
    const body = await request.json()

    const response = await fetch(
      `${BACKEND_URL}/api/mv/projects/${projectId}/scenes/${sequence}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify(body),
      }
    )

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to update scene' },
      { status: 500 }
    )
  }
}
