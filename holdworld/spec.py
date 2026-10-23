"""Helpline specs: menus, prompts, hold behaviour, executives and tasks.

A helpline is a tree of nodes. Prompts are generated from option labels with
fixed English/Hindi templates, so a real published menu (e.g. SBI's official
contact-centre page) can be written down as labels and digits only.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dfield
from typing import Any

LANG_NAMES = {
    "hi": ("हिंदी", "Hindi"), "en": ("English", "English"), "ta": ("தமிழ்", "Tamil"),
    "te": ("తెలుగు", "Telugu"), "kn": ("ಕನ್ನಡ", "Kannada"), "ml": ("മലയാളം", "Malayalam"),
    "mr": ("मराठी", "Marathi"), "bn": ("বাংলা", "Bengali"), "gu": ("ગુજરાતી", "Gujarati"),
    "pa": ("ਪੰਜਾਬੀ", "Punjabi"), "or": ("ଓଡ଼ିଆ", "Odia"), "as": ("অসমীয়া", "Assamese"),
    "kok": ("कोंकणी", "Konkani"), "bho": ("भोजपुरी", "Bhojpuri"), "mai": ("मैथिली", "Maithili"),
    "ur": ("اردو", "Urdu"),
}
PROMPT_LANGS = ("en", "hi")  # languages we have prompt text for

KEY_WORD = {"en": {"*": "star", "#": "hash"}, "hi": {"*": "स्टार", "#": "हैश"}}

EXTRA_TEXT = {
    "repeat": {"en": "To repeat this menu, press {k}.", "hi": "मेन्यू दोबारा सुनने के लिए {k} दबाएँ।"},
    "agent": {"en": "To speak to a customer care executive, press {k}.",
              "hi": "ग्राहक सेवा अधिकारी से बात करने के लिए {k} दबाएँ।"},
    "main": {"en": "For the main menu, press {k}.", "hi": "मुख्य मेन्यू के लिए {k} दबाएँ।"},
    "back": {"en": "For the previous menu, press {k}.", "hi": "पिछले मेन्यू के लिए {k} दबाएँ।"},
}

SYSTEM_TEXT = {
    "invalid": {"en": "Sorry, that is not a valid option.", "hi": "क्षमा करें, यह विकल्प मान्य नहीं है।"},
    "noinput": {"en": "Sorry, I didn't get that.", "hi": "क्षमा करें, हमें आपका जवाब नहीं मिला।"},
    "goodbye": {"en": "Thank you for calling. Goodbye.", "hi": "कॉल करने के लिए धन्यवाद।"},
    "invalid_entry": {"en": "The number you entered is invalid. Please try again.",
                      "hi": "आपके द्वारा दर्ज किया गया नंबर अमान्य है। कृपया पुनः प्रयास करें।"},
    "not_registered": {"en": "This service is available only when you call from your registered mobile number.",
                       "hi": "यह सेवा केवल आपके पंजीकृत मोबाइल नंबर से कॉल करने पर उपलब्ध है।"},
    "confirm": {"en": "To confirm, press 1. To cancel, press 2.",
                "hi": "पुष्टि करने के लिए 1 दबाएँ। रद्द करने के लिए 2 दबाएँ।"},
    "ref": {"en": "Your request has been registered. Your reference number is {ref}.",
            "hi": "आपका अनुरोध दर्ज कर लिया गया है। आपका संदर्भ नंबर {ref} है।"},
    "after_fact": {"en": "To hear this again, press 1. For the main menu, press 0.",
                   "hi": "यह जानकारी दोबारा सुनने के लिए 1 दबाएँ। मुख्य मेन्यू के लिए 0 दबाएँ।"},
    "closed": {"en": "Our executives are available from {open} AM to {close} PM. Please call during working hours.",
               "hi": "हमारे अधिकारी सुबह {open} बजे से रात {close} बजे तक उपलब्ध हैं। कृपया कार्य समय में कॉल करें।"},
    "busy": {"en": "All our executives are busy right now. Please call again later.",
             "hi": "हमारे सभी अधिकारी इस समय व्यस्त हैं। कृपया बाद में कॉल करें।"},
    "callback": {"en": "To get a call back instead of waiting, press 1 now.",
                 "hi": "प्रतीक्षा करने के बजाय कॉल बैक पाने के लिए अभी 1 दबाएँ।"},
    "callback_ok": {"en": "Thank you. We will call you back on your registered number.",
                    "hi": "धन्यवाद। हम आपको आपके पंजीकृत नंबर पर कॉल बैक करेंगे।"},
    "position": {"en": "You are number {k} in the queue.", "hi": "कतार में आपका नंबर {k} है।"},
    "est_wait": {"en": "Your estimated waiting time is {m} minutes.", "hi": "आपका अनुमानित प्रतीक्षा समय {m} मिनट है।"},
    "connecting": {"en": "Please hold while we connect your call to an executive.",
                   "hi": "कृपया प्रतीक्षा करें, हम आपकी कॉल अधिकारी से जोड़ रहे हैं।"},
    "dead_end": {"en": "This service is currently unavailable.", "hi": "यह सेवा अभी उपलब्ध नहीं है।"},
}

FIELD_TEXT = {
    "acct_last4": {"en": "Please enter the last 4 digits of your account number.",
                   "hi": "कृपया अपने खाता नंबर के अंतिम 4 अंक दर्ज करें।"},
    "acct_last5": {"en": "Please enter the last 5 digits of your account number.",
                   "hi": "कृपया अपने खाता नंबर के अंतिम 5 अंक दर्ज करें।"},
    "card_last4": {"en": "Please enter the last 4 digits of your card number.",
                   "hi": "कृपया अपने कार्ड नंबर के अंतिम 4 अंक दर्ज करें।"},
    "dob": {"en": "Please enter your date of birth in D D M M Y Y Y Y format.",
            "hi": "कृपया अपनी जन्म तिथि D D M M Y Y Y Y प्रारूप में दर्ज करें।"},
    "birth_year": {"en": "Please enter your year of birth.", "hi": "कृपया अपना जन्म वर्ष दर्ज करें।"},
    "customer_id": {"en": "Please enter your customer ID followed by hash.",
                    "hi": "कृपया अपनी ग्राहक आईडी दर्ज करें और उसके बाद हैश दबाएँ।"},
    "tpin": {"en": "Please enter your 4 digit telephone PIN.", "hi": "कृपया अपना 4 अंकों का टेलीफोन पिन दर्ज करें।"},
    "mobile": {"en": "Please enter your 10 digit mobile number.", "hi": "कृपया अपना 10 अंकों का मोबाइल नंबर दर्ज करें।"},
    "otp": {"en": "Please enter the O T P sent to your mobile number.",
            "hi": "कृपया अपने मोबाइल नंबर पर भेजा गया ओ टी पी दर्ज करें।"},
    "ticket": {"en": "Please enter your complaint number.", "hi": "कृपया अपना शिकायत नंबर दर्ज करें।"},
    "consumer_no": {"en": "Please enter your consumer number.", "hi": "कृपया अपना उपभोक्ता नंबर दर्ज करें।"},
    "order_id": {"en": "Please enter your order number.", "hi": "कृपया अपना ऑर्डर नंबर दर्ज करें।"},
    "pnr": {"en": "Please enter your booking reference using the keypad.",
            "hi": "कृपया कीपैड से अपना बुकिंग संदर्भ दर्ज करें।"},
    "file_no": {"en": "Please enter the numeric part of your file number.",
                "hi": "कृपया अपनी फ़ाइल संख्या का अंकों वाला भाग दर्ज करें।"},
}
SECRET_FIELDS = {"tpin", "otp"}


@dataclass
class Option:
    key: str
    label: dict[str, str]
    goto: str


@dataclass
class Node:
    id: str
    type: str                      # menu | collect | fact | action | queue | message | language
    options: list[Option] = dfield(default_factory=list)
    modality: str = "dtmf"         # dtmf | speech | both | broken_speech
    timeout_s: float = 6.0
    repeats: int = 2
    on_fail: str = "disconnect"    # disconnect | <node id>
    extras: dict[str, str] = dfield(default_factory=dict)  # key -> repeat|agent|main|back
    agent_target: str = ""         # queue node reached by the 'agent' extra
    # collect
    field: str = ""
    digits: int = 0
    next: str = ""
    # fact / action
    fact: str = ""
    requires_registered: bool = False
    action: str = ""
    ref_digits: int = 6
    # queue
    dept: str = ""
    # message
    text: dict[str, str] = dfield(default_factory=dict)
    title: dict[str, str] = dfield(default_factory=dict)  # short name for the tree view


@dataclass
class Task:
    id: str
    helpline: str
    goal_type: str                 # reach_human | retrieve_fact | execute_action
    goal_text: str
    concepts: list[str]
    target: str                    # node id that satisfies the goal
    path: list[str]                # canonical key presses after language choice (for scripted/human/oracle)
    pine: str = ""                 # complaint | cancel | negotiate | refund_status | "" (bridge)
    note: str = ""


@dataclass
class Helpline:
    id: str
    display_name: str
    brand: str
    sector: str
    structure_source: str          # provenance source key
    structure_tag: str             # OFFICIAL | ASSUMED ...
    dial: str
    shortcode: dict[str, Any] | None
    languages: list[tuple[str, str]]   # (key, lang) in language-menu order; ('9','more') allowed
    language_menu: bool
    welcome: dict[str, str]
    disclaimer: dict[str, str]
    barge_in: bool
    caller_id_auth: bool
    caller_id_auth_tag: str
    hours: tuple[int, int]
    root: str
    nodes: dict[str, Node]
    hold: dict[str, Any]
    queue: dict[str, Any]
    executive: dict[str, Any]
    tasks: list[Task]
    more_languages: list[tuple[str, str]] = dfield(default_factory=list)
    notes: list[str] = dfield(default_factory=list)

    def node(self, nid: str) -> Node:
        return self.nodes[nid]

    def task(self, tid: str) -> Task:
        return next(t for t in self.tasks if t.id == tid)


def option_line(opt: Option, modality: str, lang: str) -> str:
    label = opt.label.get(lang) or opt.label.get("en", "")
    k = KEY_WORD[lang].get(opt.key, opt.key)
    if lang == "hi":
        if modality == "speech":
            return f"{label} के लिए '{label}' बोलें।"
        if modality == "both":
            return f"{label} के लिए {k} दबाएँ या '{label}' बोलें।"
        return f"{label} के लिए {k} दबाएँ।"
    if modality == "speech":
        return f"For {label}, say '{label}'."
    if modality == "both":
        return f"For {label}, press {k} or say '{label}'."
    return f"For {label}, press {k}."


def menu_prompt(node: Node, lang: str) -> str:
    # broken_speech: the prompt says "press" but only speech is accepted (Sierra's hurdle 4)
    shown = "dtmf" if node.modality == "broken_speech" else node.modality
    parts = [option_line(o, shown, lang) for o in node.options]
    for k, kind in node.extras.items():
        kk = KEY_WORD[lang].get(k, k)
        parts.append(EXTRA_TEXT[kind][lang].format(k=kk))
    return " ".join(parts)


def language_prompt(langs: list[tuple[str, str]]) -> tuple[str, str]:
    """Each option is spoken in its own language, as Indian IVRs do. Returns (text, lang tag)."""
    parts = []
    for key, lang in langs:
        if lang == "more":
            parts.append(f"For other languages, press {key}.")
        elif lang == "hi":
            parts.append(f"हिंदी के लिए {key} दबाएँ।")
        elif lang == "en":
            parts.append(f"For English, press {key}.")
        else:
            native, eng = LANG_NAMES[lang]
            parts.append(f"{native}: {key}.")
    return " ".join(parts), "mixed"
