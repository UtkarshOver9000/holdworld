# HoldWorld — simulation blueprint (v2, real-data first)

**HoldForMe · Bolna Buildathon · simulation lane · written 2026-10-21 · nothing built yet**

> v1 of this blueprint was given in chat. v2 adds three things you asked for:
> (1) **real-world data behind every part**, with the source named;
> (2) **animations that show how the system actually works**, driven by real
> simulation traces, not drawn by hand;
> (3) what the "IVR simulator" world already has (the StackOverflow thread's
> topic), and how we use it.
> Background research is in `RESEARCH_HOLDFORME_SIM.md`.

---

## 0. The rule that shapes everything

**Every number on screen carries one of five tags:**

| Tag | Meaning | Example |
|---|---|---|
| `DATA` | Measured in a real dataset we load | Real waits and hang-ups from a bank call centre's full year of calls |
| `OFFICIAL` | Published by the company or regulator itself | SBI's IVR menu from sbi.bank.in; TRAI's 95%-in-90-s benchmark |
| `STD` | A technical standard or the config real systems ship with | India's ringback tone; DTMF frequencies and timing |
| `ATLAS` | Measured by us, calling real Indian helplines | Time-to-human at SBI at 7 pm |
| `ASSUMED` | No source exists. Labelled, never hidden, always swept over a range. | An executive's patience with silence, until the Atlas measures it |

The dashboard shows the tag next to each number. Click it to see the source.

**Goal:** by submission, nothing important on screen is `ASSUMED`.

---

## 1. Real data we found (and will load)

### 1.1 Queue and call-centre behaviour

**Anonymous Bank call-centre dataset** (`DATA`)
- **What it is:**
  - Technion SEE Lab, used in Brown et al., *JASA* 2005
  - every call to a real bank call centre for **12 months** (1 Jan – 31 Dec 1999)
  - **20,000–30,000 calls per month**, one record per call
- **17 fields per call:**
  - IDs: `vru+line`, `call_id`, `customer_id`
  - type and priority: `priority` (0/1/2), `type` (PS regular, PE English, IN internet, NE stock, NW prospect, TT callback)
  - IVR: `date`, `vru_entry`, `vru_exit`, **`vru_time`** (seconds in the IVR)
  - queue: `q_start`, `q_exit`, **`q_time`** (seconds on hold)
  - outcome: **`outcome`** (AGENT = served, HANG = hung up, PHANTOM = ignore)
  - service: `ser_start`, `ser_exit`, **`ser_time`** (seconds with the agent), `server` (agent name)
- **Download:** `https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/AnonymousBank.rar` (10.6 MB, public listing), with field docs in `AnonymousBank.pdf` in the same folder
- **Terms (quoted):** "The data is free for use. If used, please notify Avi Mandelbaum … and do acknowledge the data source in any of your work." → **Action: email the notification before we publish.**
- **Use:**
  - the Queue layer **replays real days**: real arrival times, real IVR times, real waits, real hang-ups, real service times
  - fitted distributions drive the "what if" runs
  - priority customers were given 1.5 min of head start; that's a real queue-jumping rule we can show
- **Honesty line:** Israel, 1999. It shows how real queues behave, not what Indian waits are. Indian waits come from the Atlas.

**Brown, Gans, Mandelbaum et al., *JASA* 2005** (`DATA`), on the dataset above:
- 65% of callers finish in the IVR
- of those who ask for an agent, ~80% are served and ~20% hang up
- an announcement replays ~every 60 s, and **hang-ups spike right after it**
- average patience 446 s (5.1–8.6 min by hour)
- % hang-ups ≈ average wait / average patience (R² 0.875)
- call lengths follow a lognormal shape
- Erlang-A (the queue model with hang-ups) fits; Erlang-C (no hang-ups) does not

**US Bank dataset** (`DATA`, optional)
- about 700–1,000 agents, 350k calls per week
- access only by request to Prof. Mandelbaum
- only worth chasing for the City layer at scale

