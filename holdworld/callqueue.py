"""The Queue layer: a call centre, simulated call by call.

Three ways to use it:
  replay()      a real day from the 1999 data, re-simulated with its real
                arrivals, real service times, real hang-ups and real staffing,
                so a HoldForMe call can be inserted and wait exactly as long
                as that day's queue would have made it wait
  simulate_day() a fitted day: arrival profile, service times and the measured
                patience curve all come from the real year; India archetypes
                change only the volume and the staffing level
  city()        the same engine with a share of callers who never hang up

The engine is an Erlang-A (M/G/N+G) discrete-event simulation: callers queue
first-come-first-served (priority callers get the dataset's 90 s head start),
hang up when their patience runs out, and are served by N(t) agents.
"""
from __future__ import annotations

import heapq
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable

INF = float("inf")


@dataclass(slots=True)
class QCaller:
    cid: int
    arrival: float
    service: float
    patience: float
    kind: str = "human"            # human | ai | probe
    key: float = 0.0               # queue order (arrival minus any head start)
    start: float | None = None
    abandoned_at: float | None = None
    desk: int | None = None
    real_wait: float | None = None  # what the record says, in replay mode
    real_outcome: str | None = None
    pool: str = ""

    @property
    def wait(self) -> float | None:
        if self.start is not None:
            return self.start - self.arrival
        if self.abandoned_at is not None:
            return self.abandoned_at - self.arrival
        return None

    @property
    def served(self) -> bool:
        return self.start is not None


def run(callers: list[QCaller], staffing: Callable[[float], int], change_times: list[float]) -> list[QCaller]:
    """Discrete-event simulation. Mutates and returns the callers."""
    ev: list = []
    seq = 0
    for c in callers:
        ev.append((c.arrival, 2, seq, "arr", c)); seq += 1
    for t in change_times:
        ev.append((t, 0, seq, "staff", None)); seq += 1
    heapq.heapify(ev)
    busy: dict[int, QCaller] = {}
    queue: list = []
    n_agents = staffing(callers[0].arrival if callers else 0.0)

    def start_waiting(now: float) -> None:
        nonlocal seq
        while queue:
            free = [d for d in range(n_agents) if d not in busy]
            if not free:
                return
            _, _, c = heapq.heappop(queue)
            if c.abandoned_at is not None:
                continue
            d = free[0]
            c.start, c.desk = now, d
            busy[d] = c
            heapq.heappush(ev, (now + c.service, 1, seq, "dep", d)); seq += 1

    while ev:
        t, _, _, kind, x = heapq.heappop(ev)
        if kind == "arr":
            heapq.heappush(queue, (x.key, x.cid, x))
            if x.patience < INF:
                heapq.heappush(ev, (t + x.patience, 3, seq, "ab", x)); seq += 1
            start_waiting(t)
        elif kind == "dep":
            busy.pop(x, None)
            start_waiting(t)
        elif kind == "ab":
            if x.start is None and x.abandoned_at is None:
                x.abandoned_at = t
        else:
            n_agents = staffing(t)
            start_waiting(t)
    return callers


def erlang_c(lam: float, mu: float, n: int) -> tuple[float, float]:
    """M/M/N: (probability of waiting, mean wait). Used to check the engine."""
    a = lam / mu
    if a >= n:
        return 1.0, INF
    s = sum(a ** k / math.factorial(k) for k in range(n))
    top = a ** n / math.factorial(n) * n / (n - a)
    pw = top / (s + top)
    return pw, pw / (n * mu - lam)


