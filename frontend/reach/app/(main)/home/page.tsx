import { aroundYouItems, popularItems } from "@/data/mockData";
import { FeedSection } from "@/components/layout/FeedSection";
import CategorySection from "@/components/layout/CategorySection";



export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
        <header className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-primary">Reach</h1>
        </header>

        <CategorySection />
        <FeedSection title="Around you" items={aroundYouItems} />
        <FeedSection title="Popular" items={popularItems} />
      </div>
    </div>
  );
}