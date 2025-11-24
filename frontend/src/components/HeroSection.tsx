import { Button } from '@/components/ui/button'
import { Play, Sparkles } from 'lucide-react'
import Link from 'next/link'

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Background gradient effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-[600px] h-[600px] rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute top-1/3 -right-1/4 w-[500px] h-[500px] rounded-full bg-purple-500/5 blur-3xl" />
      </div>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center py-12 lg:py-20">
          {/* Left Column - Content */}
          <div className="space-y-8 text-center lg:text-left">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-sm text-blue-400">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>AI-Powered Video Generation</span>
            </div>

            {/* Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-balance">
              <span className="text-white">Create </span>
              <span className="bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                video ads & music videos
              </span>
              <span className="text-white"> with AI</span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg sm:text-xl text-gray-300 leading-relaxed text-pretty max-w-2xl mx-auto lg:mx-0">
              Generate professional video advertisements and music videos from your images and audio.
              AI-powered scene generation, voiceovers, and seamless composition—no editing skills required.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link href="/create">
                <Button
                  size="lg"
                  className="text-base px-8 h-12 bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto"
                >
                  Generate Video
                  <Sparkles className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Button
                size="lg"
                variant="outline"
                className="text-base px-8 h-12 border-gray-600 bg-gray-800/50 hover:bg-gray-800 text-white"
              >
                <Play className="mr-2 w-5 h-5" />
                Watch Demo
              </Button>
            </div>

            {/* Social proof */}
            <div className="pt-8">
              <p className="text-sm text-gray-400 mb-4">Perfect for</p>
              <div className="flex flex-wrap gap-6 items-center justify-center lg:justify-start opacity-80">
                <div className="text-base font-medium text-white">🎵 Musicians</div>
                <div className="text-base font-medium text-white">📱 Content Creators</div>
                <div className="text-base font-medium text-white">🛍️ E-commerce</div>
                <div className="text-base font-medium text-white">📢 Marketers</div>
              </div>
            </div>
          </div>

          {/* Right Column - Hero Image/Video Preview */}
          <div className="relative">
            <div className="relative aspect-[4/3] rounded-2xl overflow-hidden border border-gray-700/50 bg-gray-800/50 backdrop-blur-sm shadow-2xl">
              {/* Placeholder gradient background */}
              <div className="w-full h-full bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20 flex items-center justify-center">
                <div className="text-center space-y-4">
                  <div className="text-6xl">🎬</div>
                  <p className="text-gray-300 text-lg font-medium">Demo Video Preview</p>
                </div>
              </div>

              {/* Play button overlay */}
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/20 backdrop-blur-[2px] group hover:bg-gray-900/30 transition-colors cursor-pointer">
                <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg">
                  <Play className="w-10 h-10 text-gray-900 ml-1" fill="currentColor" />
                </div>
              </div>
            </div>

            {/* Floating stats cards */}
            <div className="absolute -bottom-6 -left-6 bg-gray-800 border border-gray-700 rounded-xl px-6 py-4 shadow-xl hidden lg:block">
              <div className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">AI-Powered</div>
              <div className="text-sm text-gray-400">Scene Generation</div>
            </div>

            <div className="absolute -top-6 -right-6 bg-gray-800 border border-gray-700 rounded-xl px-6 py-4 shadow-xl hidden lg:block">
              <div className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">Minutes</div>
              <div className="text-sm text-gray-400">Not Hours</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
