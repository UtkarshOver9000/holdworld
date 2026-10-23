# The India Hold Atlas

No public data exists on how deep Indian helpline menus go or how long it takes to reach a person, by sector and hour. The Atlas fills that gap, and turns HoldWorld's `ASSUMED` parameters into `ATLAS` ones.

## Protocol

- **Sample:** about 24 helplines across sectors:
  - banks ×5
  - telecom ×3 (long numbers, not short codes)
  - airlines ×2
  - e-commerce ×3
  - electricity/gas ×3
  - government ×4
  - insurance ×2

  Take every number from the company's official site.
- **Two slots each:** weekday 11:00–13:00 and 19:00–21:00. That's about 48 calls, roughly 8 hours of phone time.
- **One row per call:** fill in `data/atlas/atlas_template.csv`. Time each segment with a stopwatch.
- **Record only machine audio** (IVR prompts, hold music, announcements). Stop at pickup, so no one's voice is stored.
- **Ask the executive a genuine question** (hours, a branch, a process), so nobody's time is wasted on a test.
- **On a few calls only,** stay silent for a few seconds after the greeting and note when the executive says "hello?" and when they hang up. This is the one number nobody has published.

## Using it

```bash
python -m holdworld.atlas data/atlas/my_calls.csv
```

This prints the measured medians next to the current assumptions and registers them as `ATLAS` parameters for the next run.
