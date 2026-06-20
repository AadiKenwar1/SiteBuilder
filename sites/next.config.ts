import type { NextConfig } from "next"
import fs from "fs"
import path from "path"

// Load the project-root .env so `npm run dev` works locally without a separate
// .env.local. Vars already in process.env (e.g. the Vercel dashboard) always win.
// NOTE: sites/ uses the ANON key only — never the service role.
function loadRootEnv() {
  const envPath = path.resolve(process.cwd(), "../.env")
  if (!fs.existsSync(envPath)) return
  for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue
    const eq = trimmed.indexOf("=")
    const k = trimmed.slice(0, eq).trim()
    const v = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, "")
    if (!(k in process.env)) process.env[k] = v
  }
}

loadRootEnv()

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },

  // Alias root-env names (no framework prefix) → what the browser client expects.
  // On Vercel, set SUPABASE_URL / SUPABASE_ANON_KEY in the project dashboard.
  env: {
    NEXT_PUBLIC_SUPABASE_URL:
      process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY:
      process.env.SUPABASE_ANON_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
}

export default nextConfig
