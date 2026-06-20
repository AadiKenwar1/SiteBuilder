// Design registry: slug -> the bespoke design module for that business.
//
// Each entry is a static dynamic-import so the bundler can code-split it. A new
// business falls back to the reference design until Claude writes a bespoke one
// and registers it here (promote.py appends the entry; see CLAUDE.md).
import type { ComponentType } from "react"
import type { BusinessContent } from "./content"

export type DesignProps = { content: BusinessContent }
type DesignModule = { default: ComponentType<DesignProps> }
type DesignLoader = () => Promise<DesignModule>

const registry: Record<string, DesignLoader> = {
  _reference: () => import("@/designs/_reference"),
  // <promote.py inserts: "<slug>": () => import("@/designs/<slug>"), >
}

export function getDesignLoader(slug: string): DesignLoader {
  return registry[slug] ?? registry._reference
}
