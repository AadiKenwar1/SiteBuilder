import { NextResponse } from "next/server"
import { listLeads, createLead } from "@/lib/crm.server"

// GET /api/leads — every lead in the CRM, best-score first.
export async function GET() {
  try {
    return NextResponse.json(await listLeads())
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}

// POST /api/leads — manually insert one lead. Body: Header-keyed field map.
export async function POST(req: Request) {
  try {
    const fields = (await req.json().catch(() => ({}))) as Record<string, string>
    if (!fields["Business Name"]?.trim())
      return NextResponse.json({ error: "Business Name is required" }, { status: 400 })
    const slug = await createLead(fields)
    return NextResponse.json({ ok: true, slug })
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}
