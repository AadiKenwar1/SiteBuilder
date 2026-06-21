// Server-only CRM data layer. Reads/writes the Supabase `cold_pitch.leads`
// table directly (service-role) and maps snake_case columns ↔ the legacy
// Header-case JSON the API + frontend already use. Building a site still shells
// out to scraper/promote.py (a local-only action — filesystem + Python).
import path from "path"
import { spawnSync } from "child_process"
import { supabaseAdmin } from "./supabase.server"

const LEAD_PHOTOS_BUCKET = "lead-photos"
const IMG_EXT = new Set([".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"])
const IMG_MIME: Record<string, string> = {
  ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
  ".webp": "image/webp", ".avif": "image/avif", ".gif": "image/gif",
}
const MAX_FILE_BYTES = 5 * 1024 * 1024

const PROJECT_ROOT = path.resolve(process.cwd(), "..")
const PROMOTE = path.join(PROJECT_ROOT, "scraper", "promote.py")
const PYTHON = process.env.PYTHON || "python"

// Header name ↔ db column (mirror of scraper/pipeline/db.py COLUMNS).
const HEADER_TO_DB: Record<string, string> = {
  "Status": "status",
  "Score": "score",
  "Business Name": "business_name",
  "Business Type": "business_type",
  "Area": "area",
  "Phone": "phone",
  "Email": "email",
  "Address": "address",
  "Rating": "rating",
  "Reviews": "review_count",
  "Lead Reason": "lead_reason",
  "Site Slug": "site_slug",
  "Preview URL": "preview_url",
  "Facebook URL": "facebook_url",
  "Instagram URL": "instagram_url",
  "Maps URL": "maps_url",
  "Website": "website_url",
  "Hours": "hours",
  "Services": "services",
  "About": "about",
  "Year": "year_established",
  "Price": "price_range",
  "Notes": "notes",
  "Contacted On": "contacted_on",
  "Slug": "slug",
  "Photos Path": "photos_path",
  "Source": "source",
}
const INT_COLS = new Set(["score", "review_count"])

export type Lead = Record<string, string>

function rowToHeader(row: Record<string, unknown>): Lead {
  const out: Lead = {}
  for (const [header, col] of Object.entries(HEADER_TO_DB)) {
    const v = row[col]
    out[header] = v === null || v === undefined ? "" : String(v)
  }
  return out
}

// The dashboard table only renders/searches/sorts on these columns. Selecting
// them explicitly avoids hauling the heavy jsonb fields (services, reviews,
// hours, about, photo_urls) over the wire for every lead. rowToHeader fills the
// unselected headers with "".
const LIST_COLS =
  "status,business_name,business_type,area,email,slug,site_slug,preview_url,score,source"

export async function listLeads(): Promise<Lead[]> {
  const { data, error } = await supabaseAdmin()
    .from("leads")
    .select(LIST_COLS)
    .order("score", { ascending: false })
  if (error) throw new Error(error.message)
  return (data ?? []).map(rowToHeader)
}

export async function getLead(slug: string): Promise<(Lead & { photos: string[] }) | null> {
  const { data, error } = await supabaseAdmin()
    .from("leads")
    .select("*")
    .eq("slug", slug)
    .limit(1)
    .maybeSingle()
  if (error) throw new Error(error.message)
  if (!data) return null
  const photos = Array.isArray(data.photo_urls) ? data.photo_urls.map(String) : []
  return { ...rowToHeader(data), photos }
}

export async function setField(slug: string, field: string, value: string): Promise<boolean> {
  const col = HEADER_TO_DB[field]
  if (!col) return false
  const val: string | number = INT_COLS.has(col) ? Number(value) || 0 : value ?? ""
  const { data, error } = await supabaseAdmin()
    .from("leads")
    .update({ [col]: val })
    .eq("slug", slug)
    .select("slug")
  if (error) throw new Error(error.message)
  return (data?.length ?? 0) > 0
}

