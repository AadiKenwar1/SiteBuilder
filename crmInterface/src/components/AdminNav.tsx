"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutList, Radar, UserPlus } from "lucide-react"

const TABS = [
  { href: "/admin", label: "Leads", icon: LayoutList },
  { href: "/admin/scrape", label: "Scrape", icon: Radar },
  { href: "/admin/new", label: "Add lead", icon: UserPlus },
]

// Two-tab nav for the admin header (Leads / Scrape). Sits on the dark header bar.
export function AdminNav() {
  const pathname = usePathname()
  return (
    <nav className="flex items-center gap-1">
      {TABS.map(({ href, label, icon: Icon }) => {
        const active = href === "/admin" ? pathname === "/admin" : pathname.startsWith(href)
        return (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active
                ? "bg-background/15 text-background"
                : "text-background/60 hover:bg-background/10 hover:text-background"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        )
      })}
    </nav>
  )
}
