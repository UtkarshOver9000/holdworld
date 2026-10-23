"""The real call-centre year: load, describe, fit and replay.

Source: "Anonymous Bank" call-centre data (Technion SEE Lab), every call of
1999 at a bank call centre in Israel. Terms: free for use; notify Avi
Mandelbaum and acknowledge the source. The raw files are not redistributed:
run `python -m holdworld fetch-data` to download them.

What this module turns the data into:
  * per-call records (IVR time, wait, outcome, service time, agent)
  * the measured patience curve (Kaplan-Meier, with hang-up spikes)
  * hourly arrival and staffing profiles
  * a sampler for service and patience, used by the queue engine
  * a single real day, ready for replay
"""
from __future__ import annotations

import bisect
import datetime as dt
import math
import pickle
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "anonbank" / "raw"
CACHE = ROOT / "data" / "anonbank" / "cache.pkl"
URL = "https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/AnonymousBank.rar"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WORKDAYS = {6, 0, 1, 2, 3}  # Sunday..Thursday in Israel (Python: Mon=0 .. Sun=6)


@dataclass(slots=True)
class Call:
    date: str          # yymmdd
    weekday: int       # Python weekday
    vru_entry: int     # seconds since midnight
    vru_time: int
    q_start: int | None
    q_time: int
    outcome: str       # AGENT | HANG | PHANTOM
    ser_start: int | None
    ser_time: int
    type: str
    priority: int
    server: str

    @property
    def arrival(self) -> int:
        """Time the caller left the IVR towards an agent."""
        return self.vru_entry + self.vru_time

    @property
    def wanted_agent(self) -> bool:
        return self.q_start is not None or self.outcome == "AGENT"

    @property
    def queued(self) -> bool:
        return self.q_start is not None and self.q_time > 0

    @property
    def abandoned(self) -> bool:
        return self.queued and self.outcome == "HANG"


def _secs(hms: str) -> int:
    h, m, s = hms.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def parse_file(path: Path) -> list[Call]:
    calls: list[Call] = []
    with open(path, encoding="latin-1") as fh:
        header = fh.readline()
        if not header.startswith("vru"):
            fh.seek(0)
        for line in fh:
            f = line.rstrip("\r\n").split("\t")
            if len(f) < 17 or len(f[5]) != 6:
                continue
            outcome = f[12].strip()
            if outcome == "PHANTOM":
                continue
            try:
                d = dt.date(1900 + int(f[5][:2]), int(f[5][2:4]), int(f[5][4:6]))
                q_start = _secs(f[9])
                ser_start = _secs(f[13])
                calls.append(Call(
                    date=f[5], weekday=d.weekday(),
                    vru_entry=_secs(f[6]), vru_time=int(f[8] or 0),
                    q_start=None if q_start == 0 else q_start, q_time=int(f[11] or 0),
                    outcome=outcome,
                    ser_start=None if ser_start == 0 else ser_start, ser_time=int(f[15] or 0),
                    type=f[4].strip(), priority=int(f[3] or 0), server=f[16].strip(),
                ))
            except (ValueError, IndexError):
                continue
    return calls


def available() -> bool:
    return any((RAW_DIR / f"{m}1999.txt").exists() for m in MONTHS)


def load(use_cache: bool = True) -> list[Call]:
    if use_cache and CACHE.exists():
        with open(CACHE, "rb") as fh:
            return pickle.load(fh)
    calls: list[Call] = []
    for m in MONTHS:
        p = RAW_DIR / f"{m}1999.txt"
        if p.exists():
            calls.extend(parse_file(p))
    if not calls:
        raise FileNotFoundError(f"No data in {RAW_DIR}. Run: python -m holdworld fetch-data")
    with open(CACHE, "wb") as fh:
        pickle.dump(calls, fh)
    return calls


# --------------------------------------------------------------------------------------
# Patience: Kaplan-Meier over everyone who waited (hang-up = event, service = censored)
# --------------------------------------------------------------------------------------
@dataclass
class Patience:
    times: list[float]      # KM step times
    surv: list[float]       # S(t) just after each time
    tail_rate: float        # exponential tail beyond the last time
    hazard_bins: list[tuple[float, float, int]]  # (bin start, hazard per s, at risk)
    spikes: list[float]     # bin starts where hazard is far above its neighbours
    mean_s: float           # restricted mean + tail

    def __post_init__(self) -> None:
        self._neg = [-s for s in self.surv]

    def sample(self, rng: random.Random, beyond: float = 0.0) -> float:
        """Patience draw; `beyond` conditions on having already waited that long."""
        s0 = self.survival(beyond)
        if s0 <= 0:
            return beyond + rng.expovariate(self.tail_rate)
        u = rng.random() * s0  # target survival level
        i = bisect.bisect_left(self._neg, -u)
        if i >= len(self.times):
            return self.times[-1] + rng.expovariate(self.tail_rate)
        return max(beyond, self.times[i])

    def survival(self, t: float) -> float:
        i = bisect.bisect_right(self.times, t) - 1
        if i < 0:
            return 1.0
        if i >= len(self.times) - 1 and t > self.times[-1]:
            return self.surv[-1] * math.exp(-self.tail_rate * (t - self.times[-1]))
        return self.surv[i]


