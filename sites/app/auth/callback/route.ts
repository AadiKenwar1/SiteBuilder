// Magic-link callback: exchange the OTP code for a session cookie, then bounce to
// the page the owner was headed for (their /<slug>/admin).
import { NextResponse } from "next/server"
import { supabaseServer } from "@/lib/supabase.server"

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get("code")
  const next = searchParams.get("next") || "/"

  if (code) {
    const supabase = await supabaseServer()
    await supabase.auth.exchangeCodeForSession(code)
  }
  // Only allow same-app relative redirects.
  const dest = next.startsWith("/") ? next : "/"
  return NextResponse.redirect(`${origin}${dest}`)
}
