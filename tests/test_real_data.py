"""Tests against the real 1999 call-centre data (440,837 calls)."""
import collections
import random
import statistics

from holdworld import anonbank as ab
from holdworld import callqueue as cq


def test_record_count_is_exact(calls):
    assert len(calls) == 440_837  # every non-phantom record in the 12 monthly files


def test_all_twelve_months_present(summary):
    assert all(20_000 <= n <= 45_000 for n in summary["per_month"].values())
    assert len(summary["per_month"]) == 12


def test_working_days(summary):
    assert summary["working_days"] >= 250


def test_abandonment_rate_in_published_range(summary):
    # Brown et al. 2005 report ~20% of agent-seeking callers abandoned
    assert 0.10 <= summary["abandon_frac"] <= 0.25


def test_mean_wait_of_served_callers(summary):
    assert 20 <= summary["mean_wait_served_s"] <= 120


def test_service_times_are_right_skewed_lognormal(summary):
    s = summary["service"]
    assert s["median_s"] < s["mean_s"]
    assert 0.7 <= s["log_sigma"] <= 1.2


def test_ivr_time_is_seconds_not_minutes(summary):
    assert 3 <= summary["vru_time_s"]["p50"] <= 20


def test_hangup_spike_after_first_message(summary):
    assert any(4 <= t <= 16 for t in summary["patience"]["spikes_s"])


def test_hangup_spike_when_message_replays_near_60s(summary):
    # the announcement effect Brown et al. describe, found directly in the records
    assert any(50 <= t <= 66 for t in summary["patience"]["spikes_s"])


def test_patience_survival_is_monotone(calls):
    p = ab.fit_patience(calls)
    assert all(a >= b - 1e-12 for a, b in zip(p.surv, p.surv[1:]))


def test_patience_index_above_one(summary):
    assert summary["patience"]["mean_s"] > summary["mean_wait_served_s"]


def test_arrival_peak_in_working_hours(summary):
    peak = max(summary["hourly"], key=lambda h: h["arrivals_per_day"])["hour"]
    assert 9 <= peak <= 16


def test_staffing_estimate_is_plausible(calls):
    day = ab.day(calls, ab.busiest_workdays(calls)[0])
    st = ab.staffing_by_interval(day, 900)
    assert 5 <= max(st.values()) <= 25  # 8 regular + 5 internet positions + supervisor


def test_priority_customers_wait_less(calls):
    w = collections.defaultdict(list)
    for c in calls:
        if c.queued and c.outcome == "AGENT":
            w[c.priority].append(c.q_time)
    assert statistics.fmean(w[2]) < statistics.fmean(w[1])  # the 90 s head start shows in the data


def test_wrapup_is_fitted_in_a_sane_range(calls, model):
    days = ab.busiest_workdays(calls, 3, 4)
    W = cq.fit_wrapup({d: ab.day(calls, d) for d in days}, model, iters=6, seeds=1)
    assert 10 <= W <= 120


def test_replay_matches_held_out_days(calls, model):
    train = ab.busiest_workdays(calls, 4, 5)
    W = cq.fit_wrapup({d: ab.day(calls, d) for d in train}, model, iters=6, seeds=1)
    test = ab.busiest_workdays(calls, 10, 6)
    h = cq.holdout_check({d: ab.day(calls, d) for d in test}, model, W, seeds=1)
    assert h["corr_wait"] > 0.9
    assert abs(h["mean_real_abandon"] - h["mean_sim_abandon"]) < 0.04


def test_patience_sampler_respects_conditioning(model):
    rng = random.Random(0)
    assert all(model.sample_patience(rng, beyond=120.0) >= 120.0 for _ in range(500))
