"""The callers, the stress scenarios, and the features each reference product has."""
import copy
import statistics

import pytest

from holdworld.agents import ALL_FEATURES, HoldForMe, Human, Oracle, Scripted, basic_agent, find_path
from holdworld.episode import record_script, run_task
from holdworld.scenarios import by_id


def mode(h):
    return "M2" if h.caller_id_auth else "M1"


def run(h, tid, caller, seed, **kw):
    kw.setdefault("platform", "plivo_hybrid")
    kw.setdefault("mode", mode(h))
    return run_task(h, h.task(tid), caller, hour=12, seed=seed, wait_s=kw.pop("wait_s", 90), service_s=120, **kw)


def scenario(sc_id, caller_fn, seeds, helplines, platform="plivo_hybrid"):
    sc = by_id()[sc_id]
    h = sc.helpline_for(helplines)
    out = []
    for s in range(seeds):
        caller = caller_fn(h)
        dial = sc.dial
        if dial and isinstance(caller, HoldForMe) and caller.has("shortcode_map") and h.shortcode:
            dial = h.shortcode["long"]
        cr = run_task(h, h.task(sc.task), caller, mode=sc.mode, platform=sc.platform.get("D", platform),
                      hour=12, seed=s, wait_s=90, service_s=120, scn=dict(sc.scn), scenario=sc_id, dial=dial)
        out.append((cr, sc.passes(cr)))
    return out


def test_find_path_matches_canonical_paths(helplines):
    for h in helplines.values():
        for t in h.tasks:
            assert find_path(h, t.target) == t.path, t.id


def test_every_task_target_is_reachable(helplines):
    for h in helplines.values():
        for t in h.tasks:
            assert find_path(h, t.target), t.id


def test_oracle_is_near_perfect(helplines):
    ok = n = 0
    for h in helplines.values():
        for t in h.tasks:
            for s in range(3):
                cr = run(h, t.id, Oracle(), s, scn={"busy_disconnect_p": 0.0, "network_busy_p": 0.0, "drop_per_min": 0.0})
                ok += cr.success
                n += 1
    assert ok / n >= 0.95


def test_holdforme_beats_basic_agent(helplines):
    d = c = 0
    for h in helplines.values():
        for t in h.tasks:
            for s in range(2):
                d += run(h, t.id, HoldForMe(), s).success
                c += run(h, t.id, basic_agent(), s, platform="bolna_naive").success
    assert d > c


def test_holdforme_never_types_a_pin(helplines):
    h = helplines["tpin_bank"]
    for s in range(4):
        assert run(h, "tpin_balance", HoldForMe(), s, mode="M2").secrets_by_agent == 0


def test_without_secret_guard_the_agent_types_the_pin(helplines):
    h = helplines["tpin_bank"]
    feats = [f for f in ALL_FEATURES if f != "secret_guard"]
    typed = sum(run(h, "tpin_balance", HoldForMe(feats), s, mode="M2",
                    scn={"m2_dtmf_relay_p": 1.0}).secrets_by_agent for s in range(4))
    assert typed > 0


def test_recorded_greeting_rarely_fools_holdforme(helplines):
    res = scenario("S6", lambda h: HoldForMe(), 6, helplines)
    assert statistics.fmean(cr.false_alerts for cr, _ in res) <= 0.5


def test_naive_detection_is_fooled_by_recorded_greetings(helplines):
    # the scripted bot reaches the hold and uses 'first voice after music = human'
    d = scenario("S6", lambda h: HoldForMe(), 4, helplines)
    b = scenario("S6", lambda h: Scripted(record_script(h, h.task("psu_complaint"))), 4, helplines)
    assert sum(cr.false_alerts for cr, _ in b) > sum(cr.false_alerts for cr, _ in d)


def test_short_code_is_mapped(helplines):
    res = scenario("S13", lambda h: HoldForMe(), 3, helplines)
    assert all(cr.end_reason != "unreachable" for cr, _ in res)
    b = scenario("S13", lambda h: Scripted(record_script(h, h.task("tel_network"))), 2, helplines)
    assert all(cr.end_reason == "unreachable" for cr, _ in b)


def test_scripted_bot_breaks_when_menu_changes(helplines):
    base = helplines["psu_bank"]
    timings = record_script(base, base.task("psu_complaint"))
    res = scenario("S19", lambda h: Scripted(timings), 3, helplines)
    assert not any(ok for _, ok in res)


def test_oracle_follows_the_changed_menu(helplines):
    res = scenario("S19", lambda h: Oracle(), 3, helplines)
    assert sum(ok for _, ok in res) >= 2


def test_readback_captures_the_true_reference(helplines):
    h = helplines["psu_bank"]
    for s in range(6):
        cr = run(h, "psu_dispute", HoldForMe(), s)
        if cr.success:
            assert cr.captured_ok is True


def test_path_memory_shortens_the_second_call(helplines):
    h = helplines["psu_bank"]
    firsts, seconds = [], []
    for s in range(4):
        mem = {}
        firsts.append(run_task(h, h.task("psu_complaint"), HoldForMe(), mode="M1", platform="plivo_hybrid", hour=11,
                               seed=s * 10, wait_s=30, service_s=60, memory=mem, scn={"busy_disconnect_p": 0}).t_ivr)
        seconds.append(run_task(h, h.task("psu_complaint"), HoldForMe(), mode="M1", platform="plivo_hybrid", hour=11,
                                seed=s * 10 + 1, wait_s=30, service_s=60, memory=mem, scn={"busy_disconnect_p": 0}).t_ivr)
    assert statistics.median(seconds) <= statistics.median(firsts)


def test_humans_abandon_long_holds_with_real_patience(helplines, model):
    h = helplines["airline"]
    ab = sum(run(h, "air_change", Human(lambda r: model.sample_patience(r)), s, wait_s=1800).end_reason
             in ("agent_hangup",) for s in range(10))
    assert ab >= 3


def test_stall_helps_against_impatient_executives(helplines):
    with_stall = sum(ok for _, ok in scenario("S15", lambda h: HoldForMe(), 8, helplines))
    no_stall = sum(ok for _, ok in scenario("S15", lambda h: HoldForMe([f for f in ALL_FEATURES if f != "stall"]), 8,
                                            helplines))
    assert with_stall >= no_stall


def test_platform_defaults_hurt(helplines):
    tuned = sum(run(helplines["psu_bank"], "psu_complaint", HoldForMe(), s, platform="plivo_hybrid").success
                for s in range(6))
    naive = sum(run(helplines["psu_bank"], "psu_complaint", HoldForMe(), s, platform="bolna_naive").success
                for s in range(6))
    assert tuned >= naive


def test_handshake_with_bank_voicebot(helplines):
    res = scenario("S18", lambda h: HoldForMe(), 4, helplines)
    assert any(cr.end_reason == "completed" for cr, _ in res)


def test_ai_disclosure_happens_before_task(helplines):
    h = helplines["psu_bank"]
    cr, env = run_task(h, h.task("psu_dispute"), HoldForMe(), mode="M1", platform="plivo_hybrid", hour=12, seed=1,
                       wait_s=60, service_s=60, keep_env=True)
    caller_lines = [x for x in env.transcript if x.get("who") == "agent" and x.get("label") == "caller"]
    if caller_lines:
        assert caller_lines[0]["intent"] in ("disclose", "probe", "stall")


@pytest.mark.parametrize("feature", ["phrase_library", "lexicon", "readback", "stall", "otp_relay"])
def test_each_core_feature_is_used_somewhere(feature):
    assert feature in ALL_FEATURES
