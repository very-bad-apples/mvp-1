import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, Video, Zap, CheckCircle } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <nav className="border-b border-gray-700/50 backdrop-blur-sm bg-gray-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Video className="h-8 w-8 text-blue-500" />
              <span className="text-xl font-bold text-white">AI Video Generator</span>
            </div>
            <div className="hidden md:flex items-center gap-6">
              <Link href="#features" className="text-gray-300 hover:text-white transition-colors">
                Features
              </Link>
              <Link href="#how-it-works" className="text-gray-300 hover:text-white transition-colors">
                How It Works
              </Link>
              <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
                Sign In
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 md:py-32">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 mb-8">
            <Sparkles className="h-4 w-4" />
            <span className="text-sm font-medium">AI-Powered Video Creation</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
            Create Stunning Videos
            <span className="block bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              In Minutes
            </span>
          </h1>

          <p className="text-xl text-gray-300 mb-10 max-w-2xl mx-auto">
            Transform your product images into professional video ads with AI.
            Upload your image, describe your vision, and let our AI do the rest.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/create">
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-6 text-lg w-full sm:w-auto">
                Start Creating Free
                <Zap className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="border-gray-600 text-white hover:bg-gray-800 px-8 py-6 text-lg">
              Watch Demo
            </Button>
          </div>

          <div className="mt-12 grid grid-cols-3 gap-8 max-w-2xl mx-auto">
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">30s</div>
              <div className="text-sm text-gray-400">Generation Time</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">$1.50</div>
              <div className="text-sm text-gray-400">Cost Per Video</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">9:16</div>
              <div className="text-sm text-gray-400">Vertical Format</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-white mb-4">
            Everything You Need
          </h2>
          <p className="text-xl text-gray-400">
            Powerful features to create professional video ads
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4">
                <Sparkles className="h-6 w-6 text-blue-400" />
              </div>
              <CardTitle className="text-white">AI Script Generation</CardTitle>
              <CardDescription className="text-gray-400">
                Our AI analyzes your product and creates engaging scripts automatically
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 rounded-lg bg-purple-500/10 flex items-center justify-center mb-4">
                <Video className="h-6 w-6 text-purple-400" />
              </div>
              <CardTitle className="text-white">Video Scene Generation</CardTitle>
              <CardDescription className="text-gray-400">
                Generate multiple video scenes with AI, perfectly synced with your message
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 rounded-lg bg-green-500/10 flex items-center justify-center mb-4">
                <Zap className="h-6 w-6 text-green-400" />
              </div>
              <CardTitle className="text-white">Professional Voiceover</CardTitle>
              <CardDescription className="text-gray-400">
                High-quality AI voiceovers that bring your video to life
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-white mb-4">
            How It Works
          </h2>
          <p className="text-xl text-gray-400">
            Create professional videos in three simple steps
          </p>
        </div>

        <div className="max-w-3xl mx-auto space-y-8">
          <div className="flex gap-6 items-start">
            <div className="flex-shrink-0 h-12 w-12 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-xl">
              1
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-white mb-2">Upload Your Product</h3>
              <p className="text-gray-400">
                Upload a product image and tell us what your ad should communicate.
                Choose from different styles like luxury, energetic, or professional.
              </p>
            </div>
          </div>

          <div className="flex gap-6 items-start">
            <div className="flex-shrink-0 h-12 w-12 rounded-full bg-purple-500 flex items-center justify-center text-white font-bold text-xl">
              2
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-white mb-2">AI Creates Your Video</h3>
              <p className="text-gray-400">
                Our AI generates a script, creates video scenes, adds professional voiceover,
                and assembles everything into a polished 30-second ad.
              </p>
            </div>
          </div>

          <div className="flex gap-6 items-start">
            <div className="flex-shrink-0 h-12 w-12 rounded-full bg-green-500 flex items-center justify-center text-white font-bold text-xl">
              3
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-white mb-2">Download and Share</h3>
              <p className="text-gray-400">
                Preview your video, make any final adjustments, and download it ready
                to share on social media or your marketing channels.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <Card className="bg-gradient-to-r from-blue-600 to-purple-600 border-0 max-w-4xl mx-auto">
          <CardHeader className="text-center py-12">
            <CardTitle className="text-4xl font-bold text-white mb-4">
              Ready to Create Your First Video?
            </CardTitle>
            <CardDescription className="text-xl text-blue-100 mb-8">
              Join thousands of creators using AI to produce professional video ads
            </CardDescription>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/create">
                <Button size="lg" className="bg-white text-blue-600 hover:bg-gray-100 px-8 py-6 text-lg font-semibold w-full sm:w-auto">
                  Get Started for Free
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 px-8 py-6 text-lg">
                Contact Sales
              </Button>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-6 mt-8 text-white/90">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                <span>7 minutes average time</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                <span>Professional quality</span>
              </div>
            </div>
          </CardHeader>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-700/50 mt-20">
        <div className="container mx-auto px-4 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <Video className="h-6 w-6 text-blue-500" />
                <span className="font-bold text-white">AI Video Generator</span>
              </div>
              <p className="text-gray-400 text-sm">
                Create professional video ads with AI in minutes.
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li><Link href="#" className="hover:text-white transition-colors">Features</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Pricing</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Examples</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">Company</h4>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li><Link href="#" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Blog</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Contact</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li><Link href="#" className="hover:text-white transition-colors">Privacy</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Terms</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Security</Link></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-700/50 mt-8 pt-8 text-center text-gray-400 text-sm">
            <p>&copy; 2024 AI Video Generator. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
