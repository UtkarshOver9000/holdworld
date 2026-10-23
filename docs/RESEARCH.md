# Research file — HoldForMe, simulation lane

**Bolna Buildathon (Symphony 2026) · idea #1 "HoldForMe" · lane: simulation, evidence, stress testing**

> Status: research only. No code written. Researched 2026-10-21 from public
> sources; every external fact below has a source in §11 and the date it was read.
> Where the web had no answer, this file says so. It does not guess.

> **Repo note.** This repository is AETHERGRID. HoldForMe should live in its
> own repo. This file sits here only because this is where you are working today.

---

## Contents

0. [The idea in one screen](#0-the-idea-in-one-screen)
1. [The event: what we are actually judged on](#1-the-event-what-we-are-actually-judged-on)
2. [The problem in measured numbers](#2-the-problem-in-measured-numbers)
3. [Seven constraints the build will hit (the sim must model all of them)](#3-seven-constraints-the-build-will-hit)
4. [Landscape: who already did what](#4-landscape-who-already-did-what)
5. [The simulation: HoldWorld](#5-the-simulation-holdworld)
6. [Stress-testing the sim idea itself](#6-stress-testing-the-sim-idea-itself)
7. [Build order, Oct 21 → Oct 31 → Nov 20](#7-build-order)
8. [Claims discipline](#8-claims-discipline)
9. [Decisions needed from Swetank before the sim is built](#9-decisions-needed-from-swetank)
10. [Things nobody could verify yet](#10-things-nobody-could-verify-yet)
11. [Sources](#11-sources)

---

## 0. The idea in one screen

**HoldWorld: a simulated India of customer-care phone lines, used three ways.**

1. **As the test bench.** A fake helpline the agent can call thousands of times
   for free. It has an IVR, a hold queue, hold music, recorded "your call is
   important" messages, and a human who picks up at a known moment. Every
   millisecond of audio is labelled with what it really is, so we can score the
   agent exactly. The build team develops against it from day one.
2. **As the evidence.** We run four kinds of caller through the same lines,
   plus a perfect-foresight oracle. That shows how much time HoldForMe saves,
   where it fails, and what it costs per call, with sample sizes and intervals.
3. **As the demo insurance.** A live call to a real bank on stage can sit on
   hold for 20 minutes. A deterministic fake line ("Bharat Bank", 90-second
   hold) always works. One recorded real-helpline run goes next to it as proof.

**Three layers, like AETHERGRID's building / colony / connection:**

| Layer | What it simulates | The question it answers |
|---|---|---|
| **Line** | One call: IVR tree, prompts, input type, hold, announcements, human pickup | Does the agent get through, and does it notice the human in time? |
| **Queue** | One call centre: arrivals, agents, service times, impatient callers (Erlang-A) | How long will this call actually wait, at this hour? |
| **City** | Many helplines and many callers, some of them AI holders | What happens to everyone else when callers stop giving up? |

**Calibrated by Phase 0, the India Hold Atlas.** No public data exists on
per-call IVR depth or time-to-human for Indian helplines (§2.3). So the team
calls about 24 real helplines in two time slots and logs a fixed set of
fields. That fits the sim to India, and it is also the slide nobody else will
have: *"we measured India's helplines."*

**What makes it ours and not a copy:** Sierra already built an IVR simulator
over the real phone network (§4). Ours is the India version (Hindi/English
prompts, registered-mobile checks, operator short codes, 8 kHz lines). It adds
two things theirs does not cover. The first is the queue, with real
abandonment behaviour. The second is the moment of handoff to the user, which
is where this product lives or dies.

---

## 1. The event: what we are actually judged on

From bolna.ai/symphony/buildathon, read 2026-10-21:

- **Name:** "Buildathon by Bolna: Build with voice at Symphony". Fully virtual build.
- **Timeline:**
  - Oct 15–31 build
  - **Oct 31 submit** (no time or time zone given; treat as Oct 30, 23:59 IST internally)
  - Nov 3 shortlist (interview invites by email)
  - **Nov 5–7 interviews**
  - Nov 8 finalists (top 10 get Symphony tickets)
  - **Nov 20 top 3 pitch** at Abhyas Hall, Lalit Ashok, Bengaluru (travel covered)
- **Rules:** "No tracks. Bring any idea, as long as it has a voice component." Solo or teams up to 4. There is no stated requirement to build on Bolna, and no required telephony provider.
- **Prizes:** ₹50k + a YC interview with Grey Baker (YC partner) / ₹40k / ₹30k.
- **Sponsors on the buildathon page:** Plivo, Exotel, Sarvam, Cartesia, Deepgram, Kalpa Labs. Symphony's Diamond tier adds Google Cloud and Truecaller for Business.
- **Submission form:** project name, a 200-character description, a link (repo, live app or demo), and a pitch deck or video link.
- **No judging criteria are published anywhere.** The real filter is the Nov 5–7 interview.

**What that means for this lane:**
- The interview is where evidence wins. A founder who says "we called 24 Indian helplines and here is what we measured" beats one with a nicer UI.
- The finale is a live pitch, so the demo must not depend on a real bank's queue that day.
- Sarvam and Cartesia (TTS) and Deepgram (STT) are sponsors. Using them to *generate the simulated IVR audio* is a natural, honest sponsor use.

---

## 2. The problem in measured numbers

### 2.1 What is measured

| Figure | Value | Source and caveat |
|---|---|---|
| Hours Indians spent on hold, 2023 | **15 billion+**; average **30.7 h per person per year** | ServiceNow CX Intelligence Report 2024 (31 Jul 2024). 4,500+ adults, online panel, fielded by Lonergan Research (ISO 20252), weighted to MoSPI estimates. **A vendor that sells AI customer service, and self-reported.** |
| Economic loss | **$55B** | Same report, from ₹502.79/h (Glassdoor) × 28.94 h × the working population who complained in business hours. Method in the release's notes. |
| Hours on hold, 2024 | **15 billion** "in the past year"; waits down "a modest 5%" | ServiceNow India, 24/25 Mar 2025. 5,000 adults, 1–15 Nov 2024. |
| Frustrations (2024 data) | 39% still waiting on hold; 36% frustrated by transfers between departments; 34% think companies make complaints "intentionally difficult"; 46% want less time on hold | Same 2025 release |
| Perceived vs actual | Agents say a simple issue takes 30 min; consumers perceive **3.8 days** | Same 2025 release |
| National Consumer Helpline, calendar 2024 | e-commerce **440,185** grievances, consumer durables 77,873, electronics 74,288, **banking 72,932, telecom 69,193** | Rajya Sabha reply, Mar 2025 |
| NCH totals | 12.36 lakh (FY24), 13.16 lakh (FY25), 20.49 lakh (FY26) | Lok Sabha reply |
| RBI Ombudsman FY25 | about **13.34 lakh** complaints, +13.55% on FY24 | RBI Annual Report of the Ombudsman Scheme 2024-25 (press coverage; the primary PDF was not opened) |
| Telecom service standard | **95% of calls answered by an executive within 90 s** (was 90% in 60 s); Jio self-reports 99.03–99.97% (June 2026) | TRAI QoS regulations; telecomtalk |

**Derived (our arithmetic, vendor inputs):** 30.7 h × ₹502.79/h ≈ **₹15,400 of time per person per year**. Use it only with the caveat attached.

### 2.2 A precise insight from the TRAI number

If telcos really answer 95% of calls within 90 s, the telecom pain is not the
queue. It is the IVR maze before you reach the "talk to an executive" option,
plus transfers.

The 90-second clock most likely starts when you *ask* for an executive. That
is unverified (§10). So the sim and the Atlas must **measure three things
separately**:

- IVR time (navigating the menus)
- queue time (after asking for a human)
- transfer time (a second hold after "let me transfer you")

ServiceNow's 36% "transferred between departments" says the third one matters.
Banks, airlines, e-commerce sellers and government lines have no 90-second
rule at all.

### 2.3 What is NOT measured anywhere (searched, not found)

- Per-call time-to-human for Indian helplines, by sector or hour. Nothing independent turned up; only vendor blogs (Aircall's global "12 minutes").
- IVR menu depth or structure for Indian helplines. The arXiv paper on IVR routing says real IVR structures "are often proprietary" and had to synthesise its own.
- Any India consumer app that calls customer care for you. None found.

**That gap is the Atlas (§5.1).** It is cheap to fill and nobody has filled it.

---

## 3. Seven constraints the build will hit

These came out of reading the Bolna, Plivo and Exotel docs. They are build
problems, but **the sim must model every one of them**, or it will say
HoldForMe works when it won't. Swetank needs these before writing the build plan.

### C1. Bolna cannot press keypad buttons on a call

Bolna's DTMF page covers only *receiving* key presses from the caller: "digit
presses from the caller are captured and sent to the agent as a text message".
No send-DTMF tool is in its API reference. Its IVR feature is for *inbound*
calls on Plivo numbers only.

- **Undocumented workaround:** a Bolna custom function receives `{call_sid}`, and our server calls Plivo's own API to send digits. This works only if the Plivo account is ours (bring-your-own Plivo), not Bolna-hosted telephony. **Untested.**
- **Plivo can send DTMF:**
  - the `<DTMF>` XML element
  - `send_digits` at call connect, which fires once, so it does not cover later menus
  - **`sendDTMF` over a bidirectional audio stream** (`{"event":"sendDTMF","dtmf":"1234#"}`)
- **Exotel:** no documented way to send DTMF on a live call. Its bot-to-Exotel messages are only mark, media and clear. Bolna also does not support DTMF on Exotel or Vobiz.

### C2. Bolna's defaults hang up on a hold queue

- `call_terminate` defaults to **90 s**.
- `hangup_after_silence` defaults to **10 s**.
- `check_if_user_online` (default on) **speaks** "Hello, are you still there?" after 10 s of silence. On a speech-driven IVR, that sentence can be taken as menu input.
- The maximum call length was raised to **40 min** in May 2025. Current docs don't state a cap.
- Whether hold music counts as "the user speaking" is undocumented.
- **Exotel's** voicebot stream lasts "up to 60 minutes per session". **Plivo's** calls default to 4 h (extendable to 24 h), and its stream timeout defaults to 86,400 s.

### C3. Bolna has no human-pickup detection

- Its voicemail detection runs in the first 30 s and **auto-disconnects**. A long IVR greeting could be misread as voicemail, so it must be off.
- Plivo's answering-machine detection only reports "machine" on answer, and the `hangup` mode would kill an IVR call.
- **Nobody's platform detects "hold music stopped, a person said hello."** HoldForMe has to build that itself. It is the core technical claim, so the sim must test it hardest.

### C4. Indian numbers need a registered business

- **Plivo:** "Only businesses registered in India can rent Indian phone numbers [or] make domestic calls within India." KYC accepts GST, Certificate of Incorporation or **Udyam Registration**; business PAN alone is refused.
- Caller ID "must use Plivo-rented Indian phone number". Both legs of a call must stay in India ("media anchoring").
- **Exotel:** KYC is mandatory for Indian outbound calls, under a company category.
- **Possible unblock for a student team (verify):** a sole-proprietor Udyam registration is free and online with Aadhaar + PAN, and Plivo lists Udyam as accepted. Or ask the Plivo/Exotel sponsors in the Bolna Builders Slack for hackathon numbers. If neither works, Bolna-hosted numbers bring back C1.

### C5. The bank won't know who is calling

- Calling line identity in India is the number you own. Spoofing it is an offence under s.42(3) of the Telecommunications Act 2023 (up to 3 years, ₹50 lakh). Plivo: you "can't use an arbitrary caller ID."
- Indian bank IVRs commonly identify you by **registered mobile number (RMN)**. A call from a cloud number lands in the "not registered" branch, and account menus and OTPs go to the user's phone.
- **This shapes the product** (§5.9): either the user is on the call, or the agent can only do non-account tasks and wait for a human.

### C6. Short codes don't work from cloud numbers

- Jio's 199/198 work "from your Jio SIM" only; from other numbers it is **1800 88 99999**.
- Airtel's 121/198 follow the same pattern; sources disagree on the long number.
- The sim's helpline registry must map every brand to a number a cloud line can reach.
- Whether Plivo India numbers can dial **1800 toll-free** is undocumented (§10).

### C7. Hold minutes cost money

- **Bolna:** ₹5.52/min ($0.06) pay-as-you-go, about ₹4.15 on larger top-ups, billed in 30-second pulses, telephony extra. "Every component except the LLM is billed by duration", so music minutes cost full price.
- A 20-min hold plus 5 min of IVR and talk on Bolna ≈ **₹138 before telephony**.
- If the hold is watched by a cheap audio classifier on a raw Plivo stream, and the LLM pipeline only wakes for IVR and human segments, the same call is 5 × ₹5.52 = **₹27.60 + telephony**.
- Plivo's India per-minute rate was not retrieved (§10).
- **The sim's cost model prints both.** It is the unit-economics slide for the YC interview.

---

## 4. Landscape: who already did what

| Who | What | Where it stops | Source |
|---|---|---|---|
| **Google "Hold for Me"** (Pixel, 2020) | Waits on hold. A Duplex model "recognizes hold music" and tells a recorded message apart from a representative. Runs on device. | Pixel only. US, Australia, Canada. English. Toll-free numbers. **No India launch found.** | Pixel help, Android Police |
| **Google "Talk to a Live Rep"** (Search Labs, Feb 2024) | Calls a supported business, waits, rings you when a human answers | US only, a fixed list of businesses; no 2025–26 status found | TechCrunch, 9to5Google |
| **Pine AI** (US) | Consumer agent that calls customer service and negotiates bills; claims 270 min saved per user | US. **$25M Series A, Dec 2025.** This validates the category for the YC angle. | BusinessWire, SiliconANGLE |
| **Sierra** (enterprise) | Agents navigating "janky" IVRs. **Built an IVR simulator over the real phone network:** "dials the number, hears synthesized prompts, sends real DTMF tones, and sits through timers and holds." Pass rate 57% → 85% with their IVR feature. | B2B (e.g. healthcare billing calls). Tree counts and detector accuracy not published. | sierra.ai blog, 11 Aug 2026 |
| **Regal** (enterprise) | IVR navigation; "Pause Detection Delay" before pressing a digit; 80% → 96% after fixing a disclaimer-before-prompt case. Argues synthetic trees miss real quirks. | B2B | regal.ai blog, 25 Aug 2026 |
| **Hamming, Cekura, Coval** | Voice-agent QA that simulates *callers to your bot*. Hamming and Cekura claim IVR/DTMF emulation. | Tests your bot; not a model of India's helplines | vendor comparisons |
| **arXiv 2510.21715** | Text-only LLM routing over one synthetic IVR (23 leaf paths, 920 intents); 77–89% exact match | No audio, no hold, no humans | arXiv, Sep 2025 |
| **GibberLink** | Won ElevenLabs' Worldwide Hackathon: two agents notice they are both AI and switch to data-over-sound (ggwave) | Hotel-booking demo, not customer care | ElevenLabs blog, Wikipedia |

**What is left that is ours:**

1. India (languages, RMN, short codes, 8 kHz Hinglish), where none of these operate.
2. The queue and the handoff, which none of the published work measures.
3. Open evidence: Sierra publishes neither its trees nor its detector accuracy.

**Do not claim "first IVR simulator"** — Sierra has one.

**Pitch risk (not this lane, flag it):** "Hold for Me" is the name of Google's
feature. A judge will say "Google did this." The answer is in the table above,
but consider a different product name.

---

## 5. The simulation: HoldWorld

### 5.1 Phase 0 — the India Hold Atlas (Oct 22–25)

**Goal:** the first public, structured measurement of Indian helplines. It
calibrates every number the sim uses.

- **Sample:** about 24 helplines across sectors:
  - banks ×5
  - telecom ×3 (long numbers, per C6)
  - airlines ×2
  - e-commerce/quick-commerce ×3
  - electricity/gas ×3 (pick Chennai/Bengaluru boards)
  - government services ×4 (passport, EPFO, rail, LIC)
  - insurance ×2
  - pick numbers from each brand's official site, not aggregator pages
- **Two slots each:** weekday late morning (11:00–13:00) and evening (19:00–21:00). That is ~48 calls at roughly 10 min = ~8 h of phone time, 2–3 h per teammate.
- **Log per call** (one row, fixed schema):
  - **When:** timestamp, slot, number dialled, sector, caller network
  - **Pre-answer:** operator network announcement before answer (Y/N, text)
  - **Language menu:** present (Y/N), options offered
  - **Menus:** per level, the prompt text, the input type (DTMF / speech / both / broken) and the option chosen; depth to reach a human; was there a direct "press 9/0 for executive"
  - **Auth gates:** RMN / account no. / OTP / DOB; what happened when not registered
  - **Timings:** IVR seconds · queue seconds · announcement interval (s) · transfer count and extra hold seconds · total
  - **Hold audio:** music type (loop length); whether queue position / wait estimate is announced; **agent-like recorded greeting** (Y/N, text)
  - **Options:** callback offered (Y/N)
  - **Outcome:** human / forced disconnect ("all executives busy, call later") / closed hours / dead end
  - **The human:** greeting text, and **how many seconds of silence before the executive says "hello?" again or hangs up** (stay silent for a few seconds once, carefully, on a few calls)
- **Recording rule:** record **only the machine audio** (IVR prompts and hold music). Stop at human pickup. That avoids storing anyone's voice and yields a real audio test set for the hold/human detector.
- **Ethics rule:** when a human answers, ask a genuine simple question (hours, a branch, a process) so no executive's time is wasted on a test.
- **Output:** `atlas/atlas.csv` + `atlas/audio/` + a one-page summary (medians and ranges, with N; no national extrapolation).

### 5.2 Layer 1 — The Line (one call, the test bench)

**Helpline spec (YAML).** Each helpline is a file:

- language menu
- tree of menus: per node the prompt text in each language, input type, timeout, repeat count, behaviour on bad input
- auth gates (RMN check, OTP)
- business hours
- the queue model it hands off to (Layer 2)
- hold behaviour: music loop, announcement text and interval, agent-like recordings
- transfer probability
- the human's behaviour: greeting, dead-air patience, verification questions

8 archetypes come from the Atlas. A generator mutates them (depth, quirks) to make hundreds.

**Three run modes, one spec:**

| Mode | What flows | Speed / cost | Used for |
|---|---|---|---|
| **Event mode** | Timed text events ("prompt: 'For English press 1' 0.0–2.4 s", "music", "human: 'Hello, this is Ravi'") in; actions (digits, speech text, wait) out. ASR error injected from a WER parameter. | Thousands of calls/min, deterministic seeds, free except LLM tokens | Arms, sweeps, ablation, stress suite |
| **Stream mode** | Real audio over a WebSocket that **speaks Plivo's stream protocol** (`start`, `media` base64 20 ms 8 kHz, `playAudio`, `clearAudio`, `sendDTMF`, `dtmf`) | Real time, no telephony cost | Detector and navigator tested end to end; **the agent code cannot tell the sim from a real Plivo call** |
| **Phone mode** | The fake helpline on a real phone number: a Bolna inbound agent playing "Bharat Bank", or a Plivo number serving our XML/stream | Real time, telephony cost | Demo line, final end-to-end proof through real PSTN audio |

**Audio for stream/phone mode:**
- Prompts are synthesised in Hindi, English and one southern language with the sponsors' TTS (Sarvam, Cartesia).
- Music is royalty-free / CC0 (check each file's licence).
- "Human executives" are recorded by teammates (with consent), with call-centre background noise added.
- Everything is degraded to 8 kHz μ-law with packet loss and jitter.
- Real Atlas machine audio is mixed in.

**Ground truth.** Every 20 ms frame carries one label:
`ringback · network_announcement · ivr_prompt · ivr_awaiting_input · hold_music · hold_announcement · agent_like_recording · silence · human_live · ai_agent_live · voicemail · disconnect`.

That is what makes exact scoring possible. No real call can give you this.

### 5.3 Layer 2 — The Queue (one call centre)

A discrete-event Erlang-A (M/M/N+G) simulator decides how long each call
actually waits.

Starting parameters come from the best public call-by-call study (Brown,
Gans, Mandelbaum et al., *JASA* 2005: a full year of a bank call centre, about
1.2M calls). **Every one is a prior to sweep, then replace with Atlas values:**

| Primitive | Published finding | How we use it |
|---|---|---|
| Arrivals | Inhomogeneous Poisson, with an intraday profile | Hour-of-day profile per sector; peak multiplier from the Atlas slots |
| Self-service | 65% of callers finished in the IVR; 35% asked for an agent | Fraction of goals answerable by the IVR ("retrieve a fact") |
| Abandonment | ~20% of those asking for an agent abandoned | Calibration target for human-caller arms |
| **Announcements** | Played every ~60 s; **the abandonment hazard peaks right after the first message and again at ~60 s**, when it replays | Human callers hang up in spikes after announcements. It is also a stress test: each announcement is a speech burst that is *not* a human. |
| Patience | Average 446 s; hourly means 5.1–8.6 min; P(abandon) ≈ E[wait]/E[patience], R² = 0.875 | Patience distribution for human callers |
| Service time | **Lognormal**, not exponential | Talk-time distribution; matters for the handshake scenario |
| Model fit | Erlang-A fits; Erlang-C (no abandonment) over-predicts delays | Erlang-A in the sim, Erlang-C as a check |

**Textbook fact the City layer depends on:** as patience → ∞, Erlang-A
becomes Erlang-C. Erlang-C has no steady state when load ≥ 1, so the queue
grows until the busy period ends.

### 5.4 Layer 3 — The City (what happens at scale)

Many helplines, a population of callers, and a knob **α = the share of callers
using an AI holder that never gives up.**

**Experiment W1, the externality.** For α ∈ {0, 5, 10, 25, 50}% at three load
levels, measure:
- human callers' wait and abandonment
- AI callers' wait
- agent utilisation and calls served

*Hypothesis, not a result:* near or above full load, AI holders push
abandonment onto human callers.

**This is the number that does not flatter us. Print it.** Then test the
mitigations:
- (a) the agent gives up on the user's behalf when the predicted wait exceeds the user's deadline
- (b) take the callback when offered
- (c) the **handshake** (idea #3): when the far end is a bank's AI agent, switch to structured data exchange. Lognormal service time is cut for the verification segment, which frees capacity.

Showing the problem *and* the fix is the systems-thinking answer a YC partner probes for.

### 5.5 Arms (same lines, same seeds)

| Arm | Caller | Purpose |
|---|---|---|
| **A** | Human: patience distribution from §5.3, abandons, re-dials | Baseline time cost; *modelled* |
| **B** | Scripted bot: a hard-coded digit path, and "first speech after music = human" | What a weekend hack does |
| **C** | LLM agent, bare: goal + tools, no hold/human specialisation | Matches Sierra's "bare" arm |
| **D** | HoldForMe full: navigator + hold detector + human detector + stall-and-bridge | The product |
| **O** | Oracle: knows the tree and the exact pickup frame | Upper bound; how much is left on the table |

### 5.6 Metrics (all with N and 95% intervals, 3+ seeds)

- **Task success**, split by goal type (Sierra's three): reach the right human and bridge the user · retrieve a fact from the IVR · do an action in the IVR
- **Time to human**, and **user minutes saved** = (IVR + queue + transfer time) − (user's setup + handoff + verification time). Print the archetypes where it is **negative** (short holds, facts the app gives faster).
- **Human-pickup detection:** precision, recall, latency (ms from the human's first word to the alert), **false alarms per call** (each one pings the user for nothing), **missed pickups** (the executive hung up)
- **Navigation:** wrong-department rate, DTMF/speech modality errors, loops entered
- **Handoff success** (§5.9)
- **₹ per call** under both architectures (C7)

### 5.7 Stress suite (scenario → what it breaks → pass condition)

| # | Scenario | Breaks | Pass |
|---|---|---|---|
| S1 | Language preamble; Hinglish prompts ("apna account number enter karein") | Navigator, ASR | Right branch, both languages |
| S2 | DTMF-only gate; speech-only gate; broken prompt ("press 3" but only speech works) | Modality choice | Recovers within one retry |
| S3 | 40-s disclaimer before the actionable prompt (Regal's case) | Turn-taking | No premature input |
| S4 | Loops, dead ends, "press 9 to repeat", timeout → IVR repeats / gives up | Navigator | Escapes or reports a dead end; no infinite loop |
| S5 | **RMN gate** fails on a cloud number; OTP sent to the user's phone | Mode (C5) | Routes to the human path, or relays the OTP from the user |
| S6 | **Agent-like recording** ("Hi, I'm Priya, your call is valuable to us") | Human detector | No alert |
| S7 | Music cut mid-note by a soft "hello?" with no transition (Sierra's hurdle 3) | Human detector | Alert within the latency budget |
| S8 | Announcement every 60 s with queue position, in Hindi | Detector false alarms | Zero alerts; extracts position → wait estimate |
| S9 | Callback offer ("press 1 for a callback") | Inbound handling | Accept or decline by policy; catch the callback |
| S10 | "All executives are busy, please call later" + forced disconnect; closed hours | Retry policy | Re-dial with backoff; tell the user honestly |
| S11 | Call drops mid-hold; platform cap hit (Bolna 40 min, Exotel stream 60 min) | Resilience (C2) | Re-dials, re-queues, reports lost position |
| S12 | 8 kHz, packet loss, jitter, low SNR, μ-law artefacts | Everything audio | Degrades gracefully; report the curve |
| S13 | Short code dialled (198/199/121) | Registry (C6) | Mapped to a reachable long number before dialling |
| S14 | Mid-call transfer → second hold → different department | Hold loop re-entry | Re-enters hold mode; no false alarm on the new music |
| S15 | Executive says "hello?" twice and hangs up after X s of dead air | Handoff | Stall script fires before X |
| S16 | Executive asks verification only the user can answer (DOB, card digits) | Bridge | User bridged before the question, or agent says "connecting the account holder" |
| S17 | **Our own platform speaks into the IVR** ("are you still there?", C2) | Config | Zero platform utterances during IVR/hold |
| S18 | Far end is an AI voicebot (handshake opportunity) | Detector classes | Classified as `ai_agent_live`, not human; optional handshake |

### 5.8 Ablation (the diagonal)

Remove one component at a time:
- language detector
- modality classifier
- **repetition detector** (recorded messages repeat word for word; humans don't)
- **contingency probe** (when unsure, say a short "hello?" — a human answers it, a recording does not)
- music/speech classifier
- stall script
- queue-position reader

Each removal should break a specific stress case that no other component
covers. If one doesn't, that component is not earning its place.

### 5.9 The handoff model, and the call mode it decides

This is where HoldForMe wins or loses, and nobody publishes it.

```
P(handoff succeeds) = P( T_user_joins  <  T_exec_patience + T_stall )
```

- `T_exec_patience` is how long the executive tolerates dead air. **No public standard exists** (searched). Use the Atlas measurement; sweep 5–30 s.
- `T_stall` is how long a stall line buys: "One moment please, connecting the account holder". Google's feature does the same, asking the representative to wait.
- `T_user_joins` depends on the **mode** (sweep, since no source gives Indian answer times):

| Mode | How | T_user_joins | RMN auth (C5) | User cost |
|---|---|---|---|---|
| **M1 Cloud dial + ring-back** | Agent dials from a cloud number; rings the user on pickup | Ring + answer (sweep 5–40 s) | ✗ fails | Lowest |
| **M2 User dials + merge** | User dials the bank, adds HoldForMe's number, merges, puts the phone down muted | ~0–3 s (already on the line) | ✓ works | Phone line busy during the hold |
| **M3 Callback** | Agent accepts the IVR's callback offer | n/a | depends | Only where offered |

**The sim's deliverable is a heatmap** of success vs (user answer time ×
executive patience) per mode, plus the sector table (banks need RMN;
e-commerce doesn't). That is a design decision made from evidence, not taste.

**Open technical risk for M2:** whether DTMF from the HoldForMe leg reaches the
bank through a VoLTE conference (§10). If it doesn't, the agent tells the
user which key to press.

### 5.10 Cost model

₹/call = minutes in each segment × the per-minute price of the components
running in that segment.

- Segments: IVR, hold, human
- Two architectures: Bolna end to end, vs a raw stream with a cheap hold classifier, with the LLM woken only on change
- Parameters with sources: Bolna ₹5.52 and ₹4.15/min, billed in 30-s pulses. Telephony is **a parameter until Plivo's India rate is fetched**.
- Output: the cost per call by sector, priced at the Atlas hold times

### 5.11 Visuals

1. **Call replay strip (P1, the strongest demo asset).** A spectrogram of one call, coloured by ground-truth class, with the detector's belief underneath and the agent's actions (digits pressed, the stall line, the bridge) as markers. It shows the moment the music stops and a human says hello, and the agent noticing 0.8 s later.
2. **Hold City (P2, finale).** AETHERGRID-style. Each helpline is a building with its queue outside. Human callers drop out in visible spikes after each announcement. AI holders never leave. Scrub time, drag α. Reuse the `viz3d/` Three.js setup, or 2D canvas if time is short.

---

## 6. Stress-testing the sim idea itself

| Objection a judge (or we) should raise | Answer |
|---|---|
| "Synthetic IVRs aren't real." (Regal's own argument) | The Atlas calibrates the archetypes, and real recorded machine audio is mixed in. **Report the sim-vs-real gap:** run arm D on held-out real Atlas lines and compare outcomes to the sim's prediction for the same archetype. |
| "Sierra already built this." | Yes, and we say so. Ours is India, adds queue dynamics and the handoff, and is open. Never claim "first". |
| "Your parameters come from a 1999 Israeli bank." | Priors only, labelled as such, swept, then replaced by Atlas fits. The *structure* (lognormal service, announcement spikes, Erlang-A over C) is what transfers. |
| "48 calls is tiny." | It is a pilot, not a census. Report medians, ranges and N; never extrapolate to "India". It is still 48 more than any public source has. |
| "The detector is evaluated on your teammates' voices." | True; state it. Diversify voices and noise; keep the real-audio slice separate; never quote the synthetic score as a field score. |
| "The demo line is staged." | Show it next to a recorded real-helpline run and the Atlas numbers. Say on screen which is which. |
| "The externality result hurts the pitch." | It shows we understand the system. Pair it with the mitigation results. Hiding it is what loses an interview. |
| "Ten days isn't enough." | Strict P0/P1/P2 cut (§7). Event mode first: it's pure Python, no audio, and gives most of the evidence. Phone mode and Hold City can wait for Nov 20. |
| "Is it legal for an AI to call a helpline for someone?" | No India rule on this found. TRAI's A2P definition covers AI-voice calls "delivered to a telecom subscriber" — a business support line is arguably not that, but **unverified**. The sim itself never calls real numbers; only the Atlas does, by hand. |

---

## 7. Build order

| Dates (IST) | Deliverable | Gate |
|---|---|---|
| Wed 21 – Thu 22 Oct | Spec format (YAML) + event schema agreed with Swetank. Atlas sheet and call list. | Build team can code against the event schema |
| Thu 22 – Sun 25 Oct | **Atlas calls** (all teammates). **P0:** "Bharat Bank" line in event mode + stream mode, ground-truth labels, a deterministic 90-s hold. Queue engine. | Agent can dial the sim and get a scored run |
| Mon 26 – Wed 28 Oct | **P1:** 8 archetypes fitted to the Atlas. Arms A–D + oracle in event mode. Stress S1–S18. Audio test set (synthetic + real machine audio). | Results table regenerates from one command |
| Thu 29 – Fri 30 Oct | Results report (generated, never typed). Call replay strip. Handoff heatmap. Cost table. Claims sheet. | Every number has a source row |
| **Sat 31 Oct** | **Submit** (aim for Fri night) | |
| Nov 1 – 7 | Interview prep: Atlas findings, W1 externality, sim-vs-real gap. Phone-mode end-to-end runs. | |
| Nov 8 – 20 | (If finalist) Hold City, live demo line hardened, handshake scenario | |

---

## 8. Claims discipline

- No figure reaches the deck, video, README or a screen unless it was measured, or is cited with its source and caveat.
- Vendor survey numbers (ServiceNow) are always said as "a ServiceNow survey of 5,000 Indians found…", never as fact.
- Every rate carries its N and interval. Synthetic-audio scores are never presented as field scores.
- The number that does not flatter us (W1, and the archetypes where time saved is negative) is printed next to the ones that do.
- Results files are generated. A claims sheet lists every number with the file, command and commit that produced it.

---

## 9. Decisions needed from Swetank

1. **Whose audio loop is it?**
   - (a) Bolna end to end: no DTMF send (C1), 10-s silence hangup (C2)
   - (b) Plivo stream + our own STT/LLM/TTS pipeline
   - (c) hybrid: Plivo stream for IVR/hold, Bolna for the human conversation

   This decides whether stream mode or phone mode is the sim's main interface.
2. **Telephony account:** whose KYC (Udyam?), which provider, by when. Until then, the sim and the agent meet only in stream/event mode.
3. **Call mode** M1 / M2 / M3 for the MVP. The sim can answer this by Oct 27 if the Atlas runs on time.
4. **Languages for v1:** Hindi + English only, or one southern language too?
5. **Event schema freeze date**, so the build team and the sim don't drift.
6. **Product name** (the Google "Hold for Me" collision).

---

## 10. Things nobody could verify yet

| Question | Why it matters | How to settle it |
|---|---|---|
| Does Plivo's India route reach 1800 toll-free numbers? | Most helplines are 1800 | One test call once there is an account |
| Plivo India per-minute rates | Cost model | Plivo pricing page, India selector |
| Bolna's current maximum `call_terminate` | Long holds | Ask in Bolna Builders Slack |
| Does hold music reset Bolna's silence timer? | C2 | One test call |
| Does DTMF from a third party reach the bank through a VoLTE conference? | M2 viability | One test call (Jio and Airtel) |
| When does TRAI's 90-s clock start? | §2.2 framing | TRAI QoS regulation text |
| Is a sole-proprietor Udyam certificate enough for Plivo India KYC? | C4 | Plivo support / sponsor contact |
| Is Google Hold for Me live in India in 2026? | Landscape | Pixel help page |
| ServiceNow 2024 vs 2025 "15 billion": same period counted twice? | Don't double-count | Cite the 2025 figure for "2024" and the 2024 one for "2023", never add them |

---

## 11. Sources

All read 2026-10-21 unless noted.

**Event**
- Bolna Buildathon — https://www.bolna.ai/symphony/buildathon
- Symphony 2026 — https://www.bolna.ai/symphony
- Bolna seed round, $6.3M led by General Catalyst (21 Jan 2026) — https://www.bolna.ai/newsroom/bolna-bags-63-million-seed-funding-led-by-general-catalyst-to-build-indias-voice-ai-platform

**Problem data**
- ServiceNow India, 31 Jul 2024 (15B hours, 30.7 h/person, $55B, method notes) — https://newsroom.servicenow.com/press-releases/details/2024/Indians-lost-over-15-billion-hours-on-hold-to-customer-service-in-2023-resulting-in-55-billion-in-economic-loss-output--07-31-2024-traffic/default.aspx
- ServiceNow India, 24 Mar 2025 — https://newsroom.servicenow.com/press-releases/details/2025/AI-to-bridge-Indias-customer-service-gap-as-80-of-consumers-rely-on-chatbots-for-key-services-03-24-2025-traffic/default.aspx
- NCH sector table, calendar 2024 (Rajya Sabha, Mar 2025) — https://rsdebate.nic.in/bitstream/123456789/759128/1/PQ_267_18032025_U1951_p192_p193.pdf
- NCH totals (Lok Sabha) — https://eparlib.nic.in/bitstream/123456789/2980727/1/AU247_BLr0jt.pdf
- RBI Ombudsman 2024-25 — https://website.rbi.org.in/web/rbi/-/publications/annual-report-of-ombudsman-scheme-2024-25 ; coverage: https://www.medianama.com/2025/12/223-rbi-ombudsman-14-banking-complaints-fy25-private-banks/
- TRAI customer-care benchmark — https://telecomtalk.info/jio-trai-customer-service-qos-norms-june2026/1010367/

**Platforms**
- Bolna docs — https://www.bolna.ai/docs/dtmf · https://www.bolna.ai/docs/supported-telephony-providers.md · https://www.bolna.ai/docs/tool-calling/transfer-calls.md · https://www.bolna.ai/docs/api-reference/agent/v2/create.md · https://www.bolna.ai/docs/changelog/may-2025.md · https://www.bolna.ai/docs/inbound/ivr.md · https://www.bolna.ai/docs/get-started/what-it-costs.md · https://www.bolna.ai/pricing
- Plivo docs — https://www.plivo.com/docs/voice/api/calls · https://www.plivo.com/docs/voice/xml/audio-streaming · https://plivo.com/docs/voice-agents/audio-streaming/concepts/audio-streaming-reference · https://www.plivo.com/docs/voice/concepts/machine-detection · https://www.plivo.com/docs/voice/concepts/account-limits · https://www.plivo.com/docs/voice/concepts/india-calling · https://www.plivo.com/docs/numbers/rent-india-numbers · https://www.plivo.com/docs/voice/api/multiparty-calls
- Exotel support — https://support.exotel.com/support/solutions/articles/3000132302 · https://support.exotel.com/support/solutions/articles/3000133761 · https://support.exotel.com/support/solutions/articles/35123

**Regulation**
- CLI spoofing, Telecom Act 2023 s.42(3), DoT advisory Feb 2025 — https://conventuslaw.com/report/india-dot-advisory-on-telecom-identifier-tampering-a-strong-regulatory-push-to-safeguard-communication-networks/
- Jio short codes — https://bajajfinserv.in/jio-customer-care-number

**Landscape**
- Hold for Me — https://www.androidpolice.com/how-to-use-hold-for-me/ · https://support.google.com/phoneapp/answer/10104618
- Talk to a Live Rep — https://techcrunch.com/2024/02/16/google-tests-a-feature-that-calls-businesses-on-your-behalf-and-holds-until-an-agent-is-available/
- Pine — https://www.businesswire.com/news/home/20251203384902/en · https://siliconangle.com/2026/05/06/pine-ai-aims-consumer-ai-agent-complex-customer-service-interactions/
- Sierra — https://sierra.ai/blog/navigating-ivr-systems
- Regal — https://www.regal.ai/blog/how-regal-ai-agents-navigate-complex-ivrs
- arXiv 2510.21715 — https://arxiv.org/html/2510.21715v1
- Voice-agent QA comparison — https://www.coval.ai/blog/hamming-vs-cekura
- GibberLink — https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon · https://en.wikipedia.org/wiki/Gibberlink

**Queueing science**
- Brown, Gans, Mandelbaum, Sakov, Shen, Zeltyn, Zhao, "Statistical Analysis of a Telephone Call Center: A Queueing-Science Perspective", *JASA* 100(469), 2005 — https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Brown-etal-CCdata.pdf

**ASR**
- Sarvam Saarika (Hindi WER 11.81% on Vistaar; not telephony-specific) — https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika.md
