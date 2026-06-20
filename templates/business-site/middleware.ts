// Standalone (ejected) site overlay. The whole app serves ONE business, so the
// domain root should show it. Rewrites "/" to "/<slug>" without changing the URL.
// `{{SLUG}}` is filled in by scripts/eject.mjs.
import { NextResponse, type NextRequest } from "next/server"

const SLUG = "{{SLUG}}"

export function middleware(req: NextRequest) {
  const url = req.nextUrl.clone()
  url.pathname = `/${SLUG}`
  return NextResponse.rewrite(url)
}

export const config = { matcher: ["/"] }
