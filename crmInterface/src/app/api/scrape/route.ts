import { NextResponse } from "next/server"
import { isLocal, startScrape, scrapeStatus, type StartInput } from "@/lib/scrape.server"

const LOCAL_ONLY = { error: "Scraping is a local-only feature." }

// GET /api/scrape — current job status + recent log tail.
export async function GET() {
  if (!isLocal()) return NextResponse.json(LOCAL_ONLY, { status: 503 })
  return NextResponse.json(scrapeStatus())
}

// POST /api/scrape — start a scrape with { state, cities, categories }.
export async function POST(req: Request) {
  if (!isLocal()) return NextResponse.json(LOCAL_ONLY, { status: 503 })
  try {
    const body = (await req.json()) as Partial<StartInput>
    const input: StartInput = {
      state: body.state || "",
      categories: body.categories || [],
      screenTarget: body.screenTarget,
      targetLeads: body.targetLeads,
    }
    if (!input.state) {
      return NextResponse.json({ error: "Pick a state." }, { status: 400 })
    }
    const job = startScrape(input)
    return NextResponse.json(job)
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 409 })
  }
}
