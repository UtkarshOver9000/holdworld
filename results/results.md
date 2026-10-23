# HoldWorld results

Generated 2026-10-23 22:43:23 (quick=False). Every number below is produced by `python -m holdworld run`; nothing is typed by hand.

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
| Human caller | 780 | 88% [85-90] | 2.11 | 86.05 | 0.0 | 0.0 |
| Scripted bot | 780 | 53% [50-57] | 0.0 | 66.0 | 0.424 | 5.2 |
| Basic agent | 780 | 3% [2-4] | 0.0 | 57.9 | 0.0 | 12.24 |
| HoldForMe | 780 | 69% [66-72] | 0.4 | 105.0 | 0.0 | 9.99 |
| Oracle | 780 | 97% [96-98] | 1.2 | 60.15 | 0.0 | 3.19 |

## 3. Stress suite (pass rate)

| Scenario | Scripted bot | Basic agent | HoldForMe | Oracle |
|---|---|---|---|---|
| S1 Hindi menus, Hinglish labels | 90% [74-97] | 0% [0-11] | 70% [52-83] | 97% [83-99] |
| S2 Menu says 'press' but only listens to speech | 0% [0-11] | 0% [0-11] | 37% [22-54] | 87% [70-95] |
| S3 40 s disclaimer, keys ignored while it plays | 87% [70-95] | 0% [0-11] | 93% [79-98] | 90% [74-97] |
| S4 Menu loop and a dead end | 90% [74-97] | 0% [0-11] | 80% [63-90] | 100% [89-100] |
| S5 Account menu needs the registered mobile | 100% [89-100] | 100% [89-100] | 100% [89-100] | 100% [89-100] |
| S6 A recording that sounds like a person, every minute | 0% [0-11] | 0% [0-11] | 73% [56-86] | 100% [89-100] |
| S7 Music cut mid-note by a soft 'hello?' | 90% [74-97] | 0% [0-11] | 47% [30-64] | 100% [89-100] |
| S8 Queue position announced in Hindi every 30 s | 0% [0-11] | 0% [0-11] | 100% [89-100] | 100% [89-100] |
| S9 Callback offered after 2 minutes | 90% [74-97] | 0% [0-11] | 97% [83-99] | 100% [89-100] |
| S10 'All executives are busy, call later' | 23% [12-41] | 0% [0-11] | 63% [46-78] | 50% [33-67] |
| S11 Call drops 40 s into the hold | 50% [33-67] | 0% [0-11] | 73% [56-86] | 57% [39-73] |
| S12 Bad line: 34.8% speech errors | 73% [56-86] | 7% [2-21] | 13% [5-30] | 100% [89-100] |
| S13 User gives the operator short code 199 | 0% [0-11] | 0% [0-11] | 87% [70-95] | 0% [0-11] |
| S14 Transferred to another team, second hold | 90% [74-97] | 0% [0-11] | 67% [49-81] | 100% [89-100] |
| S15 Impatient executive (4-6 s of silence) | 93% [79-98] | 0% [0-11] | 73% [56-86] | 100% [89-100] |
| S16 OTP to the registered mobile mid-call | 53% [36-70] | 0% [0-11] | 80% [63-90] | 93% [79-98] |
| S17 Voice platform left on default settings | 90% [74-97] | 0% [0-11] | 47% [30-64] | 100% [89-100] |
| S18 The bank's own voicebot answers | 93% [79-98] | 0% [0-11] | 77% [59-88] | 100% [89-100] |
| S19 Menu changed since the script was recorded | 0% [0-11] | 0% [0-11] | 73% [56-86] | 100% [89-100] |
| S20 Account menu needs a PIN | 0% [0-11] | 0% [0-11] | 60% [42-75] | 100% [89-100] |
| S21 Two transfers before the right team answers | 93% [79-98] | 0% [0-11] | 57% [39-73] | 100% [89-100] |
| S22 Published 139 counter-ticket path (2016 excerpt) | 90% [74-97] | 0% [0-11] | 33% [19-51] | 97% [83-99] |
| S23 Published bank card-blocking path excerpt | 0% [0-11] | 0% [0-11] | 77% [59-88] | 100% [89-100] |

## 4. Handoff modes (airline line)

- M1|stall: 100% [76-100]
- M1|no stall: 83% [55-95]
- M2|stall: 58% [32-81]
- M2|no stall: 58% [32-81]
- M3|stall: 100% [76-100]
- M3|no stall: 83% [55-95]

