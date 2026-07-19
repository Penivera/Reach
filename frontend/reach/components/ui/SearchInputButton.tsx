import { MagnifyingGlassIcon } from "@phosphor-icons/react"

interface SearchInputButtonType {
    placeholder: string;
    handleClick: () => void;
}

const SearchInputButton = ({ placeholder, handleClick }: SearchInputButtonType) => {
  return (
            <button
              type="button"
              onClick={handleClick}
              className="mb-8 flex w-full items-center gap-3 rounded-full border border-stroke bg-shade px-5 py-3 text-left shadow-sm transition-all duration-200 hover:shadow-md"
            >
              <MagnifyingGlassIcon size={18} className="shrink-0 text-muted-foreground" />
              <span className="truncate text-sm text-muted-foreground">
                {placeholder}
              </span>
            </button>
  )
}

export default SearchInputButton