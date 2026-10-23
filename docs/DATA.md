# Data, sources and terms

Every parameter is registered in `holdworld/provenance.py` with a tag and a source. The dashboard's provenance chapter is generated from it. Sources were read on 2026-10-23.

## Real datasets

| Dataset | What HoldWorld uses | Terms |
|---|---|---|
| **Anonymous Bank call-centre data**, Technion SEE Lab (every call of 1999, 440,837 non-phantom records, 17 fields per call) | Queue replay, hourly profiles, service times, the patience curve, the hold-out validation | "The data is free for use. If used, please notify Avi Mandelbaum … and do acknowledge the data source in any of your work." Not redistributed; `python -m holdworld fetch-data` downloads it from https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/ |
| **County Medi-Cal Call Center Data**, California DHCS (Jan–Jun 2026; 34 counties/month) | Contemporary monthly call volume, county average queue waits by language, and reported abandonment. Snapshotted in `data/benchmarks/medi_cal_2026/`; processed for the site by `python scripts/prepare_medi_cal_2026.py`. | Public dataset under Creative Commons Attribution (CC BY). Source, resource links, metric definitions, suppression and scope limits: [`data/benchmarks/medi_cal_2026/README.md`](../data/benchmarks/medi_cal_2026/README.md). Aggregate U.S. county data; not a call-by-call trace or an Indian bank measure. |
| Brown, Gans, Mandelbaum et al., JASA 2005 | The published findings HoldWorld reproduces (announcement hang-up spikes, lognormal service, Erlang-A over Erlang-C) | Citation |

**Please notify Prof. Mandelbaum before publishing results built on the data, as its terms ask.**

## Official / published

| Source | Used for |
|---|---|
| SBI Contact Centre page | The large public-sector bank's menu (0 block, 1 account, 2 cards and cheques, 3 certificates/INB/YONO, 4 deposits, loans, complaints); 15 languages; 34 of 50 services in the IVR |
| KVB IVRS page | Customer ID + # then a 4-digit TPIN; 6 languages; 1860 number |
| Union Bank contact page | Agent reachable at any point; 14 languages |
| IDBI, Indian Bank (BankBazaar, third-party) | The 9 = executive / * = repeat conventions |
| TRAI QoS (PR 86/2025), Airtel May 2026, Jio June 2026 | 95% within 90 s; operator ranges |
| Jio customer care numbers | 199/198 only from a Jio SIM |
| NCH (PIB, Rajya Sabha), RBI Ombudsman | Complaint volumes by sector |
| Ministry of Road Transport & Highways, PIB (14 Sep 2026) | Indian scale context: NHAI reports 1033 coverage above 146,000 km, multilingual 24/7 assistance and around 15,000 calls/day; not a bank queue measurement |
| Bolna, Plivo, Exotel docs | Call limits, silence hang-up, DTMF ability, prices |

## Standards

| Standard | Value |
|---|---|
| Asterisk `indications.conf` `[in]` | ringback 400 Hz × 25 Hz, 0.4 on / 0.2 off / 0.4 on / 2.0 off; busy 0.75/0.75; congestion 0.25/0.25 |
| ITU-T Q.23 / Q.24 | DTMF rows 697/770/852/941 Hz, columns 1209/1336/1477/1633 Hz; tones ≥ 40 ms detected |
| G.711 | 8 kHz μ-law telephone audio |

## Measured but not India-specific

- Speech recognition: Sarvam Saarika 11.81% Hindi WER (Vistaar); Gram Vaani phone baseline 29.7–34.8%
- Ring-time statistics from ~270k answered survey calls (median 10–12 s)
- ServiceNow India CX survey (vendor, n = 4,500): 30.7 h per person per year on hold

## Assumed (swept)

Executive patience with silence, stall extension, refusal of AI callers, OTP delay, the M2 conference DTMF relay, IVR prompt speaking rate, classifier score means, telephony price per minute. Each carries a note and a sweep range. The India Hold Atlas (`docs/ATLAS.md`) is how they become measured.
