"""
Lead scoring — ranks screened candidates by how likely they are to buy a website.

Weights live in config.SCORE_WEIGHTS so they can be tuned without touching logic.
Called twice in the pipeline:
  • Phase 1 (screen)  — ranks the candidate pool with the cheap signals available.
  • Phase 2 (enrich)  — recomputed for keepers once email + photos are filled in.
score_lead() reads whatever is populated on the Lead, so partial leads score fine.
"""
from .config import SCORE_WEIGHTS, REVIEW_SWEET_SPOT, VISUAL_BUSINESS_TYPES
from .models import Lead


def _to_float(s) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def score_lead(lead: Lead) -> int:
    w = SCORE_WEIGHTS
    score = 0

    # Website pain — no site is a stronger buy signal than an outdated one.
    if "No website" in lead.lead_reason:
        score += w["no_website"]
    elif "Outdated" in lead.lead_reason:
        score += w["outdated_website"]

    # Reachability — can we actually sell to them?
    if lead.email:
        score += w["has_email"]
    if lead.phone:
        score += w["has_phone"]

    # Online presence — owner already invests in being found online.
    if lead.facebook_url:
        score += w["has_facebook"]
    if lead.instagram_url:
        score += w["has_instagram"]

    # Review count sweet spot — established, but not a chain.
    lo, hi = REVIEW_SWEET_SPOT
    if lo <= lead.review_count <= hi:
        score += w["reviews_sweet_spot"]

    # Rating — a well-liked business is a better prospect.
    rating = _to_float(lead.rating)
    if rating >= 4.0:
        score += w["good_rating"]
    elif rating >= 3.0:
        score += w["good_rating"] // 2

    # Visual business — benefits most from a real website.
    btype = (lead.business_type or "").lower()
    if any(v in btype for v in VISUAL_BUSINESS_TYPES):
        score += w["visual_business"]

    # Established — has a track record.
    if lead.year_established:
        score += w["established"]

    # Assets — we actually gathered photos to build with.
    if lead.photo_count:
        score += w["has_photos"]

    return min(score, 100)
