"""Reading prompts: options, fields, cues, and the vocabulary HoldForMe matches goals with."""
from __future__ import annotations

import re

from .line import words_of

# tolerant of a misheard word or two between the label and the key ("for english uh press 2")
EN_OPT = re.compile(r"(?:for|to) ([^.]+?),? press (\d|star|hash)(?: or say [^.]+)?\.?", re.I)
EN_OPT_LOOSE = re.compile(r"(?:for|to) ([^.]+?),? (?:\S+ )?press (\d|star|hash)(?: or say [^.]+)?\.?", re.I)
EN_SAY = re.compile(r"for ([^.]+?),? say '?([^.']+?)'?\.", re.I)
EN_TO = re.compile(r"^\s*([^.]+?),? press (\d|star|hash)\.?$", re.I)
# Language names carry more meaning than the intervening ASR filler. This
# recovers common code-switched prompts such as "For English, press uh 2".
EN_LANGUAGE_OPT = re.compile(r"\b(english|hindi)\b[^.]{0,48}?\bpress\b[^.]{0,16}?(\d)", re.I)
HI_OPT = re.compile(r"([^।.]+?) के लिए (\d|स्टार|हैश) दबाएँ")
HI_OPT_LOOSE = re.compile(r"([^।.]+?) (?:\S+ ){0,2}(\d|स्टार|हैश) दबाएँ")
HI_SAY = re.compile(r"([^।.]+?) के लिए '?([^'।]+?)'? बोलें")
KEYMAP = {"star": "*", "hash": "#", "स्टार": "*", "हैश": "#"}

LEXICON = {
    "complaint": ["complaint", "complaints", "lodging", "lodge", "grievance", "शिकायत", "शिकायतों", "dispute"],
    "upi": ["upi", "यूपीआई", "payment", "transaction"],
    "balance": ["balance", "शेष", "राशि", "enquiry"],
    "account": ["account", "खाते", "खाता"],
    "block": ["block", "blocking", "hotlist", "hotlisting", "lost", "stolen", "ब्लॉक", "हॉटलिस्ट"],
    "card": ["card", "atm", "debit", "कार्ड", "एटीएम", "डेबिट"],
    "loan": ["loan", "loans", "ऋण", "products"],
    "executive": ["executive", "officer", "customer", "care", "अधिकारी", "ग्राहक", "सेवा", "speaking"],
    "charge": ["charge", "wrong", "information", "account", "शुल्क"],
    "network": ["network", "internet", "signal", "problems", "नेटवर्क", "इंटरनेट", "समस्या"],
    "bill": ["bill", "billing", "amount", "बिल", "बिलिंग", "राशि"],
    "cancel": ["cancel", "cancelling", "subscription", "disputing", "रद्द", "सब्सक्रिप्शन", "आपत्ति"],
    "subscription": ["subscription", "सब्सक्रिप्शन", "charge"],
    "port": ["porting", "port", "closing", "पोर्ट", "बंद"],
    "close": ["closing", "close", "बंद"],
    "refund": ["refund", "refunds", "रिफंड", "returns"],
    "return": ["returns", "return", "रिटर्न"],
    "change": ["changing", "change", "बदलने"],
    "flight": ["flight", "booking", "फ्लाइट", "बुकिंग"],
    "baggage": ["baggage", "सामान"],
    "order": ["order", "ऑर्डर"],
    "status": ["status", "स्थिति"],
    "outage": ["power", "cut", "बिजली", "कटौती"],
    "connection": ["connection", "कनेक्शन", "new", "नया"],
    "application": ["application", "आवेदन"],
    "officer": ["officer", "अधिकारी", "speaking"],
    "booking": ["booking", "book", "बुक", "बुकिंग", "refill"],
    "refill": ["refill", "रिफिल"],
    "safety": ["safety", "सुरक्षा", "other", "अन्य"],
}
LEXICON["lodge"] = ["lodge", "lodging", "register", "registering", "raise", "दर्ज", "complaint"]
# A counter-ticket task needs to distinguish the counter route from e-ticket.
LEXICON["counter"] = ["counter", "\u0915\u093e\u0909\u0902\u091f\u0930"]
# where a goal usually lives when no option names it directly (what a person infers)
PARENT = {
    # Balance is specifically an account branch. Generic information also matched deposit/loan options.
    "balance": ["banking", "account", "\u0916\u093e\u0924\u0947", "\u0916\u093e\u0924\u093e", "self", "\u092b\u094b\u0928", "\u092c\u0948\u0902\u0915\u093f\u0902\u0917"],
    "block": ["card", "कार्ड", "debit", "डेबिट"],
    "complaint": ["deposit", "loan", "complaints", "शिकायतों", "other", "अन्य"],
    "upi": ["blocking", "internet", "इंटरनेट"],
    "loan": ["products", "उत्पादों", "new", "नए"],
    "refund": ["returns", "booking", "बुकिंग", "changing"],
    "bill": ["billing", "बिलिंग"],
    "cancel": ["billing", "बिलिंग", "subscription"],
    "port": ["closing", "बंद"],
    "safety": ["other", "अन्य", "services", "सेवाओं"],
    "refill": ["booking", "बुक"],
}
AGENT_WORDS = {"executive", "officer", "अधिकारी", "customer", "care"}
STATUS_WORDS = {"status", "स्थिति", "dispatch", "भेजे"}
# options that do something specific: only right if the goal asks for that action
ACTION_WORDS = {"cancel": {"cancel", "cancelling", "रद्द"}, "block": {"block", "blocking", "ब्लॉक"},
                "booking": {"booking", "book", "बुकिंग", "बुक"}, "change": {"changing", "change", "बदलने"}}
