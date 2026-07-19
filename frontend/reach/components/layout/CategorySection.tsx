"use client"
import Category from "../ui/Category"
import { useCategories } from "@/context/CategoriesContext"

const CategorySection = () => {
  const { categories, getCategoryIcon, loading } = useCategories();

  if (loading) {
    return (
      <section className="mb-10 flex items-center justify-center h-24">
        <p className="text-sm text-muted-foreground animate-pulse">Loading categories...</p>
      </section>
    );
  }

  return (
    <section className="mb-10">
      <div className="grid grid-cols-4 gap-3 md:flex md:flex-wrap md:gap-4">
        {categories.map((category) => {
          // React requires components to start with a capital letter
          const Icon = getCategoryIcon(category.name);

          return (
            <Category
              key={category.id}
              label={category.name}
              title={`View ${category.name} services`}
              icon={<Icon size={22} weight="regular" />}
              onClick={() => {
                // TODO: route to category filter
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