// Auth gate for the CRM only. Protects /admin (the dashboard) and /api (its data
// routes); everything else — the public business sites at /<slug>, the root
// redirect, static assets — is untouched and stays open to prospects.
import { createServerClient } from "@supabase/ssr"
import { NextResponse, type NextRequest } from "next/server"

// Sends a logged-out request where it belongs: a clean 401 for API calls, the
// login screen (with a return path) for page navigations.
function rejectLoggedOut(req: NextRequest): NextResponse {
  const { pathname } = req.nextUrl
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  }
  const url = req.nextUrl.clone()
  url.pathname = "/admin/login"
  url.searchParams.set("next", pathname)
  return NextResponse.redirect(url)
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const isLogin = pathname === "/admin/login"

  // Fast path: no Supabase auth cookie means the request is definitely logged
  // out, so skip the auth check entirely (it ran on every request before).
  const hasAuthCookie = req.cookies
    .getAll()
    .some((c) => c.name.startsWith("sb-") && c.name.includes("auth-token"))
  if (!hasAuthCookie) {
    return isLogin ? NextResponse.next({ request: req }) : rejectLoggedOut(req)
  }

  const res = NextResponse.next({ request: req })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return req.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => res.cookies.set(name, value, options))
        },
      },
    },
  )

  // getClaims() verifies the JWT locally when the project uses asymmetric
  // signing keys — no network round-trip per request like getUser() did. (With
  // legacy HS256 secrets it falls back to a getUser call, so this never regresses.)
  const { data } = await supabase.auth.getClaims()
  const user = data?.claims ?? null

  if (!user && !isLogin) {
    // Cookie present but invalid/expired (e.g. signed out elsewhere).
    return rejectLoggedOut(req)
  }

  if (user && isLogin) {
    const url = req.nextUrl.clone()
    url.pathname = "/admin"
    url.search = ""
    return NextResponse.redirect(url)
  }

  return res
}

export const config = {
  matcher: ["/admin/:path*", "/api/:path*"],
}
