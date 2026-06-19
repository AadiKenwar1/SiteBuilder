// Server-only, LOCAL-ONLY job runner for the Scrape tab. Spawns the Python
// scraper (scraper/run.py) as a detached background process, tees its output to
// a log file, and tracks one job at a time in a module singleton. This shells to
// Python + Playwright + the local filesystem, so it only works when the app runs
// locally — never on Vercel (guard with isLocal()).
import path from "path"
import fs from "fs"
import { spawn, spawnSync, type ChildProcess } from "child_process"

const PROJECT_ROOT = path.resolve(process.cwd(), "..")
const SCRAPER_DIR = path.join(PROJECT_ROOT, "scraper")
const RUN_PY = path.join(SCRAPER_DIR, "run.py")
const OPTIONS_PY = path.join(SCRAPER_DIR, "options.py")
const RUN_DIR = path.join(SCRAPER_DIR, ".run")
const LOG_FILE = path.join(RUN_DIR, "scrape.log")
const PYTHON = process.env.PYTHON || "python"

// Scraping needs a long-lived host with Chromium — impossible on Vercel.
export function isLocal(): boolean {
  return !process.env.VERCEL
}

export type ScrapeState = "idle" | "running" | "done" | "failed"

type Job = {
  state: ScrapeState
  pid: number | null
  startedAt: string | null
  finishedAt: string | null
  exitCode: number | null
  args: string[]
}

// Module singleton — one local dev server process, so this persists across
// requests. child is kept only to allow stop(); status is the source of truth.
let child: ChildProcess | null = null
let job: Job = {
  state: "idle",
  pid: null,
  startedAt: null,
  finishedAt: null,
  exitCode: null,
  args: [],
}

export type StartInput = {
  state: string
  categories: string[]
  screenTarget?: number
  targetLeads?: number
}

function buildArgs(input: StartInput): string[] {
  const args = [RUN_PY]
  if (input.state) args.push("--state", input.state)
  if (input.categories?.length) args.push("--categories", input.categories.join(","))
  if (input.screenTarget) args.push("--screen-target", String(input.screenTarget))
  if (input.targetLeads) args.push("--target-leads", String(input.targetLeads))
  return args
}

export function startScrape(input: StartInput): Job {
  if (job.state === "running") {
    throw new Error("A scrape is already running.")
  }

  fs.mkdirSync(RUN_DIR, { recursive: true })
  const args = buildArgs(input)
  const header =
    `\n${"=".repeat(60)}\n` +
    `[${new Date().toISOString()}] starting: ${PYTHON} ${args.join(" ")}\n` +
    `${"=".repeat(60)}\n`
  // Fresh log per run.
  fs.writeFileSync(LOG_FILE, header, "utf8")
  const logFd = fs.openSync(LOG_FILE, "a")

  // PYTHONUNBUFFERED=1 so prints land in the log immediately for the live tail.
  const proc = spawn(PYTHON, args, {
    cwd: SCRAPER_DIR,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", logFd, logFd],
  })
  fs.closeSync(logFd)

  child = proc
  job = {
    state: "running",
    pid: proc.pid ?? null,
    startedAt: new Date().toISOString(),
    finishedAt: null,
    exitCode: null,
    args,
  }

  proc.on("exit", (code) => {
    job.state = code === 0 ? "done" : "failed"
    job.exitCode = code
    job.finishedAt = new Date().toISOString()
    child = null
  })
  proc.on("error", (err) => {
    job.state = "failed"
    job.finishedAt = new Date().toISOString()
    try {
      fs.appendFileSync(LOG_FILE, `\n[spawn error] ${err.message}\n`)
    } catch {}
    child = null
  })

  return job
}

function tailLog(maxLines = 80): string {
  try {
    const text = fs.readFileSync(LOG_FILE, "utf8")
    const lines = text.split("\n")
    return lines.slice(-maxLines).join("\n")
  } catch {
    return ""
  }
}

export function scrapeStatus(): Job & { log: string } {
  return { ...job, log: tailLog() }
}

export function stopScrape(): Job {
  if (job.state === "running" && child) {
    try {
      child.kill()
    } catch {}
    try {
      fs.appendFileSync(LOG_FILE, `\n[stopped by user] ${new Date().toISOString()}\n`)
    } catch {}
  }
  return job
}

export type ScrapeOptions = {
  states: { code: string; cities: string[] }[]
  categories: string[]
}

export function scrapeOptions(): ScrapeOptions {
  const res = spawnSync(PYTHON, [OPTIONS_PY], { encoding: "utf8", cwd: SCRAPER_DIR })
  if (res.error) throw new Error(res.error.message)
  if (res.status !== 0) throw new Error((res.stderr || "options failed").trim())
  return JSON.parse(res.stdout) as ScrapeOptions
}