# --------------------------------------------------------------------------------------
# Replay a real day
# --------------------------------------------------------------------------------------
def replay(day_calls, model, rng: random.Random, probes: list[float] = (), step: int = 900,
           wrapup: float = 0.0):
    """Re-simulate a real day, pool by pool. Returns (callers, {pool: staffing}).

    `wrapup` is after-call work: seconds an agent stays unavailable after each
    call. The data records talk time only, so it is fitted on one half of the
    year and checked on the other (see fit_wrapup).
    """
    from .anonbank import pools, staffing_by_interval
    out, staffing = [], {}
    for pi, (pname, pcalls) in enumerate(pools(day_calls).items()):
        staff = staffing_by_interval(pcalls, step)
        staffing[pname] = staff
        callers = []
        for i, c in enumerate(pcalls):
            if c.outcome == "AGENT":
                service = float(max(c.ser_time, 1)) + wrapup
                patience = model.sample_patience(rng, beyond=float(c.q_time if c.queued else 0))
            else:
                service = model.sample_service(rng) + wrapup
                patience = float(c.q_time)
            key = c.arrival - (90 if c.priority == 2 else 0)
            callers.append(QCaller(pi * 100000 + i, float(c.arrival), service, patience, "human", key,
                                   real_wait=float(c.q_time if c.queued else 0), real_outcome=c.outcome,
                                   pool=pname))
        if pi == 0:
            for j, t in enumerate(probes):
                callers.append(QCaller(900000 + j, t, model.sample_service(rng) + wrapup, INF, "probe", t))
        callers.sort(key=lambda q: q.arrival)
        run(callers, lambda t, s=staff: s.get(int(t // step) * step, 0) or 1, [float(x) for x in sorted(staff)])
        out.extend(callers)
    out.sort(key=lambda q: q.arrival)
    return out, staffing


def replay_validation(day_calls, model, seeds: int = 5, wrapup: float = 0.0) -> dict:
    """How well re-simulation reproduces what really happened that day."""
    real_ab = sum(c.abandoned for c in day_calls) / len(day_calls)
    real_w = statistics.fmean(c.q_time if c.queued else 0 for c in day_calls if c.outcome == "AGENT")
    sims_ab, sims_w, hourly = [], [], {}
    for s in range(seeds):
        cs, _ = replay(day_calls, model, random.Random(s), wrapup=wrapup)
        hum = [c for c in cs if c.kind == "human"]
        sims_ab.append(sum(c.abandoned_at is not None for c in hum) / len(hum))
        sims_w.append(statistics.fmean(c.wait for c in hum if c.served))
        for c in hum:
            h = int(c.arrival // 3600)
            hourly.setdefault(h, [[], []])
            hourly[h][0].append(c.real_wait if c.real_outcome == "AGENT" else None)
            hourly[h][1].append(c.wait if c.served else None)
    rows = []
    for h in sorted(hourly):
        r = [x for x in hourly[h][0] if x is not None]
        m = [x for x in hourly[h][1] if x is not None]
        if r and m:
            rows.append({"hour": h, "real_mean_wait": statistics.fmean(r), "sim_mean_wait": statistics.fmean(m)})
    return {"real_abandon": real_ab, "sim_abandon": statistics.fmean(sims_ab),
            "real_mean_wait": real_w, "sim_mean_wait": statistics.fmean(sims_w), "hourly": rows,
            "calls": len(day_calls)}


def fit_wrapup(days: dict[str, list], model, lo: float = 0.0, hi: float = 150.0, iters: int = 8,
               seeds: int = 2) -> float:
    """After-call work that makes re-simulated mean wait match the real mean wait."""
    real = statistics.fmean(c.q_time if c.queued else 0
                            for dc in days.values() for c in dc if c.outcome == "AGENT")
    for _ in range(iters):
        mid = (lo + hi) / 2
        sims = []
        for dc in days.values():
            for s in range(seeds):
                cs, _ = replay(dc, model, random.Random(s), wrapup=mid)
                sims.extend(c.wait for c in cs if c.kind == "human" and c.served)
        if statistics.fmean(sims) < real:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def holdout_check(days: dict[str, list], model, wrapup: float, seeds: int = 2) -> dict:
    """Real vs re-simulated, on days the fit never saw."""
    rows = []
    for d, dc in days.items():
        v = replay_validation(dc, model, seeds=seeds, wrapup=wrapup)
        rows.append({"date": d, **{k: v[k] for k in ("calls", "real_mean_wait", "sim_mean_wait",
                                                      "real_abandon", "sim_abandon")}})
    rw = [r["real_mean_wait"] for r in rows]
    sw = [r["sim_mean_wait"] for r in rows]
    ra = [r["real_abandon"] for r in rows]
    sa = [r["sim_abandon"] for r in rows]

    def corr(a, b):
        if len(a) < 3:
            return None
        ma, mb = statistics.fmean(a), statistics.fmean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return num / den if den else None

    return {"days": rows, "mean_real_wait": statistics.fmean(rw), "mean_sim_wait": statistics.fmean(sw),
            "mean_real_abandon": statistics.fmean(ra), "mean_sim_abandon": statistics.fmean(sa),
            "corr_wait": corr(rw, sw), "corr_abandon": corr(ra, sa),
            "mae_wait": statistics.fmean(abs(a - b) for a, b in zip(rw, sw))}


# --------------------------------------------------------------------------------------
# Fitted days, India archetypes
# --------------------------------------------------------------------------------------
@dataclass
class Profile:
    """A helpline's queue: real shapes, with volume and staffing as the knobs."""
    name: str
    arrivals: list[float]       # callers per hour wanting an agent, by hour of day
    agents: list[int]           # agents on duty by hour
    model: object               # anonbank.Model (service + patience samplers)
    tag: str = "ASSUMED"
    note: str = ""
    service_scale: float = 1.0

    def offered_load(self, h: int) -> float:
        mean_s = statistics.fmean(self.model.service_pool[:20000]) * self.service_scale
        return self.arrivals[h] * mean_s / 3600


def nhpp_arrivals(rates: list[float], rng: random.Random, t0: float = 0, t1: float = 86400) -> list[float]:
    lam_max = max(rates) / 3600
    if lam_max <= 0:
        return []
    t, out = t0, []
    while True:
        t += rng.expovariate(lam_max)
        if t >= t1:
            return out
        if rng.random() < rates[int(t // 3600) % 24] / 3600 / lam_max:
            out.append(t)


def simulate_day(profile: Profile, rng: random.Random, alpha: float = 0.0, ai_patience: float = INF,
                 ai_service_factor: float = 1.0, probe_every: float = 0.0) -> list[QCaller]:
    times = nhpp_arrivals(profile.arrivals, rng)
    callers = []
    for i, t in enumerate(times):
        ai = rng.random() < alpha
        svc = profile.model.sample_service(rng) * profile.service_scale * (ai_service_factor if ai else 1.0)
        pat = ai_patience if ai else profile.model.sample_patience(rng)
        callers.append(QCaller(i, t, svc, pat, "ai" if ai else "human", t))
    if probe_every:
        hours = [h for h in range(24) if profile.agents[h] > 0]
        k = 0
        for h in hours:
            t = h * 3600 + rng.random() * probe_every
            while t < (h + 1) * 3600:
                callers.append(QCaller(10 ** 6 + k, t, profile.model.sample_service(rng), INF, "probe", t))
                k += 1
                t += probe_every
    callers.sort(key=lambda c: c.arrival)
    agents = profile.agents
    run(callers, lambda t: agents[int(t // 3600) % 24], [h * 3600.0 for h in range(24)])
    return callers


def sqrt_staffing(arrivals: list[float], mean_service_s: float, beta: float, open_hours: tuple[int, int]) -> list[int]:
    out = []
    for h, lam in enumerate(arrivals):
        if not (open_hours[0] <= h < open_hours[1]) or lam <= 0:
            out.append(0)
            continue
        r = lam * mean_service_s / 3600
        out.append(max(1, round(r + beta * math.sqrt(r))))
    return out


def build_profile(name: str, model, volume_scale: float, beta: float, open_hours=(8, 20),
                  service_scale: float = 1.0, tag: str = "ASSUMED", note: str = "") -> Profile:
    """Real hourly shape x volume, staffed by the square-root rule with quality knob beta."""
    arrivals = [a * volume_scale if open_hours[0] <= h < open_hours[1] else 0.0
                for h, a in enumerate(model.hourly_arrivals)]
    mean_s = statistics.fmean(model.service_pool[:20000]) * service_scale
    agents = sqrt_staffing(arrivals, mean_s, beta, open_hours)
    return Profile(name, arrivals, agents, model, tag, note, service_scale)


@dataclass
class WaitTable:
    """Probe waits by hour of day: the 'wait time by hour' that Google shows."""
    by_hour: dict[int, list[float]] = field(default_factory=dict)

    def sample(self, hour: int, rng: random.Random) -> float | None:
        pool = self.by_hour.get(hour)
        if not pool:
            return None
        return rng.choice(pool)

    def stats(self) -> list[dict]:
        rows = []
        for h in sorted(self.by_hour):
            xs = sorted(self.by_hour[h])
            if len(xs) < 5:
                continue
            rows.append({"hour": h, "n": len(xs), "p25": xs[len(xs) // 4], "median": xs[len(xs) // 2],
                         "p75": xs[3 * len(xs) // 4], "p90": xs[int(.9 * len(xs))]})
        return rows


def wait_table(profile: Profile, days: int = 12, seed: int = 0, probe_every: float = 600) -> WaitTable:
    wt = WaitTable()
    for d in range(days):
        cs = simulate_day(profile, random.Random(seed * 1000 + d), probe_every=probe_every)
        for c in cs:
            if c.kind == "probe" and c.served:
                wt.by_hour.setdefault(int(c.arrival // 3600), []).append(c.wait)
    return wt


def answered_within(profile: Profile, limit_s: float, days: int = 6, seed: int = 0) -> float:
    ok = tot = 0
    for d in range(days):
        cs = simulate_day(profile, random.Random(seed + d))
        for c in cs:
            if c.kind == "human":
                tot += 1
                ok += c.served and c.wait <= limit_s
    return ok / max(tot, 1)


def calibrate_beta(make: Callable[[float], Profile], target: float, limit_s: float = 90,
                   lo: float = -1.0, hi: float = 3.0, iters: int = 10) -> float:
    """Smallest staffing quality that answers `target` of callers within `limit_s`."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        if answered_within(make(mid), limit_s) >= target:
            hi = mid
        else:
            lo = mid
    return hi


# --------------------------------------------------------------------------------------
# City: what happens when some callers never hang up
# --------------------------------------------------------------------------------------
def city(profile: Profile, alphas, seeds: int = 4, ai_patience: float = INF, ai_service_factor: float = 1.0):
    rows = []
    for a in alphas:
        acc = {"hum_wait": [], "hum_ab": [], "ai_wait": [], "served": [], "util": []}
        for s in range(seeds):
            cs = simulate_day(profile, random.Random(7000 + s), alpha=a, ai_patience=ai_patience,
                              ai_service_factor=ai_service_factor)
            hum = [c for c in cs if c.kind == "human"]
            ai = [c for c in cs if c.kind == "ai"]
            if hum:
                acc["hum_wait"].append(statistics.fmean(c.wait for c in hum if c.wait is not None))
                acc["hum_ab"].append(sum(c.abandoned_at is not None for c in hum) / len(hum))
            if ai:
                acc["ai_wait"].append(statistics.fmean(c.wait for c in ai if c.wait is not None))
            acc["served"].append(sum(c.served for c in cs))
            busy = sum(c.service for c in cs if c.served)
            cap = sum(profile.agents) * 3600
            acc["util"].append(busy / cap if cap else 0)
        rows.append({"alpha": a, **{k: (statistics.fmean(v) if v else None) for k, v in acc.items()}})
    return rows
