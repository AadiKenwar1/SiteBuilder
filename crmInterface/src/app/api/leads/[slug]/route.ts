import { NextResponse } from "next/server"
import path from "path"
import fs from "fs"
import { getLead, setField, deleteLead } from "@/lib/crm.server"

type Ctx = { params: Promise<{ slug: string }> }

// GET /api/leads/:slug — one lead, plus its photo URLs for the detail page.
export async function GET(_req: Request, { params }: Ctx) {
  const { slug } = await params
  try {
    const lead = await getLead(slug)
    if (!lead) return NextResponse.json({ error: "not found" }, { status: 404 })
    return NextResponse.json(lead)
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}

// PATCH /api/leads/:slug — set a single CRM field.
export async function PATCH(req: Request, { params }: Ctx) {
  const { slug } = await params
  const { field, value } = (await req.json().catch(() => ({}))) as {
    field?: string
    value?: string
  }
  if (!field) return NextResponse.json({ error: "field is required" }, { status: 400 })
  try {
    const ok = await setField(slug, field, value ?? "")
    if (!ok) return NextResponse.json({ error: "not found" }, { status: 404 })
    return NextResponse.json({ ok: true })
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}

// DELETE /api/leads/:slug — remove the lead row, then best-effort delete its
// local businesses/<site_slug> folder (a no-op when deployed / already gone).
export async function DELETE(_req: Request, { params }: Ctx) {
  const { slug } = await params
  try {
    const removed = await deleteLead(slug)
    if (!removed) return NextResponse.json({ error: "not found" }, { status: 404 })

    let removedFolder: string | null = null
    const site = (removed["Site Slug"] || "").trim()
    if (site) {
      const folder = path.resolve(process.cwd(), "..", "businesses", site)
      try {
        if (fs.existsSync(folder)) {
          fs.rmSync(folder, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 })
          removedFolder = folder
        }
      } catch {
        /* deployed/serverless has no local folder — ignore */
      }
    }
    return NextResponse.json({ ok: true, removed_folder: removedFolder })
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}
