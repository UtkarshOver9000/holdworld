"""Where every number in HoldWorld comes from.

Every parameter the simulation uses is registered here with one of five tags:

    DATA      measured in a real dataset (or a peer-reviewed analysis of one)
    OFFICIAL  published by the company, regulator or platform itself
    STD       a technical standard, or the config real systems ship with
    ATLAS     measured by the team calling real Indian helplines
    ASSUMED   nothing published exists; labelled, never hidden, always swept

Modules read values with `P("key")`. The dashboard's provenance panel is
generated from `export()`, so the screen and the code cannot disagree.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

TAGS = ("DATA", "OFFICIAL", "STD", "ATLAS", "ASSUMED")
READ = "2026-10-21"


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    url: str
    read: str = READ


@dataclass
class Param:
    key: str
    value: Any
    tag: str
    source: str
    unit: str = ""
    note: str = ""
    sweep: Any = None  # range explored when the value is uncertain

    def __post_init__(self) -> None:
        if self.tag not in TAGS:
            raise ValueError(f"{self.key}: unknown tag {self.tag}")


SOURCES: dict[str, Source] = {s.key: s for s in [
    Source("anonbank", "Anonymous Bank call-centre data, every call of 1999 (Technion SEE Lab)",
           "https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/"),
    Source("brown2005", "Brown, Gans, Mandelbaum et al., Statistical Analysis of a Telephone Call Center, JASA 2005",
           "https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Brown-etal-CCdata.pdf"),
    Source("sbi_official", "SBI Contact Centre page (official IVR menu)",
           "https://sbi.bank.in/web/customer-care/contact-centre"),
    Source("kvb_official", "Karur Vysya Bank IVRS page (official)",
           "https://www.kvb.bank.in/ways-to-bank/ivrs/"),
    Source("union_official", "Union Bank of India contact page (official)",
           "https://www.unionbankofindia.bank.in/en/common/contact-us"),
    Source("icici_official_partial", "ICICI Bank official card-blocking IVR path excerpt",
           "https://www.icici.bank.in/nri-banking/service-diy", "2026-10-23"),
    Source("passport_seva_partial", "Passport Seva official call-centre FAQ; IVR keys not published",
           "https://www.passportindia.gov.in/psp/FaqCallCentre", "2026-10-23"),
    Source("railway_139_2016", "Indian Railways official 139 cancellation route (historical 2016 document)",
           "https://sr.indianrailways.gov.in/ticker/1464264041236139-cancellation.pdf", "2026-10-23"),
    Source("idbi_thirdparty", "IDBI customer care IVR (BankBazaar, third-party)",
           "https://www.bankbazaar.com/idbi-home-loan-customer-care.html"),
    Source("indianbank_thirdparty", "Indian Bank customer care IVR (BankBazaar, third-party)",
           "https://www.bankbazaar.com/indian-bank-home-loan-customer-care.html"),
    Source("trai_qos", "TRAI QoS benchmark, PR 86/2025",
           "https://trai.gov.in/sites/default/files/2025-09/PR_No.86of2025.pdf"),
    Source("airtel_may2026", "Airtel QoS report May 2026 (TelecomTalk)",
           "https://telecomtalk.info/airtel-surpasses-call-centre-accessibility-benchmarks-may2026/1010350/"),
    Source("jio_jun2026", "Jio QoS report June 2026 (TelecomTalk)",
           "https://telecomtalk.info/jio-trai-customer-service-qos-norms-june2026/1010367/"),
    Source("jio_shortcode", "Jio customer care numbers (199 from Jio SIM only)",
           "https://bajajfinserv.in/jio-customer-care-number"),
    Source("nch_pib", "PIB: National Consumer Helpline monthly dockets",
           "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/mar/doc2025314520301.pdf"),
    Source("nch_rs2025", "Rajya Sabha reply, NCH grievances by sector 2024",
           "https://rsdebate.nic.in/bitstream/123456789/759128/1/PQ_267_18032025_U1951_p192_p193.pdf"),
    Source("rbi_ombudsman", "RBI Annual Report of the Ombudsman Scheme 2024-25",
           "https://website.rbi.org.in/web/rbi/-/publications/annual-report-of-ombudsman-scheme-2024-25"),
    Source("servicenow2024", "ServiceNow India CX report, 31 Jul 2024 (vendor survey, n=4,500)",
           "https://newsroom.servicenow.com/press-releases/details/2024/Indians-lost-over-15-billion-hours-on-hold-to-customer-service-in-2023-resulting-in-55-billion-in-economic-loss-output--07-31-2024-traffic/default.aspx"),
    Source("asterisk_tones", "Asterisk indications.conf, [in] India tones",
           "https://github.com/asterisk/asterisk/blob/master/configs/samples/indications.conf.sample"),
    Source("itu_q23", "ITU-T Q.23 DTMF frequencies", "https://www.itu.int/rec/T-REC-Q.23"),
    Source("itu_q24", "ITU-T Q.24 DTMF receiver timing (as quoted in W3C WebRTC list)",
           "https://lists.w3.org/Archives/Public/public-webrtc/2014Jan/0195.html"),
    Source("plivo_stream", "Plivo audio streaming reference (sendDTMF, formats)",
           "https://plivo.com/docs/voice-agents/audio-streaming/concepts/audio-streaming-reference"),
    Source("plivo_limits", "Plivo account limits (4 h default call duration)",
           "https://www.plivo.com/docs/voice/concepts/account-limits"),
    Source("plivo_india", "Plivo India calling rules", "https://www.plivo.com/docs/voice/concepts/india-calling"),
    Source("bolna_agent_api", "Bolna create-agent API (call_terminate, hangup_after_silence)",
           "https://www.bolna.ai/docs/api-reference/agent/v2/create.md"),
    Source("bolna_changelog", "Bolna changelog May 2025 (max call 40 min)",
           "https://www.bolna.ai/docs/changelog/may-2025.md"),
    Source("bolna_dtmf", "Bolna DTMF docs (receive only)", "https://www.bolna.ai/docs/dtmf"),
    Source("bolna_pricing", "Bolna pricing", "https://www.bolna.ai/pricing"),
    Source("bolna_sip", "Bolna SIP trunking", "https://www.bolna.ai/docs/sip-trunking/overview.md"),
    Source("exotel_voicebot", "Exotel Voicebot applet (60-minute stream)",
           "https://support.exotel.com/support/solutions/articles/3000132302"),
    Source("gramvaani", "Gram Vaani Hindi telephone ASR challenge, Interspeech 2022",
           "https://www.isca-archive.org/interspeech_2022/bhanushali22_interspeech.html"),
    Source("sarvam", "Sarvam Saarika model card (Hindi WER on Vistaar)",
           "https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika.md"),
    Source("yamnet", "YAMNet class map (521 AudioSet classes, Apache-2.0)",
           "https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv"),
    Source("ringtime", "Survey-dialler ring-time statistics (~270k answered calls)",
           "https://support.unicomsi.com/manuals/intelligence/75/DDL/InterviewServerArchitecture.08.130.html"),
    Source("sierra", "Sierra: navigating IVR systems (11 Aug 2026)", "https://sierra.ai/blog/navigating-ivr-systems"),
    Source("regal", "Regal: navigating complex IVRs (25 Aug 2026)",
           "https://www.regal.ai/blog/how-regal-ai-agents-navigate-complex-ivrs"),
    Source("pine", "Pine Series A (Dec 2025) and reported results",
           "https://www.businesswire.com/news/home/20251203384902/en"),
    Source("google_hfm", "Google Hold for Me / Call Assist", "https://support.google.com/phoneapp/answer/10104618"),
    Source("atlas", "India Hold Atlas: our own measured calls (pending)", ""),
    Source("assumption", "No published source exists; value is an explicit assumption", ""),
]}


_PARAMS: list[Param] = [
    # --- India call-progress tones and DTMF -------------------------------------------
    Param("tone.ring", "400*25", "STD", "asterisk_tones", note="400 Hz modulated by 25 Hz"),
    Param("tone.ring.cadence", [0.4, 0.2, 0.4, 2.0], "STD", "asterisk_tones", "s", "on/off/on/off"),
    Param("tone.busy.cadence", [0.75, 0.75], "STD", "asterisk_tones", "s"),
    Param("tone.congestion.cadence", [0.25, 0.25], "STD", "asterisk_tones", "s"),
    Param("dtmf.low_hz", [697, 770, 852, 941], "STD", "itu_q23", "Hz"),
    Param("dtmf.high_hz", [1209, 1336, 1477, 1633], "STD", "itu_q23", "Hz"),
    Param("dtmf.tone_ms", 100, "STD", "itu_q24", "ms", "receivers must detect >=40 ms; 100 ms is safe"),
    Param("dtmf.gap_ms", 100, "STD", "itu_q24", "ms", "minimum gaps 30-70 ms by country"),
    Param("audio.codec", "G.711 mu-law 8 kHz", "OFFICIAL", "plivo_stream"),

    # --- speech recognition on phone lines --------------------------------------------
    Param("asr.wer.range", [0.10, 0.35], "DATA", "gramvaani",
          note="Sarvam 11.81% (Vistaar, not phone); Gram Vaani phone baseline 29.7-34.8%"),
    Param("asr.wer.en", 0.15, "DATA", "sarvam", note="live speech: default inside the measured range", sweep=[0.10, 0.35]),
    Param("asr.wer.hi", 0.22, "DATA", "gramvaani", note="live speech: default inside the measured range", sweep=[0.10, 0.35]),
    Param("asr.wer.recorded", 0.118, "DATA", "sarvam",
          note="clean recorded prompts: the best measured Hindi WER (Sarvam, 11.81%)", sweep=[0.10, 0.35]),

    # --- queue behaviour (published analysis of the real dataset) ----------------------
    Param("queue.selfserve_frac", 0.65, "DATA", "brown2005", note="callers who finish in the IVR"),
    Param("queue.abandon_frac", 0.20, "DATA", "brown2005", note="of callers who asked for an agent"),
    Param("queue.patience_mean_s", 446, "DATA", "brown2005", "s"),
    Param("queue.announce_every_s", 60, "DATA", "brown2005", "s",
          "hang-up hazard spikes after the first message and again at ~60 s"),
    Param("queue.priority_headstart_s", 90, "DATA", "anonbank", "s", "priority customers get 1.5 min head start"),
    Param("queue.service_shape", "lognormal", "DATA", "brown2005"),

    # --- people --------------------------------------------------------------------------
    Param("user.answer_s.median", 11.0, "DATA", "ringtime", "s", "UK dialler log, median 10-12 s"),
    Param("user.answer_s.p75", 16.5, "DATA", "ringtime", "s", "upper quartile 14-19 s"),
    Param("user.miss_p", 0.08, "ASSUMED", "assumption", note="user does not pick up at all", sweep=[0.0, 0.25]),
    Param("user.primed_factor", 0.5, "ASSUMED", "assumption",
          note="answer time multiplier when warned a human is ~1 min away", sweep=[0.3, 1.0]),
    Param("user.keypress_react_s", 5.0, "ASSUMED", "assumption", "s", sweep=[2, 12]),
    Param("otp.delay_s.median", 8.0, "ASSUMED", "assumption", "s",
          "no Indian OTP latency measurement found", sweep=[3, 60]),
    Param("exec.dead_air_patience_s", [6.0, 15.0], "ASSUMED", "assumption", "s",
          "nothing published; Atlas will measure", sweep=[4, 30]),
    Param("exec.stall_extension_s", 25.0, "ASSUMED", "assumption", "s", sweep=[10, 45]),
    Param("exec.max_stalls", 2, "ASSUMED", "assumption", note="times an executive agrees to hold", sweep=[1, 3]),
    Param("exec.refuse_ai_p", 0.15, "ASSUMED", "assumption", note="'I can only speak to the account holder'",
          sweep=[0.0, 0.5]),
    Param("exec.probe_reply_p", 0.95, "ASSUMED", "assumption", note="a person answers a 'hello?'", sweep=[0.8, 1.0]),
    Param("exec.midcall_hold_p", 0.30, "ASSUMED", "assumption", note="'please hold while I check'", sweep=[0.0, 0.6]),
    Param("exec.midcall_hold_s", [20.0, 90.0], "ASSUMED", "assumption", "s", note="length of a mid-call hold"),
    Param("human.nav_correct_p", 0.90, "ASSUMED", "assumption", note="per menu level"),
    Param("human.redial_p", 0.50, "ASSUMED", "assumption", note="a person calls back after giving up", sweep=[0.2, 0.8]),

    # --- platforms ------------------------------------------------------------------------
    Param("bolna.rate_inr_min", 5.52, "OFFICIAL", "bolna_pricing", "INR/min", "pay-as-you-go, telephony extra"),
    Param("bolna.rate_bulk_inr_min", 4.15, "OFFICIAL", "bolna_pricing", "INR/min"),
    Param("bolna.pulse_s", 30, "OFFICIAL", "bolna_pricing", "s"),
    Param("bolna.call_terminate_default_s", 90, "OFFICIAL", "bolna_agent_api", "s"),
    Param("bolna.call_max_s", 2400, "OFFICIAL", "bolna_changelog", "s", "40 min (May 2025 changelog)"),
    Param("bolna.hangup_after_silence_s", 10, "OFFICIAL", "bolna_agent_api", "s"),
    Param("bolna.online_check_s", 10, "OFFICIAL", "bolna_agent_api", "s", "speaks 'Hello, are you still there?'"),
    Param("bolna.can_send_dtmf", False, "OFFICIAL", "bolna_dtmf", note="receive only"),
    Param("plivo.time_limit_s", 14400, "OFFICIAL", "plivo_limits", "s"),
    Param("plivo.can_send_dtmf", True, "OFFICIAL", "plivo_stream", note="sendDTMF over bidirectional stream"),
    Param("plivo.india_pulse_s", 30, "OFFICIAL", "plivo_india", "s"),
    Param("exotel.stream_max_s", 3600, "OFFICIAL", "exotel_voicebot", "s"),
    Param("exotel.can_send_dtmf", False, "OFFICIAL", "exotel_voicebot", note="no send-DTMF message documented"),
    Param("telephony.rate_inr_min", 0.60, "ASSUMED", "assumption", "INR/min",
          "UNVERIFIED placeholder until Plivo India pricing is read", sweep=[0.3, 1.5]),
    Param("pipeline.rate_inr_min", 5.52, "ASSUMED", "assumption", "INR/min",
          "STT+LLM+TTS while talking; Bolna's rate used as a proxy"),
    Param("holdclassifier.rate_inr_min", 0.05, "ASSUMED", "assumption", "INR/min", "small on-server audio classifier during hold", sweep=[0.0, 0.5]),
    Param("dtmf.latency_s.plivo", 0.3, "ASSUMED", "assumption", "s", "sendDTMF over the stream to tone on the line", sweep=[0.1, 1.0]),
    Param("dtmf.latency_s.bolna_custom_fn", 1.5, "ASSUMED", "assumption", "s",
          "custom function -> our server -> Plivo API; untested"),
    Param("platform.music_counts_as_silence_p", 0.7, "ASSUMED", "assumption",
          note="whether hold music resets a platform's silence timer is undocumented"),

    # --- India context ---------------------------------------------------------------------
    Param("trai.answer_90s_benchmark", 0.95, "OFFICIAL", "trai_qos", note="calls answered by an executive within 90 s"),
    Param("trai.airtel_range", [0.9521, 0.9833], "OFFICIAL", "airtel_may2026"),
    Param("trai.jio_range", [0.9903, 0.9997], "OFFICIAL", "jio_jun2026"),
    Param("nch.monthly_avg", 107966, "OFFICIAL", "nch_pib", "complaints/month", "Apr-Jun 2024"),
    Param("nch.sector_2024", {"e-commerce": 440185, "consumer durables": 77873, "electronics": 74288,
                              "banking": 72932, "telecom": 69193}, "OFFICIAL", "nch_rs2025"),
    Param("rbi.ombudsman_fy25", 1334000, "OFFICIAL", "rbi_ombudsman", "complaints", "press coverage of the report"),
    Param("servicenow.hours_per_person", 30.7, "DATA", "servicenow2024", "h/yr", "vendor survey, self-reported"),
    Param("servicenow.total_hours", 15e9, "DATA", "servicenow2024", "h/yr", "vendor survey, self-reported"),
    Param("servicenow.inr_per_hour", 502.79, "DATA", "servicenow2024", "INR/h", "Glassdoor average used by the report"),
    Param("sbi.languages", 15, "OFFICIAL", "sbi_official"),
    Param("sbi.services_ivr", 34, "OFFICIAL", "sbi_official", note="of 50 listed services"),
    Param("sbi.services_agent_only", 16, "OFFICIAL", "sbi_official", note="of 50 listed services"),

    # --- reference lines from others (vendor-reported) ------------------------------------
    Param("ref.sierra_passrate", [0.57, 0.85], "DATA", "sierra", note="vendor blog: bare vs guided"),
    Param("ref.regal_passrate", [0.80, 0.96], "DATA", "regal", note="vendor blog, one customer"),
    Param("ref.pine_minutes_saved", 270, "DATA", "pine", "min/user", "company-reported"),
]

REGISTRY: dict[str, Param] = {p.key: p for p in _PARAMS}


def P(key: str) -> Any:
    return REGISTRY[key].value


def register(param: Param) -> Param:
    """Modules that derive values from data (e.g. fitted patience) register them here."""
    if param.source not in SOURCES:
        raise KeyError(f"{param.key}: unknown source {param.source}")
    REGISTRY[param.key] = param
    return param


def export() -> dict:
    return {
        "sources": {k: asdict(v) for k, v in SOURCES.items()},
        "params": [asdict(p) for p in REGISTRY.values()],
        "counts": {t: sum(1 for p in REGISTRY.values() if p.tag == t) for t in TAGS},
    }
