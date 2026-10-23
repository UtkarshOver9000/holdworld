"""The helpline library.

Real-structure archetypes (OFFICIAL): the menus of SBI, KVB and Union Bank as
published on their own contact pages (read 2026-10-21), relabelled on screen
so no brand is impersonated. Assumed-structure archetypes (ASSUMED) cover the
sectors with no published menu until the India Hold Atlas measures them.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .spec import Helpline, Node, Option, Task


def o(key, en, hi, goto):
    return Option(key, {"en": en, "hi": hi}, goto)


def menu(nid, options, title=None, **kw):
    return Node(nid, "menu", options=options, title=title or {}, **kw)


def collect(nid, field, digits, nxt, **kw):
    return Node(nid, "collect", field=field, digits=digits, next=nxt, **kw)


def fact(nid, key, en, hi, registered=False):
    return Node(nid, "fact", fact=key, requires_registered=registered, text={"en": en, "hi": hi})


def action(nid, key, registered=False, ref_digits=6):
    return Node(nid, "action", action=key, requires_registered=registered, ref_digits=ref_digits)


def queue(nid, dept):
    return Node(nid, "queue", dept=dept)


def hold(brand, **kw):
    base = {
        "first_msg_s": 3.0,
        "announce_every_s": 60.0,          # DATA: Brown 2005 / the real hazard spike at ~58 s
        "announce": {"en": f"Thank you for calling {brand}. All our executives are busy. Your call is important to us, please stay on the line.",
                     "hi": f"{brand} में कॉल करने के लिए धन्यवाद। हमारे सभी अधिकारी व्यस्त हैं। आपकी कॉल हमारे लिए महत्वपूर्ण है, कृपया लाइन पर बने रहें।"},
        "position": False, "est_wait": False,
        "agent_like_p": 0.35,
        "agent_like": {"en": f"Hello! Thank you for calling {brand}. My name is Priya. Your call is valuable to us and an executive will be with you shortly.",
                       "hi": f"नमस्ते! {brand} में कॉल करने के लिए धन्यवाद। मेरा नाम प्रिया है। आपकी कॉल हमारे लिए महत्वपूर्ण है, जल्द ही एक अधिकारी आपसे बात करेंगे।"},
        "silence_gap_p": 0.15, "silence_gap_s": [3.0, 12.0],
        "callback_after_s": None,
        "busy_disconnect_p": 0.03,
        "abrupt_pickup_p": 0.5,
        "drop_per_min": 0.002,
        "tag": "ASSUMED",
    }
    base.update(kw)
    return base


def executive(brand, **kw):
    base = {
        "names": ["Ravi", "Pooja", "Arjun", "Sneha", "Imran", "Kavya", "Rahul", "Divya"],
        "greeting": {"en": "Good day, this is {name} from {brand}. How may I help you?",
                     "hi": "नमस्कार, मैं {brand} से {name} बात कर रहा हूँ। मैं आपकी क्या सहायता कर सकता हूँ?"},
        "brand": brand,
        "verify": ["name", "dob"],
        "otp": False,
        "transfer_p": 0.10,
        "refuse_ai_p": None,                # None = use the provenance default
        "ai_exec_p": 0.0,
        "handshake": False,
        "offers": [],
        "discounts": [],
    }
    base.update(kw)
    return base


# ----------------------------------------------------------------------------------------
# 1. Large public-sector bank, structure from SBI's official contact-centre page
# ----------------------------------------------------------------------------------------
def psu_bank() -> Helpline:
    b = "Bharat Public Bank"
    nodes = {n.id: n for n in [
        menu("main", [
            o("0", "blocking ATM card, internet banking or UPI", "एटीएम कार्ड, इंटरनेट बैंकिंग या यूपीआई ब्लॉक करने", "block"),
            o("1", "account related services", "खाते से जुड़ी सेवाओं", "acct"),
            o("2", "debit card and cheque book services", "डेबिट कार्ड और चेक बुक सेवाओं", "card"),
            o("3", "interest certificates, internet banking and YONO", "ब्याज प्रमाणपत्र, इंटरनेट बैंकिंग और योनो", "cert"),
            o("4", "deposit and loan information and complaints", "जमा और ऋण जानकारी तथा शिकायतों", "dep"),
        ], {"en": "Main menu"}, extras={"*": "repeat"}),
        menu("block", [
            o("1", "blocking your ATM card", "अपना एटीएम कार्ड ब्लॉक करने", "block_atm_c"),
            o("2", "blocking internet banking", "इंटरनेट बैंकिंग ब्लॉक करने", "block_inb_c"),
            o("3", "blocking UPI", "यूपीआई ब्लॉक करने", "block_upi_c"),
        ], {"en": "Block"}, extras={"0": "main"}),
        collect("block_atm_c", "acct_last4", 4, "block_atm"),
        action("block_atm", "block_atm_card"),
        collect("block_inb_c", "dob", 8, "block_inb"),
        action("block_inb", "block_internet_banking"),
        collect("block_upi_c", "acct_last4", 4, "block_upi"),
        action("block_upi", "block_upi"),
        menu("acct", [
            o("1", "account balance", "खाते में शेष राशि", "bal_c"),
            o("2", "last 5 transactions", "पिछले 5 लेनदेन", "txn_c"),
            o("3", "account statement", "खाता विवरण", "stmt_c"),
            o("4", "CIF information", "सीआईएफ जानकारी", "cif"),
            o("5", "nomination information", "नामांकन जानकारी", "nom"),
        ], {"en": "Account"}, extras={"0": "main"}),
        collect("bal_c", "acct_last4", 4, "bal"),
        fact("bal", "balance", "Your available balance is rupees {value}.", "आपके खाते में उपलब्ध शेष राशि {value} रुपये है।"),
        collect("txn_c", "acct_last4", 4, "txn"),
        fact("txn", "last_txn", "Your last transaction was a debit of rupees {value}.", "आपका पिछला लेनदेन {value} रुपये का डेबिट था।"),
        collect("stmt_c", "acct_last4", 4, "stmt"),
        action("stmt", "email_statement"),
        action("cif", "sms_cif"),
        fact("nom", "nomination", "Nomination is registered for this account. Status code {value}.", "इस खाते के लिए नामांकन दर्ज है। स्थिति कोड {value}।"),
        menu("card", [
            o("1", "ATM PIN generation", "एटीएम पिन बनाने", "pin_c"),
            o("2", "debit card dispatch status", "डेबिट कार्ड भेजे जाने की स्थिति", "disp"),
            o("3", "debit card re-issue", "डेबिट कार्ड दोबारा जारी करने", "reissue_c"),
            o("4", "a new cheque book", "नई चेक बुक", "chq"),
            o("5", "cheque book dispatch status", "चेक बुक भेजे जाने की स्थिति", "chqst"),
            o("6", "switching your ATM card on or off", "एटीएम कार्ड चालू या बंद करने", "switch_c"),
            o("7", "stopping a cheque", "चेक रोकने", "stopchq_c"),
        ], {"en": "Cards & cheques"}, extras={"0": "main"}),
        collect("pin_c", "acct_last5", 5, "pin_c2"),
        collect("pin_c2", "birth_year", 4, "pin"),
        action("pin", "atm_pin_otp"),
        fact("disp", "card_dispatch", "Your debit card was dispatched with tracking number {value}.", "आपका डेबिट कार्ड ट्रैकिंग नंबर {value} के साथ भेजा गया है।"),
        collect("reissue_c", "dob", 8, "reissue"),
        action("reissue", "reissue_card"),
        action("chq", "cheque_book"),
        fact("chqst", "cheque_dispatch", "Your cheque book was dispatched with tracking number {value}.", "आपकी चेक बुक ट्रैकिंग नंबर {value} के साथ भेजी गई है।"),
        collect("switch_c", "acct_last5", 5, "switch"),
        action("switch", "card_switch"),
        collect("stopchq_c", "acct_last4", 4, "stopchq"),
        action("stopchq", "stop_cheque"),
        menu("cert", [
            o("1", "YONO", "योनो", "q_yono"),
            o("2", "YONO Business", "योनो बिज़नेस", "q_yono"),
            o("3", "TDS and deposit interest certificate", "टीडीएस और जमा ब्याज प्रमाणपत्र", "tds"),
            o("4", "home loan interest certificate", "गृह ऋण ब्याज प्रमाणपत्र", "hlc"),
            o("5", "education loan interest certificate", "शिक्षा ऋण ब्याज प्रमाणपत्र", "elc"),
            o("6", "internet banking", "इंटरनेट बैंकिंग", "q_inb"),
        ], {"en": "Certificates & digital"}, extras={"0": "main"}),
        queue("q_yono", "digital"), queue("q_inb", "digital"),
        action("tds", "email_tds"), action("hlc", "email_hlc"), action("elc", "email_elc"),
        menu("dep", [
            o("1", "deposit and loan interest rates", "जमा और ऋण ब्याज दरों", "rates"),
            o("2", "loan and deposit product information", "ऋण और जमा उत्पाद जानकारी", "q_products"),
            o("3", "complaint status", "शिकायत की स्थिति", "cstat_c"),
            o("4", "lodging a complaint", "शिकायत दर्ज करने", "q_complaints"),
            o("5", "Haj Yatra", "हज यात्रा", "q_products"),
        ], {"en": "Deposits, loans, complaints"}, extras={"0": "main"}),
        fact("rates", "fd_rate", "The current one year deposit rate is {value} percent.", "एक वर्ष की जमा दर अभी {value} प्रतिशत है।"),
        queue("q_products", "products"), queue("q_complaints", "complaints"),
        collect("cstat_c", "ticket", 8, "cstat"),
        fact("cstat", "complaint_status", "Your complaint is under process. Expected resolution date {value}.", "आपकी शिकायत पर कार्रवाई जारी है। अनुमानित समाधान तिथि {value}।"),
    ]}
    return Helpline(
        id="psu_bank", display_name="Large public-sector bank", brand=b, sector="bank",
        structure_source="sbi_official", structure_tag="OFFICIAL", dial="1800-XXX-1234",
        shortcode=None,
        # language digits: third-party (BankBazaar) order; SBI's page lists 15 languages, no digits
        languages=[("1", "hi"), ("2", "en"), ("3", "kn"), ("4", "ta"), ("5", "ml"), ("9", "more")],
        more_languages=[("1", "te"), ("2", "mr"), ("3", "bn"), ("4", "gu"), ("5", "pa"), ("6", "or"), ("7", "as")],
        language_menu=True,
        welcome={"en": f"Welcome to {b}.", "hi": f"{b} में आपका स्वागत है।"},
        disclaimer={},
        barge_in=True, caller_id_auth=False, caller_id_auth_tag="OFFICIAL",
        hours=(0, 24), root="main", nodes=nodes,
        hold=hold(b),
        queue={"volume_scale": 8.0, "beta": -0.35, "open": [0, 24], "tag": "ASSUMED",
               "note": "real 1999 shape x volume; level assumed until the Atlas"},
        executive=executive(b, verify=["name", "dob", "acct_last4"], otp=True),
        tasks=[
            Task("psu_complaint", "psu_bank", "reach_human", "Lodge a complaint about a failed UPI payment that was debited",
                 ["complaint", "lodge", "upi"], "q_complaints", ["4", "4"]),
            Task("psu_balance", "psu_bank", "retrieve_fact", "Find out my account balance",
                 ["balance", "account"], "bal", ["1", "1", "#acct_last4"]),
            Task("psu_block", "psu_bank", "execute_action", "Block my lost ATM card", ["block", "card"],
                 "block_atm", ["0", "1", "#acct_last4"]),
            Task("psu_dispute", "psu_bank", "reach_human", "Raise a dispute for a failed UPI debit and get the complaint number",
                 ["complaint", "lodge", "upi"], "q_complaints", ["4", "4"], pine="complaint"),
        ],
        notes=["Menu digits and services from SBI's official page (read 2026-10-21); the page itself "
               "numbers some sub-menus inconsistently.", "16 of SBI's 50 listed services go only to a human."],
    )


# ----------------------------------------------------------------------------------------
# 2. TPIN-gated private bank, structure from KVB's official IVRS page
# ----------------------------------------------------------------------------------------
def tpin_bank() -> Helpline:
    b = "Kaveri Trust Bank"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "phone banking", "फोन बैंकिंग", "cid"),
            o("2", "debit card hotlisting", "डेबिट कार्ड हॉटलिस्ट करने", "hot_c"),
            o("3", "new loans and other products", "नए ऋण और अन्य उत्पादों", "q_loans"),
            o("4", "FASTag queries", "फास्टैग से जुड़े प्रश्नों", "q_fastag"),
        ], {"en": "Main menu"}),
        collect("cid", "customer_id", 10, "tpin"),
        collect("tpin", "tpin", 4, "bank"),
        menu("bank", [
            o("1", "balance enquiry", "शेष राशि जानने", "bal"),
            o("2", "last 3 transactions", "पिछले 3 लेनदेन", "txn"),
            o("4", "fund transfer", "फंड ट्रांसफर", "q_ft"),
        ], {"en": "Self service"}),
        fact("bal", "balance", "Your available balance is rupees {value}.", "आपके खाते में उपलब्ध शेष राशि {value} रुपये है।", registered=True),
        fact("txn", "last_txn", "Your last transaction was a debit of rupees {value}.", "आपका पिछला लेनदेन {value} रुपये का डेबिट था।", registered=True),
        collect("hot_c", "card_last4", 4, "hot"),
        action("hot", "hotlist_card"),
        queue("q_loans", "loans"), queue("q_fastag", "fastag"), queue("q_ft", "phone_banking"),
    ]}
    return Helpline(
        id="tpin_bank", display_name="TPIN-gated private bank", brand=b, sector="bank",
        structure_source="kvb_official", structure_tag="OFFICIAL", dial="1860-XXX-1916 (not toll-free)",
        shortcode=None,
        languages=[("1", "en"), ("2", "ta"), ("3", "hi"), ("4", "te"), ("5", "kn"), ("6", "ml")],
        language_menu=True,
        welcome={"en": f"Welcome to {b} phone banking.", "hi": f"{b} फोन बैंकिंग में आपका स्वागत है।"},
        disclaimer={}, barge_in=True, caller_id_auth=True, caller_id_auth_tag="OFFICIAL",
        hours=(9, 21), root="main", nodes=nodes,
        hold=hold(b, agent_like_p=0.2),
        queue={"volume_scale": 2.5, "beta": -0.15, "open": [9, 21], "tag": "ASSUMED", "note": "level assumed"},
        executive=executive(b, verify=["name", "customer_id"], otp=True),
        tasks=[
            Task("tpin_balance", "tpin_bank", "retrieve_fact", "Check my account balance", ["balance"], "bal",
                 ["1", "#customer_id", "#tpin", "1"]),
            Task("tpin_hotlist", "tpin_bank", "execute_action", "Hotlist my stolen debit card", ["block", "card"],
                 "hot", ["2", "#card_last4"]),
            Task("tpin_loan", "tpin_bank", "reach_human", "Ask about a personal loan", ["loan"], "q_loans", ["3"]),
        ],
        notes=["Customer ID then # then a 4-digit TPIN; first registration must be from the registered "
               "mobile (official page). HoldForMe never types a PIN for the user."],
    )


# ----------------------------------------------------------------------------------------
# 3. 'Zero-out anytime' bank, Union Bank's published behaviour (+ IDBI digit conventions)
# ----------------------------------------------------------------------------------------
def zero_out_bank() -> Helpline:
    b = "Sagar Bank"
    agent = {"9": "agent"}
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "account information", "खाते की जानकारी", "acct"),
            o("2", "debit card hotlisting", "डेबिट कार्ड हॉटलिस्ट करने", "hot_c"),
            o("3", "Aadhaar seeding", "आधार सीडिंग", "aadhaar"),
            o("4", "stopping a cheque", "चेक रोकने", "stop_c"),
        ], {"en": "Main menu"}, extras={**agent, "*": "repeat"}, agent_target="q_general"),
        menu("acct", [
            o("1", "balance", "शेष राशि", "bal"),
            o("2", "last five transactions", "पिछले पांच लेनदेन", "txn"),
        ], {"en": "Account"}, extras={**agent, "8": "back"}, agent_target="q_general"),
        fact("bal", "balance", "Your balance is rupees {value}.", "आपकी शेष राशि {value} रुपये है।", registered=True),
        fact("txn", "last_txn", "Your last debit was rupees {value}.", "आपका पिछला डेबिट {value} रुपये था।", registered=True),
        collect("hot_c", "card_last4", 4, "hot"), action("hot", "hotlist_card"),
        action("aadhaar", "aadhaar_seed"),
        collect("stop_c", "acct_last4", 4, "stop"), action("stop", "stop_cheque"),
        queue("q_general", "general"),
    ]}
    return Helpline(
        id="zero_out_bank", display_name="Zero-out-anytime bank", brand=b, sector="bank",
        structure_source="union_official", structure_tag="OFFICIAL", dial="1800-XXX-8333", shortcode=None,
        languages=[("1", "hi"), ("2", "en"), ("3", "mr"), ("4", "ta")], language_menu=True,
        welcome={"en": f"Welcome to {b}.", "hi": f"{b} में आपका स्वागत है।"}, disclaimer={},
        barge_in=True, caller_id_auth=False, caller_id_auth_tag="ASSUMED", hours=(0, 24), root="main",
        nodes=nodes, hold=hold(b), executive=executive(b, verify=["name", "acct_last4"]),
        queue={"volume_scale": 6.0, "beta": -0.25, "open": [0, 24], "tag": "ASSUMED", "note": "level assumed"},
        tasks=[
            Task("zero_human", "zero_out_bank", "reach_human", "Talk to someone about a wrong charge on my account",
                 ["executive", "charge"], "q_general", ["9"]),
            Task("zero_hotlist", "zero_out_bank", "execute_action", "Hotlist my debit card", ["block", "card"],
                 "hot", ["2", "#card_last4"]),
        ],
        notes=["Union Bank: agent reachable at any point, 24x7x365 (official). The '9' digit follows "
               "IDBI/Indian Bank published conventions (third-party)."],
    )


# ----------------------------------------------------------------------------------------
# 4. Telecom operator: short code rule (OFFICIAL), queue pinned to TRAI-reported answer rates
# ----------------------------------------------------------------------------------------
def telecom() -> Helpline:
    b = "Tarang Mobile"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "recharge and plans", "रिचार्ज और प्लान", "plan_g"),
            o("2", "network or internet problems", "नेटवर्क या इंटरनेट की समस्या", "q_tech"),
            o("3", "billing", "बिलिंग", "bill"),
            o("4", "closing or porting your number", "नंबर बंद या पोर्ट करने", "q_retention"),
        ], {"en": "Main menu"}, extras={"9": "agent"}, agent_target="q_general"),
        collect("plan_g", "mobile", 10, "plan_o"),
        collect("plan_o", "otp", 6, "plan"),
        fact("plan", "current_plan", "Your current plan is rupees {value} for 28 days.", "आपका वर्तमान प्लान 28 दिनों के लिए {value} रुपये का है।"),
        menu("bill", [
            o("1", "your bill amount", "आपकी बिल राशि", "bill_g"),
            o("2", "disputing a charge or cancelling a subscription", "किसी शुल्क पर आपत्ति या सब्सक्रिप्शन रद्द करने", "q_billing"),
        ], {"en": "Billing"}, extras={"9": "agent"}, agent_target="q_general"),
        collect("bill_g", "mobile", 10, "bill_o"),
        collect("bill_o", "otp", 6, "billamt"),
        fact("billamt", "bill_amount", "Your outstanding amount is rupees {value}.", "आपकी बकाया राशि {value} रुपये है।"),
        queue("q_tech", "tech"), queue("q_billing", "billing"), queue("q_retention", "retention"),
        queue("q_general", "general"),
    ]}
    return Helpline(
        id="telecom", display_name="Mobile operator", brand=b, sector="telecom",
        structure_source="jio_shortcode", structure_tag="ASSUMED", dial="1800-XX-99999",
        shortcode={"code": "199", "network_only": True, "long": "1800-XX-99999"},
        languages=[("1", "hi"), ("2", "en")], language_menu=True,
        welcome={"en": f"Welcome to {b} customer care.", "hi": f"{b} कस्टमर केयर में आपका स्वागत है।"},
        disclaimer={}, barge_in=True, caller_id_auth=True, caller_id_auth_tag="ASSUMED", hours=(0, 24),
        root="main", nodes=nodes,
        hold=hold(b, agent_like_p=0.2, announce_every_s=30.0),
        queue={"volume_scale": 10.0, "beta": None, "open": [0, 24], "tag": "OFFICIAL",
               "calibrate": {"limit_s": 90, "target": 0.97},
               "note": "staffing solved so 97% are answered within 90 s (TRAI 95%; Airtel 95.2-98.3%, Jio 99.0-99.97%)"},
        executive=executive(b, verify=["name", "mobile"], otp=True, transfer_p=0.15,
                            offers=["50 percent off your next two recharges", "a free 2 GB data pack every month for three months"],
                            discounts=[0, 10, 20]),
        tasks=[
            Task("tel_network", "telecom", "reach_human", "Complain that my mobile internet keeps dropping",
                 ["network"], "q_tech", ["2"]),
            Task("tel_bill", "telecom", "retrieve_fact", "Find out my outstanding bill amount", ["bill"], "billamt",
                 ["3", "1", "#mobile", "#otp"]),
            Task("tel_cancel", "telecom", "reach_human", "Cancel a caller-tune subscription I never asked for",
                 ["cancel", "subscription"], "q_billing", ["3", "2"], pine="cancel"),
            Task("tel_negotiate", "telecom", "reach_human", "Ask for a discount on my plan or I will port out",
                 ["port", "close"], "q_retention", ["4"], pine="negotiate"),
        ],
        notes=["Short code 199 works only from the operator's own SIM; others must dial the toll-free number "
               "(published by Jio for 199/198)."],
    )


# ----------------------------------------------------------------------------------------
# 5-9. Assumed-structure archetypes (no published menus; the Atlas will replace these)
# ----------------------------------------------------------------------------------------
def airline() -> Helpline:
    b = "Megh Airways"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "a new booking", "नई बुकिंग", "q_sales"),
            o("2", "changing or cancelling a booking", "बुकिंग बदलने या रद्द करने", "chg"),
            o("3", "refund status", "रिफंड की स्थिति", "q_refund"),
            o("4", "baggage", "सामान", "q_baggage"),
        ], {"en": "Main menu"}, extras={"*": "repeat"}),
        menu("chg", [
            o("1", "changing your flight", "अपनी फ्लाइट बदलने", "q_changes"),
            o("2", "cancelling your booking", "अपनी बुकिंग रद्द करने", "q_changes"),
        ], {"en": "Changes"}, extras={"0": "main"}),
        queue("q_sales", "sales"), queue("q_changes", "changes"), queue("q_refund", "refunds"),
        queue("q_baggage", "baggage"),
    ]}
    return Helpline(
        id="airline", display_name="Airline", brand=b, sector="airline", structure_source="assumption",
        structure_tag="ASSUMED", dial="0124-XXX-3838", shortcode=None, languages=[("1", "en"), ("2", "hi")],
        language_menu=True, welcome={"en": f"Welcome to {b}.", "hi": f"{b} में आपका स्वागत है।"},
        disclaimer={"en": "Due to heavy call volumes, waiting times are longer than usual. For faster service, please visit our website or app.",
                    "hi": "अधिक कॉल के कारण प्रतीक्षा समय सामान्य से अधिक है। तेज़ सेवा के लिए हमारी वेबसाइट या ऐप देखें।"},
        barge_in=True, caller_id_auth=False, caller_id_auth_tag="ASSUMED", hours=(0, 24), root="main",
        nodes=nodes, hold=hold(b, callback_after_s=120.0, position=True, agent_like_p=0.5),
        queue={"volume_scale": 7.0, "beta": -0.6, "open": [0, 24], "service_scale": 1.3, "tag": "ASSUMED",
               "note": "long holds assumed; disruption days (e.g. Dec 2025) are a stress scenario"},
        executive=executive(b, verify=["name", "pnr"], transfer_p=0.25),
        tasks=[
            Task("air_refund", "airline", "reach_human", "Ask when the refund for my cancelled flight will arrive",
                 ["refund"], "q_refund", ["3"], pine="refund_status"),
            Task("air_change", "airline", "reach_human", "Change my flight to a later date", ["change", "flight"],
                 "q_changes", ["2", "1"]),
            Task("air_baggage", "airline", "reach_human", "Report delayed baggage and get a complaint number",
                 ["baggage", "complaint"], "q_baggage", ["4"], pine="complaint"),
        ],
    )


def ecommerce() -> Helpline:
    b = "BazaarKart"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "the status of an order", "ऑर्डर की स्थिति", "ord_c"),
            o("2", "returns and refunds", "रिटर्न और रिफंड", "q_returns"),
            o("3", "cancelling an order", "ऑर्डर रद्द करने", "can_c"),
        ], {"en": "Main menu"}, modality="both"),
        collect("ord_c", "order_id", 10, "ord"),
        fact("ord", "order_status", "Your order will be delivered on {value}.", "आपका ऑर्डर {value} को डिलीवर होगा।"),
        collect("can_c", "order_id", 10, "can"), action("can", "cancel_order"),
        queue("q_returns", "returns"),
    ]}
    return Helpline(
        id="ecommerce", display_name="E-commerce marketplace", brand=b, sector="ecommerce",
        structure_source="assumption", structure_tag="ASSUMED", dial="1800-XXX-7777", shortcode=None,
        languages=[("1", "en"), ("2", "hi")], language_menu=True,
        welcome={"en": f"Welcome to {b}.", "hi": f"{b} में आपका स्वागत है।"},
        disclaimer={"en": "For quicker help, use the help centre in the app.", "hi": "जल्दी मदद के लिए ऐप में हेल्प सेंटर का उपयोग करें।"},
        barge_in=True, caller_id_auth=True, caller_id_auth_tag="ASSUMED", hours=(7, 23), root="main",
        nodes=nodes, hold=hold(b, agent_like_p=0.4),
        queue={"volume_scale": 5.0, "beta": -0.2, "open": [7, 23], "tag": "ASSUMED", "note": "level assumed"},
        executive=executive(b, verify=["name", "order_id"]),
        tasks=[
            Task("ecom_order", "ecommerce", "retrieve_fact", "Find out when my order will be delivered",
                 ["order", "status"], "ord", ["1", "#order_id"]),
            Task("ecom_refund", "ecommerce", "reach_human", "Complain that my return refund has not arrived",
                 ["refund", "return"], "q_returns", ["2"], pine="complaint"),
        ],
        notes=["Order IDs carry letters (e.g. OD...), which a keypad cannot type: the ID-format quirk."],
    )


def electricity() -> Helpline:
    b = "Urja Vidyut Board"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "power cut complaint", "बिजली कटौती की शिकायत", "out_c"),
            o("2", "bill information", "बिल की जानकारी", "bill_c"),
            o("3", "new connection", "नया कनेक्शन", "q_newconn"),
        ], {"en": "Main menu"}, modality="speech"),
        collect("out_c", "consumer_no", 9, "out"), action("out", "outage_complaint", ref_digits=7),
        collect("bill_c", "consumer_no", 9, "bill"),
        fact("bill", "bill_amount", "Your bill amount is rupees {value}.", "आपकी बिल राशि {value} रुपये है।"),
        queue("q_newconn", "connections"),
    ]}
    return Helpline(
        id="electricity", display_name="State electricity board", brand=b, sector="utility",
        structure_source="assumption", structure_tag="ASSUMED", dial="1912", shortcode=None,
        languages=[("1", "hi"), ("2", "en")], language_menu=True,
        welcome={"en": f"Welcome to {b}.", "hi": f"{b} में आपका स्वागत है।"}, disclaimer={},
        barge_in=False, caller_id_auth=False, caller_id_auth_tag="ASSUMED", hours=(8, 20), root="main",
        nodes=nodes, hold=hold(b, busy_disconnect_p=0.12),
        queue={"volume_scale": 4.0, "beta": -0.5, "open": [8, 20], "tag": "ASSUMED", "note": "level assumed"},
        executive=executive(b, verify=["name", "consumer_no"]),
        tasks=[
            Task("elec_outage", "electricity", "execute_action", "Register a power cut complaint and get the number",
                 ["outage"], "out", ["1", "#consumer_no"]),
            Task("elec_newconn", "electricity", "reach_human", "Ask about a new electricity connection",
                 ["connection"], "q_newconn", ["3"]),
        ],
        notes=["Speech-only main menu (bolo), Hindi first: the 'Bolna can't press keys' case is not a problem here."],
    )


def gov_docs() -> Helpline:
    b = "Dastavez Seva Kendra"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "application status", "आवेदन की स्थिति", "app_c"),
            o("2", "appointment booking", "अपॉइंटमेंट बुकिंग", "q_appt"),
            o("3", "speaking to an officer", "अधिकारी से बात करने", "q_officer"),
        ], {"en": "Main menu"}, extras={"*": "repeat"}),
        collect("app_c", "file_no", 8, "app"),
        fact("app", "application_status", "Your application is at stage {value}.", "आपका आवेदन चरण {value} पर है।"),
        queue("q_appt", "appointments"), queue("q_officer", "officers"),
    ]}
    return Helpline(
        id="gov_docs", display_name="Government documents helpline", brand=b, sector="government",
        structure_source="assumption", structure_tag="ASSUMED", dial="1800-XXX-1800", shortcode=None,
        languages=[("1", "hi"), ("2", "en")], language_menu=True,
        welcome={"en": f"Welcome to the {b} helpline.", "hi": f"{b} हेल्पलाइन में आपका स्वागत है।"},
        disclaimer={"en": "Please note that this call may be recorded for quality and training purposes. Officials will never ask for your password or payment over the phone. Beware of fraudulent websites and agents. Applications can also be tracked online on our official portal.",
                    "hi": "कृपया ध्यान दें कि गुणवत्ता और प्रशिक्षण के लिए यह कॉल रिकॉर्ड की जा सकती है। अधिकारी फोन पर कभी भी आपका पासवर्ड या भुगतान नहीं मांगेंगे। धोखाधड़ी वाली वेबसाइटों और एजेंटों से सावधान रहें। आवेदन की स्थिति हमारे आधिकारिक पोर्टल पर भी देखी जा सकती है।"},
        barge_in=False, caller_id_auth=False, caller_id_auth_tag="ASSUMED", hours=(8, 20), root="main",
        nodes=nodes, hold=hold(b, busy_disconnect_p=0.18, position=True, est_wait=True),
        queue={"volume_scale": 6.0, "beta": -0.7, "open": [8, 20], "tag": "ASSUMED", "note": "level assumed"},
        executive=executive(b, verify=["name", "file_no"], transfer_p=0.15),
        tasks=[
            Task("gov_status", "gov_docs", "retrieve_fact", "Check the status of my application", ["application", "status"],
                 "app", ["1", "#file_no"]),
            Task("gov_officer", "gov_docs", "reach_human", "Talk to an officer about a wrong address on my document",
                 ["officer"], "q_officer", ["3"]),
        ],
    )


def gas() -> Helpline:
    b = "Agni Gas"
    nodes = {n.id: n for n in [
        menu("main", [
            o("1", "booking a refill", "रिफिल बुक करने", "book_c"),
            o("2", "other services", "अन्य सेवाओं", "other"),
        ], {"en": "Main menu"}),
        menu("other", [
            o("1", "a safety complaint", "सुरक्षा शिकायत", "q_safety"),
            o("2", "transferring your connection", "कनेक्शन ट्रांसफर करने", "dead"),
            o("3", "more services", "और सेवाओं", "main"),        # loops back to the start
        ], {"en": "Other services"}),
        Node("dead", "message", text={"en": "This service is currently unavailable.", "hi": "यह सेवा अभी उपलब्ध नहीं है।"},
             next="main"),
        collect("book_c", "consumer_no", 9, "book"), action("book", "refill_booking"),
        queue("q_safety", "safety"),
    ]}
    return Helpline(
        id="gas", display_name="Cooking gas distributor", brand=b, sector="utility", structure_source="assumption",
        structure_tag="ASSUMED", dial="1800-XXX-2333", shortcode=None, languages=[("1", "hi"), ("2", "en")],
        language_menu=True, welcome={"en": f"Welcome to {b}.", "hi": f"{b} में आपका स्वागत है।"}, disclaimer={},
        barge_in=True, caller_id_auth=True, caller_id_auth_tag="ASSUMED", hours=(9, 18), root="main", nodes=nodes,
        hold=hold(b), executive=executive(b, verify=["name", "consumer_no"]),
        queue={"volume_scale": 2.0, "beta": -0.3, "open": [9, 18], "tag": "ASSUMED", "note": "level assumed"},
        tasks=[
            Task("gas_book", "gas", "execute_action", "Book a gas refill", ["booking", "refill"], "book",
                 ["1", "#consumer_no"]),
            Task("gas_safety", "gas", "reach_human", "Report a gas leak smell near my cylinder", ["safety", "complaint"],
                 "q_safety", ["2", "1"]),
        ],
        notes=["'More services' loops back to the main menu and one option is a dead end."],
    )


BUILDERS = [psu_bank, tpin_bank, zero_out_bank, telecom, airline, ecommerce, electricity, gov_docs, gas]


def all_helplines() -> dict[str, Helpline]:
    return {h.id: h for h in (b() for b in BUILDERS)}


def export_json(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for h in all_helplines().values():
        (out_dir / f"{h.id}.json").write_text(json.dumps(asdict(h), ensure_ascii=False, indent=1), encoding="utf-8")
