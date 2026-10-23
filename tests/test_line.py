"""The call environment: phone standards, IVR behaviour, executive, platforms."""
import random

from holdworld import perception as pc
from holdworld.agents import HoldForMe, Oracle
from holdworld.episode import run_task
from holdworld.line import DIGIT_S, WAIT, Action, CallEnv
from holdworld.people import make_persona
from holdworld.platforms import PLATFORMS
from holdworld.provenance import P


def env_for(h, tid, mode="M1", platform="plivo_hybrid", wait=30.0, hour=12, scn=None, dial=None, seed=1):
    task = h.task(tid)
    return CallEnv(h, task, make_persona(random.Random(seed)), mode=mode, platform=PLATFORMS[platform], wait_s=wait,
                   hour=hour, rng=random.Random(seed), scn=scn or {}, dial=dial)


def drive(env, actions=None, max_steps=4000):
    actions = actions or {}
    for _ in range(max_steps):
        a = actions.pop(round(env.t, 1), WAIT) if actions else WAIT
        env.step(a)
        if env.done:
            break
    return env


def test_india_ringback_cadence(helplines):
    env = drive(env_for(helplines["psu_bank"], "psu_complaint", scn={"ring_s": 3.0}), max_steps=20)
    rings = [s for s in env.segs if s.label == pc.RING]
    assert round(rings[0].end - rings[0].start, 2) == 1.0       # 0.4 on + 0.2 off + 0.4 on
    assert round(rings[1].end - rings[1].start, 2) == 2.0       # 2.0 off
    assert P("tone.ring.cadence") == [0.4, 0.2, 0.4, 2.0]


def test_dtmf_digit_takes_tone_plus_gap():
    assert abs(DIGIT_S - 0.2) < 1e-9  # 100 ms tone + 100 ms gap (ITU-T Q.24 safe values)


def test_short_code_unreachable_from_other_networks(helplines):
    env = drive(env_for(helplines["telecom"], "tel_network", dial="199"))
    assert env.end_reason == "unreachable"


def test_closed_hours(helplines):
    o = Oracle()
    cr = run_task(helplines["gov_docs"], helplines["gov_docs"].task("gov_officer"), o, mode="M1",
                  platform="plivo_hybrid", hour=22, seed=1, wait_s=30, service_s=60,
                  scn={"busy_disconnect_p": 0.0, "network_busy_p": 0.0})
    assert cr.end_reason == "closed"


def test_busy_disconnect(helplines):
    cr = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_complaint"), Oracle(), mode="M1",
                  platform="plivo_hybrid", hour=12, seed=1, wait_s=30, service_s=60,
                  scn={"busy_disconnect_p": 1.0, "network_busy_p": 0.0})
    assert cr.end_reason == "busy_disconnect"


def test_invalid_key_gets_invalid_prompt(helplines):
    env = env_for(helplines["telecom"], "tel_network", scn={"ring_s": 2.0, "network_busy_p": 0.0})
    for _ in range(40):
        env.step(WAIT)
    env.step(Action("dtmf", digits="7"))
    drive(env, max_steps=40)
    assert any("not a valid option" in s.text for s in env.segs)


def test_barge_in_accepts_keys_during_prompt(helplines):
    env = env_for(helplines["telecom"], "tel_network", scn={"ring_s": 2.0, "network_busy_p": 0.0})
    while not (env.segs and "दबाएँ" in env.segs[-1].text):
        env.step(WAIT)
    env.step(Action("dtmf", digits="2"))
    for _ in range(4):
        env.step(WAIT)
    assert any("For" in s.text and "press" in s.text for s in env.segs[-3:])  # English main menu began


def test_non_barge_ivr_ignores_keys_during_disclaimer(helplines):
    env = env_for(helplines["gov_docs"], "gov_officer", scn={"ring_s": 2.0, "network_busy_p": 0.0})
    while not (env.segs and "रिकॉर्ड" in env.segs[-1].text):
        env.step(WAIT)
    env.step(Action("dtmf", digits="2"))
    for _ in range(10):
        env.step(WAIT)
    assert env.visited == []  # still in the disclaimer / language menu


