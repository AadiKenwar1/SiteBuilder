import type { ReactNode } from "react"
import "./globals.css"

// Minimal root layout — each business design owns its own fonts, colors, and
// chrome. No global branding here; the shell stays invisible so the design leads.
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
