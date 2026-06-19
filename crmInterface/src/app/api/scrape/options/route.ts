import { NextResponse } from "next/server"
import { isLocal, scrapeOptions } from "@/lib/scrape.server"

// GET /api/scrape/options — states (+ cities) and business-type categories for
// the Scrape tab dropdowns. Local-only (shells to Python).
export async function GET() {
  if (!isLocal()) {
    return NextResponse.json({ error: "Scraping is a local-only feature." }, { status: 503 })
  }
  try {
    return NextResponse.json(scrapeOptions())
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}
