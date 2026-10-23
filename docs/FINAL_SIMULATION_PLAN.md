# HoldWorld — the final simulation plan

**What to add, what to improve, and everything the research found.** Written 2026-10-23.

The rule for everything below: **the simulation is the pitch.** A judge opens the link and, without reading a word, watches India's helplines eat someone's afternoon, then watches HoldForMe take that afternoon back. Explanations, tables and sources move into drawers. The screen belongs to the simulation.

---

## 1. Who is judging, and what they will do with our link

**The event:** Bolna Buildathon at Symphony 2026.

| Date | Step |
|---|---|
| Oct 31 | Submissions close |
| Nov 3 | Shortlist |
| Nov 5–7 | Interviews |
| Nov 8 | Top 10 announced |
| Nov 20 | Top 3 pitch at the Lalit Ashok, Bengaluru |

- **Prize:** ₹50k plus a YC interview with Grey Baker, YC partner.
- **Judging criteria:** none published. **The interview is the real filter.**
- **Sponsors:** Plivo, Exotel, Sarvam, Cartesia, Deepgram, Kalpa Labs.

**What a judge actually does:**
1. Opens the Vercel link from the submission form, probably on a laptop and probably for under 2 minutes.
2. If something is moving and obviously about a real problem, they stay. If it's a wall of tabs, they skim and leave.
3. Before the interview, they come back looking for proof: does it work, is the data real, what breaks.

**So the site needs two modes:**
- **Watch mode** (default, autoplay): a 90-second, self-running film made of real simulation runs. No clicks needed.
- **Explore mode** (one click): the judge drives it. Pick a helpline, pick a problem, press call, and watch, or play the human yourself.

---

## 2. Where HoldWorld stands today (v1, built and tested)