OTHER_WORDS = {"other", "अन्य", "more", "और"}

FIELD_CUES = [
    ("acct_last4", ["last 4 digits of your account", "खाता नंबर के अंतिम 4"]),
    ("acct_last5", ["last 5 digits of your account", "खाता नंबर के अंतिम 5"]),
    ("card_last4", ["last 4 digits of your card", "कार्ड नंबर के अंतिम 4"]),
    ("birth_year", ["year of birth", "जन्म वर्ष"]),
    ("dob", ["date of birth", "जन्म तिथि"]),
    ("customer_id", ["customer id", "ग्राहक आईडी"]),
    ("tpin", ["telephone pin", "टेलीफोन पिन"]),
    ("mobile", ["10 digit mobile", "मोबाइल नंबर दर्ज"]),
    ("otp", ["o t p sent", "ओ टी पी दर्ज"]),
    ("ticket", ["complaint number", "शिकायत नंबर दर्ज"]),
    ("consumer_no", ["consumer number", "उपभोक्ता नंबर"]),
    ("order_id", ["order number", "ऑर्डर नंबर दर्ज"]),
    ("file_no", ["file number", "फ़ाइल संख्या"]),
    ("pnr", ["booking reference using", "बुकिंग संदर्भ दर्ज"]),
]

RECORDED_PHRASES = [  # phrase library: what recordings say and live people rarely do
    "your call is important to us", "please stay on the line", "all our executives are busy",
    "your call is valuable to us", "an executive will be with you shortly", "thank you for your patience",
    "आपकी कॉल हमारे लिए महत्वपूर्ण है", "कृपया लाइन पर बने रहें", "हमारे सभी अधिकारी व्यस्त हैं",
    "जल्द ही एक अधिकारी आपसे बात करेंगे", "estimated waiting time", "in the queue", "अनुमानित प्रतीक्षा समय",
    "कतार में आपका नंबर",
]
QUESTION_CUES = ["how may i help", "how can i help", "can you hear me", "may i know", "क्या मदद", "सहायता कर सकता",
                 "सुन पा रहे", "बताइए", "help you today"]
REPLY_CUES = ["yes", "hello", "hear you", "जी", "हेलो", "सुन पा रहा"]
INVALID_CUES = ["not a valid", "didn't get", "invalid", "मान्य नहीं", "जवाब नहीं मिला", "अमान्य"]
AI_CUES = ["virtual assistant", "वर्चुअल असिस्टेंट"]


def parse_options(text: str) -> list[tuple[str, str, str]]:
    """(key, label, how) where how is 'press' or 'say'."""
    out = []
    for sent in re.split(r"(?<=[.।])\s*", text):
        if not sent.strip():
            continue
        m = EN_OPT.search(sent) or EN_OPT_LOOSE.search(sent)
        if m:
            label = m.group(1).strip().lower()
            also = re.search(r"or say (.+?)\.?$", sent, re.I)   # 'press 1 or say X' states the label twice
            if also:
                label = label + " " + also.group(1).strip().lower()
            out.append((KEYMAP.get(m.group(2).lower(), m.group(2)), label, "press"))
            continue
        m = EN_LANGUAGE_OPT.search(sent)
        if m:
            out.append((m.group(2), m.group(1).lower(), "press"))
            continue
        m = HI_OPT.search(sent) or HI_OPT_LOOSE.search(sent)
        if m:
            label = re.sub(r"\s*(के लिए|और|के|से)$", "", m.group(1).strip())
            also = re.search(r"या (.+?) बोलें", sent)
            if also:
                label = label + " " + also.group(1).strip()
            out.append((KEYMAP.get(m.group(2), m.group(2)), label, "press"))
    if not out:
        for m in EN_SAY.finditer(text):
            out.append(("", m.group(2).strip().lower(), "say"))
        for m in HI_SAY.finditer(text):
            out.append(("", m.group(2).strip(), "say"))
    seen, uniq = set(), []
    for o in out:
        if (o[0], o[1]) not in seen:
            seen.add((o[0], o[1]))
            uniq.append(o)
    return uniq


def contains_any(text: str, cues) -> bool:
    t = text.lower()
    return any(c in t for c in cues)


def field_cue(text: str) -> str | None:
    t = text.lower()
    for f, cues in FIELD_CUES:
        if any(c in t for c in cues):
            return f
    return None


def token_overlap(a: str, b: str) -> float:
    wa, wb = set(words_of(a)), set(words_of(b))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def phrase_match(text: str) -> bool:
    w = set(words_of(text))
    for ph in RECORDED_PHRASES:
        pw = set(words_of(ph))
        if pw and len(w & pw) / len(pw) >= 0.6:
            return True
    return False


def digits_in(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


E161 = {c: d for d, letters in {"2": "abc", "3": "def", "4": "ghi", "5": "jkl", "6": "mno", "7": "pqrs",
                                "8": "tuv", "9": "wxyz"}.items() for c in letters}


def keypad(value: str) -> str:
    """How a naive agent types an ID with letters: ITU E.161 keypad letters."""
    return "".join(E161.get(ch.lower(), ch) for ch in value if ch.isalnum())
