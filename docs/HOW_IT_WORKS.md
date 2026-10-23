# How HoldWorld works

## Three layers

| Layer | Simulates | Built from |
|---|---|---|
| **Line** (`line.py`) | One phone call, stepped every 0.5 s: ringing, operator messages, welcome, disclaimers, the language menu, menus that take keys or speech, ID entry, facts and actions, the hold, the executive | Official menus, India tones, ITU-T DTMF timing, measured speech-to-text error rates |
| **Queue** (`callqueue.py`) | A call centre: arrivals by hour, agents on duty, service times, impatient callers | The real 1999 call-centre year |
| **City** (`callqueue.city`) | Many callers, some of them AI holders that never hang up | The same engine, at scale |

## The call, frame by frame

The helpline side is written as a generator script that yields what it plays (`_Play`) and what it waits for (`_Listen`). The driver advances it in half-second frames, delivers the caller's key presses (each digit takes 100 ms tone + 100 ms gap) and speech, and records the **truth label** of every frame: ringback, IVR prompt, IVR waiting, hold music, hold announcement, recording that sounds human, silence, live human, human listening, bank voicebot, data burst, disconnected.

What the caller gets each frame (`perception.py`) is what a real listening pipeline would produce:

- speech-to-text words, revealed as partials and finals, with substitutions and deletions at a word error rate inside the measured range (clean recorded prompts use Sarvam's 11.8%; live speech is noisier; a bad line pushes it higher)
- classifier scores per frame: speech, music, synthetic voice, live room sound (the YAMNet classes phase 2 will use on real audio)

## The executive

After the hold, an executive (or the bank's own voicebot) greets the caller and starts a silence timer. "Hello? Hello, can you hear me?" comes at half the patience, and a hang-up at the full patience. A stall line ("one moment please") buys time, up to two times. If the user joins, the call is handed off. If the caller says it's an AI, the executive may refuse ("only the account holder"), or verify (name, date of birth, account digits, an OTP to the registered mobile), then do the task:

- **complaint / refund:** a reference number, repeated or confirmed on request
- **cancel:** retention offers first
- **negotiate:** a discount ladder that moves only when pushed

It may also transfer the call (a second hold) or put the caller on a mid-call hold.

## The callers

| | Caller | How it decides |
|---|---|---|
| A | Human | Reads the true prompts, picks the wrong option 10% of the time, gives up after a patience drawn from the real Kaplan–Meier curve |
| B | Scripted bot | Key presses at times recorded from one dry run; "first voice after music = human" |
| C | Basic agent | Plain word overlap, exact phrase matching, platform defaults |
| D | HoldForMe | 25 components, each switchable (ablation) |
| O | Oracle | Knows the tree (shortest path, BFS) and the exact pickup |

HoldForMe's understanding layer (`understand.py`) classifies each prompt by F1 overlap of content words with standard phrasings. A menu heard twice is merged option by option (the newest hearing wins a misheard digit). It acts on one hearing only when the best option is clearly ahead, and otherwise presses `*` or waits for the repeat. Detecting a person combines known recorded phrases, repetition, room sound, synthetic voice, question cues and a `hello?` probe.

## The queue

Every call in the 1999 data has its IVR time, queue time, outcome and service time. HoldWorld:

1. measures the hang-up hazard (Kaplan–Meier over everyone who waited), which shows spikes after the first message and at ~60 s
2. estimates agents on duty per 15 minutes from peak simultaneous calls, split into the regular and internet pools (separate from August 1999)
3. fits after-call work (the data records talk time only) on January–June days
4. checks the re-simulation against July–December days it never saw
5. builds each India archetype from the real hourly shape × a volume, staffed by the square-root rule with a quality knob; the telecom line is solved to answer 97% within 90 s (TRAI)

## Scoring

Every call ends with a `CallResult`:

- success by goal type
- time to a person, and detection delay
- false alerts (the user was rung for a recording)
- missed pickups
- the user's own minutes
- PINs typed by the agent (should be zero)
- platform utterances
- cost by platform

Rates are reported with Wilson 95% intervals.
