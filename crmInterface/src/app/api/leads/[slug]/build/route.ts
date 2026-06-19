import { NextResponse } from "next/server"
import { promote } from "@/lib/crm.server"

type Ctx = { params: Promise<{ slug: string }> }

// POST /api/leads/:slug/build — promote the CRM lead into a buildable folder.
export async function POST(_req: Request, { params }: Ctx) {
  const { slug } = await params
  try {
    const out = promote(slug)
    return NextResponse.json({ ok: true, slug, message: out })
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}
