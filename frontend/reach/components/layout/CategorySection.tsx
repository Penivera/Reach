"use client"
import Category from "../ui/Category"
import { useCategories } from "@/context/CategoriesContext"

const SKELETON_COUNT = 8;

const CategorySkeleton = ({ className = "" }: { className?: string }) => (
  <div className={`flex flex-col items-center gap-2 md:h-24 md:w-24 ${className}`}>
    <div className="h-12 w-12 rounded-full bg-shade animate-pulse" />
    <div className="h-3 w-10 rounded bg-shade animate-pulse" />
  </div>
);

const CategorySection = () => {
  const { categories, getCategoryIcon, loading } = useCategories();

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

  return (
    <section className="mb-10">
      <div className="grid grid-cols-4 gap-3 md:flex md:flex-wrap md:gap-4">
        {categories.map((category) => {
          const Icon = getCategoryIcon(category.name);
          return (
            <Category
              key={category.id}
              label={category.name}
              title={`View ${category.name} services`}
              icon={<Icon size={22} weight="regular" />}
              onClick={() => {
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