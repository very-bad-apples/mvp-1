/**
 * API Routes for Individual Project Management
 *
 * GET /api/projects/[id] - Get a specific project
 * PATCH /api/projects/[id] - Update a project
 * DELETE /api/projects/[id] - Delete a project
 */

import { NextRequest, NextResponse } from 'next/server'
import { projectStore } from '@/lib/projectStore'
import { UpdateProjectRequest, UpdateProjectResponse, GetProjectResponse } from '@/types/project'

interface RouteContext {
  params: {
    id: string
  }
}

/**
 * GET /api/projects/[id]
 * Get a specific project by ID
 */
export async function GET(req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = params

    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Project ID is required', project: null },
        { status: 400 }
      )
    }

    const project = await projectStore.get(id)

    if (!project) {
      const response: GetProjectResponse = {
        success: false,
        error: 'Project not found',
        project: null,
      }
      return NextResponse.json(response, { status: 404 })
    }

    const response: GetProjectResponse = {
      success: true,
      project,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error(`[GET /api/projects/${params.id}] Error:`, error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch project',
        project: null,
      },
      { status: 500 }
    )
  }
}

/**
 * PATCH /api/projects/[id]
 * Update a project (partial update)
 */
export async function PATCH(req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = params

    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Project ID is required' },
        { status: 400 }
      )
    }

    const body = await req.json() as UpdateProjectRequest

    // Validate that at least one field is provided
    if (Object.keys(body).length === 0) {
      return NextResponse.json(
        { success: false, error: 'No update fields provided' },
        { status: 400 }
      )
    }

    // Update the project
    const updatedProject = await projectStore.update(id, body)

    if (!updatedProject) {
      return NextResponse.json(
        { success: false, error: 'Project not found' },
        { status: 404 }
      )
    }

    const response: UpdateProjectResponse = {
      success: true,
      project: updatedProject,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error(`[PATCH /api/projects/${params.id}] Error:`, error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update project',
      },
      { status: 500 }
    )
  }
}

/**
 * DELETE /api/projects/[id]
 * Delete a project
 */
export async function DELETE(req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = params

    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Project ID is required' },
        { status: 400 }
      )
    }

    const existed = await projectStore.delete(id)

    if (!existed) {
      return NextResponse.json(
        { success: false, error: 'Project not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({
      success: true,
      message: 'Project deleted successfully',
    })
  } catch (error) {
    console.error(`[DELETE /api/projects/${params.id}] Error:`, error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete project',
      },
      { status: 500 }
    )
  }
}
