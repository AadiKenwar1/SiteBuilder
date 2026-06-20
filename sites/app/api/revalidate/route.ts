// On-demand ISR revalidation so an owner's save shows on their public page
// immediately instead of waiting out the 60s window. Revalidating a path only
// refreshes the cache (no data exposure), so this stays open.
import { NextResponse } from "next/server"
import { revalidatePath } from "next/cache"

export async function POST(request: Request) {
  const slug = new URL(request.url).searchParams.get("slug")
  if (!slug) {
    return NextResponse.json({ error: "slug required" }, { status: 400 })
  }
  revalidatePath(`/${slug}`)
  return NextResponse.json({ revalidated: true, slug })
}
