import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.API_KEY || ''

export async function GET(request: NextRequest) {
  try {
    console.log(`[Proxy] Fetching director configs from: ${BACKEND_URL}/api/mv/get_director_configs`)

    const response = await fetch(`${BACKEND_URL}/api/mv/get_director_configs`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
    })

    console.log(`[Proxy] Backend response status: ${response.status}`)

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('[Proxy] Error fetching director configs:', error)
    return NextResponse.json(
      { error: 'Failed to fetch director configs', details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    )
  }
}
