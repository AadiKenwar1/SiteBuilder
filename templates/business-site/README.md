# business-site — eject overlay

This folder is **not** a standalone app by itself. `scripts/eject.mjs <slug>`
builds the standalone by copying the shared `sites/` app and overlaying the files
here (with the token `{{SLUG}}` replaced by the business slug). Keeping only the
standalone-specific bits here avoids drift from `sites/`.

Overlay contents:
- `middleware.ts` — rewrites `/` → `/<slug>` so the customer's domain root shows
  their site.

The ejected app uses the **anon key only** (safe to transfer via Vercel Claim
Deployments). See `SITES-PLATFORM-PLAN.md` (Step 6) and `CLAUDE.md`.
