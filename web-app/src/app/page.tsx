import { HeroSection } from "@/components/blocks/galaxy-interactive-hero-section"
import { PageLoader } from "@/components/blocks/page-loader"

export default function Home() {
  return (
    <main className="bg-black relative min-h-screen w-full overflow-hidden">
      <PageLoader />
      <HeroSection />
    </main>
  );
}
