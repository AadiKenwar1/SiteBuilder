"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  Hammer,
  Trash2,
  ExternalLink,
  Search,
  RotateCw,
  Loader2,
  CheckCircle2,
  LogOut,
} from "lucide-react"

import { api, type Lead } from "@/lib/api"
import { supabaseBrowser } from "@/lib/supabase.browser"
import { AdminNav } from "@/components/AdminNav"
import { StatusSelect } from "@/components/StatusSelect"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

function UrlCell({ lead }: { lead: Lead }) {
  const [val, setVal] = useState(lead["Preview URL"] || "")
  const save = async () => {
    if (val === (lead["Preview URL"] || "")) return
    try {
      await api.setField(lead.Slug, "Preview URL", val)
      lead["Preview URL"] = val
      toast.success("URL saved")
    } catch (e) {
      toast.error(`Save failed: ${(e as Error).message}`)
    }
  }
  return (
    <div className="flex items-center gap-1.5">
      <Input
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
        placeholder="https://…"
        className="h-8 font-mono text-xs"
      />
      {val ? (
        <a href={val} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary">
          <ExternalLink className="h-4 w-4" />
        </a>
      ) : null}
    </div>
  )
}

// Leads are fetched server-side and passed in as initialLeads, so the table
// renders on first paint with no client fetch waterfall. Refresh re-fetches
// via the API on demand.
export function DashboardClient({ initialLeads }: { initialLeads: Lead[] }) {
  const router = useRouter()
  const [leads, setLeads] = useState<Lead[]>(initialLeads)
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState("")
  const [busy, setBusy] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<Lead | null>(null)

  async function signOut() {
    await supabaseBrowser().auth.signOut()
    router.replace("/admin/login")
    router.refresh()
  }

  async function load() {
    setLoading(true)
    try {
      setLeads(await api.list())
    } catch (e) {
      toast.error(`Could not load leads: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return leads
    return leads.filter((l) =>
      [l["Business Name"], l["Business Type"], l["Area"], l["Email"]]
        .filter(Boolean)
        .some((v) => v.toLowerCase().includes(q)),
    )
  }, [leads, query])

  async function onStatus(lead: Lead, value: string) {
    const prev = lead.Status
    setLeads((ls) => ls.map((l) => (l.Slug === lead.Slug ? { ...l, Status: value } : l)))
    try {
      await api.setField(lead.Slug, "Status", value)
    } catch (e) {
      setLeads((ls) => ls.map((l) => (l.Slug === lead.Slug ? { ...l, Status: prev } : l)))
      toast.error(`Status update failed: ${(e as Error).message}`)
    }
  }

  async function onBuild(lead: Lead) {
    setBusy(lead.Slug)
    try {
      await api.build(lead.Slug)
      toast.success(`Built directory for ${lead["Business Name"]}`)
      await load()
    } catch (e) {
      toast.error(`Build failed: ${(e as Error).message}`)
    } finally {
      setBusy(null)
    }
  }

  async function onDelete(lead: Lead) {
    setBusy(lead.Slug)
    try {
      await api.remove(lead.Slug)
      setLeads((ls) => ls.filter((l) => l.Slug !== lead.Slug))
      toast.success(`Deleted ${lead["Business Name"]}`)
    } catch (e) {
      toast.error(`Delete failed: ${(e as Error).message}`)
    } finally {
      setBusy(null)
      setConfirm(null)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-foreground text-background">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Cold-Pitch Pipeline</h1>
              <p className="text-xs text-background/60">
                {leads.length} lead{leads.length === 1 ? "" : "s"} in the CRM
              </p>
            </div>
            <AdminNav />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={load}
              className="gap-1.5"
              disabled={loading}
            >
              <RotateCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
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
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name, type, area, email…"
              className="h-9 bg-card pl-8"
            />
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/60 hover:bg-muted/60">
                <TableHead className="w-[190px]">Status</TableHead>
                <TableHead>Business</TableHead>
                <TableHead className="w-[280px]">URL</TableHead>
                <TableHead className="w-[210px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-32 text-center text-muted-foreground">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-32 text-center text-muted-foreground">
                    No leads{query ? " match your search" : " yet — run the scraper"}.
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((lead) => {
                  const promoted = !!(lead["Site Slug"] || "").trim()
                  const isBusy = busy === lead.Slug
                  return (
                    <TableRow key={lead.Slug} className="group">
                      <TableCell>
                        <StatusSelect value={lead.Status} onChange={(v) => onStatus(lead, v)} />
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/admin/b/${encodeURIComponent(lead.Slug)}`}
                          className="font-medium text-foreground decoration-primary/40 underline-offset-4 hover:underline"
                        >
                          {lead["Business Name"] || "(unnamed)"}
                        </Link>
                        {promoted && (
                          <span className="ml-2 inline-flex items-center gap-1 align-middle text-[11px] font-medium text-green-700">
                            <CheckCircle2 className="h-3.5 w-3.5" /> built
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <UrlCell lead={lead} />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 gap-1.5"
                            disabled={isBusy}
                            onClick={() => onBuild(lead)}
                          >
                            {isBusy ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Hammer className="h-3.5 w-3.5" />
                            )}
                            {promoted ? "Rebuild" : "Build"}
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                            disabled={isBusy}
                            onClick={() => setConfirm(lead)}
                            aria-label="Delete"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      </main>

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {confirm?.["Business Name"]}?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the lead from the CRM and deletes its{" "}
              <code className="font-mono">businesses/{confirm?.["Site Slug"] || "—"}</code> folder
              and photos from disk. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => confirm && onDelete(confirm)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
