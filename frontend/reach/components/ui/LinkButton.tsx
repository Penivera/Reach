"use client"
import Link from "next/link"

interface LinkButtonType {
  href: string;
  label: string;
}

const LinkButton = ({href, label}: LinkButtonType) => {
  return (
    <Link 
      href={href}
      className="shrink-0 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-transform hover:scale-105 active:scale-95"
    >
      {label}
    </Link>
  )
}

export default LinkButton