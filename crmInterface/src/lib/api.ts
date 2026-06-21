// Talks to the Next.js route handlers under app/api, which bridge to
// scraper/crm_cli.py via src/lib/crm.server.ts.
const BASE = "/api"

export type Lead = Record<string, string>
export type LeadDetail = Lead & { photos: string[] }

export type ScrapeOptions = {
  states: { code: string; cities: string[] }[]
  categories: string[]
}
export type ScrapeJob = {
  state: "idle" | "running" | "done" | "failed"
  pid: number | null
  startedAt: string | null
  finishedAt: string | null
  exitCode: number | null
  args: string[]
  log: string
}
export type StartScrapeInput = {
  state: string
  categories: string[]
  screenTarget?: number
  targetLeads?: number
}

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

const slugPath = (slug: string) => `${BASE}/leads/${encodeURIComponent(slug)}`

export const api = {
  list: () => req<Lead[]>(`${BASE}/leads`),
  get: (slug: string) => req<LeadDetail>(slugPath(slug)),
  setField: (slug: string, field: string, value: string) =>
    req<{ ok: true }>(slugPath(slug), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, value }),
    }),
  build: (slug: string) =>
    req<{ ok: true; slug: string }>(`${slugPath(slug)}/build`, { method: "POST" }),
  remove: (slug: string) => req<{ ok: true }>(slugPath(slug), { method: "DELETE" }),
  create: (fields: Record<string, string>) =>
    req<{ ok: true; slug: string }>(`${BASE}/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    }),
  uploadPhotos: (slug: string, form: FormData) =>
    req<{ ok: true; photo_urls: string[] }>(`${slugPath(slug)}/photos`, {
      method: "POST",
      body: form,
    }),
}

export const scrape = {
  options: () => req<ScrapeOptions>(`${BASE}/scrape/options`),
  status: () => req<ScrapeJob>(`${BASE}/scrape`),
  start: (body: StartScrapeInput) =>
    req<ScrapeJob>(`${BASE}/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  stop: () => req<ScrapeJob>(`${BASE}/scrape/stop`, { method: "POST" }),
}
