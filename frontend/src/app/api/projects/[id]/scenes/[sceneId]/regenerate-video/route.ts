/**
 * API Route for Scene Video Regeneration
 *
 * POST /api/projects/[id]/scenes/[sceneId]/regenerate-video
 */

import { NextRequest, NextResponse } from 'next/server'
import { projectStore } from '@/lib/projectStore'

interface RouteContext {
  params: {
    id: string
    sceneId: string
  }
}

/**
 * POST /api/projects/[id]/scenes/[sceneId]/regenerate-video
 * Regenerate the video for a specific scene
 */
export async function POST(req: NextRequest, { params }: RouteContext) {
  try {
    const { id, sceneId } = params

    if (!id || !sceneId) {
      return NextResponse.json(
        { success: false, error: 'Project ID and Scene ID are required' },
        { status: 400 }
      )
    }

    const sceneIdNum = parseInt(sceneId, 10)
    if (isNaN(sceneIdNum)) {
      return NextResponse.json(
        { success: false, error: 'Invalid Scene ID' },
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

    // Find the scene
    const sceneIndex = project.scenes.findIndex(s => s.id === sceneIdNum)
    if (sceneIndex === -1) {
      return NextResponse.json(
        { success: false, error: 'Scene not found' },
        { status: 404 }
      )
    }

    // Update scene status to regenerating
    const updatedScenes = [...project.scenes]
    updatedScenes[sceneIndex] = {
      ...updatedScenes[sceneIndex],
      status: 'generating',
      retryCount: (updatedScenes[sceneIndex].retryCount || 0) + 1,
    }

    const updatedProject = await projectStore.update(id, {
      scenes: updatedScenes,
    })

    if (!updatedProject) {
      return NextResponse.json(
        { success: false, error: 'Failed to update scene status' },
        { status: 500 }
      )
    }

    // TODO: Trigger backend video regeneration
    // const backendUrl = process.env.NEXT_PUBLIC_API_URL
    // const scene = updatedScenes[sceneIndex]
    // await fetch(`${backendUrl}/api/mv/generate_video`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     prompt: scene.prompt,
    //     negative_prompt: scene.negativePrompt,
    //     reference_image_base64: project.characterRefImage,
    //   }),
    // })

    return NextResponse.json({
      success: true,
      message: 'Video regeneration started',
      scene: updatedScenes[sceneIndex],
    })
  } catch (error) {
    console.error(
      `[POST /api/projects/${params.id}/scenes/${params.sceneId}/regenerate-video] Error:`,
      error
    )
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to regenerate video',
      },
      { status: 500 }
    )
  }
}
