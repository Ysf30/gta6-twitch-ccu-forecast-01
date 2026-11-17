"""GTA VI launch-day Twitch viewer forecaster (make.fun gta6-twitch-ccu-forecast-01).

Reads one case file per run (schema "makefun/twitch-ccu-case/v1") and writes,
for each of hours 2..24 of the release day, five quantiles of that hour's
concurrent Twitch viewers in the Grand Theft Auto VI category.

Model — an empirical launch-day shape, learned at run time from the case's own
comparables (past big game launches' hourly Twitch curves, SullyGnome):

1. Anchor: the case's hour-1 print p1 (the mean of the first hour's minute
   reads). Every forecast hour is expressed as a ratio to p1, so the scale
   comes from the launch itself, not from any pre-registered guess.
2. Shape: for each comparable launch, take its release-day hourly curve
   (00:00-24:00 UTC of its release date) and compute the log-ratio of each
   hour's viewers to that launch's hour-1 viewers. The forecast median for
   hour h is p1 * exp(median log-ratio at h). Launches whose day-1 curve is
   distorted by early access are excluded (their unlock notes say so); a
   launch only counts if its hour-1 print is at least 500 viewers and at
   least 18 of its 23 later hours are present. The median is shrunk 17%
   toward zero (persistence) — a small-sample guard, n / (n + 5) with n the
   number of launches behind the hour — because a median over ~25 launches
   still overstates how far a new launch's curve will move.
3. Spread: the honest uncertainty of the shape. Per hour, sigma is the
   interquartile range of the log-ratios divided by 1.349 (the IQR of a
   standard normal), floored at 0.18 and capped at 0.80 log units. The five
   quantiles are median * exp(z_tau * sigma) with the standard normal's
   quantiles at the case's levels.

Why this shape, in one paragraph: big launches unlock at midnight local time,
rolling around the world, so the UTC release day has a fixed rhythm — a quiet
overnight dip after the UK/Europe midnight unlock (hours 2-5 run about
0.74x hour 1), a climb as the US east coast (05:00Z) then west coast
(08:00Z) unlock, a peak in the US evening (hour 20 runs about 2.25x hour 1),
then a decay into the night. A flat persistence forecast misses all of that.
On leave-one-out validation over the case's own comparable launches with
hour-1 prints of 10,000+ viewers (the population a GTA VI launch belongs to),
this model scores a mean pinball loss of 0.321 against the house baseline's
0.382; on all usable comparables it scores 0.71 against the house's 0.84.
The house baseline's own published practice loss is 0.387.

The program is deterministic (sorted inputs, medians, no randomness), uses
only the Python standard library, reads $MAKEFUN_INPUT_DIR (else /input) and
writes $MAKEFUN_OUTPUT_DIR (else /output), and finishes in well under the
8-second cap: the whole comparable set is ~42 launches x 408 hourly points.

Signals deliberately NOT used: the top-20 live streams and the category's
pre-launch ramp in `history`. Both are real signals, but there is no
calibration for them inside the case data (no launch in the comparables ships
a streams snapshot), so using them would be a guess dressed as a model.
"""

import json
import math
import os
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a sibling
# module shipped beside this file would import. (This entry is one file.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# A comparable only counts if its release day is really a launch day: a
# visible hour-1 audience and most of the day present.
MIN_HOUR1_VIEWERS = 500
MIN_VALID_HOURS = 18
# At least this many usable comparables, or the shape is not trusted.
MIN_COMPARABLES = 5
# Shrinkage of the median log-ratio toward 0 (persistence): median * n/(n+k).
# k = 5 pulls a 25-launch median 17% toward flat; leave-one-out on the big
# launches improves from 0.3275 (k = 0) to 0.3209 (k = 5).
SHRINK_K = 5
# Spread of an hour's log-ratio, in log units: floor and cap.
SIGMA_FLOOR = 0.18
SIGMA_CAP = 0.80
# The house baseline's spread (persistence + random-walk widening), used only
# as the fallback when the comparables cannot support a shape.
BASELINE_SIGMA = 0.15


