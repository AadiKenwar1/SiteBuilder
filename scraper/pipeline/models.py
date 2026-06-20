from dataclasses import dataclass, field


@dataclass
class Review:
    business_id:   str = ""
    business_name: str = ""
    reviewer:      str = ""
    stars:         str = ""
    date:          str = ""
    text:          str = ""


@dataclass
class Lead:
    # ── Identity ──────────────────────────────────────────────────────────────
    business_id:      str = ""   # BIZ_001 … links to Reviews sheet
    business_name:    str = ""
    business_type:    str = ""
    area:             str = ""
    maps_url:         str = ""

    # ── Contact ───────────────────────────────────────────────────────────────
    address:          str = ""
    phone:            str = ""
    email:            str = ""

    # ── Social ────────────────────────────────────────────────────────────────
    facebook_url:     str = ""
    instagram_url:    str = ""

    # ── Rich info (for website creation) ──────────────────────────────────────
    rating:           str = ""   # "4.2"
    review_count:     int = 0
    price_range:      str = ""   # "$" / "$$" / "$$$"
    hours:            str = ""   # "Mon: 9am-5pm | Tue: 9am-5pm …"
    services:         str = ""   # comma-separated
    about:            str = ""   # description blurb (Maps + FB + IG)
    logo_url:         str = ""   # profile photo from Facebook or Instagram
    year_established: str = ""   # "2008"

    # ── Lead metadata ─────────────────────────────────────────────────────────
    lead_reason:      str = ""   # "No website" or "Outdated — © 2012"
    score:            int = 0    # likelihood-to-buy ranking (0–100)

    # ── Photos ────────────────────────────────────────────────────────────────
    photo_dir:        str = ""   # local folder of downloaded real photos
    photo_count:      int = 0    # number of photos saved (incl. hero)

    # ── Internal (excluded from output) ───────────────────────────────────────
    slug:             str  = field(default="", repr=False)  # stable identity / folder key
    website_url:      str  = field(default="", repr=False)
    logo_verified:    bool = field(default=False, repr=False)  # True only when social page name-matched