### 1.2 India: official menus, rules and volumes

**SBI contact centre, official page** (`OFFICIAL`, read 2026-10-21)
- 15 languages; toll-free 1800 1234 / 1800 2100
- menu:
  - **0** block card / net banking / UPI
  - **1** account services (balance, last 5 transactions, statement, CIF, nomination)
  - **2** debit card and cheques
  - **3** interest certificates, INB, YONO
  - **4** deposits and loans, complaints
- **of 50 listed services, 34 run in the IVR and 16 go only to a human** (e.g. lodge a complaint, YONO help)
- checks: last 4/5 digits of account or card, birth year, DOB; OTPs go to the registered mobile
- **Becomes our flagship archetype, with the real tree.** The official page itself has inconsistencies (e.g. sub-menu digits differ between its table and its steps). That is useful: real menus are messy.

**KVB IVRS, official page** (`OFFICIAL`)
- 6 languages (1 English, 2 Tamil, 3 Hindi, 4 Telugu, 5 Kannada, 6 Malayalam)
- Customer ID + # then a 4-digit TPIN
- first-time registration needs a call from the registered mobile, the 16-digit debit card and an OTP
- 1860 number (local charges, **not toll-free**)
- **Archetype for TPIN-gated menus.**

**Union Bank, official page** (`OFFICIAL`)
- 14 languages, agent reachable "at any point", 24×7×365, IVR account info only with a registered PIN
- **Archetype for "zero-out anytime".**

**IDBI and Indian Bank, third-party pages (BankBazaar)** (`OFFICIAL`-adjacent, marked third-party)
- IDBI: 9 = executive from anywhere, * = repeat, 8 = previous menu, 0 = main menu; T-PIN for phone banking
- Indian Bank: 9 = executive
- **Used for navigation conventions, labelled third-party.**

**Telecom customer care** (`OFFICIAL`)
- TRAI benchmark: 95% of calls answered by an executive within 90 s
- Airtel, May 2026: **95.21% (Kolkata) – 98.33% (UP West)**
- Jio, June 2026: **99.03% (Andhra Pradesh) – 99.97% (UP East)**
- accessibility 97.42–99.87%
- **Use:** calibrate the telecom archetype so P(wait ≤ 90 s) matches. The pain there is the menu and transfers, not the queue.
- Short codes: Jio 199/198 only from a Jio SIM; others call 1800 88 99999

**Complaint volumes** (`OFFICIAL`)
- National Consumer Helpline: average **1,07,966 complaints per month** (Apr–Jun 2024, PIB); 13.16 lakh in FY25
- by sector, calendar 2024: e-commerce 4,40,185; banking 72,932; telecom 69,193
- RBI Ombudsman FY25: about 13.34 lakh
- **Use:** impact screen; arrival-rate scale for a government-helpline archetype

**Time lost on hold** (`DATA`, vendor survey)
- 30.7 h per person per year on hold; 15B hours (ServiceNow / Lonergan, n = 4,500)
- **Use:** impact screen only, always with the caveat

**Platform limits** (`OFFICIAL`)
- Bolna: 90 s default limit, 40 min maximum (changelog), 10-s silence hang-up, cannot send DTMF, ₹5.52/min
- Plivo: 4 h limit, `sendDTMF` on the audio stream, 8 kHz μ-law/L16 audio
- Exotel: 60-minute stream
- **Use:** platform profiles and the cost model

### 1.3 Sound and speech

**India call-progress tones** (`STD`), from the `[in]` section of Asterisk's `indications.conf`, the tone table real PBXs ship with:
- **ringback:** 400 Hz modulated by 25 Hz, cadence **0.4 s on, 0.2 off, 0.4 on, 2.0 off**
- **busy:** 400 Hz, 0.75 on / 0.75 off
- **congestion:** 400 Hz, 0.25 / 0.25
- **dial:** 400 Hz × 25 continuous
- **Use:** the sim's ringback and busy segments are timed exactly like an Indian line. The animation **plays** the real Indian ringback.