def fit_patience(calls: list[Call], bin_s: int = 2, horizon: int = 900) -> Patience:
    waited = [(c.q_time, c.abandoned) for c in calls if c.queued]
    waited.sort()
    n = len(waited)
    times, surv = [], []
    s, i = 1.0, 0
    while i < n:
        t = waited[i][0]
        deaths = cens = 0
        while i < n and waited[i][0] == t:
            deaths += waited[i][1]
            cens += not waited[i][1]
            i += 1
        at_risk = n - (i - deaths - cens)
        if deaths:
            s *= 1 - deaths / at_risk
            times.append(float(t))
            surv.append(s)
    # hazard histogram
    all_t = [t for t, _ in waited]
    ev_t = sorted(t for t, e in waited if e)
    bins = []
    for b0 in range(0, horizon, bin_s):
        at_risk = n - bisect.bisect_left(all_t, b0)
        d = bisect.bisect_left(ev_t, b0 + bin_s) - bisect.bisect_left(ev_t, b0)
        if at_risk < 50:
            break
        bins.append((float(b0), d / at_risk / bin_s, at_risk))
    # tail: average hazard over the last 300 s of usable bins
    tail = [h for b, h, _ in bins if b >= max(0, bins[-1][0] - 300)] if bins else []
    tail_rate = max(statistics.fmean(tail) if tail else 1 / 446, 1e-4)
    # a spike is a local maximum (+-3 bins) well above the median of its +-15-bin window
    spikes = []
    hs = [h for _, h, _ in bins]
    for k in range(3, min(len(bins) - 3, 100)):
        if hs[k] < max(hs[k - 3:k + 4]):
            continue
        neigh = sorted(hs[max(0, k - 15):k + 16])
        if hs[k] > 1.4 * neigh[len(neigh) // 2]:
            spikes.append(bins[k][0])
    # restricted mean of S(t) plus exponential tail
    mean, prev_t, prev_s = 0.0, 0.0, 1.0
    for t, sv in zip(times, surv):
        mean += prev_s * (t - prev_t)
        prev_t, prev_s = t, sv
    mean += prev_s / tail_rate
    return Patience(times, surv, tail_rate, bins, spikes, mean)


# --------------------------------------------------------------------------------------
# Profiles: arrivals, staffing, service, IVR time
# --------------------------------------------------------------------------------------
def staffing_by_interval(day_calls: list[Call], step: int = 900, mode: str = "concurrent") -> dict[int, int]:
    """Agents on duty per interval, estimated from who was actually talking.

    concurrent: the most calls in service at the same moment within the interval.
                When a queue exists every available agent is busy, so this is the
                capacity the callers actually saw (breaks and wrap-up excluded).
    distinct:   distinct agent names seen in the interval (over-counts: shift
                changes and agents who take one call then leave).
    """
    served = [c for c in day_calls
              if c.outcome == "AGENT" and c.ser_start is not None and c.server != "NO_SERVER"]
    if mode == "distinct":
        busy: dict[int, set] = defaultdict(set)
        for c in served:
            end = c.ser_start + max(c.ser_time, 1)
            for k in range(c.ser_start // step, end // step + 1):
                busy[k * step].add(c.server)
        return {k: len(v) for k, v in busy.items()}
    events = []
    for c in served:
        events.append((c.ser_start, 1))
        events.append((c.ser_start + max(c.ser_time, 1), -1))
    events.sort(key=lambda e: (e[0], e[1]))
    peak: dict[int, int] = defaultdict(int)
    level = 0
    for t, d in events:
        level += d
        k = (t // step) * step
        peak[k] = max(peak[k], level)
    return dict(peak)


def pools(day_calls: list[Call]) -> dict[str, list[Call]]:
    """From August 1999 internet (IN) callers had their own agents (Brown et al. 2005)."""
    if day_calls and int(day_calls[0].date[2:4]) >= 8:
        return {"regular": [c for c in day_calls if c.type != "IN"],
                "internet": [c for c in day_calls if c.type == "IN"]}
    return {"all": list(day_calls)}


def lognormal_fit(xs: list[float]) -> tuple[float, float]:
    logs = [math.log(x) for x in xs if x > 0]
    return statistics.fmean(logs), statistics.pstdev(logs)


def summarize(calls: list[Call]) -> dict:
    by_date: dict[str, list[Call]] = defaultdict(list)
    for c in calls:
        by_date[c.date].append(c)
    work_dates = sorted(d for d, cs in by_date.items() if cs[0].weekday in WORKDAYS)
    agent_calls = [c for c in calls if c.wanted_agent]
    queued = [c for c in calls if c.queued]
    served = [c for c in agent_calls if c.outcome == "AGENT"]
    abandoned = [c for c in queued if c.outcome == "HANG"]
    vru_only = [c for c in calls if not c.wanted_agent]

    # hourly profile over working days
    arr = defaultdict(int)
    staff = defaultdict(list)
    waits_h = defaultdict(list)
    aband_h = defaultdict(lambda: [0, 0])
    for d in work_dates:
        cs = by_date[d]
        for c in cs:
            if c.wanted_agent:
                h = min(c.arrival // 3600, 23)
                arr[h] += 1
                aband_h[h][1] += 1
                aband_h[h][0] += c.abandoned
                if c.outcome == "AGENT":
                    waits_h[h].append(c.q_time if c.queued else 0)
        st = staffing_by_interval(cs, 3600)
        for h in range(24):
            staff[h].append(st.get(h * 3600, 0))
    nd = max(len(work_dates), 1)
    hourly = []
    for h in range(24):
        w = waits_h[h]
        hourly.append({
            "hour": h,
            "arrivals_per_day": arr[h] / nd,
            "agents_avg": statistics.fmean(staff[h]) if staff[h] else 0.0,
            "mean_wait_s": statistics.fmean(w) if w else 0.0,
            "abandon_frac": aband_h[h][0] / aband_h[h][1] if aband_h[h][1] else 0.0,
        })

    ser = [c.ser_time for c in served if c.ser_time >= 10]
    mu, sigma = lognormal_fit(ser)
    by_type = {}
    for t in sorted({c.type for c in served}):
        xs = [c.ser_time for c in served if c.type == t and c.ser_time >= 10]
        if len(xs) > 200:
            m, s = lognormal_fit(xs)
            by_type[t] = {"n": len(xs), "mean_s": statistics.fmean(xs), "log_mu": m, "log_sigma": s}
    pat = fit_patience(calls)
    waits_served = [c.q_time if c.queued else 0 for c in served]
    vt = sorted(c.vru_time for c in agent_calls)

    def q(xs, p):
        return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else 0

    return {
        "records": len(calls),
        "days": len(by_date),
        "working_days": len(work_dates),
        "per_month": {m: sum(1 for c in calls if int(c.date[2:4]) == i + 1) for i, m in enumerate(MONTHS)},
        "vru_only": len(vru_only),
        "wanted_agent": len(agent_calls),
        "served": len(served),
        "served_immediately": sum(1 for c in served if not c.queued),
        "queued": len(queued),
        "abandoned": len(abandoned),
        "abandon_frac": len(abandoned) / len(agent_calls) if agent_calls else 0,
        "mean_wait_served_s": statistics.fmean(waits_served) if waits_served else 0,
        "p_wait_zero": sum(1 for w in waits_served if w == 0) / max(len(waits_served), 1),
        "service": {"n": len(ser), "mean_s": statistics.fmean(ser), "median_s": statistics.median(ser),
                    "log_mu": mu, "log_sigma": sigma, "by_type": by_type},
        "vru_time_s": {"p10": q(vt, .1), "p50": q(vt, .5), "p90": q(vt, .9)},
        "patience": {"mean_s": pat.mean_s, "tail_rate": pat.tail_rate, "spikes_s": pat.spikes,
                     "hazard": [[b, round(h, 6), r] for b, h, r in pat.hazard_bins[:150]],
                     "km": [[t, round(s, 5)] for t, s in zip(pat.times, pat.surv) if t <= 900][::3]},
        "hourly": hourly,
    }


@dataclass
class Model:
    """Everything the queue engine needs, fitted from the real year."""
    hourly_arrivals: list[float]   # per working day, callers who want an agent
    hourly_agents: list[float]
    service_pool: list[int]        # real service times (s), >=10 s
    patience: Patience
    vru_pool: list[int]            # real IVR times (s)

    def sample_service(self, rng: random.Random) -> float:
        return float(rng.choice(self.service_pool))

    def sample_patience(self, rng: random.Random, beyond: float = 0.0) -> float:
        return self.patience.sample(rng, beyond)


def fit_model(calls: list[Call]) -> Model:
    s = summarize(calls)
    served = [c.ser_time for c in calls if c.outcome == "AGENT" and c.ser_time >= 10]
    vru = [c.vru_time for c in calls if c.wanted_agent and c.vru_time > 0]
    return Model(
        hourly_arrivals=[h["arrivals_per_day"] for h in s["hourly"]],
        hourly_agents=[h["agents_avg"] for h in s["hourly"]],
        service_pool=served,
        patience=fit_patience(calls),
        vru_pool=vru,
    )


# --------------------------------------------------------------------------------------
# One real day, for replay
# --------------------------------------------------------------------------------------
def day(calls: list[Call], date: str) -> list[Call]:
    return sorted((c for c in calls if c.date == date and c.wanted_agent), key=lambda c: c.arrival)


def busiest_workdays(calls: list[Call], month: int = 11, k: int = 5) -> list[str]:
    counts = defaultdict(int)
    for c in calls:
        if int(c.date[2:4]) == month and c.weekday in WORKDAYS and c.wanted_agent:
            counts[c.date] += 1
    return [d for d, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:k]]
