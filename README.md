# GTA VI launch-day Twitch viewer forecast

Forecasts how many people watch Grand Theft Auto VI live on Twitch in each
hour of its release day (19 November 2026, UTC), as five quantiles per hour,
from everything recorded up to the end of the day's first hour.

Entry for make.fun competition `gta6-twitch-ccu-forecast-01`
($250, 20 places; deadline 2026-11-19T01:00:00Z).

## Run

```sh
python3 main.py            # reads /input/*.in, writes /output/*.out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only, no network, deterministic, ~0.1 s a case.

## Model

An empirical launch-day shape learned at run time from the case's own
comparables (42 past big launches' hourly Twitch curves):

1. **Anchor** — the case's hour-1 print. Every forecast hour is a ratio to
   it, so the scale comes from the launch itself.
2. **Shape** — for each comparable, the log-ratio of each release-day hour to
   its hour-1 viewers; the forecast median is the (shrunk) median log-ratio.
   Early-access-distorted launches are excluded. The shape says: dip to
   ~0.74x in the overnight hours, climb through the US unlocks, peak ~2.25x
   at hour 20 (US evening), then decay.
3. **Spread** — per-hour IQR of the log-ratios / 1.349, floored at 0.18 and
   capped at 0.80 log units; quantiles are median * exp(z_tau * sigma).

See `NOTES.md` for the research, the assumptions, and the leave-one-out
validation (big launches: mean pinball loss 0.321 vs the house baseline's
0.382).

## License

MIT — see `LICENSE`.
