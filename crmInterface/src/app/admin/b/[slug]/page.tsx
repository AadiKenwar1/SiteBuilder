"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, ExternalLink, Loader2, Star } from "lucide-react"

import { api, type LeadDetail } from "@/lib/api"
import { statusMeta } from "@/lib/status"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  if (children === null || children === undefined || children === "") return null
  return (
    <div className="space-y-0.5">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="text-sm text-foreground">{children}</div>
    </div>
  )
}

const linkClass = "inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"

export default function Detail() {
  const params = useParams<{ slug: string }>()
  const slug = params.slug ?? ""
  const [data, setData] = useState<LeadDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    api
      .get(slug)
      .then(setData)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [slug])

  if (loading)
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  if (error || !data)
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <Link href="/admin" className={linkClass}>
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
        <p className="mt-4 text-destructive">{error || "Not found."}</p>
      </div>
    )

  const g = (k: string) => (data[k] || "").trim()
  const meta = statusMeta(g("Status"))
  const services = g("Services")
    .split(/[,;]/)
    .map((s) => s.trim())
    .filter(Boolean)
  const hours = g("Hours")
    .split(/\s*\|\s*/)
    .map((s) => s.trim())
    .filter(Boolean)

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-foreground text-background">
        <div className="mx-auto max-w-5xl px-6 py-4">
          <Link href="/admin" className="inline-flex items-center gap-1 text-sm text-background/70 hover:text-background">
            <ArrowLeft className="h-4 w-4" /> Pipeline
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{g("Business Name")}</h1>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.chip}`}>
              {g("Status") || "New"}
            </span>
            {g("Score") && (
              <span className="rounded-full bg-background/15 px-2.5 py-0.5 text-xs font-medium text-background">
                score {g("Score")}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-background/60">
            {[g("Business Type"), g("Area")].filter(Boolean).join(" · ")}
          </p>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-5 px-6 py-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contact</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <Field label="Phone">
              {g("Phone") && <a className={linkClass} href={`tel:${g("Phone")}`}>{g("Phone")}</a>}
            </Field>
            <Field label="Email">
              {g("Email") && <a className={linkClass} href={`mailto:${g("Email")}`}>{g("Email")}</a>}
            </Field>
            <div className="col-span-2">
              <Field label="Address">{g("Address")}</Field>
            </div>
            <Field label="Website">
              {g("Website") && (
                <a className={linkClass} href={g("Website")} target="_blank" rel="noreferrer">
                  visit <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </Field>
            <Field label="Maps">
              {g("Maps URL") && (
                <a className={linkClass} href={g("Maps URL")} target="_blank" rel="noreferrer">
                  open <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </Field>
            <Field label="Facebook">
              {g("Facebook URL") && (
                <a className={linkClass} href={g("Facebook URL")} target="_blank" rel="noreferrer">
                  page <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </Field>
            <Field label="Instagram">
              {g("Instagram URL") && (
                <a className={linkClass} href={g("Instagram URL")} target="_blank" rel="noreferrer">
                  profile <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Performance</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <Field label="Rating">
              {g("Rating") && (
                <span className="inline-flex items-center gap-1">
                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                  {g("Rating")}
                </span>
              )}
            </Field>
            <Field label="Reviews">{g("Reviews")}</Field>
            <Field label="Price">{g("Price")}</Field>
            <Field label="Established">{g("Year")}</Field>
            <Field label="Lead reason">{g("Lead Reason")}</Field>
            <Field label="Contacted on">{g("Contacted On")}</Field>
          </CardContent>
        </Card>

        {(hours.length > 0 || services.length > 0 || g("About")) && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {g("About") && <Field label="About">{g("About")}</Field>}
              {services.length > 0 && (
                <Field label="Services">
                  <div className="flex flex-wrap gap-1.5">
                    {services.map((s, i) => (
                      <span key={i} className="rounded-md border border-border bg-secondary px-2 py-0.5 text-xs">
                        {s}
                      </span>
                    ))}
                  </div>
                </Field>
              )}
              {hours.length > 0 && (
                <Field label="Hours">
                  <ul className="font-mono text-xs leading-relaxed">
                    {hours.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                </Field>
              )}
            </CardContent>
          </Card>
        )}

        {g("Notes") && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm">{g("Notes")}</p>
            </CardContent>
          </Card>
        )}

        {data.photos && data.photos.length > 0 && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Photos ({data.photos.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {data.photos.map((src) => (
                  <a key={src} href={src} target="_blank" rel="noreferrer">
                    <img
                      src={src}
                      alt=""
                      loading="lazy"
                      className="aspect-square w-full rounded-md border border-border object-cover transition hover:opacity-90"
                    />
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {g("Preview URL") && (
          <div className="md:col-span-2">
            <Button asChild variant="outline">
              <a href={g("Preview URL")} target="_blank" rel="noreferrer">
                Open live site <ExternalLink className="ml-1.5 h-4 w-4" />
              </a>
            </Button>
          </div>
        )}
      </main>
    </div>
  )
}
