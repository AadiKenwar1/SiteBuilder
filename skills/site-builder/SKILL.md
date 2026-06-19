---
name: site-builder
description: How to design and build a one-page mockup website for a small business, based on its info.txt and images/.
---

# Site Builder

## Goal
Produce a single-page website (`site/index.html` + `site/styles.css`, plus
any assets) that looks like it was designed specifically for this business -
not a template with the name swapped in.

## Before you design
Read `info.txt` fully, then read `skills/impeccable/SKILL.md` completely
before writing a single line of code. That skill is the primary guide for
all visual and aesthetic decisions — follow its guidance to commit to a bold,
specific aesthetic direction for this business before touching HTML or CSS. The business type, name, location, and notes should
drive every decision. A power-washing company and a bakery should not end up
looking similar — if two businesses in a row would get a similar
palette/layout, deliberately pick something different for the second one.

### What's in info.txt
Folders created by the lead scraper (`leads/`) or the intake form carry an
extended `info.txt`. Mine it for real, specific content — empty fields just
mean it wasn't found, so design around what's there:
- **Hours** — render a real hours block in Contact instead of a placeholder.
- **Services** — seed the Services/Menu section from this, not invented items.
- **About** — ground the About/Story section in this blurb.
- **Rating / Review count** — a real trust signal (e.g. "5.0★ on Google").
- **Year established** — "Serving since 2008" style lines.
- **Website** — for outdated-site leads, their current URL (don't link it).
- **Facebook / Instagram** — real social links in nav/footer.
- **Customer reviews (GENUINE …)** — see Testimonial below.

## Design variety
For each business, choose:
- **A color palette** — if `images/` contains a logo, run:
  ```
  python3 skills/site-builder/extract-colors.py <path-to-logo>
  ```
  Use the CSS custom properties it outputs directly in `styles.css`. Do not
  override or second-guess them — they come from the business's own brand.
  If there is no logo, pick a palette from `skills/ui-ux-pro-max/SKILL.md`
  that fits the trade and doesn't default to blue-and-white.
- **A font pairing** — pick one from `skills/ui-ux-pro-max/SKILL.md`. Match
  the personality: a bakery can afford a warm serif or script accent; a
  contractor probably wants something clean and sturdy. Load via Google Fonts.
  That's all you need from ui-ux-pro-max — ignore the rest of it.
- **A hero layout** — pick whichever fits the content you actually have:
  - Full-bleed color/gradient block with large type (no photos needed)
  - Split layout: text left, image or graphic right
  - Centered with a strong background color and bold headline
  - Full-bleed photo background (only if `images/` has a strong photo)
- **A visual motif** that gives the page a distinct feel — diagonal section
  dividers, a bold oversized headline that bleeds off-screen, a colored
  sidebar accent, a card grid with strong drop shadows, a dark hero with a
  light body, overlapping elements, a large icon or SVG illustration. Pick
  one and carry it through the page. Without this, every site looks the same.

## Page structure
The page must feel designed for this specific business, not like a template.
The sections below are defaults — rename them, reorder them, or replace them
if something fits the business better. What matters is that the result looks
intentional and specific, not generic.

**Always include:**
- **Nav** — business name/logo on the left, 3-4 anchor links on the right.
  On mobile, collapse to a simple stacked or hamburger-style menu.
- **Hero** — the single most important impression. Lead with the business
  name and a punchy, specific tagline written from `info.txt` (not "Welcome
  to our website"). CTA button should match the business: "Call Now",
  "Get a Free Quote", "See Our Work", "Book a Cut", "Order Now" — not a
  generic label. Link to `tel:` or `mailto:` from `info.txt`.
- **Contact** — real address, phone (`tel:` link), email (`mailto:` link),
  Google Maps `<iframe>` if an address is available.
- **Footer** — business name, current year.

**Include as appropriate (rename to fit the business):**
- **About / Our Story / Who We Are** — 1-2 short paragraphs grounded in
  specifics from `info.txt`. If you have nothing specific, keep it short.
  Don't pad with generic claims like "we are committed to excellence."
- **Services / What We Do / Specialties / Menu** — present offerings in a
  layout that fits the type: icon cards for contractors, a styled price list
  for salons, a two-column grid for food businesses. 3-5 items max.
- **Why Us / How It Works / Our Process** — use this instead of a generic
  About section if the business has a clear differentiator or a step-by-step
  process (movers, cleaners, contractors). 3 steps or reasons in a visual
  row works well here.
- **Gallery / Our Work** — only include if `images/` has 3+ usable photos.
  A CSS grid or simple flexbox row. Don't fake it with placeholders.
- **Testimonial** — if `info.txt` has a "Customer reviews (GENUINE …)"
  section, those are REAL reviews scraped from Google Maps: use them as
  actual testimonials, quoted verbatim with the reviewer's name, and do NOT
  label them as samples. If there is no genuine-reviews section and no real
  quote elsewhere in `info.txt`, skip testimonials entirely — a missing one
  looks better than a fake the owner will instantly recognize as invented
  (any quote you write yourself must be clearly labeled "Sample review").

## Using images
- **Measure first — don't guess dimensions.** Before choosing a hero or
  gallery layout, run:
  ```
  python3 skills/site-builder/measure-images.py businesses/<slug>/images
  ```
  It prints each photo's real size, aspect ratio, orientation, the exact
  `width`/`height` attrs to paste into `<img>`, a low-res flag, and a layout
  hint. Build the layout around the real ratios. Guessed dimensions are the
  usual cause of weird galleries: a square photo forced into a landscape slot
  crops hard, and a fixed grid-cell ratio crops every photo that doesn't match.
  For a mix of orientations, use masonry (`column-count`) or give each
  `<figure>` its own `aspect-ratio` rather than one shared grid cell. Don't use
  a photo flagged low-res as a full-bleed hero/background.
- If `images/` contains a logo, use it in the nav (and as a favicon if
  reasonable).
- If `images/` contains usable photos of the location/product, use 1-3 of
  them - hero background, about section, or a small gallery. "Usable" means
  reasonably lit and in focus; don't force a bad photo in just because it
  exists.
- If `images/` is empty or low quality, lean entirely on color, type, and
  simple CSS/SVG (shapes, gradients, a small icon set). Don't reach for stock
  photography or placeholder images - they read as unfinished.

## Common embeds
Third-party widgets the business could add. Only include one in the mockup
if `info.txt` notes they already use that service - otherwise mention it as
a suggestion in `pitch.md`, not in the site itself.

- **Bookings/appointments**: Calendly, Square Appointments, Acuity -
  typically a `<div>` + `<script src="...">` embed.
- **Online ordering**: Square Online, Toast (restaurants).
- **Contact form (no backend needed)**: Formspree, or a plain `mailto:` form
  action.
- **Maps**: Google Maps embed `<iframe>` using the address from `info.txt`.
- **Reviews**: a link to their Google Business or Yelp page, if known.

## Technical requirements
- Single `index.html`, separate `styles.css` (vanilla CSS, no build step or
  framework).
- Mobile-first and responsive - most of these get opened on a phone.
- `<meta name="robots" content="noindex, nofollow">` in `<head>`.
- Real `alt` text on every image.
- Visible focus states on links/buttons (don't remove the default outline
  without replacing it).
- No tracking scripts, no analytics, no external dependencies beyond Google
  Fonts and any embed explicitly justified above.
