import Link from "next/link"
import type { ReactNode } from "react"

// Shared chrome wrapped around every business design. Intentionally minimal: the
// design carries the page; the shell only adds a discreet "Owner login" link that
// routes to this business's admin panel.
export function Shell({ slug, children }: { slug: string; children: ReactNode }) {
  return (
    <>
      {children}
      <div className="w-full border-t border-black/10 bg-white py-3 text-center text-xs text-black/40">
        <Link
          href={`/${slug}/admin`}
          className="underline-offset-2 hover:text-black/70 hover:underline"
        >
          Owner login
        </Link>
      </div>
    </>
  )
}
