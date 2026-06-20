// Reference design — the content-driven fallback/example every new business gets
// until Claude writes a bespoke one. Demonstrates the contract: a single
// `content` prop, every value read from it, sections hidden when their data is
// empty. Plain <img> (no next/image) so an ejected copy stays portable.
import {
  WEEKDAYS,
  WEEKDAY_LABELS,
  type BusinessContent,
} from "@/lib/content"
import "./styles.css"

function telHref(phone: string) {
  return "tel:" + phone.replace(/[^\d+]/g, "")
}

export default function Site({ content }: { content: BusinessContent }) {
  const {
    business_name,
    business_type,
    about,
    phone,
    email,
    address,
    maps_url,
    rating,
    review_count,
    reviews,
    hours,
    holidays_note,
    services,
    photo_hero_url,
    photo_gallery_urls,
    facebook_url,
    instagram_url,
  } = content

  const hasRating = Boolean(rating && Number(rating) > 0)
  const year = new Date().getFullYear()

  return (
    <div className="ref">
      {/* ── Nav ───────────────────────────────────────────────────────── */}
      <header className="ref-nav">
        <a className="ref-brand" href="#top">
          {business_name}
        </a>
        <nav className="ref-navlinks">
          {services.length > 0 && <a href="#services">Services</a>}
          {Object.values(hours).some((h) => h !== "Closed") && <a href="#hours">Hours</a>}
          <a href="#contact">Contact</a>
        </nav>
        {phone && (
          <a className="ref-btn ref-btn--sm" href={telHref(phone)}>
            Call {phone}
          </a>
        )}
      </header>

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="ref-hero" id="top">
        <div className="ref-hero__text">
          {business_type && <p className="ref-eyebrow">{business_type}</p>}
          <h1 className="ref-h1">{business_name}</h1>
          {about && <p className="ref-lead">{about}</p>}
          <div className="ref-hero__cta">
            {phone && (
              <a className="ref-btn" href={telHref(phone)}>
                Call {phone}
              </a>
            )}
            {email && (
              <a className="ref-btn ref-btn--ghost" href={`mailto:${email}`}>
                Email us
              </a>
            )}
          </div>
          {hasRating && (
            <p className="ref-trust">
              <span className="ref-stars" aria-hidden="true">
                ★★★★★
              </span>{" "}
              <strong>{rating}</strong>
              {review_count > 0 && <> from {review_count} reviews</>}
            </p>
          )}
        </div>
        {photo_hero_url && (
          <div className="ref-hero__media">
            <img src={photo_hero_url} alt={`${business_name}`} loading="eager" />
          </div>
        )}
      </section>

      {/* ── Services ──────────────────────────────────────────────────── */}
      {services.length > 0 && (
        <section className="ref-section" id="services">
          <h2 className="ref-h2">What we offer</h2>
          <ul className="ref-services">
            {services.map((s, i) => (
              <li className="ref-service" key={`${s.name}-${i}`}>
                <div className="ref-service__head">
                  <h3>{s.name}</h3>
                  {s.price && <span className="ref-price">{s.price}</span>}
                </div>
                {s.description && <p>{s.description}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Gallery ───────────────────────────────────────────────────── */}
      {photo_gallery_urls.length > 0 && (
        <section className="ref-section ref-section--tight">
          <h2 className="ref-h2">Gallery</h2>
          <div className="ref-gallery">
            {photo_gallery_urls.slice(0, 6).map((url, i) => (
              <figure className="ref-gallery__item" key={i}>
                <img src={url} alt={`${business_name} photo ${i + 1}`} loading="lazy" />
              </figure>
            ))}
          </div>
        </section>
      )}

      {/* ── Reviews ───────────────────────────────────────────────────── */}
      {reviews.length > 0 && (
        <section className="ref-section ref-reviews">
          <h2 className="ref-h2">What customers say</h2>
          <div className="ref-reviews__grid">
            {reviews.slice(0, 3).map((r, i) => (
              <blockquote className="ref-quote" key={i}>
                <p>&ldquo;{r.text}&rdquo;</p>
                <footer>
                  {r.name || "Customer"}
                  {r.stars && <span className="ref-quote__stars"> · {r.stars}★</span>}
                </footer>
              </blockquote>
            ))}
          </div>
        </section>
      )}

      {/* ── Hours ─────────────────────────────────────────────────────── */}
      <section className="ref-section ref-hours" id="hours">
        <h2 className="ref-h2">Hours</h2>
        <table className="ref-hours__table">
          <tbody>
            {WEEKDAYS.map((d) => (
              <tr key={d}>
                <th scope="row">{WEEKDAY_LABELS[d]}</th>
                <td className={hours[d] === "Closed" ? "ref-closed" : undefined}>
                  {hours[d]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {holidays_note && <p className="ref-hours__note">{holidays_note}</p>}
      </section>

      {/* ── Contact ───────────────────────────────────────────────────── */}
      <section className="ref-section ref-contact" id="contact">
        <h2 className="ref-h2">Visit or get in touch</h2>
        <div className="ref-contact__grid">
          <ul className="ref-contact__list">
            {phone && (
              <li>
                <span>Phone</span>
                <a href={telHref(phone)}>{phone}</a>
              </li>
            )}
            {email && (
              <li>
                <span>Email</span>
                <a href={`mailto:${email}`}>{email}</a>
              </li>
            )}
            {address && (
              <li>
                <span>Address</span>
                {maps_url ? (
                  <a href={maps_url} target="_blank" rel="noopener noreferrer">
                    {address}
                  </a>
                ) : (
                  <span className="ref-plain">{address}</span>
                )}
              </li>
            )}
            {(facebook_url || instagram_url) && (
              <li>
                <span>Social</span>
                <span className="ref-social">
                  {facebook_url && (
                    <a href={facebook_url} target="_blank" rel="noopener noreferrer">
                      Facebook
                    </a>
                  )}
                  {instagram_url && (
                    <a href={instagram_url} target="_blank" rel="noopener noreferrer">
                      Instagram
                    </a>
                  )}
                </span>
              </li>
            )}
          </ul>
          {address && (
            <div className="ref-map">
              <iframe
                title={`Map showing ${business_name}`}
                src={`https://www.google.com/maps?q=${encodeURIComponent(address)}&output=embed`}
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              />
            </div>
          )}
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="ref-footer">
        <span>
          &copy; {year} {business_name}
        </span>
        {address && <span className="ref-footer__addr">{address}</span>}
      </footer>
    </div>
  )
}
