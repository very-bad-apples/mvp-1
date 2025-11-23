'use client'

import { useState, useMemo } from 'react'
import { Image, Film, Music, Download, Share2, X, ChevronLeft, ChevronRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Asset, AssetFilter, AssetGalleryProps } from '@/types/asset'

/**
 * AssetGallery Component
 * Displays project assets (images, videos, lipsync videos) in a responsive grid
 * with filtering, lightbox preview, and download/share functionality
 */
export function AssetGallery({
  scenes = [],
  characterReferenceImageId,
  isLoading = false,
  error = null,
  className = '',
}: AssetGalleryProps) {
  const [filter, setFilter] = useState<AssetFilter>('all')
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)
  const [lightboxOpen, setLightboxOpen] = useState(false)

  // Convert project data to Asset objects
  const assets = useMemo(() => {
    const assetList: Asset[] = []

    // Add character reference image
    if (characterReferenceImageId) {
      const imageUrl = characterReferenceImageId.startsWith('http')
        ? characterReferenceImageId
        : `/api/mv/get_character_reference/${characterReferenceImageId}`

      assetList.push({
        id: `character-${characterReferenceImageId}`,
        type: 'character',
        url: imageUrl,
        description: 'Character Reference',
      })
    }

    // Add scene videos
    scenes.forEach((scene) => {
      if (scene.videoClipUrl && scene.status === 'completed') {
        // Check if this is a lip-synced video (simple heuristic)
        const isLipSynced = scene.videoClipUrl.includes('lipsync') || scene.videoClipUrl.includes('lip-sync')

        assetList.push({
          id: `scene-${scene.sequence}`,
          type: isLipSynced ? 'lipsync' : 'video',
          url: scene.videoClipUrl,
          description: scene.prompt,
          sceneSequence: scene.sequence,
          metadata: {
            isLipSynced,
          },
        })
      }
    })

    return assetList
  }, [scenes, characterReferenceImageId])

  // Filter assets based on selected filter
  const filteredAssets = useMemo(() => {
    if (filter === 'all') return assets
    return assets.filter((asset) => asset.type === filter)
  }, [assets, filter])

  // Count assets by type
  const assetCounts = useMemo(() => {
    return {
      all: assets.length,
      image: assets.filter((a) => a.type === 'image').length,
      video: assets.filter((a) => a.type === 'video').length,
      lipsync: assets.filter((a) => a.type === 'lipsync').length,
      character: assets.filter((a) => a.type === 'character').length,
    }
  }, [assets])

  // Handle asset click to open lightbox
  const handleAssetClick = (asset: Asset) => {
    setSelectedAsset(asset)
    setLightboxOpen(true)
  }

  // Navigate to previous/next asset in lightbox
  const navigateLightbox = (direction: 'prev' | 'next') => {
    if (!selectedAsset) return

    const currentIndex = filteredAssets.findIndex((a) => a.id === selectedAsset.id)
    let newIndex = direction === 'prev' ? currentIndex - 1 : currentIndex + 1

    // Wrap around
    if (newIndex < 0) newIndex = filteredAssets.length - 1
    if (newIndex >= filteredAssets.length) newIndex = 0

    setSelectedAsset(filteredAssets[newIndex])
  }

  // Download asset
  const handleDownload = async (asset: Asset) => {
    try {
      const response = await fetch(asset.url)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${asset.type}-${asset.id}.${asset.type === 'character' ? 'png' : 'mp4'}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

  // Share asset
  const handleShare = async (asset: Asset) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: asset.description || 'Asset',
          text: `Check out this ${asset.type}`,
          url: asset.url,
        })
      } catch (error) {
        console.error('Share failed:', error)
      }
    } else {
      // Fallback: copy to clipboard
      try {
        await navigator.clipboard.writeText(asset.url)
        alert('Link copied to clipboard!')
      } catch (error) {
        console.error('Copy to clipboard failed:', error)
      }
    }
  }

  // If no assets exist
  if (!isLoading && assets.length === 0) {
    return null
  }

  return (
    <div className={`bg-gray-800/50 border border-gray-700 rounded-lg p-6 ${className}`}>
      <div className="flex items-center gap-2 mb-6">
        <Image className="w-5 h-5 text-blue-400" />
        <h2 className="text-xl font-semibold text-white">Assets</h2>
        {!isLoading && (
          <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20 ml-auto">
            {filteredAssets.length} {filter === 'all' ? 'Total' : filter}
          </Badge>
        )}
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Filter Tabs */}
      <Tabs value={filter} onValueChange={(value) => setFilter(value as AssetFilter)} className="mb-6">
        <TabsList className="bg-gray-900/50 border border-gray-700">
          <TabsTrigger value="all" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            All ({assetCounts.all})
          </TabsTrigger>
          {assetCounts.character > 0 && (
            <TabsTrigger value="character" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
              <Image className="w-4 h-4 mr-1" />
              Character ({assetCounts.character})
            </TabsTrigger>
          )}
          {assetCounts.video > 0 && (
            <TabsTrigger value="video" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
              <Film className="w-4 h-4 mr-1" />
              Videos ({assetCounts.video})
            </TabsTrigger>
          )}
          {assetCounts.lipsync > 0 && (
            <TabsTrigger value="lipsync" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
              <Music className="w-4 h-4 mr-1" />
              Lip-sync ({assetCounts.lipsync})
            </TabsTrigger>
          )}
        </TabsList>
      </Tabs>

      {/* Loading State */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="aspect-square rounded-lg" />
          ))}
        </div>
      ) : (
        /* Asset Grid */
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {filteredAssets.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onClick={() => handleAssetClick(asset)}
              onDownload={() => handleDownload(asset)}
              onShare={() => handleShare(asset)}
            />
          ))}
        </div>
      )}

      {/* Lightbox Dialog */}
      <AssetLightbox
        asset={selectedAsset}
        isOpen={lightboxOpen}
        onClose={() => {
          setLightboxOpen(false)
          setSelectedAsset(null)
        }}
        onPrevious={() => navigateLightbox('prev')}
        onNext={() => navigateLightbox('next')}
        onDownload={handleDownload}
        onShare={handleShare}
        hasMultiple={filteredAssets.length > 1}
      />
    </div>
  )
}

