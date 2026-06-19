import { NextResponse } from "next/server"
import { isLocal, stopScrape } from "@/lib/scrape.server"

// POST /api/scrape/stop — kill the running scrape job.
export async function POST() {
  if (!isLocal()) {
    return NextResponse.json({ error: "Scraping is a local-only feature." }, { status: 503 })
  }
  return NextResponse.json(stopScrape())
}
