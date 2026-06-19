// Server-only Supabase client using the SERVICE-ROLE key. Never import this from
// a client component — the service-role key bypasses RLS and must stay on the
// server. Scoped to the `cold_pitch` schema (see supabase/schema.sql).
import { createClient } from "@supabase/supabase-js"

function createAdmin() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) {
    throw new Error(
      "Supabase env missing: set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
    )
  }
  // Schema scoped to cold_pitch; the inferred return type carries that through.
  return createClient(url, key, {
    db: { schema: "cold_pitch" },
    auth: { persistSession: false, autoRefreshToken: false },
  })
}

let _admin: ReturnType<typeof createAdmin> | null = null

export function supabaseAdmin() {
  if (!_admin) _admin = createAdmin()
  return _admin
}
