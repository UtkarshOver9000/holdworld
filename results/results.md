# HoldWorld results

Generated 2026-10-22 19:15:54 (quick=False). Every number below is produced by `python -m holdworld run`; nothing is typed by hand.

## 1. The real call-centre year (Anonymous Bank, 1999)

- Records: 440,837 calls over 363 days; 417,149 asked for an agent
- Abandoned while waiting: 15.3%; mean wait of served callers 58 s; 44% served immediately
- Service time: median 122 s, mean 202 s (lognormal mu 4.84, sigma 0.94)
- Hang-up hazard spikes at [8.0, 58.0, 172.0] s (first message, and the ~60 s replay)
- Replay check on 12 held-out days: real mean wait 76.3 s vs simulated 69.3 s; abandonment 16.7% vs 16.8%; correlation across days 0.990 (wait), 0.993 (abandonment)
- After-call work fitted on Jan-Jun: 50.1 s

## 2. Callers on every task (success, 95% interval)

| Caller | n | Success | User minutes (median) | Time to human (median s) | False alerts / call | Cost INR (median) |
|---|---|---|---|---|---|---|
| Human caller | 192 | 86% [80-90] | 2.04 | 83.7 | 0.0 | 0.0 |
| Scripted bot | 192 | 51% [44-58] | 0.0 | 55.6 | 0.422 | 5.15 |
| Basic agent | 192 | 4% [2-8] | 0.0 | 55.8 | 0.021 | 12.24 |
| HoldForMe | 192 | 71% [64-77] | 0.4 | 110.5 | 0.0 | 10.31 |
| Oracle | 192 | 99% [96-100] | 1.21 | 51.8 | 0.0 | 3.2 |

## 3. Stress suite (pass rate)

| Scenario | Scripted bot | Basic agent | HoldForMe | Oracle |
|---|---|---|---|---|
| S1 Hindi menus, Hinglish labels | 70% [40-89] | 10% [2-40] | 70% [40-89] | 90% [60-98] |
| S2 Menu says 'press' but only listens to speech | 0% [0-28] | 0% [0-28] | 90% [60-98] | 70% [40-89] |
| S3 40 s disclaimer, keys ignored while it plays | 70% [40-89] | 10% [2-40] | 60% [31-83] | 90% [60-98] |
| S4 Menu loop and a dead end | 90% [60-98] | 0% [0-28] | 90% [60-98] | 100% [72-100] |
| S5 Account menu needs the registered mobile | 100% [72-100] | 100% [72-100] | 100% [72-100] | 100% [72-100] |
| S6 A recording that sounds like a person, every minute | 0% [0-28] | 0% [0-28] | 80% [49-94] | 100% [72-100] |
| S7 Music cut mid-note by a soft 'hello?' | 80% [49-94] | 0% [0-28] | 60% [31-83] | 100% [72-100] |
| S8 Queue position announced in Hindi every 30 s | 0% [0-28] | 0% [0-28] | 90% [60-98] | 100% [72-100] |
| S9 Callback offered after 2 minutes | 90% [60-98] | 0% [0-28] | 80% [49-94] | 100% [72-100] |
| S10 'All executives are busy, call later' | 50% [24-76] | 0% [0-28] | 60% [31-83] | 60% [31-83] |
| S11 Call drops 40 s into the hold | 30% [11-60] | 0% [0-28] | 80% [49-94] | 50% [24-76] |
| S12 Bad line: poor signal, 1.6x speech errors | 60% [31-83] | 0% [0-28] | 0% [0-28] | 100% [72-100] |
| S13 User gives the operator short code 199 | 0% [0-28] | 0% [0-28] | 80% [49-94] | 0% [0-28] |
| S14 Transferred to another team, second hold | 80% [49-94] | 0% [0-28] | 0% [0-28] | 100% [72-100] |
| S15 Impatient executive (4-6 s of silence) | 80% [49-94] | 0% [0-28] | 80% [49-94] | 100% [72-100] |
| S16 OTP to the registered mobile mid-call | 50% [24-76] | 0% [0-28] | 60% [31-83] | 100% [72-100] |
| S17 Voice platform left on default settings | 70% [40-89] | 0% [0-28] | 40% [17-69] | 100% [72-100] |
| S18 The bank's own voicebot answers | 80% [49-94] | 0% [0-28] | 20% [6-51] | 100% [72-100] |
| S19 Menu changed since the script was recorded | 0% [0-28] | 0% [0-28] | 80% [49-94] | 100% [72-100] |
| S20 Account menu needs a PIN | 0% [0-28] | 0% [0-28] | 50% [24-76] | 100% [72-100] |

## 4. Handoff modes (airline line)

- M1|stall: 83% [55-95]
- M1|no stall: 75% [47-91]
- M2|stall: 58% [32-81]
- M2|no stall: 58% [32-81]
- M3|stall: 92% [65-99]
- M3|no stall: 83% [55-95]

## 5. City: share of callers who never hang up

- psu_bank / none: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 43 s, human abandon 12.7%; alpha 0.25: human wait 50 s, human abandon 14.5%; alpha 0.5: human wait 76 s, human abandon 20.2%
- psu_bank / deadline_20min: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 43 s, human abandon 12.7%; alpha 0.25: human wait 50 s, human abandon 14.5%; alpha 0.5: human wait 76 s, human abandon 20.2%
- psu_bank / handshake: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 37 s, human abandon 11.1%; alpha 0.25: human wait 32 s, human abandon 9.8%; alpha 0.5: human wait 29 s, human abandon 8.6%
- airline / none: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 53 s, human abandon 15.2%; alpha 0.25: human wait 64 s, human abandon 17.8%; alpha 0.5: human wait 100 s, human abandon 25.6%
- airline / deadline_20min: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 53 s, human abandon 15.2%; alpha 0.25: human wait 64 s, human abandon 17.8%; alpha 0.5: human wait 100 s, human abandon 25.6%
- airline / handshake: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 47 s, human abandon 13.6%; alpha 0.25: human wait 44 s, human abandon 12.6%; alpha 0.5: human wait 38 s, human abandon 11.4%

Path memory: first call IVR 122.4 s, second call 65.65 s

Provenance counts: DATA 24, OFFICIAL 24, STD 8, ATLAS 0, ASSUMED 21
