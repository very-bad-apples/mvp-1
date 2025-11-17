import { Suspense } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { ProjectPageClient } from './ProjectPageClient'

interface ProjectPageProps {
  params: Promise<{ id: string }>
}

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-linear-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Skeleton className="w-8 h-8 rounded-lg" />
              <Skeleton className="w-40 h-6" />
            </div>
            <Skeleton className="w-24 h-10 rounded-md" />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 space-y-8">
        {/* Project Header */}
        <div className="space-y-4">
          <Skeleton className="w-3/4 h-10" />
          <Skeleton className="w-40 h-5" />
        </div>

        {/* Phase Tracker */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6">
          <Skeleton className="w-32 h-6 mb-6" />
          <div className="flex items-center gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="w-12 h-12 rounded-full" />
            ))}
          </div>
        </div>

        {/* Scenes Grid */}
        <div>
          <Skeleton className="w-32 h-6 mb-4" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-64 rounded-lg" />
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}

export default async function ProjectPage({ params }: ProjectPageProps) {
  const { id } = await params

  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <ProjectPageClient projectId={id} />
    </Suspense>
  )
}
