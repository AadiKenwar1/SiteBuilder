import type { NextConfig } from "next"
import fs from "fs"
import path from "path"

// Load the project-root .env so running `npm run dev` from crmInterface/ works
// without a separate .env.local. Vars already in process.env (e.g. Vercel
// dashboard) always take precedence — this is local-dev convenience only.
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

  // The CRM lives under /admin so business sites can own the clean root.
  async redirects() {
    return [{ source: "/", destination: "/admin", permanent: false }]
  },

  // Business sites are static files staged into public/<slug>/ by copy-sites.mjs.
  // A bare /janes-bakery should serve public/janes-bakery/index.html. `fallback`
  // runs only after routes and real static files miss, so /admin, /api, /photos,
  // /_next and direct asset hits (e.g. /janes-bakery/styles.css) are untouched.
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [{ source: "/:slug", destination: "/:slug/index.html" }],
    }
  },
}

export default nextConfig