Pre-warn policy: alert the user 80 s before predicted pickup (90% readiness target not reached; selected the best observed rate; 25 s prediction-error SD assumption).


## 5. City: share of callers who never hang up

- psu_bank / none: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 43 s, human abandon 12.7%; alpha 0.25: human wait 50 s, human abandon 14.5%; alpha 0.5: human wait 76 s, human abandon 20.2%
- psu_bank / deadline_20min: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 43 s, human abandon 12.7%; alpha 0.25: human wait 50 s, human abandon 14.5%; alpha 0.5: human wait 76 s, human abandon 20.2%
- psu_bank / callback: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 33 s, human abandon 7.8%; alpha 0.25: human wait 22 s, human abandon 3.9%; alpha 0.5: human wait 19 s, human abandon 2.9%
- psu_bank / offpeak: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 42 s, human abandon 12.8%; alpha 0.25: human wait 53 s, human abandon 14.6%; alpha 0.5: human wait 94 s, human abandon 22.0%
- psu_bank / handshake: alpha 0.0: human wait 35 s, human abandon 10.6%; alpha 0.1: human wait 37 s, human abandon 11.1%; alpha 0.25: human wait 32 s, human abandon 9.8%; alpha 0.5: human wait 29 s, human abandon 8.6%
- tpin_bank / none: alpha 0.0: human wait 56 s, human abandon 15.8%; alpha 0.1: human wait 67 s, human abandon 18.1%; alpha 0.25: human wait 73 s, human abandon 19.2%; alpha 0.5: human wait 106 s, human abandon 26.2%
- tpin_bank / deadline_20min: alpha 0.0: human wait 56 s, human abandon 15.8%; alpha 0.1: human wait 67 s, human abandon 18.1%; alpha 0.25: human wait 73 s, human abandon 19.2%; alpha 0.5: human wait 106 s, human abandon 26.2%
- tpin_bank / callback: alpha 0.0: human wait 56 s, human abandon 15.8%; alpha 0.1: human wait 60 s, human abandon 14.4%; alpha 0.25: human wait 45 s, human abandon 8.6%; alpha 0.5: human wait 32 s, human abandon 4.9%
- tpin_bank / offpeak: alpha 0.0: human wait 56 s, human abandon 15.8%; alpha 0.1: human wait 88 s, human abandon 18.7%; alpha 0.25: human wait 164 s, human abandon 26.0%; alpha 0.5: human wait 149 s, human abandon 22.9%
- tpin_bank / handshake: alpha 0.0: human wait 56 s, human abandon 15.8%; alpha 0.1: human wait 61 s, human abandon 16.5%; alpha 0.25: human wait 56 s, human abandon 14.8%; alpha 0.5: human wait 50 s, human abandon 13.9%
- zero_out_bank / none: alpha 0.0: human wait 41 s, human abandon 11.7%; alpha 0.1: human wait 45 s, human abandon 13.0%; alpha 0.25: human wait 53 s, human abandon 14.9%; alpha 0.5: human wait 76 s, human abandon 20.0%
- zero_out_bank / deadline_20min: alpha 0.0: human wait 41 s, human abandon 11.7%; alpha 0.1: human wait 45 s, human abandon 13.0%; alpha 0.25: human wait 53 s, human abandon 14.9%; alpha 0.5: human wait 76 s, human abandon 20.0%
- zero_out_bank / callback: alpha 0.0: human wait 41 s, human abandon 11.7%; alpha 0.1: human wait 37 s, human abandon 8.5%; alpha 0.25: human wait 22 s, human abandon 4.2%; alpha 0.5: human wait 18 s, human abandon 3.0%
- zero_out_bank / offpeak: alpha 0.0: human wait 41 s, human abandon 11.7%; alpha 0.1: human wait 47 s, human abandon 13.3%; alpha 0.25: human wait 57 s, human abandon 15.3%; alpha 0.5: human wait 94 s, human abandon 22.9%
- zero_out_bank / handshake: alpha 0.0: human wait 41 s, human abandon 11.7%; alpha 0.1: human wait 40 s, human abandon 11.4%; alpha 0.25: human wait 35 s, human abandon 10.3%; alpha 0.5: human wait 28 s, human abandon 7.9%
- telecom / none: alpha 0.0: human wait 10 s, human abandon 3.3%; alpha 0.1: human wait 13 s, human abandon 4.2%; alpha 0.25: human wait 13 s, human abandon 4.0%; alpha 0.5: human wait 14 s, human abandon 4.3%
- telecom / deadline_20min: alpha 0.0: human wait 10 s, human abandon 3.3%; alpha 0.1: human wait 13 s, human abandon 4.2%; alpha 0.25: human wait 13 s, human abandon 4.0%; alpha 0.5: human wait 14 s, human abandon 4.3%
- telecom / callback: alpha 0.0: human wait 10 s, human abandon 3.3%; alpha 0.1: human wait 18 s, human abandon 3.6%; alpha 0.25: human wait 17 s, human abandon 2.7%; alpha 0.5: human wait 18 s, human abandon 2.8%
- telecom / offpeak: alpha 0.0: human wait 10 s, human abandon 3.3%; alpha 0.1: human wait 12 s, human abandon 3.7%; alpha 0.25: human wait 16 s, human abandon 4.7%; alpha 0.5: human wait 31 s, human abandon 8.1%
- telecom / handshake: alpha 0.0: human wait 10 s, human abandon 3.3%; alpha 0.1: human wait 10 s, human abandon 3.4%; alpha 0.25: human wait 7 s, human abandon 2.3%; alpha 0.5: human wait 3 s, human abandon 0.9%
- airline / none: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 53 s, human abandon 15.2%; alpha 0.25: human wait 64 s, human abandon 17.8%; alpha 0.5: human wait 100 s, human abandon 25.6%
- airline / deadline_20min: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 53 s, human abandon 15.2%; alpha 0.25: human wait 64 s, human abandon 17.8%; alpha 0.5: human wait 100 s, human abandon 25.6%
- airline / callback: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 40 s, human abandon 9.8%; alpha 0.25: human wait 21 s, human abandon 4.1%; alpha 0.5: human wait 17 s, human abandon 2.8%
- airline / offpeak: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 56 s, human abandon 16.1%; alpha 0.25: human wait 69 s, human abandon 18.4%; alpha 0.5: human wait 125 s, human abandon 28.3%
- airline / handshake: alpha 0.0: human wait 47 s, human abandon 13.9%; alpha 0.1: human wait 47 s, human abandon 13.6%; alpha 0.25: human wait 44 s, human abandon 12.6%; alpha 0.5: human wait 38 s, human abandon 11.4%
- ecommerce / none: alpha 0.0: human wait 42 s, human abandon 12.1%; alpha 0.1: human wait 44 s, human abandon 12.6%; alpha 0.25: human wait 56 s, human abandon 15.3%; alpha 0.5: human wait 80 s, human abandon 20.1%
- ecommerce / deadline_20min: alpha 0.0: human wait 42 s, human abandon 12.1%; alpha 0.1: human wait 44 s, human abandon 12.6%; alpha 0.25: human wait 56 s, human abandon 15.3%; alpha 0.5: human wait 80 s, human abandon 20.1%
- ecommerce / callback: alpha 0.0: human wait 42 s, human abandon 12.1%; alpha 0.1: human wait 42 s, human abandon 9.1%; alpha 0.25: human wait 31 s, human abandon 5.7%; alpha 0.5: human wait 25 s, human abandon 3.9%
- ecommerce / offpeak: alpha 0.0: human wait 42 s, human abandon 12.1%; alpha 0.1: human wait 84 s, human abandon 16.0%; alpha 0.25: human wait 106 s, human abandon 17.2%; alpha 0.5: human wait 103 s, human abandon 16.0%
- ecommerce / handshake: alpha 0.0: human wait 42 s, human abandon 12.1%; alpha 0.1: human wait 40 s, human abandon 11.3%; alpha 0.25: human wait 39 s, human abandon 10.9%; alpha 0.5: human wait 30 s, human abandon 8.6%
- electricity / none: alpha 0.0: human wait 60 s, human abandon 16.6%; alpha 0.1: human wait 67 s, human abandon 18.2%; alpha 0.25: human wait 86 s, human abandon 22.8%; alpha 0.5: human wait 153 s, human abandon 33.5%
- electricity / deadline_20min: alpha 0.0: human wait 60 s, human abandon 16.6%; alpha 0.1: human wait 67 s, human abandon 18.2%; alpha 0.25: human wait 86 s, human abandon 22.8%; alpha 0.5: human wait 153 s, human abandon 33.5%
- electricity / callback: alpha 0.0: human wait 60 s, human abandon 16.6%; alpha 0.1: human wait 60 s, human abandon 13.5%; alpha 0.25: human wait 43 s, human abandon 8.5%; alpha 0.5: human wait 34 s, human abandon 5.4%
- electricity / offpeak: alpha 0.0: human wait 60 s, human abandon 16.6%; alpha 0.1: human wait 100 s, human abandon 20.0%; alpha 0.25: human wait 126 s, human abandon 21.2%; alpha 0.5: human wait 120 s, human abandon 19.0%
- electricity / handshake: alpha 0.0: human wait 60 s, human abandon 16.6%; alpha 0.1: human wait 60 s, human abandon 16.7%; alpha 0.25: human wait 62 s, human abandon 17.3%; alpha 0.5: human wait 63 s, human abandon 17.0%
- gov_docs / none: alpha 0.0: human wait 59 s, human abandon 16.8%; alpha 0.1: human wait 65 s, human abandon 18.2%; alpha 0.25: human wait 83 s, human abandon 22.3%; alpha 0.5: human wait 129 s, human abandon 31.8%
- gov_docs / deadline_20min: alpha 0.0: human wait 59 s, human abandon 16.8%; alpha 0.1: human wait 65 s, human abandon 18.2%; alpha 0.25: human wait 83 s, human abandon 22.3%; alpha 0.5: human wait 129 s, human abandon 31.8%
- gov_docs / callback: alpha 0.0: human wait 59 s, human abandon 16.8%; alpha 0.1: human wait 60 s, human abandon 13.8%; alpha 0.25: human wait 40 s, human abandon 7.3%; alpha 0.5: human wait 34 s, human abandon 5.3%
- gov_docs / offpeak: alpha 0.0: human wait 59 s, human abandon 16.8%; alpha 0.1: human wait 107 s, human abandon 20.7%; alpha 0.25: human wait 124 s, human abandon 20.1%; alpha 0.5: human wait 123 s, human abandon 18.6%
- gov_docs / handshake: alpha 0.0: human wait 59 s, human abandon 16.8%; alpha 0.1: human wait 58 s, human abandon 16.4%; alpha 0.25: human wait 58 s, human abandon 16.1%; alpha 0.5: human wait 52 s, human abandon 14.9%
- gas / none: alpha 0.0: human wait 61 s, human abandon 16.3%; alpha 0.1: human wait 68 s, human abandon 17.6%; alpha 0.25: human wait 66 s, human abandon 17.0%; alpha 0.5: human wait 111 s, human abandon 25.3%
- gas / deadline_20min: alpha 0.0: human wait 61 s, human abandon 16.3%; alpha 0.1: human wait 68 s, human abandon 17.6%; alpha 0.25: human wait 66 s, human abandon 17.0%; alpha 0.5: human wait 111 s, human abandon 25.3%
- gas / callback: alpha 0.0: human wait 61 s, human abandon 16.3%; alpha 0.1: human wait 78 s, human abandon 16.2%; alpha 0.25: human wait 71 s, human abandon 12.1%; alpha 0.5: human wait 59 s, human abandon 9.0%
- gas / offpeak: alpha 0.0: human wait 61 s, human abandon 16.3%; alpha 0.1: human wait 92 s, human abandon 19.2%; alpha 0.25: human wait 131 s, human abandon 22.2%; alpha 0.5: human wait 208 s, human abandon 31.9%
- gas / handshake: alpha 0.0: human wait 61 s, human abandon 16.3%; alpha 0.1: human wait 63 s, human abandon 16.2%; alpha 0.25: human wait 49 s, human abandon 13.3%; alpha 0.5: human wait 59 s, human abandon 15.4%
- icici_fragment / none: alpha 0.0: human wait 48 s, human abandon 13.5%; alpha 0.1: human wait 53 s, human abandon 14.9%; alpha 0.25: human wait 65 s, human abandon 17.1%; alpha 0.5: human wait 97 s, human abandon 22.9%
- icici_fragment / deadline_20min: alpha 0.0: human wait 48 s, human abandon 13.5%; alpha 0.1: human wait 53 s, human abandon 14.9%; alpha 0.25: human wait 65 s, human abandon 17.1%; alpha 0.5: human wait 97 s, human abandon 22.9%
- icici_fragment / callback: alpha 0.0: human wait 48 s, human abandon 13.5%; alpha 0.1: human wait 44 s, human abandon 10.9%; alpha 0.25: human wait 28 s, human abandon 6.1%; alpha 0.5: human wait 19 s, human abandon 3.0%
- icici_fragment / offpeak: alpha 0.0: human wait 48 s, human abandon 13.5%; alpha 0.1: human wait 53 s, human abandon 14.4%; alpha 0.25: human wait 70 s, human abandon 17.9%; alpha 0.5: human wait 101 s, human abandon 22.8%
- icici_fragment / handshake: alpha 0.0: human wait 48 s, human abandon 13.5%; alpha 0.1: human wait 49 s, human abandon 13.6%; alpha 0.25: human wait 46 s, human abandon 12.9%; alpha 0.5: human wait 47 s, human abandon 12.4%
- railway_139_2016 / none: alpha 0.0: human wait 50 s, human abandon 14.1%; alpha 0.1: human wait 53 s, human abandon 14.8%; alpha 0.25: human wait 64 s, human abandon 17.5%; alpha 0.5: human wait 100 s, human abandon 24.0%
- railway_139_2016 / deadline_20min: alpha 0.0: human wait 50 s, human abandon 14.1%; alpha 0.1: human wait 53 s, human abandon 14.8%; alpha 0.25: human wait 64 s, human abandon 17.5%; alpha 0.5: human wait 100 s, human abandon 24.0%
- railway_139_2016 / callback: alpha 0.0: human wait 50 s, human abandon 14.1%; alpha 0.1: human wait 41 s, human abandon 9.6%; alpha 0.25: human wait 25 s, human abandon 5.2%; alpha 0.5: human wait 18 s, human abandon 2.7%
- railway_139_2016 / offpeak: alpha 0.0: human wait 50 s, human abandon 14.1%; alpha 0.1: human wait 53 s, human abandon 14.7%; alpha 0.25: human wait 72 s, human abandon 18.1%; alpha 0.5: human wait 123 s, human abandon 27.9%
- railway_139_2016 / handshake: alpha 0.0: human wait 50 s, human abandon 14.1%; alpha 0.1: human wait 46 s, human abandon 13.1%; alpha 0.25: human wait 46 s, human abandon 12.8%; alpha 0.5: human wait 40 s, human abandon 11.0%