def test_wrong_entry_is_rejected(helplines):
    h = helplines["electricity"]
    cr = run_task(h, h.task("elec_outage"), HoldForMe(features=[f for f in __import__("holdworld.agents").agents.ALL_FEATURES
                                                                if f != "id_retry"]),
                  mode="M1", platform="plivo_hybrid", hour=12, seed=2, wait_s=30, service_s=60)
    assert cr.end_reason in ("ivr_completed", "agent_hangup", "ivr_fail_entry", "ivr_fail", "busy_disconnect")


def test_registered_only_service_refuses_cloud_number(helplines):
    o = Oracle()
    cr, env = run_task(helplines["tpin_bank"], helplines["tpin_bank"].task("tpin_balance"), o, mode="M2",
                       platform="plivo_hybrid", hour=12, seed=3, wait_s=30, service_s=60, keep_env=True,
                       scn={"m2_dtmf_relay_p": 1.0, "network_busy_p": 0.0})
    env2 = env_for(helplines["tpin_bank"], "tpin_balance", mode="M1")
    assert env2.registered is False and env.registered is True


def test_every_frame_has_a_known_truth_label(helplines):
    cr, env = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_complaint"), HoldForMe(), mode="M1",
                       platform="plivo_hybrid", hour=12, seed=4, wait_s=60, service_s=60, keep_env=True)
    labels = {f[1] for f in env.frames}
    known = {pc.RING, pc.BUSY, pc.NETWORK, pc.PROMPT, pc.IVR_WAIT, pc.MUSIC, pc.ANNOUNCE, pc.AGENT_LIKE, pc.SILENCE,
             pc.HUMAN, pc.HUMAN_WAIT, pc.AI_AGENT, pc.DATA, pc.ENDED}
    assert labels <= known and len(env.frames) > 50


def test_executive_hangs_up_on_dead_air(helplines):
    o = Oracle()
    o.act = lambda obs: WAIT if o.env.pickup_t else Oracle.act(o, obs)
    cr = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_complaint"), o, mode="M1",
                  platform="plivo_hybrid", hour=12, seed=5, wait_s=20, service_s=60,
                  scn={"busy_disconnect_p": 0.0, "network_busy_p": 0.0, "drop_per_min": 0.0})
    assert cr.end_reason == "exec_hung_up"


def test_bolna_default_call_cap(helplines):
    cr = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_complaint"), HoldForMe(), mode="M1",
                  platform="bolna_default", hour=12, seed=6, wait_s=300, service_s=60)
    assert cr.t_total <= P("bolna.call_terminate_default_s") + 1
    assert cr.end_reason in ("platform_cap", "platform_silence_hangup", "ivr_fail_language", "ivr_fail")


def test_bolna_cannot_press_keys(helplines):
    cr = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_complaint"), Oracle(), mode="M1",
                  platform="bolna_default", hour=12, seed=7, wait_s=30, service_s=60)
    assert cr.dtmf_unavailable > 0


def test_recorded_prompts_use_lower_error_rate():
    assert pc.wer_for("hi", "good", recorded=True) < pc.wer_for("hi", "good")


def test_mishear_hits_target_error_rate():
    rng = random.Random(9)
    words = ["word%d" % i for i in range(20000)]
    heard = pc.mishear(words, 0.2, "en", rng)
    kept = sum(1 for a, b in zip(words, heard) if a == b)
    assert 0.12 < 1 - len(set(heard) & set(words)) / len(words) < 0.28


def test_same_seed_same_call(helplines):
    a = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_balance"), HoldForMe(), mode="M1",
                 platform="plivo_hybrid", hour=12, seed=8, wait_s=60, service_s=60)
    b = run_task(helplines["psu_bank"], helplines["psu_bank"].task("psu_balance"), HoldForMe(), mode="M1",
                 platform="plivo_hybrid", hour=12, seed=8, wait_s=60, service_s=60)
    assert a == b