| Area | State |
|---|---|
| Real queue data | 440,837 calls from a real bank call centre (Technion SEE Lab, 1999). Replay checked on 12 held-out days: wait correlation 0.990, hang-ups 16.7% real vs 16.8% simulated |
| Measured human behaviour | Hang-up spikes at 8 s and 58 s, straight from the records (Brown et al. 2005's finding, reproduced) |
| Helplines | 9 archetypes; 3 from official menus (SBI, KVB, Union Bank), 6 assumed until the Atlas |
| Standards | India ringback cadence (Asterisk `[in]`), DTMF (ITU-T Q.23/Q.24), G.711 8 kHz, measured Hindi speech-to-text error rates |
| Callers | Human, scripted bot, basic agent, HoldForMe (25 switchable components), Oracle |
| Results (192 calls each) | HoldForMe 71% [64–77] with **zero false alarms**; human 86%; Oracle 99%; scripted bot 51%; basic agent 4% |
| Stress suite | 20 scenarios. HoldForMe wins where others fail: recordings that sound human (80% vs bot 0%), changed menus (80% vs 0%), short code 199 (80% vs 0%), voice-only menus (90%) |
| Scale finding | If half of a bank's callers used an AI that never hangs up, human waits go from 35 s to 76 s and hang-ups from 10.6% to 20.2% |
| Handoff | Airline line: M1 + stall 83%, M3 (callback) 92%, M2 (merge) 58% |
| Telecom | Staffed to 97.1% answered within 90 s (TRAI benchmark 95%) |
| Tests | 81/81, many on the real data; report saved in `results/tests.json` |
| Dashboard | 11 chapters plus a 21-step tour; deployed static on Vercel |

**Known weak spots** (fixes partly in code, not yet re-run in full):

| Scenario | Before | Now | Next |
|---|---|---|---|
| S14: transfer, then a second hold | 0% | 7/12 in a quick check | Finish the fix: the simulator was forcing a transfer on every executive, and HoldForMe didn't re-introduce itself to the new person |
| S18: bank's own voicebot | 20% | 9/12 | The handshake worked; the last frame was dropped before HoldForMe read the result |
| S12: bad line | 0% | — | Re-ground the scenario at the worst *measured* error rate (34.8%) and add a noise sweep (§5.4) |
| S17: platform on default settings | 40% | — | This is a real finding about Bolna's defaults, not a bug. Show it, don't hide it |
| S20: PIN-gated menu | 50% | — | Split by mode: impossible in M1 (the user can't type into a cloud call), fine in M2 |
| Language menu on noisy lines | occasional failures | — | Never pick "other languages"; wait for the menu to repeat (done, needs re-run) |

---

## 3. The big change: Judge Mode (sim-first)

### 3.1 The landing screen is the simulation

No hero text, no tabs. The page opens straight into a full-screen **split-screen race** on the same helpline, the same hour and the same queue (same seed):

```
┌──────────────────────── 7:04 pm · Large public-sector bank · “failed UPI payment” ────────────────────────┐
│  YOU, CALLING YOURSELF                         │  HOLDFORME, CALLING FOR YOU                              │
│  [phone menu tree lighting up, Hindi prompts]  │  [same tree, picked by meaning, keys flashing]           │
│  ♪ hold music … “your call is important” …     │  ♪ same hold … belief meter: recording / recording       │
│  You hung up at 7:46 (real patience curve)     │  “Hello?” → no reply → still a recording                 │
│  Called again …                                │  Person picks up → detected in 0.6 s → “one moment”      │
│                                                │  📱 your phone rings → connected                          │
├────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
│  YOUR TIME:  18:42   keys pressed: 9           │  YOUR TIME:  0:24    hold absorbed: 12:10   false alarms: 0│
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Left:** the human caller (A), with real patience drawn from the 1999 records. They hang up, re-dial, and lose time.
- **Right:** HoldForMe (D), the same task.
- **The counter is the pitch.** "Your time" ticks fast on the left and almost not at all on the right.
- **The end card** comes from the run, never typed, for example: *"You: 18 min 42 s on the phone, gave up once. HoldForMe: 24 s of your time. Connected at 7:58."*
- Time is compressed automatically: dense moments (menus, pickup) play near real time, hold plays at 30–60×, with a "holding… 12:10" overlay. Judges see every interesting second and none of the boring ones.

### 3.2 The autoplay film: six scenes, all real runs

Watch mode chains six scenes with a camera director: zooms, highlights, lower-third captions of 10 words or fewer.

| # | Scene (~15 s each) | What the judge learns without reading |
|---|---|---|
| 1 | **The problem at scale:** a real day of the 1999 call centre at 600×. Dots pile up, red dots fall away in bursts after each "please hold" message | Queues are real; people give up in predictable bursts |
| 2 | **The maze:** the SBI-structure menu in Hindi, 15 languages, a 40 s disclaimer | Menus are long, multilingual, broken |
| 3 | **The trap:** "Hi, I'm Priya, your call is valuable to us." The scripted bot rings the user for nothing; HoldForMe's belief stays low | Telling a recording from a person is the hard part |
| 4 | **The race:** the person picks up, the patience bar drains, the stall line, the phone rings, connected | The handoff is where products win or lose |
| 5 | **Doing it for you (Pine mode):** verification, OTP relayed from the phone, retention offer refused, reference number read back | It can finish the job, not just wait |
| 6 | **At scale:** Hold City with the AI-holder slider rising; queues swell; then the voicebot handshake shrinks them | We know the second-order effect and the fix |

The film ends on the race summary: "Your time saved across 192 simulated calls" (from the run), then the **Try it yourself** button.

### 3.3 "Try it yourself": the judge plays the human

This is the stickiest thing we can build, and it's how we make judges spend minutes, not seconds:

- An on-screen phone keypad; the IVR speaks (browser speech in Hindi/English, real DTMF tones and Indian ringback in WebAudio).
- The judge has to navigate the real SBI-structure menu to "lodge a complaint", then sits through hold music and "your call is important".
- HoldForMe runs the same call in a corner picture-in-picture.
- When the judge gives up (most will), the screen shows: *"You lasted 1 min 50 s. 15% of real 1999 callers hang up by now. HoldForMe is still holding for you."*
- **Implementation:** the same engine, run in the browser. Port `line.py`'s helpline script to JS, or run the real Python engine with Pyodide (preferred: one source of truth).

### 3.4 Always-on HUD (top bar, every scene)

- **Your time saved** (minutes, live)
- **Hold absorbed** by HoldForMe
- **False alarms** (0)
- **₹ cost of this call** (platform price × minutes)
- **Data badge:** "Queue: 440,837 real calls · Menus: official · Tones: ITU/Asterisk"

### 3.5 Fewer tabs

- **Top level:** Watch · Explore · Try it yourself.
- Everything else (evidence, stress matrix, ablation, parity, provenance, tests) becomes **drawers** that slide over the simulation, opened from a small "Proof" button. Every number in a drawer is clickable and opens the call behind it in the main sim.

---

## 4. What to add to the simulation (depth judges will probe)

### 4.1 Real audio (the biggest visible upgrade)

- **Voices:** every IVR prompt and executive line voiced with **Sarvam** (Hindi/Indian English) or **Cartesia** TTS. Both are sponsors, which makes it an honest sponsor use. Cache the audio files in `site/audio/` so the deploy needs no keys.
- **Hold sound:** music from MUSAN (CC BY 4.0), with call-centre background noise for live executives.
- **Phone channel:** everything degraded to G.711 8 kHz μ-law.
- **A real listener:** YAMNet (Apache-2.0) running on that audio. Its "Speech" vs "Speech synthesizer" vs "Music" scores replace today's assumed classifier means. The "what the agent hears" strip then shows real classifier output.
- **Result:** the judge hears exactly what HoldForMe hears.

### 4.2 A real agent in the loop

- **"Bring your agent":** a WebSocket that speaks Plivo's audio-stream protocol (`start`, `media`, `playAudio`, `sendDTMF`). Any agent built for Plivo connects to HoldWorld unchanged.
- **Run the real build:** HoldForMe's own Bolna/LLM pipeline (Swetank's) calls a simulated helpline. The dashboard shows the *real product* being scored.
- **Bolna's new bring-your-own SIP trunk (Oct 2026):** point it at our own Asterisk server running the simulated helplines. Real SIP and RTP, real RFC 2833 tones, no Indian number or KYC. Ask Bolna support whether a self-hosted gateway is allowed.

### 4.3 Real-protocol testbed (phase 2)

- **Asterisk:** our helpline files generated into dialplans (`Read()` for keys, `app_queue` for holds, `MusicOnHold`). Real call-centre software running our menus.
- **SIPp:** floods the same queue with background "human" callers, so the queue is real at the protocol level.
- **Live wall:** a "Live calls" panel shows real SIP calls in progress against the testbed.

### 4.4 The India Hold Atlas (turns assumptions into data)

- **What:** about 24 real helplines × 2 time slots (about 48 calls), logged in `data/atlas/atlas_template.csv`.
- **What it fixes:**
  - Indian time-to-human by sector and hour
  - announcement intervals and wording
  - recordings that sound human
  - how long executives tolerate silence (published nowhere)
  - OTP delay
  - callback offers
- **Ethics:** record only machine audio; ask the executive a real question.
- **On screen:** every `ASSUMED` badge that turns into `ATLAS` is visible proof of progress. A counter: "17 assumptions → measured".

### 4.5 More real menus

Add official IVR trees as they're found (HDFC, ICICI, Axis, Canara, IRCTC 139, LIC, Passport Seva, EPFO, Indane, BESCOM/TNEB), each with source and date. Re-check SBI's page monthly: menus change, and that change is itself a stress scenario.

### 4.6 Queue realism for India

- **Volume levels:** scale each archetype with public volumes (NCH ~1.08 lakh complaints per month; RBI Ombudsman 13.34 lakh per year) and Atlas waits.
- **Calendar:** day-of-week and festive-season curves.
- **Disruption days:** for example, the IndiGo crisis of Dec 2025 (~4,500 flights cancelled), modelled as an airline volume ×3 scenario.
- **Callbacks** inside the queue engine, not just in the call script.
- **Multi-skill queues:** cards vs complaints teams, with transfers between them.

### 4.7 Richer executives and companies

- **Speech:** code-switched Hinglish executives; accents (as audio arrives).
- **Behaviour:**
  - chains of transfers
  - "call back on the registered number" policies
  - companies that refuse AI callers outright, with an AI-disclosure line and a policy-compliant fallback to the user
- **Verification:** account digits, date of birth, OTP, TPIN, card CVV refusal. HoldForMe must **never** voice or type a secret.

### 4.8 The handoff, made real

- **Ring times:** replace the UK ring-time data with Indian ring-time measurements (Atlas).
- **M2 relay:** measure whether keypad tones pass through a VoLTE conference on Jio and Airtel. M2's whole viability depends on it, and it's currently assumed at 50%.
- **Timing:** add a "pre-warn" policy optimisation: when to ring the user so they're on the line exactly at pickup.

### 4.9 Scale and fairness (the interview question)

- **Coverage:** City curves for all 9 helplines, not 2.
- **Business view:** agent occupancy, calls served, cost per resolved call.
- **Polite AI holder policies, compared:**
  - give up after a deadline
  - take the callback
  - join only off-peak (using wait-by-hour)
  - agent-to-agent handshake
- **Optimiser:** pick the policy that saves the user most time while adding the least to human callers' waits.

### 4.10 Cost and unit economics

- **Prices:** Plivo India per-minute rates (still a placeholder at ₹0.60), Bolna ₹5.52/min, Exotel.
- **Output:** cost per resolved call, and **₹ per hour of user time saved**, the number a YC partner asks for.
- **Architecture comparison:** Bolna-only vs Plivo stream + hold classifier (LLM only while talking). Today's medians: about ₹10 per HoldForMe call vs ₹12 for the basic agent; refine with real rates.

### 4.11 Evaluation rigor

- **Sample size:** 30+ seeds per cell; intervals on every rate (already Wilson 95%).
- **Sensitivity:** a tornado chart over the assumptions (executive patience, error rate, refusal rate, OTP delay, M2 relay) showing which one moves HoldForMe's success most. That is where the Atlas should measure first.
- **Sim vs real:** once Atlas audio exists, run HoldForMe on the recorded real menus and compare to the simulation's prediction for the same archetype.
- **Analytic check:** draw the Erlang-A formula over the simulated queue curves.

---

## 5. What to improve in HoldForMe (inside the sim)

1. **Transfers (S14):** finish and re-run. Treat any fresh greeting after a conversation as a new person; re-introduce; reset verification. The simulator forces only one transfer.
2. **Voicebot (S18):** keep the final-frame fix; add a fallback when the bot doesn't support a handshake (state the request in one sentence, ask for a human if bridging).
3. **Bad lines (S12):**
   - set the scenario at the worst published phone error rate (Gram Vaani 34.8%)
   - add a **noise sweep** (error rate 10% → 50%) for every caller, shown as a degradation curve
   - teach HoldForMe to listen up to three times when unsure, and to press `*` to repeat
4. **Platform defaults (S17):** show side by side: same agent, Bolna defaults vs tuned settings. This is a useful finding for Bolna judges ("here's what your defaults do to holds").
5. **PIN menus (S20):** route PIN steps to the user's own keypad in M2; in M1, say honestly that the call needs the user's phone.
6. **Language menus:** never "other languages"; wait for the repeat; fall back to English.
7. **Path memory:** show the second call to the same helpline getting shorter.
8. **The understanding layer** (`understand.py`): swap the fuzzy classifier for a small LLM call behind the same interface. Measure the gain on the same 192-call set and the cost per call it adds.

---

## 6. Build order

| By | Deliverable | Why it matters |
|---|---|---|
| **Oct 26** | Re-run with today's fixes; S12 noise sweep; tests still 81+ passing | Honest numbers before anything visual |
| **Oct 28** | **Judge Mode landing:** split-screen race (human vs HoldForMe) with time compression and the end card | The 10-second hook |
| **Oct 29** | **The autoplay film** (6 scenes, director, captions); everything else into drawers | The 90-second story with no reading |
| **Oct 30** | Sarvam/Cartesia voices cached for the featured calls; real ringback/DTMF already in | Judges *hear* the problem |
| **Oct 31** | **Submit:** Vercel link + 90 s screen recording of Watch mode as the pitch video | |
| **Nov 1–4** | "Try it yourself" (judge plays the human); India Hold Atlas calls (48); first `ASSUMED → ATLAS` swaps | Interview prep: measured India data |
| **Nov 5–7** | Interviews: open the link live; the stress matrix and City curves answer "what breaks" and "what at scale" | |
| **Nov 8–20** | (If top 10) real audio for all calls + YAMNet listener; Bolna SIP trunk → Asterisk; the real product scored in the sim; sensitivity tornado | Finale: a live call from the real agent into the simulated helpline, scored on stage |

---

## 7. The research, in one place

### 7.1 The problem, in numbers (cite with the caveat)

| Fact | Value | Source |
|---|---|---|
| Time Indians spend on hold | 15 billion+ hours (2023); 30.7 h per person per year; $55B at ₹502.79/h | ServiceNow India CX report, Jul 2024 (vendor survey, n = 4,500, Lonergan Research) |
| Same, 2024 | 15 billion hours; 39% still waiting on hold; 36% frustrated by transfers; 34% think companies make complaining "intentionally difficult" | ServiceNow India, Mar 2025 (n = 5,000) |
| Complaints escalated to the government helpline | 13.16 lakh (FY25), 20.49 lakh (FY26); 2024: e-commerce 4,40,185, banking 72,932, telecom 69,193 | National Consumer Helpline (Lok Sabha / Rajya Sabha replies) |
| Banking complaints to the RBI Ombudsman | about 13.34 lakh (FY25, +13.55%) | RBI Annual Report of the Ombudsman Scheme 2024-25 |
| Telecom service standard | 95% of calls answered by an executive within 90 s; Airtel 95.2–98.3%, Jio 99.0–99.97% | TRAI QoS; operator reports May/June 2026 |
| Real queue behaviour | 65% finish in the IVR; ~20% of agent-seekers hang up; announcements trigger hang-up bursts; Erlang-A fits, Erlang-C doesn't | Brown, Gans, Mandelbaum et al., JASA 2005; reproduced on the full 1999 data |

### 7.2 The constraints the build must respect (all modelled in the sim)

1. **Bolna can't send DTMF** (it only receives). Plivo can (`sendDTMF` on the stream); Exotel has no documented way.
2. **Bolna's defaults kill holds:** 90 s call limit, 10 s silence hang-up, and "Hello, are you still there?" spoken into the menu. The maximum is 40 min (May 2025 changelog).
3. **No platform detects "hold music stopped, a person said hello".** HoldForMe must build it; it's the core technical claim.
4. **Indian numbers need a registered business** (Plivo: GST / Certificate of Incorporation / Udyam). Caller ID must be a number you rent; spoofing is an offence (Telecom Act 2023, s.42(3)).
5. **Registered-mobile checks:** a call from a cloud number lands in the "unregistered" branch. Hence the modes: M1 cloud dial, M2 the user dials and merges, M3 callback.
6. **Short codes** (Jio 199/198) work only from that operator's SIM; dial the toll-free number instead.
7. **Hold minutes cost money:** Bolna ₹5.52/min including hold. A hybrid (cheap hold classifier, LLM only while talking) is about 5× cheaper on long holds.
8. **New since Oct 2026:** Bolna bring-your-own SIP trunks. HoldForMe on Bolna can dial a self-hosted Asterisk test helpline (confirm with Bolna support).

### 7.3 The landscape (what's already done, and our gap)

| Who | What | Where it stops |
|---|---|---|
| Google Hold for Me | Waits on hold; tells hold music and recordings from a representative; on device | Pixel only; US/Australia/Canada; English; toll-free numbers |
| Google "Talk to a Live Rep" | Calls supported businesses and rings you when a person answers | US Search Labs, fixed list (2024) |
| Pine | Consumer agent that calls customer service, negotiates bills, cancels subscriptions; $25M Series A (Dec 2025) | US only |
| Sierra | Agents that navigate janky IVRs; an IVR simulator over the real phone network; 57% → 85% pass rate | B2B; trees and detector accuracy unpublished |
| Regal | IVR navigation; 80% → 96% after fixing disclaimer timing | B2B |
| Hamming, Cekura, Coval | Simulate *callers* to test your bot | Not a model of India's helplines |
| arXiv 2510.21715 | LLM routing on one synthetic IVR; 77–89% exact match | Text only |
| GibberLink | Two agents recognise each other and switch to data-over-sound; won ElevenLabs' Worldwide Hackathon | A demo, not customer care |

**Our gap:** India (languages, registered-mobile rules, short codes, 8 kHz Hinglish), the queue from real data, the handoff race, and open evidence. **Never claim "first IVR simulator"**: Sierra has one.

### 7.4 Real data and standards behind the sim

- **Anonymous Bank call-centre data** (Technion SEE Lab): 12 monthly files, 17 fields per call. Free for use with acknowledgement; downloaded by `fetch-data`, not redistributed.
- **Official menus:**
  - SBI contact centre: 15 languages; menu 0–4; 34 of 50 services in the IVR, 16 only with a human
  - KVB IVRS: customer ID + TPIN; 6 languages; 1860 number
  - Union Bank: an agent at any point; 14 languages
  - Third-party conventions: IDBI and Indian Bank (9 = executive)
- **Tones:** Asterisk `indications.conf [in]`: ringback 400 Hz × 25 Hz, 0.4/0.2/0.4/2.0 s; busy 0.75/0.75; congestion 0.25/0.25.
- **DTMF:** ITU-T Q.23 frequencies; Q.24 timing (≥ 40 ms detected); we send 100 ms tone + 100 ms gap.
- **Speech-to-text error rates:** Sarvam Saarika 11.81% Hindi (Vistaar); Gram Vaani phone baseline 29.7–34.8%.
- **Audio models and corpora:** YAMNet, 521 classes including Speech, Speech synthesizer, Music, DTMF, Dial tone, Busy signal, Silence (Apache-2.0). MUSAN: about 109 h of music, speech and noise (CC BY 4.0).
- **Ring time:** about 270k answered survey calls, median 10–12 s (UK; replace with Atlas data).
- **IVR testing tools:**
  - SIPp: generates SIP calls; RTP and RFC 2833 tones via pcap
  - Asterisk: open-source PBX with queues and music on hold
  - MockTell (IIIT-Delhi): emulates callers to IVRs
  - Cyara, VistaCX: commercial, but they call *into* IVRs (the wrong direction for us)

### 7.5 Open questions to settle

| Question | Why | How |
|---|---|---|
| Can Plivo India numbers dial 1800 toll-free? | Most helplines are 1800 | One test call |
| Plivo India per-minute rate | Cost model | Pricing page, India selector |
| Bolna's current maximum call length | Long holds | Ask in Bolna Builders Slack |
| Does hold music reset Bolna's silence timer? | Holds | One test call |
| Do keypad tones pass through a VoLTE conference? | M2 viability | Test calls on Jio and Airtel |
| How long do executives tolerate silence? | The handoff race | India Hold Atlas |
| Will Bolna accept a self-hosted Asterisk as a SIP trunk gateway? | Real-protocol testing without an Indian number | Bolna support |

---

## 8. Risks, and how the plan handles them

| Risk | Handling |
|---|---|
| "The demo is staged" | Every scene is a recorded run with its seed; the drawer shows the trace id; "Try it yourself" runs live |
| "Your queue data is from Israel, 1999" | Shown as such; it validates *behaviour* (held-out r 0.99); India levels come from the Atlas, marked `ATLAS` |
| "HoldForMe fails 29% of the time" | That's the honest number; the stress matrix shows exactly where and why, and each fix is visible run over run |
| "AI holders make queues worse" | We measured it (35 s → 76 s) and show the polite-holder policies that cut it |
| Judges spend 20 seconds | Watch mode autoplays; the split-screen race lands the problem and the solution in the first 10 seconds |
| No keys on Vercel | All audio pre-generated and cached; the site stays static |
