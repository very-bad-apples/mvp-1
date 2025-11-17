/**
 * API Route for Project Generation Orchestration
 *
 * POST /api/projects/[id]/generate - Start full generation pipeline
 */

import { NextRequest, NextResponse } from 'next/server'
import { projectStore } from '@/lib/projectStore'

interface RouteContext {
  params: {
    id: string
  }
}

/**
 * POST /api/projects/[id]/generate
 * Start the full generation pipeline for a project
 */
export async function POST(req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = params

    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Project ID is required' },
        { status: 400 }
      )
    }

    // Get the project
    const project = await projectStore.get(id)

    if (!project) {
      return NextResponse.json(
        { success: false, error: 'Project not found' },
        { status: 404 }
      )
    }

    // Check if project is in a valid state to start generation
    if (project.status !== 'creating-scenes' && project.status !== 'error') {
      return NextResponse.json(
        {
          success: false,
          error: 'Project is not in a valid state to start generation',
          details: `Current status: ${project.status}`,
        },
        { status: 400 }
      )
    }

    // Update project status to start generation
    const updatedProject = await projectStore.update(id, {
      status: 'generating-images',
      progress: 0,
    })

    if (!updatedProject) {
      return NextResponse.json(
        { success: false, error: 'Failed to update project status' },
        { status: 500 }
      )
    }

    // TODO: Trigger backend orchestration
    // This would typically:
    // 1. Queue a background job for the generation pipeline
    // 2. Call the backend orchestrator service
    // 3. Return immediately while processing continues in background
    //
    // Example:
    // const backendUrl = process.env.NEXT_PUBLIC_API_URL
    // await fetch(`${backendUrl}/api/projects/${id}/start-pipeline`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ projectId: id }),
    // })

    return NextResponse.json({
      success: true,
      message: 'Generation started successfully',
      project: updatedProject,
    })
  } catch (error) {
    console.error(`[POST /api/projects/${params.id}/generate] Error:`, error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to start generation',
      },
      { status: 500 }
    )
  }
}