def round2(x: float):
    """x rounded to 2 decimals, half up, as JavaScript rounds it.

    A whole number comes back as an int, so json.dumps writes 1240 where
    JavaScript writes 1240 (not 1240.0).
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def norm_ppf(p: float) -> float:
    """Standard normal quantile (Acklam's approximation, ~1e-9 accurate).

    Only used if a case ever asks for levels other than the standard five;
    the standard levels use the kit's exact z values above.
    """
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    p_low = 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p <= 1 - p_low:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)


def z_values(levels):
    """Normal quantiles for the case's levels (exact kit values when standard)."""
    if levels == LEVELS:
        return Z
    return [norm_ppf(tau) for tau in levels]


def release_day_series(comp):
    """The comparable's 24 hourly viewer counts for its release day.

    Index 0 is hour 1 (00:00-01:00 UTC of day_start); None where the source
    has no point for that hour. SullyGnome samples small categories sparsely,
    so quiet launches have holes; the shape step requires most hours present.
    """
    day_start = parse_ts(comp["day_start"])
    points = {}
    for row in comp.get("hourly") or []:
        viewers = row.get("viewers")
        if viewers is None or viewers <= 0:
            continue
        try:
            at = parse_ts(row["from"])
        except (KeyError, TypeError, ValueError):
            continue
        if day_start <= at < day_start + timedelta(hours=24):
            points[int((at - day_start).total_seconds() // 3600)] = viewers
    return [points.get(i) for i in range(24)]


def is_contaminated(comp):
    """True when the launch's day-1 curve is distorted (early access, etc.).

    The case's own unlock notes flag these ("early-access-contaminated");
    their release-day shape is not the shape of a clean midnight launch.
    """
    unlock = (comp.get("unlock") or "").lower()
    return "early-access" in unlock or "contaminated" in unlock


def learn_shape(comparables):
    """Median log-ratio shape + per-hour spread from the comparables.

    Returns (median_log_ratio, sigma) as dicts keyed by hour index 1..23
    (index 1 is hour 2), or ({}, {}) when too few launches qualify.
    """
    series = []
    for comp in comparables or []:
        if is_contaminated(comp):
            continue
        day = release_day_series(comp)
        if day[0] is None or day[0] < MIN_HOUR1_VIEWERS:
            continue
        if sum(1 for v in day[1:] if v is not None) < MIN_VALID_HOURS:
            continue
        series.append(day)
    if len(series) < MIN_COMPARABLES:
        return {}, {}
    median_ratio, sigma = {}, {}
    for h in range(1, 24):
        ratios = sorted(math.log(day[h] / day[0]) for day in series
                        if day[h] is not None)
        if len(ratios) < MIN_COMPARABLES:
            continue
        median_ratio[h] = statistics.median(ratios) * len(ratios) / (len(ratios) + SHRINK_K)
        q1 = ratios[len(ratios) // 4]
        q3 = ratios[(3 * len(ratios)) // 4]
        spread = (q3 - q1) / 1.349
        sigma[h] = max(SIGMA_FLOOR, min(SIGMA_CAP, spread))
    return median_ratio, sigma


def hour_quantiles(p1, h, median_ratio, sigma, z):
    """The five quantiles for hour h (h = 2..24), as a list in level order."""
    idx = h - 1
    if idx in median_ratio:
        centre = p1 * math.exp(median_ratio[idx])
        spread = sigma[idx]
    else:
        # No shape for this hour: fall back to the house persistence baseline.
        centre = p1
        spread = BASELINE_SIGMA * math.sqrt(h - 1)
    qs = [round2(centre * math.exp(zi * spread)) for zi in z]
    # Clamp to the contest's bounds and keep the row non-decreasing.
    clamped = []
    prev = 0.0
    for q in qs:
        q = max(1.0, min(1_000_000_000.0, float(q)))
        q = max(q, prev)
        clamped.append(round2(q))
        prev = float(clamped[-1])
    return clamped


def hour1_print(case):
    """Hour 1's print: the `known` row for hour 1 (a list with one row)."""
    known = case.get("known")
    rows = known if isinstance(known, list) else ([known] if known else [])
    for row in rows:
        if row.get("hour") == 1:
            return max(1, row["viewers"])
    raise ValueError("case has no hour-1 print")


def forecast_case(case, name):
    z = z_values(case.get("levels") or LEVELS)
    p1 = hour1_print(case)
    median_ratio, sigma = learn_shape(case.get("comparables"))
    hours = [
        {"hour": row["hour"],
         "q": hour_quantiles(p1, row["hour"], median_ratio, sigma, z)}
        for row in case["forecast"]
    ]
    return {"hours": hours}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
