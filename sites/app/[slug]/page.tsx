import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { getContent } from "@/lib/content"
import { getDesignLoader } from "@/lib/designs"
import { Shell } from "@/components/Shell"

// ISR: cache the rendered page, refresh at most once a minute so owner edits show
// within ~60s without a redeploy. No generateStaticParams → new slugs render
// on-demand (no build-time DB dependency).
export const revalidate = 60

type Params = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params
  const content = await getContent(slug)
  if (!content) return { title: "Not found" }

  // Previews are hidden from search; a handed-off ('active') site is indexable.
  const noindex = content.site_status !== "active"
  return {
    title: content.business_name || "Business",
    description: content.about ? content.about.slice(0, 155) : undefined,
    robots: noindex ? { index: false, follow: false } : undefined,
  }
}

export default async function SitePage({ params }: Params) {
  const { slug } = await params
  const content = await getContent(slug)
  if (!content) notFound()

  const { default: Design } = await getDesignLoader(slug)()
  return (
    <Shell slug={slug}>
      <Design content={content} />
    </Shell>
  )
}
