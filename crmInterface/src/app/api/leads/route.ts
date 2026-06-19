import { NextResponse } from "next/server"
import { listLeads } from "@/lib/crm.server"

// GET /api/leads — every lead in the CRM, best-score first.
export async function GET() {
  try {
    return NextResponse.json(await listLeads())
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}
