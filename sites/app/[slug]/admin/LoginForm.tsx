"use client"

import { useState } from "react"
import { supabaseBrowser } from "@/lib/supabase.browser"

export function LoginForm({
  slug,
  businessName,
}: {
  slug: string
  businessName: string
}) {
  const [email, setEmail] = useState("")
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle")
  const [msg, setMsg] = useState("")

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setState("sending")
    setMsg("")
    const supabase = supabaseBrowser()
    const cleaned = email.trim().toLowerCase()

    // Friendly pre-check; the RLS-equivalent functions are the real gate, so even
    // a magic link sent to the wrong address can't edit anything.
    const { data: isOwner, error: rpcErr } = await supabase.rpc("is_owner", {
      p_slug: slug,
      p_email: cleaned,
    })
    if (rpcErr) {
      setState("error")
      setMsg(rpcErr.message)
      return
    }
    if (!isOwner) {
      setState("error")
      setMsg("That email isn't the registered owner for this site.")
      return
    }

    const redirectTo = `${window.location.origin}/auth/callback?next=/${slug}/admin`
    const { error } = await supabase.auth.signInWithOtp({
      email: cleaned,
      options: { emailRedirectTo: redirectTo },
    })
    if (error) {
      setState("error")
      setMsg(error.message)
      return
    }
    setState("sent")
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 font-sans">
      <div className="rounded-2xl border border-neutral-200 p-8 shadow-sm">
        <h1 className="text-xl font-semibold">{businessName || "Owner login"}</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Sign in to edit your site. We&rsquo;ll email you a one-time login link &mdash;
          no password needed.
        </p>

        {state === "sent" ? (
          <p className="mt-6 rounded-lg bg-green-50 p-4 text-sm text-green-800">
            Check <strong>{email.trim()}</strong> for your login link. You can close this
            tab &mdash; the link opens your editor.
          </p>
        ) : (
          <form onSubmit={onSubmit} className="mt-6 space-y-3">
            <label className="block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-900"
              placeholder="you@business.com"
            />
            {msg && <p className="text-sm text-red-600">{msg}</p>}
            <button
              type="submit"
              disabled={state === "sending"}
              className="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {state === "sending" ? "Sending…" : "Send login link"}
            </button>
          </form>
        )}

        <a
          href={`/${slug}`}
          className="mt-6 inline-block text-sm text-neutral-500 underline-offset-2 hover:underline"
        >
          ← Back to the site
        </a>
      </div>
    </main>
  )
}
