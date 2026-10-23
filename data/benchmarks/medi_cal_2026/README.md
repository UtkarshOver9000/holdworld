# California Medi-Cal call-centre data, 2026

Snapshot of the California Department of Health Care Services public **County Medi-Cal Call Center Data**. The source covers January–June 2026 and was updated on September 30, 2026; dataset metadata was updated October 8, 2026.

- [Dataset and metadata](https://publish.data.ca.gov/dataset/county-medi-cal-call-center-data)
- [Total call volume CSV](https://data.chhs.ca.gov/dataset/176e1bec-f1cc-41db-994c-ce5d460bbb68/resource/d192f34c-48d2-4ba0-88f6-bfd4b12cc902/download/total-call-volume.csv)
- [Average wait time by language CSV](https://data.chhs.ca.gov/dataset/176e1bec-f1cc-41db-994c-ce5d460bbb68/resource/8b0301ff-5bd9-4520-8223-b3e1a8b4679a/download/average-call-wait-time-june-2026.csv)
- [Average abandonment rate CSV](https://data.chhs.ca.gov/dataset/176e1bec-f1cc-41db-994c-ce5d460bbb68/resource/9ecaa5b1-6d4d-4d0a-8b50-d8984f4c5c7e/download/average-call-abandonment-rate.csv)

The dataset is public under Creative Commons Attribution (CC BY). The downloaded source CSV files are retained here. Run `python scripts/prepare_medi_cal_2026.py` to rebuild [`site/data/medi_cal_2026.json`](../../../site/data/medi_cal_2026.json), the dashboard payload.

The measures are monthly and county-level aggregates, not individual call records. Call volume includes the automated response/IVR system and calls outside regular hours. Wait time measures time from entering a queue to an agent pickup and is reported for all languages and by language. Abandonment is calculated among calls that entered the live-agent queue; it excludes callers who self-served in the IVR. Suppressed or absent values remain blank. The dashboard's county medians are unweighted medians across reporting counties; they are not statewide caller-weighted estimates and are not estimates for Indian banks.
