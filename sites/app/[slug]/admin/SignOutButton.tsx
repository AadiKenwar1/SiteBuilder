"use client"

import { supabaseBrowser } from "@/lib/supabase.browser"

export function SignOutButton() {
  async function signOut() {
    await supabaseBrowser().auth.signOut()
    window.location.reload()
  }
  return (
    <button
      onClick={signOut}
      className="text-sm text-blue-600 underline-offset-2 hover:underline"
    >
      Sign out
    </button>
  )
}
