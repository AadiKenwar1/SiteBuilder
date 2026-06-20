// Owner admin gate. Per-session, never cached. Three states:
//   1. not logged in      -> magic-link login form
//   2. logged in, not owner-> polite "wrong account" notice
//   3. logged in + owner   -> the edit form
import { notFound } from "next/navigation"

import { supabaseServer } from "@/lib/supabase.server"
import { getContent } from "@/lib/content"
import { LoginForm } from "./LoginForm"
import { EditForm } from "./EditForm"
import { SignOutButton } from "./SignOutButton"

export const dynamic = "force-dynamic"

type Params = { params: Promise<{ slug: string }> }

export default async function AdminPage({ params }: Params) {
  const { slug } = await params
  const content = await getContent(slug)
  if (!content) notFound()

  const supabase = await supabaseServer()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    return <LoginForm slug={slug} businessName={content.business_name} />
  }

  const { data: isOwner } = await supabase.rpc("is_owner", {
    p_slug: slug,
    p_email: user.email,
  })

  if (!isOwner) {
    return (
      <main className="mx-auto max-w-md px-6 py-20 text-center font-sans">
        <h1 className="mb-2 text-xl font-semibold">Wrong account</h1>
        <p className="text-sm text-neutral-500">
          You&rsquo;re signed in as <strong>{user.email}</strong>, which isn&rsquo;t the
          registered owner of this site. Sign out and use the owner email.
        </p>
        <div className="mt-6 flex items-center justify-center gap-4">
          <SignOutButton />
          <a
            href={`/${slug}`}
            className="text-sm text-neutral-500 underline-offset-2 hover:underline"
          >
            ← Back to the site
          </a>
        </div>
      </main>
    )
  }

  return <EditForm slug={slug} initial={content} />
}
