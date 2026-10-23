"""The queue engine: textbook checks plus the India calibrations."""
import random
import statistics

from holdworld import callqueue as cq


def _mm_n(lam, mu, n, count, seed, patience=cq.INF):
    rng = random.Random(seed)
    t, cs = 0.0, []
    for i in range(count):
        t += rng.expovariate(lam)
        cs.append(cq.QCaller(i, t, rng.expovariate(mu), patience, "human", t))
    cq.run(cs, lambda _t: n, [])
    return cs


def test_engine_matches_erlang_c():
    lam, mu, n = 0.05, 1 / 200, 12
    analytic = cq.erlang_c(lam, mu, n)[1]
    sim = statistics.fmean(statistics.fmean(c.wait for c in _mm_n(lam, mu, n, 20000, s)[2000:]) for s in range(4))
    assert abs(sim - analytic) / analytic < 0.12


def test_erlang_a_matches_erlang_c_without_abandonment():
    lam, mu, n = 2.0, 1.0, 3
    assert cq.erlang_a_mean_wait(lam, mu, n, 0.0) == cq.erlang_c(lam, mu, n)[1]


def test_more_impatient_queue_reduces_erlang_a_wait():
    slow = cq.erlang_a_mean_wait(4.0, 1.0, 4, 1 / 600)
    impatient = cq.erlang_a_mean_wait(4.0, 1.0, 4, 1 / 60)
    assert impatient < slow


def test_every_caller_is_served_or_abandons():
    cs = _mm_n(0.06, 1 / 200, 10, 3000, 1, patience=120.0)
    assert all(c.served or c.abandoned_at is not None for c in cs)


def test_infinite_patience_means_no_abandonment():
    cs = _mm_n(0.05, 1 / 200, 12, 3000, 2)
    assert not any(c.abandoned_at is not None for c in cs)


def test_first_come_first_served():
    cs = _mm_n(0.055, 1 / 200, 11, 3000, 3)
    starts = [c.start for c in sorted(cs, key=lambda c: c.arrival)]
    assert all(a <= b + 1e-9 for a, b in zip(starts, starts[1:]))


def test_priority_head_start_jumps_the_queue():
    cs = [cq.QCaller(0, 0.0, 100.0, cq.INF, "human", 0.0),
          cq.QCaller(1, 1.0, 50.0, cq.INF, "human", 1.0),
          cq.QCaller(2, 2.0, 50.0, cq.INF, "human", 2.0 - 90)]  # priority: 90 s head start
    cq.run(cs, lambda _t: 1, [])
    assert cs[2].start < cs[1].start


def test_staffing_changes_take_effect():
    cs = [cq.QCaller(i, float(i), 1000.0, cq.INF, "human", float(i)) for i in range(4)]
    cq.run(cs, lambda t: 1 if t < 10 else 4, [10.0])
    assert sum(1 for c in cs if c.start is not None and c.start <= 10.0) == 4


def test_telecom_meets_trai_benchmark(model):
    make = lambda b: cq.build_profile("telecom", model, 10.0, b, (0, 24))
    beta = cq.calibrate_beta(make, 0.97, 90, iters=8)
    assert cq.answered_within(make(beta), 90) >= 0.95  # TRAI: 95% within 90 s


def test_wait_table_has_open_hours(model):
    prof = cq.build_profile("x", model, 6.0, -0.3, (8, 20))
    wt = cq.wait_table(prof, days=3)
    hours = [r["hour"] for r in wt.stats()]
    assert hours and all(8 <= h < 21 for h in hours)
    assert all(r["median"] >= 0 for r in wt.stats())


def test_more_ai_holders_means_longer_human_waits(model):
    prof = cq.build_profile("x", model, 8.0, -0.35, (0, 24))
    rows = cq.city(prof, [0.0, 0.5], seeds=2)
    assert rows[1]["hum_wait"] > rows[0]["hum_wait"]


def test_overloaded_line_without_abandonment_grows(model):
    prof = cq.build_profile("x", model, 8.0, -0.8, (8, 20))
    a = cq.city(prof, [0.0], seeds=1)[0]
    b = cq.city(prof, [1.0], seeds=1, ai_patience=cq.INF)[0]
    assert (b["ai_wait"] or 0) > a["hum_wait"]
