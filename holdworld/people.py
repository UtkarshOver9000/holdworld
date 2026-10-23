"""The user (the person HoldForMe works for) and their account details."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .provenance import P

NAMES = ["Aarav Sharma", "Ananya Iyer", "Rohan Gupta", "Meera Nair", "Kabir Singh", "Priya Reddy",
         "Vikram Rao", "Sana Khan", "Aditya Joshi", "Lakshmi Menon", "Harsh Patel", "Nisha Das"]


@dataclass
class Persona:
    name: str
    dob: str            # DDMMYYYY
    acct_last4: str
    acct_last5: str
    card_last4: str
    birth_year: str
    customer_id: str    # stored with a letter prefix: the ID-format quirk
    tpin: str
    mobile: str
    consumer_no: str
    order_id: str       # stored as 'OD' + digits
    file_no: str        # stored as 'DL' + digits
    pnr: str
    ticket: str
    lang_pref: str
    accept_offers: bool = False
    target_discount: int = 10
    truth: dict = field(default_factory=dict)  # values the helpline will speak

    def field_value(self, f: str) -> str:
        return getattr(self, f)

    @staticmethod
    def digits_only(v: str) -> str:
        return "".join(ch for ch in v if ch.isdigit())


def make_persona(rng: random.Random, lang_pref: str | None = None) -> Persona:
    d = lambda n: "".join(str(rng.randrange(10)) for _ in range(n))
    year = rng.randrange(1960, 2004)
    acct = d(11)
    p = Persona(
        name=rng.choice(NAMES), dob=f"{rng.randrange(1, 28):02d}{rng.randrange(1, 13):02d}{year}",
        acct_last4=acct[-4:], acct_last5=acct[-5:], card_last4=d(4), birth_year=str(year),
        customer_id="KV" + d(10), tpin=d(4), mobile="9" + d(9), consumer_no=d(9), order_id="OD" + d(10),
        file_no="DL" + d(8), pnr="6E" + d(4), ticket=d(8),
        lang_pref=lang_pref or rng.choice(["en", "en", "hi"]),
        target_discount=rng.choice([10, 20]),
    )
    p.truth = {
        "balance": f"{rng.randrange(1200, 98000)}", "last_txn": f"{rng.randrange(100, 9000)}",
        "nomination": d(3), "card_dispatch": d(8), "cheque_dispatch": d(8), "fd_rate": f"{rng.choice([6, 7])}",
        "complaint_status": f"{rng.randrange(1, 28)} {rng.choice(['November', 'December'])}",
        "current_plan": f"{rng.choice([299, 349, 399, 719])}", "bill_amount": f"{rng.randrange(200, 2500)}",
        "order_status": f"{rng.randrange(1, 28)} November", "application_status": f"{rng.randrange(2, 6)}",
        "otp": d(6),
    }
    return p


@dataclass
class User:
    """How the person behaves when the agent needs them."""
    rng: random.Random
    mode: str          # M1 cloud dial + ring back | M2 user dials + merges | M3 callback
    primed: bool = False

    def answer_delay(self) -> float | None:
        """Seconds until the user is on the line after HoldForMe asks, or None if missed."""
        if self.mode == "M2":
            return 1.5 + self.rng.random() * 1.5          # already on the call, just unmutes
        if self.rng.random() < P("user.miss_p"):
            return None
        med = P("user.answer_s.median")
        sigma = math.log(P("user.answer_s.p75") / med) / 0.6745
        t = med * math.exp(self.rng.gauss(0, sigma))
        return t * (P("user.primed_factor") if self.primed else 1.0) + 1.0  # +1 s to say "hello"

    def otp_delay(self) -> float:
        return P("otp.delay_s.median") * math.exp(self.rng.gauss(0, 0.6)) + self.rng.uniform(3, 8)

    def keypress_delay(self) -> float:
        return P("user.keypress_react_s") * math.exp(self.rng.gauss(0, 0.4))
