// Browser client (anon key) for the owner admin: magic-link auth, the
// update_business_content RPC, and photo uploads to Storage. Cookie-based session
// via @supabase/ssr; RLS + the security-definer RPC enforce that only the row's
// owner_email can write. Scoped to the cold_pitch schema.
import { createBrowserClient } from "@supabase/ssr"

export function supabaseBrowser() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { db: { schema: "cold_pitch" } },
  )
}
