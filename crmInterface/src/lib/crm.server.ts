// Server-only CRM data layer. Reads/writes the Supabase `cold_pitch.leads`
// table directly (service-role) and maps snake_case columns ↔ the legacy
// Header-case JSON the API + frontend already use. Building a site still shells
// out to scraper/promote.py (a local-only action — filesystem + Python).
import path from "path"
import { spawnSync } from "child_process"
import { supabaseAdmin } from "./supabase.server"

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
  "status,business_name,business_type,area,email,slug,site_slug,preview_url,score"

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

// Local-only: promote a CRM lead into a buildable businesses/<slug>/ folder.
// Works when the app runs locally (Python on PATH); not available on Vercel.
export function promote(slug: string): string {
  const res = spawnSync(PYTHON, [PROMOTE, "--slug", slug], { encoding: "utf8" })
  if (res.error) throw new Error(res.error.message)
  if (res.status !== 0) throw new Error((res.stderr || "promote failed").trim())
  return (res.stdout || "").trim()
}