**DTMF** (`STD`)
- frequencies (ITU-T Q.23): rows 697/770/852/941 Hz × columns 1209/1336/1477/1633 Hz
- receiver timing (ITU-T Q.24, as quoted in standards discussions): tones ≥ 40 ms must be detected and < 23 ms rejected; gaps ~30–70 ms; ~93–125 ms per digit
- **Use:** we send 100 ms tone + 100 ms gap. The keypad animation shows the two frequencies of each key.

**Telephone audio** (`OFFICIAL`)
- G.711 μ-law at 8 kHz (Plivo's stream formats)
- **Use:** phase 2 audio is degraded to exactly this

**Hindi speech recognition on phone lines** (`DATA`)
- Gram Vaani challenge (Interspeech 2022): real phone recordings, ~1,108 h; baseline **29.7% WER** on eval (TDNN), 34.8% dev (end-to-end)
- Sarvam Saarika: **11.81%** Hindi WER on Vistaar (not phone-specific)
- **Use:** a word-error-rate range of 10–35%, swept. The stress test pushes it to the bad end.

**YAMNet** (`DATA`, a pretrained model, Apache-2.0)
- 521 sound classes, including **Speech, Speech synthesizer, Music, Background music, Carnatic music, Telephone, Ringtone, "Telephone dialing, DTMF", Dial tone, Busy signal, Silence**
- **Use (phase 2):** a real "what am I hearing" baseline on real audio. "Speech synthesizer" vs "Speech" is a direct feature for telling a recorded prompt from a live human. YAMNet expects 16 kHz audio, so test it on upsampled 8 kHz before relying on it.

**MUSAN corpus** (`DATA`, CC BY 4.0)
- ~109 h of music, speech in 12 languages, and noise; 16 kHz WAV
- **Use (phase 2):** hold music and call-centre background noise for the audio test set

### 1.4 People

**How fast people pick up** (`DATA`, non-India)
- a large survey-dialler log (~270k answered calls, UK): median **~10–12 s**, upper quartile 14–19 s
- **Use:** the starting estimate for how long the user takes to answer when the agent rings them (mode M1), until the Atlas or our own test calls replace it

**How long an executive tolerates silence** — nothing published (searched). `ASSUMED` 5–30 s and swept, until the Atlas measures it.

**OTP delivery time in India** — no measurement found (only TRAI saying the 2024 traceability rules "will not delay" messages). `ASSUMED`, swept 3–60 s; the Atlas can time it on our own phones.

### 1.5 The gaps only the Atlas fills (`ATLAS`)

These cannot be filled from anything public:
- Indian time-to-human by sector and hour
- real announcement intervals and wording in Hindi and English
- recordings that sound like a person
- menu prompt lengths
- the executive's silence tolerance
- callback offers
- "busy, call later" disconnects

The Atlas protocol is in the research file §5.1: ~24 helplines × 2 time slots; record only machine audio; ask the human a genuine question.

---

## 2. The "IVR simulator" world, and what we take from it

The StackOverflow thread (`/questions/18179903`) **could not be read**: StackOverflow's bot check blocks automated reads, and the archive copy is blocked too. Please paste it or open it in the browser pane. What the wider research shows:

| Tool | What it does | Direction | Use for us |
|---|---|---|---|
| **Asterisk** (open source, GPL-2.0, active) | The PBX many real call centres run. Phone menus via `Read()` with DTMF, queues via `app_queue`, `musicclass` hold music, RFC 2833 DTMF | **Hosts** menus and queues | **Our phase-2 real-protocol helpline:** generate an Asterisk dialplan from each helpline file, so the agent dials real SIP/RTP with real DTMF and real hold music |
| **SIPp** (open source, GPL, active, 3.8.x) | Generates thousands of SIP calls; plays RTP from pcap, including RFC 2833 digit packets | Calls *into* systems | Load-tests our Asterisk helpline; scripted "human callers" in the City layer on real protocol |
| **MockTell** (IIIT-Delhi, 2013–14) | Dials an IVR, listens to prompts, sends DTMF or recorded speech; can replay real-call data | Tests IVRs | Related work from India; validates the "replay real calls" idea |
| **Cyara, VistaCX (ex-Empirix Hammer)** | Commercial IVR and voice-bot testing | Calls your IVR | Wrong direction; cite only |
| **Sierra's simulator** | Synthesised prompts, real DTMF, timers and holds over the real phone network | Hosts menus | The closest prior art; we credit it |

**Key unblock found today:** Bolna added **bring-your-own SIP trunks** (Oct 2026 changelog):
- outbound calls go to *our* gateway: "any carrier that speaks standard SIP" at a public IP
- DTMF is RFC 2833
- the far side must allow Bolna's IPs (15.252.21.46, 13.206.230.198), use PCMU/PCMA codecs and RTP ports 30000–40000

So a Bolna-built HoldForMe could dial **our Asterisk helpline** with **no Indian phone number and no KYC**. The docs are written for carriers, so **confirm with Bolna support** before relying on it. Bolna still can't *send* DTMF, so this tests the hold, detection and handoff parts, while key presses go through Plivo.

---

## 3. What the simulation contains (v2)

Same three layers as v1; what's new is marked **new**.

### 3.1 Helpline library (the menus)

**Real-structure archetypes:**
- **SBI** (official tree): 15 languages, digit verification, 16 human-only services
- **KVB** (official): TPIN gate, 1860 number
- **Union** (official): zero-out anytime
- **IDBI-convention bank** (third-party): 9 / * / 8 / 0 conventions
- **Telecom** calibrated to TRAI and operator figures, with the short-code rule

**Assumed-structure archetypes, until the Atlas:** airline, e-commerce, electricity board, government documents, gas.

**Names:** each file names its source and date. **Decision for you:** show real bank names in the demo ("structure from SBI's official page, 21 Oct 2026") or relabel ("Large PSU bank, SBI-structure"). Relabelling is safer for a public video.

### 3.2 Queue layer — **new: replays real data**

- **Replay mode** (`DATA`): load a real day from the Anonymous Bank data. Every caller arrives, waits in the IVR, waits on hold, hangs up or is served **exactly as in the record**. Our agent's call is inserted into that real queue, so its hold time is what it would really have been that day.
- **Fitted mode** (`DATA` → model): distributions fitted from the full year — the arrival profile by hour, lognormal service, patience with the announcement spikes — drive the what-if runs (more AI holders, more agents, India-scaled volumes).
- **Check:** fitted mode must reproduce the real data's hourly hang-up rate and wait distribution within stated tolerances before it's used. **The fit is shown on screen next to the real numbers.**
- **India calibration:** each archetype's waits are rescaled to Atlas medians (`ATLAS`). The telecom archetype is pinned to TRAI/operator answer rates (`OFFICIAL`).

### 3.3 Line layer (one call) — **new: real timings**

- Ringback and busy use India's real cadence (`STD`).
- Menu prompts use real menu text (SBI/KVB) where we have it. Prompt durations come from the Atlas recordings, otherwise from the text at a measured speaking rate.
- DTMF timing follows Q.24 (`STD`).
- Speech-recognition errors are swept over the real 10–35% range (`DATA`).
- Everything else from v1 is unchanged:
  - ground-truth label every 0.5 s
  - recordings that sound like a person, mid-call holds, transfers, registered-mobile/TPIN checks, short codes
  - the executive model: silence tolerance, stall line, OTP, transfers, refusing an AI

### 3.4 Callers, metrics, stress tests, ablation, handoff, cost

As in v1:
- **five callers:** human, scripted bot, basic agent, HoldForMe, perfect-knowledge benchmark
- **stress tests S1–S18**; the ablation diagonal
- **handoff modes M1/M2/M3**; Bolna-default / tuned / Plivo / Exotel cost profiles

What's new:
- every metric is shown with its sample size, 95% range, and data tag
- the human caller's patience is no longer assumed: **it is sampled from the real dataset's measured patience**

### 3.5 Phase 2: real-protocol testbed (after the core works)

```
helpline JSON ──► Asterisk dialplan generator ──► Asterisk (Read/DTMF, app_queue, MusicOnHold)
                                                   ▲  SIP/RTP, RFC 2833, μ-law 8 kHz
          HoldForMe agent (Plivo stream or Bolna via SIP trunk) ──┘
          SIPp ──► background "human callers" filling the same queue
```

Prompts are synthesised with the sponsors' TTS (Sarvam, Cartesia), music comes from MUSAN, noise is added, and a YAMNet baseline listens.

---

## 4. Animations — how the system actually works

**Principle:** every animation **replays a real trace** that the simulation wrote (a JSON log of every 0.5 s frame, every key press, every queue event). Nothing is keyframed by hand, so what you see is what was computed. Each panel shows its data tags.

**Tech:**
- one offline HTML page (canvas + SVG + plain JS), plus Three.js 0.160 for the 3D city, the same version and dark style as AETHERGRID's `viz3d/`
- can also be published as a private shareable page
- a timeline scrubber controls every animation; speed ×1 / ×10 / ×60
- the two calls you choose are the same seeds the results came from

**A0 — "How HoldForMe works" (the overview, ~60 s loop)**
- A flow diagram: user's phone → HoldForMe app → agent → phone network → helpline menu → hold queue → executive → back to the user.
- A glowing packet travels the path of one real simulated call. Each stage lights up as the call reaches it, with a one-line caption ("pressing 4 for complaints", "on hold: 7 min 12 s", "human detected in 0.8 s", "connecting you").
- Click any stage to jump into its detailed animation below.
- **This is the opening shot of the demo video.**

**A1 — The menu, live**
- The real SBI menu tree drawn as a branching graph from the official structure. The agent's path lights up node by node.
- Subtitles show each prompt in Hindi/English as "heard" (with recognition errors in red).
- A keypad flashes each key press with its two DTMF frequencies.
- An input-window timer drains while the menu waits. Repeats and "invalid option" show as loop-backs.
- Switch the caller to the scripted bot and watch it press keys on a timer and fall off the tree when the menu has changed. **Sierra's point, shown in five seconds.**

**A2 — What the agent hears**
- A scrolling strip of 0.5-s frames coloured by **truth**: ringback, menu prompt, music, announcement, person-like recording, silence, live human.
- Under it, the agent's **meters**: music, speech, "synthesised voice", room sound, "heard this before?"
- A belief gauge for "is this a human?" and the decision line.
- The **"hello?" probe** appears as a speech bubble; the reply (or the recording ignoring it) is shown.
- When the gauge crosses the line: an alert, plus the measured detection delay ("0.8 s after the human's first word").
- **Audio toggle:** plays the real Indian ringback cadence and DTMF tones generated from the standards.

**A3 — The queue, from real data**
- A call centre floor:
  - agent desks across the top, numbered as in the data for that day
  - callers as dots arriving at the **real timestamps** of a real day from the Anonymous Bank data
  - they queue, then either reach a desk (served) or fade out red (hung up), exactly as recorded
- An announcement ripple sweeps the queue every ~60 s, and you can see the **hang-up spike right after it** (Brown 2005's finding, shown in the real data).
- Our HoldForMe caller (gold) joins at 7 pm and waits exactly as long as the real queue would have made it.
- **Then the "what if" switch:** the same day re-simulated with 10/25/50% of callers being AI holders that never hang up. Human waits and hang-ups change; the side panel shows the numbers. The real replay and the simulated version are always labelled.

**A4 — The handoff race**
- The moment a human answers: the executive's patience bar drains in real time (Hello? … Hello?).
- The user's phone rings, with a pickup time drawn from the real ring-time data.
- HoldForMe's stall line refills the bar ("one moment, connecting the account holder").
- Green if the user joins before the bar empties, red if the executive hangs up.
- A mode switch M1 / M2 / M3 shows why merging the call (M2) wins on speed and why M1 fails the registered-mobile check.
- Below, the heatmap from 10,000 simulated handoffs: success by user answer time × executive patience.

**A5 — Pine mode, the conversation**
- A chat-style replay of the agent talking to the executive:
  - verification (last 4 digits, DOB)
  - **OTP relayed from the user's phone** (shown as a phone notification)
  - a retention offer declined twice, then the cancellation
  - the reference number read back and confirmed
- Money saved and user minutes saved tick up at the end.

**A6 — Hold City (3D)**
- One building per sector archetype, each with its queue outside.
- A 24-hour clock on each building shows the **expected wait by hour** (Google's wait-time feature, from our queue layer).
- The telecom building carries a "TRAI: 95% in 90 s" badge with the real operator ranges.
- Drag the AI-share slider and watch queues grow.
- Camera presets: city / one building / one caller.

**A7 — The evidence board**
- Every result as a chart: callers compared, the stress-test pass matrix, the ablation diagonal, cost per call per platform, the City curves.
- Each with its sample size, 95% range and tags.
- **Every bar and every cell is clickable:** it opens A1/A2 replaying an actual call behind that number. That is how the simulation "shows literally everything": no number without the calls that made it.

**A8 — Data provenance panel**
- A table of every parameter in the run: its value, its tag, its source link and date.
- `ASSUMED` rows are highlighted orange, with their sweep range.
- The Atlas progress bar shows how many `ASSUMED` rows the field calls have replaced.

---

## 5. Folder layout (v2)

```
holdworld/
  README.md
  data/
    anonbank/            loader + fitter for the real call-centre year (raw .rar not committed; download script)
    menus/               sbi_official.json, kvb_official.json, union_official.json, idbi_thirdparty.json (+ source, date)
    india/               trai_care.json, nch_volumes.json, tones_in.json (Asterisk [in]), dtmf_std.json
    atlas/               atlas_template.csv, fit.py  → fills ATLAS-tagged parameters
    provenance.json      every parameter: value, tag, source URL, date read
  configs/helplines/     archetypes built from data/menus + calibration
  holdworld/
    spec.py  queue.py (replay + fitted)  line.py  perception.py  executive.py
    detectors.py  handoff.py  platforms.py  cost.py  city.py  scenarios.py
    agents/ human.py scripted.py basic.py holdforme.py oracle.py
    trace.py             writes the frame-by-frame JSON every animation replays
    experiments.py  stats.py  report.py  __main__.py
  testbed/               phase 2: asterisk dialplan generator, sipp scenarios
  viz/
    index.html           A0–A8, offline; three.js 0.160 for A6
  results/               generated: results.md, raw.json, traces/*.json, dashboard
  tests/
```

---

## 6. Build order

| Step | What | Output you can see |
|---|---|---|
| 1 | Provenance registry + data loaders (Anonymous Bank, official menus, TRAI, tones, DTMF) | `provenance.json`; a printout of the real dataset's hourly stats |
| 2 | Queue layer: replay a real day, fit the year, check fit vs real | A3 works on a real day |
| 3 | Line layer on the real SBI tree + India tones + trace writer | A1 and A2 work on a real menu |
| 4 | Five callers, executive, handoff, platforms | A4 and A5 work |
| 5 | Experiments: callers, stress, ablation, City, cost | A7 filled with numbers + `results.md` |
| 6 | A0 overview, A6 Hold City, A8 provenance | the full dashboard |
| 7 | Atlas fitting hook | `ASSUMED` rows turn into `ATLAS` as calls come in |
| Later | Phase 2: Asterisk/SIPp testbed, TTS audio, YAMNet baseline | real-protocol runs |

---

## 7. What it still won't be

- **Not a measurement of India by itself.** The real queue data is Israeli (1999). India-specific waits need the Atlas. The screen always says which is which.
- **No real phone calls in phase 1.** Real-protocol testing is phase 2 (Asterisk), and live helplines are only ever called by hand for the Atlas.
- **No LLM in the loop by default.** Callers are rule-based so runs are free and repeatable; there's a socket for Swetank's real agent.
- **Real bank menus are snapshots.** They are dated, and they change. The official SBI page even contradicts itself.

---

## 8. What I need from you

1. **The StackOverflow thread:** paste the text, or open it in the browser pane and pass the check yourself (I can't and won't bypass bot checks).
2. **Real bank names on screen,** or relabelled?
3. **Go-ahead to download** the Anonymous Bank `.rar` (10.6 MB), and someone to send the notification email its terms ask for.
4. **Ask Bolna support** whether a self-hosted Asterisk can be the gateway on a BYO SIP trunk.
5. **Go-ahead to build** (steps 1–6 first).

---

## 9. Sources (read 2026-10-21)

**Call-centre data**
- Anonymous Bank data and docs — https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/
- SEE Lab data repository — https://seelab.net.technion.ac.il/data/
- Brown et al. 2005 — https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Brown-etal-CCdata.pdf

**Indian menus, rules and volumes**
- SBI contact centre (official) — https://sbi.bank.in/web/customer-care/contact-centre
- KVB IVRS (official) — https://www.kvb.bank.in/ways-to-bank/ivrs/
- Union Bank (official) — https://www.unionbankofindia.bank.in/en/common/contact-us
- IDBI (third-party) — https://www.bankbazaar.com/idbi-home-loan-customer-care.html
- Indian Bank (third-party) — https://www.bankbazaar.com/indian-bank-home-loan-customer-care.html
- Airtel QoS, May 2026 — https://telecomtalk.info/airtel-surpasses-call-centre-accessibility-benchmarks-may2026/1010350/
- Jio QoS, June 2026 — https://telecomtalk.info/jio-trai-customer-service-qos-norms-june2026/1010367/
- TRAI PR 86/2025 (benchmark) — https://trai.gov.in/sites/default/files/2025-09/PR_No.86of2025.pdf
- NCH monthly average (PIB) — https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/mar/doc2025314520301.pdf

**Tones, DTMF and audio**
- India tones (Asterisk) — https://github.com/asterisk/asterisk/blob/master/configs/samples/indications.conf.sample
- Q.24 DTMF timing discussion — https://lists.w3.org/Archives/Public/public-webrtc/2014Jan/0195.html
- Gram Vaani ASR — https://www.isca-archive.org/interspeech_2022/bhanushali22_interspeech.html · https://openslr.org/118/
- Sarvam Saarika — https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika.md
- YAMNet class map — https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv
- MUSAN — https://openslr.org/17/ · https://arxiv.org/abs/1510.08484

**People**
- Ring-time data — https://support.unicomsi.com/manuals/intelligence/75/DDL/InterviewServerArchitecture.08.130.html

**Testbed tools**
- Asterisk — https://github.com/asterisk/asterisk · https://docs.asterisk.org/Configuration/Applications/Asterisk-Queues/Building-Queues/
- SIPp — https://github.com/SIPp/sipp · https://sipp.sourceforge.net/doc/reference.html
- MockTell — https://repository.iiitd.edu.in/jspui/handle/123456789/125
- Bolna SIP trunking — https://www.bolna.ai/docs/sip-trunking/overview.md · https://www.bolna.ai/docs/sip-trunking/outbound-calls.md
