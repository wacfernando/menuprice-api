"""
Market insights for the MenuPrice recommendation API.

Builds three short, human-readable insights to show next to the price
recommendation:
  1. demand_signal    - how customer-endorsed (top-liked / popular) the category is in the tier
  2. rating_check     - how the user's restaurant rating compares to competitors
  3. menu_suggestion  - the best-endorsed category in the tier + local supply of it

Only uses columns that already exist in the reference CSV. Optional columns
(restaurant_name, area) are used when present and skipped gracefully when not.
"""
import pandas as pd

MIN_CATEGORY_DISHES = 100  # a category needs this many dishes in a tier to be ranked
MIN_AREA_DISHES     = 15   # min dishes before an area-level comparison is trusted
MIN_OWN_DISHES      = 30   # below this, do not even report a rate for the chosen category

NOTE = "Based on category-level popularity flags, not individual dish reviews."


# ── helpers ───────────────────────────────────────────────────────────────────
def _col(df, name):
    return df[name] if name in df.columns else pd.Series(0, index=df.index)


def prepare_reference(df):
    """Call once at startup. Adds an `_endorsed` flag (top-liked OR popular)."""
    df = df.copy()
    df["_endorsed"] = (
        (_col(df, "is_top_liked") == 1) | (_col(df, "is_popular") == 1)
    ).astype(int)
    return df


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _area_mask(df, area, area_enc):
    """Works whether the CSV stores area as text or only as an encoded number."""
    if "area" in df.columns and pd.api.types.is_string_dtype(df["area"]):
        return df["area"] == area
    if "area_encoded" in df.columns and area_enc is not None:
        return df["area_encoded"] == area_enc
    return pd.Series(False, index=df.index)


def _n_restaurants(df):
    return int(df["restaurant_name"].nunique()) if "restaurant_name" in df.columns else None


def _avg_rating(df):
    r = pd.to_numeric(df["restaurant_overall_rating"], errors="coerce")
    if "restaurant_name" in df.columns:
        r = r.groupby(df["restaurant_name"]).mean()   # each restaurant counts once
    r = r.dropna()
    return float(r.mean()) if len(r) else None


def _tier_category_rates(df, tier):
    t = df[df["restaurant_tier"] == tier]
    g = t.groupby("dish_category_std").agg(
        dishes=("_endorsed", "size"), endorsed=("_endorsed", "sum")
    )
    g = g[g["dishes"] >= MIN_CATEGORY_DISHES].copy()
    g["rate"] = g["endorsed"] / g["dishes"] * 100
    return g.sort_values(["rate", "dishes"], ascending=False)


# ── main entry point ──────────────────────────────────────────────────────────
def build_insights(df, tier, area, area_enc, category, user_rating):
    rates    = _tier_category_rates(df, tier)
    tier_cat = df[(df["restaurant_tier"] == tier) & (df["dish_category_std"] == category)]

    # 1) Demand signal ---------------------------------------------------------
    if category in rates.index:
        row  = rates.loc[category]
        rank = list(rates.index).index(category) + 1
        if int(row["endorsed"]) == 0:
            demand = (f"No {category} dishes in the {tier} tier are flagged top-liked "
                      f"or popular, so there is little customer-endorsement signal here.")
        else:
            rank_txt = "the most" if rank == 1 else f"the {_ordinal(rank)} most"
            demand = (f"{category} is {rank_txt} customer-endorsed category in the {tier} tier "
                      f"({int(row['endorsed'])} of {int(row['dishes'])} dishes flagged "
                      f"top-liked or popular).")
    else:
        n_dishes = len(tier_cat)
        n_end    = int(tier_cat["_endorsed"].sum())
        if n_dishes >= MIN_OWN_DISHES:
            demand = (f"{n_end} of {n_dishes} {category} dishes in the {tier} tier are flagged "
                      f"top-liked or popular ({n_end / n_dishes * 100:.1f}%), but there are too "
                      f"few dishes to rank it against other categories.")
        else:
            demand = (f"There are too few {category} dishes in the {tier} tier "
                      f"to measure customer endorsement reliably.")

    # 2) Rating check ----------------------------------------------------------
    in_area = tier_cat[_area_mask(tier_cat, area, area_enc)]
    if len(in_area) >= MIN_AREA_DISHES:
        scope, scope_label = in_area, f"in {area}"
    else:
        scope, scope_label = tier_cat, f"across all areas ({area} has too few for a fair comparison)"

    avg = _avg_rating(scope) if len(scope) else None
    if avg is None:
        rating_check = "Not enough rating data to compare against competitors."
    elif user_rating is None or user_rating < 1.0:
        rating_check = (f"No rating set yet. {category} competitors {scope_label} average "
                        f"{avg:.2f}, so early reviews will matter for your positioning.")
    else:
        diff = user_rating - avg
        word = "below" if diff < -0.2 else "above" if diff > 0.2 else "in line with"
        rating_check = (f"Your rating ({user_rating:.1f}) is {word} the {avg:.2f} average "
                        f"of {category} competitors {scope_label}.")

    # 3) Menu suggestion -------------------------------------------------------
    others = rates.drop(index=category, errors="ignore")
    others = others[others["endorsed"] > 0]
    if others.empty:
        menu = "No other category stands out in this tier based on the available data."
    else:
        best, best_rate = others.index[0], float(others.iloc[0]["rate"])
        if category in rates.index and rates.index[0] == category:
            lead = (f"Your category already leads the {tier} tier. The next strongest is "
                    f"{best} ({best_rate:.1f}%)")
        else:
            lead = f"{best} has the strongest endorsement rate in {tier} ({best_rate:.1f}%)"

        best_df   = df[(df["restaurant_tier"] == tier) & (df["dish_category_std"] == best)]
        best_area = best_df[_area_mask(best_df, area, area_enc)]
        if len(best_area) > 0:
            med = best_area["selling_price_lkr"].median()
            n   = _n_restaurants(best_area)
            if n is None:
                supply = f"{len(best_area)} {area} dishes already exist at a median of Rs.{med:,.0f}."
            else:
                supply = (f"{n} {area} restaurant{'s' if n != 1 else ''} already "
                          f"offer{'s' if n == 1 else ''} it at a median of Rs.{med:,.0f}.")
            menu = f"{lead}, and {supply}"
        else:
            menu = (f"{lead}, and no {tier} restaurants in {area} offer it in this "
                    f"dataset, which could be a gap.")

    return {
        "demand_signal":   demand,
        "rating_check":    rating_check,
        "menu_suggestion": menu,
        "note":            NOTE,
    }
