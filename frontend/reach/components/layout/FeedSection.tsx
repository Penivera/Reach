"use client"
import { FeedItem } from "@/types";
import FeedCard from "../ui/FeedCard";

export function FeedSection({ title, items }: { title: string; items: FeedItem[] }) {
  return (
    <section className="mb-10">
      <h2 className="mb-3 text-sm font-semibold text-foreground">{title}</h2>
      <div
        className="flex gap-3 overflow-x-auto pb-1 -mx-4 px-4
          md:mx-0 md:grid md:grid-cols-3 md:gap-4 md:overflow-visible md:px-0 md:pb-0
          lg:grid-cols-4
          scrollbar-none not-last-of-type:[&::-webkit-scrollbar]:hidden"
      >
        {items.map((item) => (
          <FeedCard
            key={item.id}
            imageSrc={item.imageSrc}
            imageAlt={item.title}
            title={item.title}
            subtitle={item.subtitle}
            price={item.price}
            className="w-55 shrink-0 md:w-full md:shrink"
            onClick={() => {
              // TODO: route to item detail page
            }}
          />
        ))}
      </div>
    </section>
  );
}