// The content contract: the shape every design renders, and the reader that
// pulls it from cold_pitch.public_business_content with the anon key.
import { supabaseAnon } from "./supabase.anon"

export const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const
export type Weekday = (typeof WEEKDAYS)[number]

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  mon: "Monday",
  tue: "Tuesday",
  wed: "Wednesday",
  thu: "Thursday",
  fri: "Friday",
  sat: "Saturday",
  sun: "Sunday",
}

// Uniform hours: every site has all seven keys, each a time range or "Closed".
export type Hours = Record<Weekday, string>

export type Service = { name: string; description?: string; price?: string }
export type Review = { text: string; name?: string; stars?: string; date?: string }

export type BusinessContent = {
  slug: string
  site_status: "preview" | "active"
  business_name: string
  business_type: string
  phone: string
  email: string
  address: string
  maps_url: string
  rating: string
  review_count: number
  reviews: Review[]
  hours: Hours
  holidays_note: string
  about: string
  services: Service[]
  photo_hero_url: string
  photo_gallery_urls: string[]
  facebook_url: string
  instagram_url: string
}

const EMPTY_HOURS: Hours = {
  mon: "Closed", tue: "Closed", wed: "Closed", thu: "Closed",
  fri: "Closed", sat: "Closed", sun: "Closed",
}

// Coerce a raw DB row (jsonb columns arrive as already-parsed JS values) into the
// typed shape, filling sensible defaults so a design never crashes on a null.
function normalize(row: Record<string, unknown>): BusinessContent {
  const hours = { ...EMPTY_HOURS, ...((row.hours as Partial<Hours>) ?? {}) }
  return {
    slug: String(row.slug ?? ""),
    site_status: row.site_status === "active" ? "active" : "preview",
    business_name: String(row.business_name ?? ""),
    business_type: String(row.business_type ?? ""),
    phone: String(row.phone ?? ""),
    email: String(row.email ?? ""),
    address: String(row.address ?? ""),
    maps_url: String(row.maps_url ?? ""),
    rating: String(row.rating ?? ""),
    review_count: Number(row.review_count ?? 0),
    reviews: Array.isArray(row.reviews) ? (row.reviews as Review[]) : [],
    hours,
    holidays_note: String(row.holidays_note ?? ""),
    about: String(row.about ?? ""),
    services: Array.isArray(row.services) ? (row.services as Service[]) : [],
    photo_hero_url: String(row.photo_hero_url ?? ""),
    photo_gallery_urls: Array.isArray(row.photo_gallery_urls)
      ? (row.photo_gallery_urls as string[])
      : [],
    facebook_url: String(row.facebook_url ?? ""),
    instagram_url: String(row.instagram_url ?? ""),
  }
}

// Read one business's public content. Returns null when the slug doesn't exist.
export async function getContent(slug: string): Promise<BusinessContent | null> {
  const { data, error } = await supabaseAnon()
    .from("public_business_content")
    .select("*")
    .eq("slug", slug)
    .maybeSingle()
  if (error || !data) return null
  return normalize(data as Record<string, unknown>)
}
