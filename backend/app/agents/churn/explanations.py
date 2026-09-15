"""Churn scoring and explanations."""

from typing import Any, Dict, List
import numpy as np
from app.agents.churn.definitions import MODEL_FEATURES, FEATURE_DISPLAY_NAMES, RISK_DESCRIPTORS, TIER_PERCENTILE_BREAKS


def _assign_tiers_by_rank(probabilities: np.ndarray) -> np.ndarray:
    """Assign risk tiers by population-relative rank.

    Uses percentile rank (not value-based thresholds) so that the
    tier distribution is meaningful even when probabilities cluster
    around a few values.  Standard practice in credit and churn
    risk scoring.
    """
    n = len(probabilities)
    # argsort twice gives the 0-indexed rank for each element
    ranks = np.argsort(np.argsort(probabilities))
    # Convert to percentile (0-100)
    percentiles = (ranks + 1) / n * 100

    tiers = np.empty(n, dtype=object)
    for percentile_floor, tier_name in TIER_PERCENTILE_BREAKS:
        mask = percentiles >= percentile_floor
        # Only assign if not already assigned by a higher tier
        unassigned = tiers == None  # noqa: E711
        tiers[mask & unassigned] = tier_name

    return tiers

def _top_shap_factors(
    shap_row: np.ndarray, feature_row: np.ndarray, top_n: int = 3
) -> List[Dict[str, Any]]:
    """Extract the top-N SHAP-based risk factors for one customer."""
    indices = np.argsort(-np.abs(shap_row))[:top_n]
    factors = []

    for idx in indices:
        name = MODEL_FEATURES[idx]
        shap_val = float(shap_row[idx])
        descriptors = RISK_DESCRIPTORS.get(name, ("elevated", "healthy"))
        descriptor = descriptors[0] if shap_val > 0 else descriptors[1]

        factors.append(
            {
                "feature": FEATURE_DISPLAY_NAMES.get(name, name),
                "importance": round(abs(shap_val), 4),
                "value": round(float(feature_row[idx]), 2),
                "direction": "increases risk" if shap_val > 0 else "decreases risk",
                "descriptor": descriptor,
            }
        )

    return factors

def _fmt_factor(f: Dict[str, Any]) -> str:
    """Format a SHAP factor with its numeric value for specificity."""
    name = f.get("feature", "")
    value = f.get("value", 0)
    descriptor = f.get("descriptor", name)
    name_lower = name.lower()

    if "auto" in name_lower and "renew" in name_lower:
        val_str = "off" if value == 0 else "on"
    elif "revenue" in name_lower or "mrr" in name_lower or "value" in name_lower:
        val_str = f"${value:,.0f}"
    elif "days" in name_lower or "recency" in name_lower or "renewal" in name_lower:
        val_str = f"{int(value)}d"
    elif "score" in name_lower or "probability" in name_lower:
        val_str = f"{value:.2f}"
    elif value == int(value):
        val_str = str(int(value))
    else:
        val_str = f"{value:.1f}"

    return f"{descriptor} ({val_str})"

def _generate_explanation(
    prob: float, tier: str, factors: List[Dict[str, Any]]
) -> str:
    """Build a human-readable churn explanation from SHAP-based factors.

    Separates risk-increasing and risk-decreasing (protective) factors so
    explanations remain honest when rank-based tiers diverge from absolute
    probability values.  Includes numeric values for per-customer specificity.
    """
    if not factors:
        return "Insufficient data for detailed risk factor analysis."

    risk_drivers = [f for f in factors if f["direction"] == "increases risk"]
    protective = [f for f in factors if f["direction"] == "decreases risk"]

    if risk_drivers and protective:
        risk_text = _join_natural([_fmt_factor(f) for f in risk_drivers])
        prot_text = _join_natural([_fmt_factor(f) for f in protective])
        return f"Risk driven by {risk_text}, offset by {prot_text}."

    if risk_drivers:
        risk_text = _join_natural([_fmt_factor(f) for f in risk_drivers])
        return f"Risk driven by {risk_text}."

    prot_text = _join_natural([_fmt_factor(f) for f in protective])
    return f"Risk mitigated by {prot_text}."

def _join_natural(items: List[str]) -> str:
    """Join a list with commas and 'and' for the last item."""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
