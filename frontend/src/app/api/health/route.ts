import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
    })

    return NextResponse.json({ ok: response.ok }, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { ok: false, error: 'Health check failed' },
      { status: 500 }
    )
  }
}
