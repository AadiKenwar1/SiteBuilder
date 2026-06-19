"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Play, Square, Loader2, LogOut, Radar } from "lucide-react"

import { scrape, type ScrapeOptions, type ScrapeJob } from "@/lib/api"
import { supabaseBrowser } from "@/lib/supabase.browser"
import { AdminNav } from "@/components/AdminNav"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// A toggleable chip used for the city + business-type multi-selects.
function Chip({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-sm transition-colors ${
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-card text-foreground hover:bg-accent"
      }`}
    >
      {label}
    </button>
  )
}

const RUNNING_STATES = new Set(["running"])

function statusBadge(state: ScrapeJob["state"]) {
  const map: Record<ScrapeJob["state"], { label: string; cls: string }> = {
    idle: { label: "Idle", cls: "bg-muted text-muted-foreground" },
    running: { label: "Running", cls: "bg-primary text-primary-foreground" },
    done: { label: "Done", cls: "bg-emerald-600 text-white" },
    failed: { label: "Failed", cls: "bg-destructive text-destructive-foreground" },
  }
  return map[state]
}

export default function ScrapePage() {
  const router = useRouter()
  const [options, setOptions] = useState<ScrapeOptions | null>(null)
  const [localOnly, setLocalOnly] = useState(false)
  const [stateCode, setStateCode] = useState("")
  const [categories, setCategories] = useState<string[]>([])
  const [screenTarget, setScreenTarget] = useState("")
  const [targetLeads, setTargetLeads] = useState("")
  const [job, setJob] = useState<ScrapeJob | null>(null)
  const [starting, setStarting] = useState(false)
  const logRef = useRef<HTMLPreElement>(null)

  const running = job ? RUNNING_STATES.has(job.state) : false

  // Load dropdown options once.
  useEffect(() => {
    scrape
      .options()
      .then((opts) => {
        setOptions(opts)
        if (opts.states.length === 1) setStateCode(opts.states[0].code)
        setCategories(opts.categories) // default: all types selected
      })
      .catch((e) => {
        // 503 → deployed (local-only); anything else is a real error.
        if (String(e.message).includes("local-only")) setLocalOnly(true)
        else toast.error(`Couldn't load options: ${e.message}`)
      })
  }, [])

  // Poll status while a job is running.
  useEffect(() => {
    if (!running) return
    const id = setInterval(async () => {
      try {
        const s = await scrape.status()
        setJob(s)
      } catch {
        /* transient */
      }
    }, 2000)
    return () => clearInterval(id)
  }, [running])

  // Pick up an in-progress job on first mount (e.g. after a page refresh).
  useEffect(() => {
    if (localOnly) return
    scrape.status().then(setJob).catch(() => {})
  }, [localOnly])

  // Auto-scroll the log to the bottom as it grows.
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [job?.log])

  function toggle(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  async function onRun() {
    if (!stateCode) return toast.error("Pick a state.")
    setStarting(true)
    try {
      const j = await scrape.start({
        state: stateCode,
        categories,
        screenTarget: screenTarget ? Number(screenTarget) : undefined,
        targetLeads: targetLeads ? Number(targetLeads) : undefined,
      })
      setJob(j)
      toast.success("Scrape started")
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setStarting(false)
    }
  }

  async function onStop() {
    try {
      await scrape.stop()
      toast.message("Stopping…")
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  async function signOut() {
    await supabaseBrowser().auth.signOut()
    router.replace("/admin/login")
    router.refresh()
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-foreground text-background">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Cold-Pitch Pipeline</h1>
              <p className="text-xs text-background/60">Run the lead scraper</p>
            </div>
            <AdminNav />
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={signOut}
            className="gap-1.5 text-background/70 hover:bg-background/10 hover:text-background"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-6">
        {localOnly ? (
          <div className="rounded-lg border border-border bg-card p-8 text-center">
            <Radar className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
            <h2 className="text-base font-semibold">Scraping is a local-only feature</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              The scraper drives a real browser and writes files to disk, so it can&apos;t run
              on the deployed app. Run the dashboard locally (<code className="font-mono">npm run dev</code>)
              to use this tab.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
            {/* ── Controls ─────────────────────────────────────────── */}
            <div className="space-y-5">
              <div className="space-y-1.5">
                <Label>State</Label>
                <Select value={stateCode} onValueChange={setStateCode}>
                  <SelectTrigger className="bg-card">
                    <SelectValue placeholder="Pick a state" />
                  </SelectTrigger>
                  <SelectContent>
                    {options?.states.map((s) => (
                      <SelectItem key={s.code} value={s.code}>
                        {s.code.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Business types <span className="text-muted-foreground">({categories.length})</span></Label>
                  <button
                    type="button"
                    className="text-xs text-muted-foreground hover:text-foreground"
                    onClick={() =>
                      setCategories(
                        options && categories.length === options.categories.length ? [] : [...(options?.categories ?? [])],
                      )
                    }
                  >
                    {options && categories.length === options.categories.length ? "Clear" : "All"}
                  </button>
                </div>
                <div className="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto rounded-md border border-border bg-card p-2">
                  {options?.categories.map((c) => (
                    <Chip key={c} label={c} active={categories.includes(c)} onClick={() => toggle(categories, setCategories, c)} />
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="screen">Screen target</Label>
                  <Input id="screen" inputMode="numeric" placeholder="default" value={screenTarget} onChange={(e) => setScreenTarget(e.target.value.replace(/\D/g, ""))} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="target">Keep top</Label>
                  <Input id="target" inputMode="numeric" placeholder="default" value={targetLeads} onChange={(e) => setTargetLeads(e.target.value.replace(/\D/g, ""))} />
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={onRun} disabled={running || starting || !stateCode} className="gap-1.5">
                  {starting || running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  {running ? "Running…" : "Run scraper"}
                </Button>
                {running && (
                  <Button variant="destructive" onClick={onStop} className="gap-1.5">
                    <Square className="h-4 w-4" />
                    Stop
                  </Button>
                )}
              </div>
            </div>

            {/* ── Status + log ─────────────────────────────────────── */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Progress</span>
                {job && (
                  <Badge className={statusBadge(job.state).cls}>{statusBadge(job.state).label}</Badge>
                )}
                {job?.exitCode != null && job.state === "failed" && (
                  <span className="text-xs text-muted-foreground">exit {job.exitCode}</span>
                )}
              </div>
              <pre
                ref={logRef}
                className="h-[60vh] overflow-auto rounded-md border border-border bg-foreground p-4 font-mono text-xs leading-relaxed text-background/90"
              >
                {job?.log?.trim() || "No run yet. Configure filters and hit Run scraper."}
              </pre>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
