import { HeroSection } from "@/components/HeroSection";
import { Logo } from "@/components/Logo";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <nav className="absolute top-0 left-0 right-0 z-50">
        <div className="container mx-auto px-4 py-6">
          <Link href="/" className="flex items-center gap-3 w-fit">
            <Logo size="sm" className="text-blue-500" />
            <span className="text-2xl font-bold text-white">Bad Apple</span>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <HeroSection />
    </div>
  );
}
