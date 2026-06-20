// Cookie-less anon client for PUBLIC reads. Using this (rather than the
// cookie-aware server client) keeps the [slug] page statically ISR-cacheable —
// reading request cookies would force dynamic rendering and defeat the cache.
import { createClient } from "@supabase/supabase-js"

export function supabaseAnon() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { db: { schema: "cold_pitch" }, auth: { persistSession: false } },
  )
}
