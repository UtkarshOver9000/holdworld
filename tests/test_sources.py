"""Every number has a source, and the encoded real-world facts match those sources."""
from holdworld.provenance import P, REGISTRY, SOURCES, TAGS, export


def test_every_param_has_a_valid_tag_and_source():
    for p in REGISTRY.values():
        assert p.tag in TAGS and p.source in SOURCES, p.key


def test_assumed_params_are_swept_or_explained():
    for p in REGISTRY.values():
        if p.tag == "ASSUMED":
            assert p.sweep is not None or p.note, p.key


def test_export_counts_all_tags():
    e = export()
    assert set(e["counts"]) == set(TAGS) and sum(e["counts"].values()) == len(e["params"])


def test_sbi_structure_main_menu(helplines):
    main = helplines["psu_bank"].nodes["main"]
    assert [o.key for o in main.options] == ["0", "1", "2", "3", "4"]  # SBI official: 0 block .. 4 deposits/complaints
    assert helplines["psu_bank"].structure_source == "sbi_official"


def test_sbi_counts_from_official_page():
    assert P("sbi.languages") == 15 and P("sbi.services_ivr") + P("sbi.services_agent_only") == 50


def test_kvb_language_order(helplines):
    assert helplines["tpin_bank"].languages[:3] == [("1", "en"), ("2", "ta"), ("3", "hi")]  # KVB official


def test_kvb_needs_customer_id_then_tpin(helplines):
    n = helplines["tpin_bank"].nodes
    assert n["cid"].field == "customer_id" and n["cid"].next == "tpin" and n["tpin"].field == "tpin"


def test_union_bank_agent_anytime(helplines):
    assert all("9" in n.extras for n in helplines["zero_out_bank"].nodes.values() if n.type == "menu")


def test_telecom_short_code_rule(helplines):
    sc = helplines["telecom"].shortcode
    assert sc["code"] == "199" and sc["network_only"]


def test_india_tones_match_asterisk():
    assert P("tone.ring") == "400*25" and P("tone.busy.cadence") == [0.75, 0.75]
    assert P("tone.congestion.cadence") == [0.25, 0.25]


def test_dtmf_frequencies_itu_q23():
    assert P("dtmf.low_hz") == [697, 770, 852, 941] and P("dtmf.high_hz") == [1209, 1336, 1477, 1633]


def test_platform_limits_from_docs():
    assert P("bolna.rate_inr_min") == 5.52 and P("bolna.call_terminate_default_s") == 90
    assert P("plivo.time_limit_s") == 14400 and P("exotel.stream_max_s") == 3600
    assert P("bolna.can_send_dtmf") is False


def test_trai_benchmark_and_operator_ranges():
    assert P("trai.answer_90s_benchmark") == 0.95
    lo, hi = P("trai.airtel_range")
    assert 0.95 <= lo < hi <= 1.0


def test_wer_range_from_measured_benchmarks():
    lo, hi = P("asr.wer.range")
    assert lo <= P("asr.wer.recorded") <= hi and lo <= P("asr.wer.hi") <= hi
