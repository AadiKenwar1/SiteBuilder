#!/usr/bin/env node
// Eject one business site from the shared `sites/` app into a standalone Next app
// for handoff (Vercel Claim Deployments). The standalone is derived from `sites/`
// (no separate copy to maintain) + the templates/business-site overlay, pruned to
// the one business. It uses the ANON key ONLY — never the service-role key, which
// a Vercel Claim would transfer to the customer.
//
// Usage:
//   node scripts/eject.mjs <slug> [--deploy]
//
// Builds .eject/<slug>/ ; with --deploy and the Vercel CLI installed/authed, also
// runs `vercel deploy --prod`. Prints the follow-up manual steps either way.
import fs from "fs"
import path from "path"
import { fileURLToPath } from "url"
import { execSync } from "child_process"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, "..")
const SITES = path.join(ROOT, "sites")
const OVERLAY = path.join(ROOT, "templates", "business-site")

const slug = process.argv[2]
const doDeploy = process.argv.includes("--deploy")

if (!slug || slug.startsWith("--")) {
  console.error("usage: node scripts/eject.mjs <slug> [--deploy]")
  process.exit(1)
}
if (!fs.existsSync(path.join(SITES, "designs", slug))) {
  console.error(
    `No design at sites/designs/${slug}. Promote + build the site first ` +
      `(it can use the reference design).`,
  )
  process.exit(1)
}

const OUT = path.join(ROOT, ".eject", slug)
const EXCLUDE = new Set(["node_modules", ".next", ".vercel", ".git"])

// 1. Fresh copy of sites/, skipping heavy/dev-only dirs and ANY env file.
function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true })
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (EXCLUDE.has(entry.name) || entry.name.startsWith(".env")) continue
    const s = path.join(src, entry.name)
    const d = path.join(dest, entry.name)
    if (entry.isDirectory()) copyDir(s, d)
    else fs.copyFileSync(s, d)
  }
}
fs.rmSync(OUT, { recursive: true, force: true })
copyDir(SITES, OUT)

// 2. Prune designs to just _reference + this business.
const designsOut = path.join(OUT, "designs")
for (const name of fs.readdirSync(designsOut)) {
  if (name !== "_reference" && name !== slug) {
    fs.rmSync(path.join(designsOut, name), { recursive: true, force: true })
  }
}

// 3. Regenerate the design registry with only those two entries.
const registryTs = `// Ejected standalone — only this business's design.
import type { ComponentType } from "react"
import type { BusinessContent } from "./content"

export type DesignProps = { content: BusinessContent }
type DesignModule = { default: ComponentType<DesignProps> }
type DesignLoader = () => Promise<DesignModule>

const registry: Record<string, DesignLoader> = {
  _reference: () => import("@/designs/_reference"),
  ${JSON.stringify(slug)}: () => import(${JSON.stringify("@/designs/" + slug)}),
}

export function getDesignLoader(s: string): DesignLoader {
  return registry[s] ?? registry._reference
}
`
fs.writeFileSync(path.join(OUT, "lib", "designs.ts"), registryTs)

// 4. Apply the overlay (middleware.ts root-rewrite), filling in {{SLUG}}.
if (fs.existsSync(OVERLAY)) {
  for (const entry of fs.readdirSync(OVERLAY, { withFileTypes: true })) {
    if (!entry.isFile() || entry.name === "README.md") continue
    const body = fs
      .readFileSync(path.join(OVERLAY, entry.name), "utf8")
      .replaceAll("{{SLUG}}", slug)
    fs.writeFileSync(path.join(OUT, entry.name), body)
  }
}

// 5. Write .env.local with the ANON vars only (read from the project-root .env).
function rootEnv(key) {
  const p = path.join(ROOT, ".env")
  if (!fs.existsSync(p)) return ""
  for (const line of fs.readFileSync(p, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/)
    if (m && m[1] === key) return m[2].replace(/^["']|["']$/g, "").trim()
  }
  return ""
}
fs.writeFileSync(
  path.join(OUT, ".env.local"),
  `NEXT_PUBLIC_SUPABASE_URL=${rootEnv("SUPABASE_URL")}\n` +
    `NEXT_PUBLIC_SUPABASE_ANON_KEY=${rootEnv("SUPABASE_ANON_KEY")}\n`,
)

// 6. Optionally deploy.
const rel = path.relative(ROOT, OUT)
if (doDeploy) {
  try {
    execSync("vercel deploy --prod --yes", { cwd: OUT, stdio: "inherit" })
  } catch (e) {
    console.error(`\nvercel deploy failed (CLI installed and authed?): ${e.message}`)
  }
}

console.log(`
✓ Ejected → ${rel}

Next steps (handoff):
  1. Deploy as its own Vercel project (anon env only):
       cd ${rel} && npm install && vercel deploy --prod
     Set on the Vercel project: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY.
  2. Flip the site live in Supabase (drops noindex):
       update cold_pitch.business_content set site_status='active', claimed_at=now() where slug='${slug}';
  3. Transfer to the customer: Vercel dashboard → the new Project → Settings →
     Advanced → Transfer (or the Claim Deployments URL). They make a free account
     and the project + domain become theirs. They keep editing at /${slug}/admin.
  4. Record the project URL in the CRM 'Preview URL' for this lead.
`)
