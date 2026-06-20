// Cookie-aware anon client for AUTH'd flows only (the owner admin + auth
// callback). Carries the magic-link session via cookies. All public page reads
// use supabase.anon.ts instead, to stay statically cacheable.
import { createServerClient } from "@supabase/ssr"
import { cookies } from "next/headers"

export async function supabaseServer() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      db: { schema: "cold_pitch" },
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            )
          } catch {
            // setAll from a Server Component is a no-op; middleware/route handlers refresh.
          }
        },
      },
    },
  )
}