Airline disruption sensitivity: 3x volume (ASSUMED)
- none: alpha 0.0: human wait 425 s; alpha 0.25: human wait 614 s; alpha 0.5: human wait 647 s
- deadline_20min: alpha 0.0: human wait 425 s; alpha 0.25: human wait 511 s; alpha 0.5: human wait 515 s
- handshake: alpha 0.0: human wait 425 s; alpha 0.25: human wait 565 s; alpha 0.5: human wait 643 s

Weekday pattern: observed 1999 call-centre arrivals; festive peak multipliers below are ASSUMED.
- Mon 1.28x; Tue 1.31x; Wed 1.23x; Thu 1.26x; Fri 0.40x; Sat 0.14x; Sun 1.38x
- 1.00x volume: 50 s mean wait; 1.25x volume: 160 s mean wait; 1.50x volume: 290 s mean wait

## 6. One-factor sensitivity (success rate)

| Assumption | Setting | n | Success | Change from middle (pp) |
|---|---:|---:|---:|---:|
| Executive silence tolerance | 4-6 s | 30 | 73% [56-86] | +0.0 |
| Executive silence tolerance | 10-14 s | 30 | 73% [56-86] | +0.0 |
| Executive silence tolerance | 24-30 s | 30 | 73% [56-86] | +0.0 |
| Speech error rate | 10 | 30 | 63% [46-78] | +46.7 |
| Speech error rate | 35 | 30 | 17% [7-34] | +0.0 |
| Speech error rate | 50 | 30 | 3% [1-17] | -13.3 |
| Executive AI refusal | 0% | 30 | 73% [56-86] | +0.0 |
| Executive AI refusal | 15% | 30 | 73% [56-86] | +0.0 |
| Executive AI refusal | 40% | 30 | 73% [56-86] | +0.0 |
| OTP delivery delay | 0.5x | 30 | 83% [66-93] | +0.0 |
| OTP delivery delay | 1x | 30 | 83% [66-93] | +0.0 |
| OTP delivery delay | 2x | 30 | 77% [59-88] | -6.7 |
| M2 keypad relay reliability | 0% | 30 | 57% [39-73] | -30.0 |
| M2 keypad relay reliability | 50% | 30 | 87% [70-95] | +0.0 |
| M2 keypad relay reliability | 100% | 30 | 87% [70-95] | +0.0 |

Path memory: first call IVR 156.9 s, second call 64.05 s

Provenance counts: DATA 24, OFFICIAL 24, STD 8, ATLAS 0, ASSUMED 21
