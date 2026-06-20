# Product

## Users

Local small business owners — restaurants, salons, contractors, auto shops,
lawyers, accountants — who have no website or an outdated one. They are not
technical. They will judge the site in the first 3 seconds on a phone. The
person buying (us, pitching cold) is separate from the person consuming
(the business owner evaluating, then their customers using the live site).

## Product Purpose

Generate a bespoke, content-driven one-page website for each local business
and a cold-outreach pitch (email + Facebook DM) to send them. The site is
built once by Claude into `sites/designs/<slug>/Site.tsx`, served from a
shared Next.js preview app, and handed off to the owner as a standalone
Vercel project when they buy. The owner can edit hours, about, services, and
photos via a magic-link login — no code required. Design is bespoke per
business; content comes from a Supabase row the owner controls.

## Brand Personality

Legitimate. Specific. Confident. Each site must make the business look
credible and trustworthy to their customers — that is the only bar. The
design should feel like it was made for this specific business, grounded in
their real photos, name, type, and location.

## Anti-references

- Generic small-business website builders (Wix, Squarespace defaults) —
  templated, interchangeable, forgettable.
- AI-generated landing pages that look like every other AI-generated page:
  warm off-white/cream backgrounds, Fraunces italic, three-column ruled
  separators, Inter body text, bland blue CTA.
- "Polished but soulless" SaaS aesthetics applied to a pizza shop or a
  plumber — wrong register entirely.
- Designs that are distinctive for distinctiveness's sake — dark themes,
  heavy effects, unusual palettes chosen to avoid the "obvious" answer rather
  than because they fit the business.

## Design Principles

1. **One business, one design.** Commit fully to the aesthetic direction that
   fits this specific business type, location, and personality. Hedge nothing.
2. **Content drives the layout.** Sections that have no content are hidden,
   not faked. Real photos, real hours, real reviews — not placeholders.
3. **Mobile is the primary screen.** Most business owners will open the
   preview on their phone. Design mobile-first; desktop is the upgrade.
4. **Legitimate over flashy.** The goal is to make the business look
   credible and trustworthy to their customers — not to win a design award.
   Motion and effects serve that goal; they don't perform for their own sake.
5. **Every field is editable.** Nothing in `Site.tsx` is hardcoded. Name,
   phone, hours, about, services, photos — all from the `content` prop so
   the owner's edits show up live.

## Accessibility & Inclusion

- Real `alt` text on every image (describe the actual photo, not "photo").
- Color contrast ≥ 4.5:1 for body text, ≥ 3:1 for large headings.
- `tel:` links on phone numbers — one tap to call on mobile.
- `prefers-reduced-motion` respected — wrap motion in the appropriate
  media query or use `motion`'s built-in reduced-motion support.
- Visible focus states on all interactive elements.
