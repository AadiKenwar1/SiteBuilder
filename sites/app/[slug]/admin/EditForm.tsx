"use client"

import { useState } from "react"
import {
  WEEKDAYS,
  WEEKDAY_LABELS,
  type BusinessContent,
  type Service,
  type Hours,
} from "@/lib/content"
import { supabaseBrowser } from "@/lib/supabase.browser"

export function EditForm({
  slug,
  initial,
}: {
  slug: string
  initial: BusinessContent
}) {
  const [hours, setHours] = useState<Hours>(initial.hours)
  const [holidaysNote, setHolidaysNote] = useState(initial.holidays_note)
  const [phone, setPhone] = useState(initial.phone)
  const [about, setAbout] = useState(initial.about)
  const [services, setServices] = useState<Service[]>(initial.services)
  const [facebook, setFacebook] = useState(initial.facebook_url)
  const [instagram, setInstagram] = useState(initial.instagram_url)
  const [heroUrl, setHeroUrl] = useState(initial.photo_hero_url)

  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null)

  const supabase = supabaseBrowser()

  function setDay(day: (typeof WEEKDAYS)[number], value: string) {
    setHours((h) => ({ ...h, [day]: value }))
  }
  function addService() {
    setServices((s) => [...s, { name: "", description: "", price: "" }])
  }
  function setService(i: number, patch: Partial<Service>) {
    setServices((s) => s.map((row, idx) => (idx === i ? { ...row, ...patch } : row)))
  }
  function removeService(i: number) {
    setServices((s) => s.filter((_, idx) => idx !== i))
  }

  async function onHeroChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setMsg(null)
    const safe = file.name.replace(/[^a-zA-Z0-9.]/g, "-")
    const path = `${slug}/hero-${Date.now()}-${safe}`
    const { error } = await supabase.storage
      .from("business-photos")
      .upload(path, file, { upsert: true, contentType: file.type })
    if (error) {
      setUploading(false)
      setMsg({ kind: "err", text: `Photo upload failed: ${error.message}` })
      return
    }
    const { data } = supabase.storage.from("business-photos").getPublicUrl(path)
    setHeroUrl(data.publicUrl)
    setUploading(false)
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMsg(null)
    const patch = {
      hours,
      holidays_note: holidaysNote,
      phone,
      about,
      services: services.filter((s) => s.name.trim()),
      facebook_url: facebook,
      instagram_url: instagram,
      photo_hero_url: heroUrl,
    }
    const { error } = await supabase.rpc("update_business_content", {
      p_slug: slug,
      p_patch: patch,
    })
    if (error) {
      setSaving(false)
      setMsg({ kind: "err", text: error.message })
      return
    }
    // Refresh the public page cache so the change is visible right away.
    await fetch(`/api/revalidate?slug=${encodeURIComponent(slug)}`, { method: "POST" })
    setSaving(false)
    setMsg({ kind: "ok", text: "Saved. Your live site is updating now." })
  }

  async function signOut() {
    await supabase.auth.signOut()
    window.location.reload()
  }

  const input =
    "w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-900"
  const label = "block text-sm font-medium mb-1"

  return (
    <main className="mx-auto max-w-2xl px-6 py-10 font-sans text-neutral-900">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{initial.business_name}</h1>
          <p className="text-sm text-neutral-500">Edit your site</p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={`/${slug}`}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-blue-600 underline-offset-2 hover:underline"
          >
            View site ↗
          </a>
          <button
            onClick={signOut}
            className="text-sm text-neutral-500 underline-offset-2 hover:underline"
          >
            Sign out
          </button>
        </div>
      </header>

      <form onSubmit={onSave} className="space-y-8">
        {/* Hero photo */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Hero photo
          </h2>
          {heroUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={heroUrl}
              alt="Current hero"
              className="mb-3 h-40 w-full rounded-lg object-cover"
            />
          )}
          <input type="file" accept="image/*" onChange={onHeroChange} className="text-sm" />
          {uploading && <p className="mt-2 text-sm text-neutral-500">Uploading…</p>}
        </section>

        {/* Contact */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Contact
          </h2>
          <div>
            <label className={label} htmlFor="phone">Phone</label>
            <input id="phone" className={input} value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className={label} htmlFor="fb">Facebook URL</label>
              <input id="fb" className={input} value={facebook} onChange={(e) => setFacebook(e.target.value)} />
            </div>
            <div>
              <label className={label} htmlFor="ig">Instagram URL</label>
              <input id="ig" className={input} value={instagram} onChange={(e) => setInstagram(e.target.value)} />
            </div>
          </div>
        </section>

        {/* About */}
        <section>
          <label className={label} htmlFor="about">About</label>
          <textarea
            id="about"
            rows={4}
            className={input}
            value={about}
            onChange={(e) => setAbout(e.target.value)}
          />
        </section>

        {/* Hours */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Hours
          </h2>
          <div className="space-y-2">
            {WEEKDAYS.map((d) => (
              <div key={d} className="flex items-center gap-3">
                <span className="w-28 text-sm">{WEEKDAY_LABELS[d]}</span>
                <input
                  className={input}
                  value={hours[d]}
                  onChange={(e) => setDay(d, e.target.value)}
                  placeholder='e.g. 9 AM–5 PM or "Closed"'
                />
              </div>
            ))}
          </div>
          <div className="mt-3">
            <label className={label} htmlFor="hol">Holidays note</label>
            <input
              id="hol"
              className={input}
              value={holidaysNote}
              onChange={(e) => setHolidaysNote(e.target.value)}
              placeholder="Reduced hours on major holidays — call ahead."
            />
          </div>
        </section>

        {/* Services */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
              Services
            </h2>
            <button
              type="button"
              onClick={addService}
              className="text-sm font-medium text-blue-600 hover:underline"
            >
              + Add
            </button>
          </div>
          <div className="space-y-3">
            {services.map((s, i) => (
              <div key={i} className="rounded-lg border border-neutral-200 p-3">
                <div className="flex gap-2">
                  <input
                    className={input}
                    value={s.name}
                    onChange={(e) => setService(i, { name: e.target.value })}
                    placeholder="Service name"
                  />
                  <input
                    className="w-32 rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-900"
                    value={s.price ?? ""}
                    onChange={(e) => setService(i, { price: e.target.value })}
                    placeholder="Price"
                  />
                  <button
                    type="button"
                    onClick={() => removeService(i)}
                    aria-label="Remove service"
                    className="px-2 text-neutral-400 hover:text-red-600"
                  >
                    ✕
                  </button>
                </div>
                <input
                  className={`${input} mt-2`}
                  value={s.description ?? ""}
                  onChange={(e) => setService(i, { description: e.target.value })}
                  placeholder="Short description (optional)"
                />
              </div>
            ))}
            {services.length === 0 && (
              <p className="text-sm text-neutral-400">No services yet — add one.</p>
            )}
          </div>
        </section>

        {/* Save bar */}
        <div className="sticky bottom-0 -mx-6 border-t border-neutral-200 bg-white/90 px-6 py-4 backdrop-blur">
          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={saving || uploading}
              className="rounded-lg bg-neutral-900 px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
            {msg && (
              <span className={msg.kind === "ok" ? "text-sm text-green-700" : "text-sm text-red-600"}>
                {msg.text}
              </span>
            )}
          </div>
        </div>
      </form>
    </main>
  )
}
