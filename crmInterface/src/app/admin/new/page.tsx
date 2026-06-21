"use client"

import { useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { LogOut, UserPlus, X, ImagePlus } from "lucide-react"

import { api } from "@/lib/api"
import { supabaseBrowser } from "@/lib/supabase.browser"
import { AdminNav } from "@/components/AdminNav"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { STATUSES } from "@/lib/status"

// ── Image picker ──────────────────────────────────────────────────────────────

type ImageFile = { file: File; preview: string }

function ImagePicker({
  images,
  onAdd,
  onRemove,
}: {
  images: ImageFile[]
  onAdd: (files: File[]) => void
  onRemove: (i: number) => void
}) {
  const ref = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    onAdd(Array.from(e.dataTransfer.files))
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {images.map((img, i) => (
          <div key={img.preview} className="relative">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={img.preview}
              alt={img.file.name}
              className="h-24 w-auto max-w-[140px] rounded-md border border-border object-cover"
            />
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-white shadow"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => ref.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          className="flex h-24 w-28 flex-col items-center justify-center gap-1.5 rounded-md border border-dashed border-border bg-card text-muted-foreground transition-colors hover:bg-accent"
        >
          <ImagePlus className="h-5 w-5" />
          <span className="text-xs">Add images</span>
        </button>
      </div>
      <p className="text-xs text-muted-foreground">
        Drop in any photos — logo, exterior, interior, products. Claude will figure out which is which when building the site.
      </p>
      <input
        ref={ref}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length) onAdd(Array.from(e.target.files))
          e.target.value = ""
        }}
      />
    </div>
  )
}

// ── Form field helper ─────────────────────────────────────────────────────────

function Field({
  id,
  label,
  value,
  onChange,
  required,
  placeholder,
  type = "text",
  inputMode,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  required?: boolean
  placeholder?: string
  type?: string
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"]
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      <Input
        id={id}
        type={type}
        inputMode={inputMode}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="bg-card"
      />
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

const EMPTY: Record<string, string> = {
  "Business Name": "",
  "Business Type": "",
  "Area": "",
  "Phone": "",
  "Email": "",
  "Address": "",
  "Website": "",
  "Maps URL": "",
  "Facebook URL": "",
  "Instagram URL": "",
  "Lead Reason": "",
  "Notes": "",
  "Status": "New",
  "Score": "",
}

export default function NewLeadPage() {
  const router = useRouter()
  const [fields, setFields] = useState<Record<string, string>>({ ...EMPTY })
  const [images, setImages] = useState<ImageFile[]>([])
  const [submitting, setSubmitting] = useState(false)

  function set(key: string) {
    return (v: string) => setFields((f) => ({ ...f, [key]: v }))
  }

  function addImages(files: File[]) {
    setImages((prev) => [
      ...prev,
      ...files.map((f) => ({ file: f, preview: URL.createObjectURL(f) })),
    ])
  }

  function removeImage(i: number) {
    setImages((prev) => {
      URL.revokeObjectURL(prev[i].preview)
      return prev.filter((_, idx) => idx !== i)
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!fields["Business Name"].trim()) {
      toast.error("Business Name is required")
      return
    }
    setSubmitting(true)
    try {
      const { slug } = await api.create(fields)

      if (images.length > 0) {
        const form = new FormData()
        for (const img of images) form.append("images", img.file)
        await api.uploadPhotos(slug, form)
      }

      toast.success(`Lead created: ${slug}`)
      router.push(`/admin/b/${slug}`)
    } catch (err) {
      toast.error((err as Error).message)
      setSubmitting(false)
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
              <p className="text-xs text-background/60">Add a lead manually</p>
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

      <main className="mx-auto max-w-3xl px-6 py-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* ── Business details ─────────────────────────────────── */}
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Business details
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="name" label="Business Name" required value={fields["Business Name"]} onChange={set("Business Name")} placeholder="Jane's Bakery" />
              <Field id="type" label="Business Type" value={fields["Business Type"]} onChange={set("Business Type")} placeholder="Bakery" />
              <Field id="area" label="Area" value={fields["Area"]} onChange={set("Area")} placeholder="Newark, NJ" />
              <Field id="phone" label="Phone" value={fields["Phone"]} onChange={set("Phone")} placeholder="(555) 000-0000" type="tel" />
              <Field id="email" label="Email" value={fields["Email"]} onChange={set("Email")} placeholder="owner@example.com" type="email" />
              <Field id="address" label="Address" value={fields["Address"]} onChange={set("Address")} placeholder="123 Main St, Newark, NJ 07102" />
            </div>
          </section>

          {/* ── Links ────────────────────────────────────────────── */}
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Links
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="website" label="Website" value={fields["Website"]} onChange={set("Website")} placeholder="https://example.com" type="url" />
              <Field id="maps" label="Google Maps URL" value={fields["Maps URL"]} onChange={set("Maps URL")} placeholder="https://maps.google.com/…" type="url" />
              <Field id="facebook" label="Facebook URL" value={fields["Facebook URL"]} onChange={set("Facebook URL")} placeholder="https://facebook.com/…" type="url" />
              <Field id="instagram" label="Instagram URL" value={fields["Instagram URL"]} onChange={set("Instagram URL")} placeholder="https://instagram.com/…" type="url" />
            </div>
          </section>

          {/* ── CRM metadata ─────────────────────────────────────── */}
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              CRM
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="status">Status</Label>
                <Select value={fields["Status"]} onValueChange={set("Status")}>
                  <SelectTrigger id="status" className="bg-card">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUSES.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Field id="lead-reason" label="Lead Reason" value={fields["Lead Reason"]} onChange={set("Lead Reason")} placeholder="No website found" />
              <Field id="score" label="Score" value={fields["Score"]} onChange={set("Score")} placeholder="0–100" inputMode="numeric" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="notes">Notes</Label>
              <textarea
                id="notes"
                value={fields["Notes"]}
                onChange={(e) => set("Notes")(e.target.value)}
                placeholder="Any extra context…"
                rows={3}
                className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
          </section>

          {/* ── Images ───────────────────────────────────────────── */}
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Images
            </h2>
            <ImagePicker images={images} onAdd={addImages} onRemove={removeImage} />
          </section>

          {/* ── Submit ───────────────────────────────────────────── */}
          <div className="flex items-center gap-3 border-t border-border pt-6">
            <Button type="submit" disabled={submitting} className="gap-1.5">
              <UserPlus className="h-4 w-4" />
              {submitting ? "Creating…" : "Create lead"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => router.push("/admin")}
              disabled={submitting}
            >
              Cancel
            </Button>
          </div>
        </form>
      </main>
    </div>
  )
}