// Deletes the row and returns it (so the caller can clean up its folder), or
// null if the slug wasn't found.
export async function deleteLead(slug: string): Promise<Lead | null> {
  const { data, error } = await supabaseAdmin()
    .from("leads")
    .delete()
    .eq("slug", slug)
    .select("*")
  if (error) throw new Error(error.message)
  if (!data || data.length === 0) return null
  return rowToHeader(data[0])
}

// ── Slug generation (mirrors scraper/pipeline/utils.py lead_slug) ────────────

function leadSlug(name: string, address = ""): string {
  const base = `${name} ${address.slice(0, 20)}`.toLowerCase()
  const s = base.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
  return (s || "biz").slice(0, 60)
}

async function uniqueSlug(base: string): Promise<string> {
  const { data } = await supabaseAdmin()
    .from("leads")
    .select("slug")
    .like("slug", `${base}%`)
  const existing = new Set((data ?? []).map((r: { slug: string }) => r.slug))
  if (!existing.has(base)) return base
  for (let i = 2; i < 1000; i++) {
    const candidate = `${base}-${i}`
    if (!existing.has(candidate)) return candidate
  }
  return `${base}-${Date.now()}`
}

// Insert one manually-entered lead. Returns the new slug.
// Status defaults to 'New' (DB default); caller may override via fields.
export async function createLead(fields: Record<string, string>): Promise<string> {
  if (!fields["Business Name"]?.trim()) throw new Error("Business Name is required")
  const base = leadSlug(fields["Business Name"], fields["Address"] ?? "")
  const slug = await uniqueSlug(base)
  const payload: Record<string, string | number> = { slug, source: "manual" }
  for (const [header, value] of Object.entries(fields)) {
    const col = HEADER_TO_DB[header]
    if (col && col !== "slug" && col !== "source" && value !== "" && value != null) {
      payload[col] = INT_COLS.has(col) ? Number(value) || 0 : value
    }
  }
  const { error } = await supabaseAdmin().from("leads").insert(payload)
  if (error) throw new Error(error.message)
  return slug
}

// Upload images to lead-photos/<slug>/ as 01.ext, 02.ext… and store the public
// URLs in leads.photo_urls. Claude decides which is the logo/hero/gallery when
// building the site — no pre-categorisation needed here.
export async function uploadLeadPhotos(slug: string, files: { bytes: Uint8Array; name: string }[]): Promise<string[]> {
  const bucket = supabaseAdmin().storage.from(LEAD_PHOTOS_BUCKET)
  const urls: string[] = []

  for (let i = 0; i < files.length; i++) {
    const { bytes, name } = files[i]
    const ext = "." + (name.split(".").pop() ?? "jpg").toLowerCase()
    const mime = IMG_MIME[ext] ?? "image/jpeg"
    const key = `${slug}/${String(i + 1).padStart(2, "0")}${ext}`
    const { error } = await bucket.upload(key, bytes, { contentType: mime, upsert: true })
    if (error) throw new Error(`Upload failed (${name}): ${error.message}`)
    urls.push(bucket.getPublicUrl(key).data.publicUrl)
  }

  if (urls.length > 0) {
    const { error } = await supabaseAdmin()
      .from("leads")
      .update({ photo_urls: urls })
      .eq("slug", slug)
    if (error) throw new Error(error.message)
  }
  return urls
}

export { IMG_EXT, MAX_FILE_BYTES }

// Local-only: promote a CRM lead into a buildable businesses/<slug>/ folder.
// Works when the app runs locally (Python on PATH); not available on Vercel.
export function promote(slug: string): string {
  const res = spawnSync(PYTHON, [PROMOTE, "--slug", slug], { encoding: "utf8" })
  if (res.error) throw new Error(res.error.message)
  if (res.status !== 0) throw new Error((res.stderr || "promote failed").trim())
  return (res.stdout || "").trim()
}
