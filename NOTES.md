# NOTES — gta6-twitch-ccu-forecast-01

Research, model assumptions, and validation for the GTA VI Twitch CCU
forecaster. Checked 2026-11-17 (WIB).

## The launch (ground facts)

- Grand Theft Auto VI releases **19 November 2026** on PlayStation 5 and
  Xbox Series X|S (no PC until 2027), single-player. Unlock is midnight
  local time, rolling: New Zealand first (18 Nov 11:00Z), central Europe
  23:00Z, UK 00:00Z, US East 05:00Z, US West 08:00Z. (Kit RULES.txt /
  competition.yaml; Rockstar.)
- The counted figure is Twitch's concurrent live viewers in the "Grand Theft
  Auto VI" category (Twitch game id 1867279146) — the directory-page number.
  The house reads it once a minute from Twitch's public GraphQL API. An
  hour's print is the mean of its valid minute reads.
- Pre-launch the category already sat at ~1,240 viewers / 181 channels
  (house probe 2026-11-17, kit competition.yaml); GTA V's category read
  81,611 viewers / 3,514 channels at the same moment.

## Hype signals (why this launch is the biggest Twitch event ever)

- Trailer 1 (4 Dec 2023): **90.4M YouTube views in 24 hours** — Guinness
  World Record for most-viewed video game reveal; ~304M total by Oct 2026.
- Trailer 2 (6 May 2025): **475M views across all platforms in 24 hours**
  (Rockstar via The Hollywood Reporter) — the biggest video launch of all
  time, ahead of Deadpool & Wolverine (365M).
- Extended Look (27 Aug 2026): ~37M YouTube views; Launch Trailer
  (15 Oct 2026): ~80M.
- Gameplay reveal: **3.97M peak viewers across platforms** from 9,000+
  streamers, Twitch taking 44% of hours watched (Streams Charts).
- Press estimate for launch-day Twitch peak: **1.5–2.5M** concurrent viewers
  (DuvalWire, Nov 2026 — their own math, not a tracker forecast).

## Comparable launch peaks (Twitch, for scale)

- GTA V: all-time peak **1,140,747** (TwitchTracker, 3 May 2021); NoPixel
  3.0 record 438,085 (Feb 2021); still ~72k average concurrent viewers in
  2026.
- Cyberpunk 2077: **1,140,960** peak (Dec 2020). Elden Ring: **909,800**
  (Feb 2022). Hogwarts Legacy: 1.21M peak (Feb 2023) — but early-access
  contaminated (72h early access), so excluded from the shape.
- The case's own data source for all of these: SullyGnome.com hourly Twitch
  category averages (kit `input/NOTICE.txt`).

## Model assumptions

1. **Hour-1 anchoring.** The final case's hour-1 print (00:00–01:00 UTC,
   UK + CET + NZ/AU unlocked, US not yet) carries the launch's scale. All
   ratios are relative to it, so the model never bakes in an absolute
   viewer count from press estimates.
2. **The launch-day rhythm is shared across rolling-midnight launches.**
   Median log-ratio shape over 25 clean comparables (38 in a practice case,
   42 in the final; 9 early-access-contaminated excluded; a launch counts
   only with hour-1 >= 500 viewers and >= 18 of 23 later hours present):
   hours 2–5 dip to ~0.74x hour 1, hours 6–8 climb through the US unlocks,
   peak ~2.25x at hour 20 (19:00–20:00 UTC, US evening), decay to ~1.75x
   by hour 24. Every hour is supported by all 25 launches.
3. **Honest spread, not a point forecast.** Per-hour sigma = IQR of the
   log-ratios / 1.349, floored 0.18, capped 0.80. Launches genuinely
   disagree about midday (IQR up to ~1.1 log units), so midday quantiles
   are wide; the pinball loss pays for both over- and under-confidence.
4. **Shrinkage.** Median log-ratios are pulled 17% toward zero
   (n / (n + 5)) — a small-sample guard against overstating the move.
5. **What is NOT used, and why:** the top-20 live streams and the
   pre-launch ramp in `history` are real signals, but no launch in the
   comparables ships a streams snapshot, so there is no calibration for
   them inside the case data. Using them would be a guess dressed as a
   model. The comparables' shape already carries the launch-day pattern.

## Validation (leave-one-out over the case's own comparables)

Method: each usable comparable as pseudo-target; shape learned from all
other usable comparables; pinball loss on the log scale, same 5 levels.

| Population | This model | House baseline |
|---|---|---|
| Big launches (hour-1 >= 10k, n=19) | **0.3209** | 0.3820 |
| All usable comparables (n=25) | 0.7075 | 0.8399 |

The house baseline's published practice loss is 0.387 — the LOO reproduces
it (0.3820 on big launches), so the comparison is honest. Sensitivities:
sigma cap 0.65 → 0.3292, 0.80 → 0.3209, 1.00 → 0.3332 (0.80 kept);
shrinkage k=0 → 0.3275, k=5 → 0.3209, k=10 → 0.3203 (k=5 kept, the
k=5/k=10 gap is noise); console-only shape alone is no better than the
all-clean shape on big launches (0.3243 blended vs 0.3224).

Caveat: practice answers are the historical source's hourly counts, not the
final's minute-mean prints, and the final is one launch, not 19 — the edge
is an expectation, not a guarantee. GTA VI is bigger than every comparable,
so the peak ratio is the most extrapolated number in the forecast; the
wide midday spread is the model's honest answer to that.

## Local test results (2026-11-17)

- `python3 main.py` on the kit's 4 practice cases: 0.44 s for all 4
  (~0.1 s a case, cap is 8 s); outputs byte-identical across two runs;
  all 4 outputs valid (23 rows, hours 2–24, 5 non-decreasing quantiles
  each in (0, 1e9], <= 1,600 bytes each).
- Example (p02, God of War Ragnarök, hour-1 print 269,517): hour-2
  median 240,309; hour-12 median 275,836; hour-20 median 605,870
  (2.25x); hour-24 median 532,066.
