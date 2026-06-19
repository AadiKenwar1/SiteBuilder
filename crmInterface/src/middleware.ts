// Auth gate for the CRM only. Protects /admin (the dashboard) and /api (its data
// routes); everything else — the public business sites at /<slug>, the root
// redirect, static assets — is untouched and stays open to prospects.
import { createServerClient } from "@supabase/ssr"
import { NextResponse, type NextRequest } from "next/server"

export async function middleware(req: NextRequest) {
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

  const {
    data: { user },
  } = await supabase.auth.getUser()

  const { pathname } = req.nextUrl
  const isLogin = pathname === "/admin/login"

  if (!user && !isLogin) {
    // API calls get a clean 401; page navigations get sent to the login screen.
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 })
    }
    const url = req.nextUrl.clone()
    url.pathname = "/admin/login"
    url.searchParams.set("next", pathname)
    return NextResponse.redirect(url)
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