/**
 * AssetCard Component
 * Individual asset card in the grid
 */
interface AssetCardProps {
  asset: Asset
  onClick: () => void
  onDownload: () => void
  onShare: () => void
}

function AssetCard({ asset, onClick, onDownload, onShare }: AssetCardProps) {
  const isVideo = asset.type === 'video' || asset.type === 'lipsync'

  return (
    <Card className="group relative aspect-square overflow-hidden border-gray-700 bg-gray-800/50 hover:border-blue-500/50 transition-all cursor-pointer">
      <div onClick={onClick} className="w-full h-full">
        {isVideo ? (
          <video
            src={asset.url}
            className="object-cover w-full h-full group-hover:scale-110 transition-transform duration-300"
            muted
            loop
            playsInline
            onMouseEnter={(e) => e.currentTarget.play()}
            onMouseLeave={(e) => {
              e.currentTarget.pause()
              e.currentTarget.currentTime = 0
            }}
          />
        ) : (
          <img
            src={asset.url}
            alt={asset.description || asset.type}
            className="object-cover w-full h-full group-hover:scale-110 transition-transform duration-300"
          />
        )}
      </div>

      {/* Overlay with info and actions */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/0 to-black/0 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="absolute top-2 right-2 flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0 bg-gray-900/80 hover:bg-gray-900 text-white"
            onClick={(e) => {
              e.stopPropagation()
              onDownload()
            }}
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0 bg-gray-900/80 hover:bg-gray-900 text-white"
            onClick={(e) => {
              e.stopPropagation()
              onShare()
            }}
          >
            <Share2 className="h-4 w-4" />
          </Button>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-2">
          <div className="flex items-center gap-2">
            <Badge className="bg-gray-900/80 text-white border-gray-700 text-xs capitalize">
              {asset.type === 'lipsync' ? 'Lip-sync' : asset.type}
            </Badge>
            {asset.sceneSequence && (
              <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/20 text-xs">
                Scene {asset.sceneSequence}
              </Badge>
            )}
          </div>
          {asset.description && (
            <p className="text-white text-xs mt-1 line-clamp-1">{asset.description}</p>
          )}
        </div>
      </div>

      {/* Type indicator */}
      <div className="absolute top-2 left-2">
        {isVideo ? (
          <div className="bg-gray-900/80 p-1.5 rounded-full">
            <Film className="h-4 w-4 text-blue-400" />
          </div>
        ) : (
          <div className="bg-gray-900/80 p-1.5 rounded-full">
            <Image className="h-4 w-4 text-blue-400" />
          </div>
        )}
      </div>
    </Card>
  )
}

/**
 * AssetLightbox Component
 * Full-screen preview dialog for assets
 */
interface AssetLightboxProps {
  asset: Asset | null
  isOpen: boolean
  onClose: () => void
  onPrevious: () => void
  onNext: () => void
  onDownload: (asset: Asset) => void
  onShare: (asset: Asset) => void
  hasMultiple: boolean
}

function AssetLightbox({
  asset,
  isOpen,
  onClose,
  onPrevious,
  onNext,
  onDownload,
  onShare,
  hasMultiple,
}: AssetLightboxProps) {
  if (!asset) return null

  const isVideo = asset.type === 'video' || asset.type === 'lipsync'

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl bg-gray-900 border-gray-700 p-0">
        {/* Header */}
        <DialogHeader className="p-6 pb-0">
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="text-white text-xl">
                {asset.description || `${asset.type} Preview`}
              </DialogTitle>
              <DialogDescription className="text-gray-400 mt-1">
                <Badge className="bg-gray-800 text-gray-300 border-gray-700 capitalize">
                  {asset.type === 'lipsync' ? 'Lip-sync Video' : asset.type}
                </Badge>
                {asset.sceneSequence && (
                  <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/20 ml-2">
                    Scene {asset.sceneSequence}
                  </Badge>
                )}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Media content */}
        <div className="relative bg-black">
          {isVideo ? (
            <video
              src={asset.url}
              controls
              autoPlay
              className="w-full max-h-[70vh] object-contain"
            />
          ) : (
            <img
              src={asset.url}
              alt={asset.description || asset.type}
              className="w-full max-h-[70vh] object-contain"
            />
          )}

          {/* Navigation buttons */}
          {hasMultiple && (
            <>
              <Button
                size="lg"
                variant="ghost"
                className="absolute left-4 top-1/2 -translate-y-1/2 bg-gray-900/80 hover:bg-gray-900 text-white h-12 w-12 p-0 rounded-full"
                onClick={onPrevious}
              >
                <ChevronLeft className="h-6 w-6" />
              </Button>
              <Button
                size="lg"
                variant="ghost"
                className="absolute right-4 top-1/2 -translate-y-1/2 bg-gray-900/80 hover:bg-gray-900 text-white h-12 w-12 p-0 rounded-full"
                onClick={onNext}
              >
                <ChevronRight className="h-6 w-6" />
              </Button>
            </>
          )}
        </div>

        {/* Actions footer */}
        <div className="p-6 flex items-center justify-between border-t border-gray-700">
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="border-gray-700 text-gray-300 hover:bg-gray-800"
              onClick={() => onDownload(asset)}
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button
              variant="outline"
              className="border-gray-700 text-gray-300 hover:bg-gray-800"
              onClick={() => onShare(asset)}
            >
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
          </div>
          <Button
            variant="ghost"
            className="text-gray-400 hover:text-white"
            onClick={onClose}
          >
            <X className="h-4 w-4 mr-2" />
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
