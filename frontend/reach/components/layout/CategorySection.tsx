"use client"
import Category from "../ui/Category"
import { useCategories } from "@/context/CategoriesContext"
import { useRouter } from "next/navigation"

const SKELETON_COUNT = 8;

const FALLBACK_CATEGORIES = [
  { id: 'f1', name: 'Food' },
  { id: 'f2', name: 'Fix' },
  { id: 'f3', name: 'Move' },
  { id: 'f4', name: 'Beauty' },
  { id: 'f5', name: 'Tutor' },
  { id: 'f6', name: 'Clean' },
  { id: 'f7', name: 'Trade' },
  { id: 'f8', name: 'More' },
];

const CategorySkeleton = ({ className = "" }: { className?: string }) => (
  <div className={`flex flex-col items-center gap-2 md:h-24 md:w-24 ${className}`}>
    <div className="h-12 w-12 rounded-full bg-shade animate-pulse" />
    <div className="h-3 w-10 rounded bg-shade animate-pulse" />
  </div>
);

const CategorySection = () => {
  const { categories, getCategoryIcon, loading } = useCategories();
  const router = useRouter();

  if (loading) {
    return (
      <section className="mb-10">
        <div className="grid grid-cols-4 gap-3 md:flex md:flex-wrap md:gap-4">
          {[...Array(SKELETON_COUNT)].map((_, i) => (
            <CategorySkeleton key={i} />
          ))}
        </div>
      </section>
    );
  }

  // const displayCategories = categories.length > 0 ? categories : FALLBACK_CATEGORIES;
  const displayCategories = categories.length > 0 
    ? [...categories.slice(0, 7), { id: 'btn-more', name: 'More' } as any] 
    : FALLBACK_CATEGORIES;

  return (
    <section className="mb-10">
      <div className="grid grid-cols-4 gap-3 md:flex md:flex-wrap md:gap-4">
        {displayCategories.map((category, index) => {
          const Icon = getCategoryIcon(category.name);
          const iconBgColor = index % 2 === 0 ? "#FFF1ED" : "#E6F4F4";

          return (
            <Category
              key={category.id}
              label={category.name}
              title={`View ${category.name} services`}
              icon={
                <div 
                  className="flex items-center justify-center shrink-0" 
                  style={{ 
                    width: '36px', 
                    height: '36px', 
                    borderRadius: '10px', 
                    backgroundColor: iconBgColor 
                  }}
                >
                  <Icon size={22} weight="regular" />
                </div>
              }
              onClick={() => {
                if (category.name === "More") {
                  router.push("?search=true");
                } else {
                  router.push(`?search=true&q=${encodeURIComponent(category.name)}`);
                }
              }}
              className="md:h-24 md:w-24"
            />
          );
        })}
      </div>
    </section>
  )
}

export default CategorySection