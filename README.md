# HoldWorld

**A simulated India of customer-care phone lines, built on real data, for testing an AI agent that waits on hold for you.**

HoldForMe (our Bolna Buildathon project) dials a helpline, gets through the phone menu, waits on hold, notices the moment a real person answers, and either connects you or finishes the task itself. HoldWorld is the world it is tested in:

- **Helplines from official menus.** SBI's contact-centre tree, KVB's TPIN-gated IVRS and Union Bank's "agent at any point" structure, as published on their own pages, relabelled so no brand is impersonated. Six more sectors (telecom, airline, e-commerce, electricity, government, gas) are clearly tagged as assumed until the India Hold Atlas measures them.
- **Current queue evidence plus event-level validation.** The dashboard includes California DHCS county call-centre reports from Jan–Jun 2026 (volume, average waits by language, abandonment) alongside the 440,837 individual calls from the 1999 "Anonymous Bank" dataset (Technion SEE Lab, used in Brown et al., JASA 2005). The historical replay is checked on 12 days the fit never saw: wait correlation 0.99, abandonment 16.7% real vs 16.8% simulated. The newer figures are aggregate U.S. measurements, not current Indian bank waits.
- **Real standards.** India's ringback cadence (Asterisk `indications.conf`), DTMF frequencies and timing (ITU-T Q.23/Q.24), G.711 8 kHz audio, and speech-recognition error rates from published benchmarks (Sarvam 11.8%, Gram Vaani 29.7–34.8% on phone audio).
- **Five callers on every task.** A human (who gives up the way the real records say people give up), a scripted bot, a basic agent (Sierra's "bare" arm), HoldForMe, and a perfect-knowledge Oracle.
- **Everything three reference products do.** Google Hold for Me (hold-music recognition, recorded-vs-live detection, stall line, menu as text, wait times by hour), Pine (verification, OTP relay, refusing retention offers, negotiating, reference numbers) and Sierra (blind navigation of janky menus, keys vs speech, disclaimers, ID retry, path memory).
- **Provenance on every number.** Each parameter is tagged `DATA`, `OFFICIAL`, `STD`, `ATLAS` or `ASSUMED`, with its source. Assumptions are swept, never hidden.

The dashboard (`site/`) replays all of it: a call theatre frame by frame, contemporary 2026 county/month queue data with language detail, a historical event-level call-centre replay, wait times by hour, the handoff race, Pine-style conversations, a 3D Hold City, the evidence and stress matrices, feature parity, provenance and the test report. A guided **tour** walks through everything.

## Quick start

```bash
python -m pip install -r requirements-dev.txt   # pytest only; the simulator itself is pure Python 3.10+
python -m holdworld fetch-data                  # downloads the real 1999 data (10.6 MB) and extracts it
python -m holdworld test                        # 81 tests; writes results/tests.json (the proof)
python -m holdworld run                         # every experiment (~2.5 min); writes results/ and site/data/
python -m http.server 8030 --directory site     # open http://localhost:8030 and press "Take the tour"
```

`python -m holdworld run --quick` runs a smaller version in under a minute.

## Deploy (Vercel)

The site is static: `site/` plus the generated `site/data/*.js`. Commit `site/data/` after a run, push, and import the repo in Vercel; `vercel.json` points it at `site/`. No build step and no API keys. See `docs/DEPLOY.md`.

## Layout

```
holdworld/
  provenance.py   every parameter, its tag and its source
  anonbank.py     the real call-centre year: parse, describe, fit, replay a day
  callqueue.py    Erlang-A discrete-event queue: replay, fitted days, wait-by-hour, city
  spec.py         helpline data model, prompt templates (English + Hindi)
  helplines.py    the nine archetypes (three from official menus)
  line.py         one phone call stepped every 0.5 s: IVR, hold, executive, platform rules
  perception.py   what the agent hears: speech-to-text errors, classifier scores
  understand.py   robust prompt understanding (fuzzy, F1-scored)
  agents.py       the five callers; HoldForMe's 25 switchable components
  episode.py      run a task with re-dials and score it against the truth
  scenarios.py    the 20 stress scenarios
  experiments.py  every experiment
  report.py       site data + results/results.md
site/             the dashboard (vanilla JS, canvas, SVG, three.js)
tests/            81 tests (many on the real data)
docs/             how it works, data and terms, the Atlas protocol, deployment, the research
```

## Data terms

The Anonymous Bank data is "free for use. If used, please notify Avi Mandelbaum … and do acknowledge the data source in any of your work." Its raw files are **not** redistributed here; `fetch-data` downloads them from the Technion SEE Lab. The 2026 California DHCS county dataset is included under its Creative Commons Attribution (CC BY) license; its limits, definitions and rebuild command are documented alongside the source files. Official menu structures are cited with the date they were read (2026-10-21). See `docs/DATA.md`.

## What it is not (yet)

- Not a measurement of Indian wait times by itself. The real queue data is Israeli (1999); India-specific levels come from the India Hold Atlas (`docs/ATLAS.md`).
- No real audio or phone calls in phase 1. Phase 2 is an Asterisk + SIPp testbed with TTS prompts and a YAMNet listener.
- No LLM in the loop by default. The callers are rule-based so runs are free and reproducible; HoldForMe's understanding layer is where a real model plugs in.
