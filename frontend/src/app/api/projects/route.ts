/**
 * API Routes for Project Management
 *
 * POST /api/projects - Create a new project
 * GET /api/projects - Get all projects (optional status filter)
 */

import { NextRequest, NextResponse } from 'next/server'
import { projectStore } from '@/lib/projectStore'
import { CreateProjectRequest, CreateProjectResponse, Project } from '@/types/project'

/**
 * POST /api/projects
 * Create a new project
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as CreateProjectRequest

    // Validate required fields
    if (!body.projectId) {
      return NextResponse.json(
        { success: false, error: 'projectId is required' },
        { status: 400 }
      )
    }

    if (!body.mode || !['ad-creative', 'music-video'].includes(body.mode)) {
      return NextResponse.json(
        { success: false, error: 'Valid mode is required (ad-creative or music-video)' },
        { status: 400 }
      )
    }

    if (!body.idea || !body.idea.trim()) {
      return NextResponse.json(
        { success: false, error: 'idea is required' },
        { status: 400 }
      )
    }

    if (!body.scenes || !Array.isArray(body.scenes)) {
      return NextResponse.json(
        { success: false, error: 'scenes array is required' },
        { status: 400 }
      )
    }

    // Check if project already exists
    const exists = await projectStore.has(body.projectId)
    if (exists) {
      return NextResponse.json(
        { success: false, error: 'Project with this ID already exists' },
        { status: 409 }
      )
    }

    // Create project with proper initialization
    // NOTE: Since backend is not ready, projects start in 'creating-scenes' state
    // This is a terminal-like state that won't trigger polling loops
    const now = new Date().toISOString()
    const project: Project = {
      projectId: body.projectId,
      mode: body.mode,
      idea: body.idea,
      characterDescription: body.characterDescription || '',
      characterRefImage: body.characterRefImage || null,
      scenes: body.scenes.map((scene, index) => ({
        ...scene,
        id: scene.id ?? index + 1,
        status: 'pending',
        videoId: null,
        videoUrl: null,
        retryCount: 0,
      })),
      createdAt: now,
      updatedAt: now,
      status: 'creating-scenes', // Set to initial state, won't auto-process
      progress: 0,
      completedScenes: 0,
      failedScenes: 0,
    }

    // Save to storage
    await projectStore.set(project.projectId, project)

    const response: CreateProjectResponse = {
      success: true,
      projectId: project.projectId,
      project,
    }

    return NextResponse.json(response, { status: 201 })
  } catch (error) {
    console.error('[POST /api/projects] Error:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create project',
      },
      { status: 500 }
    )
  }
}

/**
 * GET /api/projects
 * Get all projects or filter by status
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const statusFilter = searchParams.get('status') as Project['status'] | null

    let projects: Project[]

    if (statusFilter) {
      projects = await projectStore.getByStatus(statusFilter)
    } else {
      projects = await projectStore.getAll()
    }

    // Sort by creation date (newest first)
    projects.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())

    return NextResponse.json({
      success: true,
      projects,
      count: projects.length,
    })
  } catch (error) {
    console.error('[GET /api/projects] Error:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch projects',
        projects: [],
      },
      { status: 500 }
    )
  }
}
