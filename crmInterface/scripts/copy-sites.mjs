// Build step: assemble the deployable static business sites into public/.
//
// Each canonical site lives in ../businesses/<slug>/ as `site/` (index.html,
// styles.css) plus a sibling `images/` folder, and the HTML references images as
// `../images/...`. This flattens that into public/<slug>/ (index.html + an
// images/ subfolder) and rewrites `../images/` -> `images/` so assets resolve.
// info.txt and anything else are deliberately NOT copied (privacy).
//
// Runs before `next dev` / `next build` (see package.json). Output under public/
// is a gitignored artifact — ../businesses stays the source of truth.
import fs from "fs"
import path from "path"
import { fileURLToPath } from "url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PUBLIC = path.resolve(__dirname, "..", "public")
const BUSINESSES = path.resolve(__dirname, "..", "..", "businesses")

// public/ entries we keep (the app's own committed assets); everything else
// under public/ is a generated site folder we own and may delete.
const KEEP = new Set(["favicon.svg", "icons.svg", ".gitignore"])

function rewriteAssetPaths(text) {
  // The generator consistently uses ../images/ from site/index.html; once
  // flattened, images sit one level closer.
  return text.replaceAll("../images/", "images/")
}

function copyImages(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return
  fs.mkdirSync(destDir, { recursive: true })
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    if (entry.isFile()) fs.copyFileSync(path.join(srcDir, entry.name), path.join(destDir, entry.name))
  }
}

function copySite(slug) {
  const siteDir = path.join(BUSINESSES, slug, "site")
  const indexHtml = path.join(siteDir, "index.html")
  // Skip promoted-but-not-yet-built folders (empty site/).
  if (!fs.existsSync(indexHtml) || fs.statSync(indexHtml).size === 0) return false

  const destDir = path.join(PUBLIC, slug)
  fs.mkdirSync(destDir, { recursive: true })

  for (const entry of fs.readdirSync(siteDir, { withFileTypes: true })) {
    if (!entry.isFile()) continue
    const src = path.join(siteDir, entry.name)
    const dest = path.join(destDir, entry.name)
    if (/\.(html?|css)$/i.test(entry.name)) {
      fs.writeFileSync(dest, rewriteAssetPaths(fs.readFileSync(src, "utf8")))
    } else {
      fs.copyFileSync(src, dest)
    }
  }
  copyImages(path.join(BUSINESSES, slug, "images"), path.join(destDir, "images"))
  return true
}

function main() {
  fs.mkdirSync(PUBLIC, { recursive: true })

  // Clear previously generated site folders so deleted/renamed businesses don't
  // linger in the artifact. Leaves the app's own KEEP assets untouched.
  for (const entry of fs.readdirSync(PUBLIC, { withFileTypes: true })) {
    if (entry.isDirectory() && !KEEP.has(entry.name)) {
      // maxRetries rides out transient Windows EPERM locks (AV/indexer handles).
      fs.rmSync(path.join(PUBLIC, entry.name), {
        recursive: true,
        force: true,
        maxRetries: 5,
        retryDelay: 100,
      })
    }
  }

  if (!fs.existsSync(BUSINESSES)) {
    console.log("copy-sites: no ../businesses directory — nothing to copy.")
    return
  }

  let count = 0
  for (const entry of fs.readdirSync(BUSINESSES, { withFileTypes: true })) {
    if (entry.isDirectory() && copySite(entry.name)) count++
  }
  console.log(`copy-sites: staged ${count} built site(s) into public/.`)
}

main()
