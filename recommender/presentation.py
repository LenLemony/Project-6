"""Format the model results for the plan cards."""

import math


def number_or_none(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def plan_cards(recommendations):
    cards = []
    for rank, row in enumerate(recommendations.to_dict("records"), start=1):
        referral = row["referral_required"]
        referral = None if number_or_none(referral) is None else bool(referral)
        cards.append({
            "rank": rank, "variant_id": row["variant_id"], "name": row["plan_name"],
            "issuer": row["issuer_name"], "plan_type": row["plan_type"],
            "metal_level": row["metal_level"],
            "monthly_premium": float(row["monthly_premium"]),
            "annual_premium": float(row["annual_premium"]),
            "deductible": number_or_none(row["deductible_individual"]),
            "moop": number_or_none(row["moop_individual"]),
            "referrals_required": referral,
            # A single benefit does not tell us the whole plan's network coverage.
            "out_of_network_covered": None,
            "score": float(row["ranking_score"]),
            "covered_people": int(row.get("covered_people", 1)),
        })
    return cards


def money(value, decimals=0):
    number = number_or_none(value)
    return "Not available" if number is None else f"USD {number:,.{decimals}f}"
