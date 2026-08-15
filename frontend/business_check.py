"""
business_check.py
Verified Business Checker — detects impersonation of real companies.

Covers:
  • Nigerian banks (GTBank, Access, UBA, Zenith, First Bank, CBN, etc.)
  • Nigerian telecoms (MTN, Airtel, Glo, 9mobile)
  • Nigerian government (EFCC, NAFDAC, FIRS, INEC, CBN, NCC)
  • Nigerian companies (Dangote, Flutterwave, Paystack, Jumia, Konga)
  • International brands commonly impersonated in Nigeria
    (DHL, FedEx, PayPal, Amazon, Apple, Google, Microsoft, Netflix, WhatsApp, etc.)
"""

import re
from difflib import SequenceMatcher
from flask import Blueprint, request, jsonify
from extensions import limiter

business_bp = Blueprint("business", __name__, url_prefix="/api/business")

# ------------------------------------------------------------------
# VERIFIED BUSINESS DATABASE
# Each entry: (canonical_name, [official_domains], [aliases/variants])
# ------------------------------------------------------------------
VERIFIED_BUSINESSES = [
    # ── Nigerian Banks ────────────────────────────────────────────
    ("GTBank (Guaranty Trust Bank)",
     ["gtbank.com", "gtco.com"],
     ["guaranty trust", "gtb", "gtbank"]),

    ("Access Bank Nigeria",
     ["accessbankplc.com"],
     ["access bank", "accessbank", "access diamond"]),

    ("UBA (United Bank for Africa)",
     ["ubagroup.com"],
     ["united bank for africa", "uba bank"]),

    ("Zenith Bank",
     ["zenithbank.com"],
     ["zenith bank", "zenithbank"]),

    ("First Bank Nigeria",
     ["firstbanknigeria.com"],
     ["first bank", "firstbank nigeria", "fbn"]),

    ("Fidelity Bank Nigeria",
     ["fidelitybank.ng"],
     ["fidelity bank", "fidelitybank"]),

    ("Stanbic IBTC",
     ["stanbicibtc.com"],
     ["stanbic", "ibtc bank"]),

    ("Sterling Bank",
     ["sterling.ng", "sterlingbank.com"],
     ["sterling bank"]),

    ("Polaris Bank",
     ["polarisbanklimited.com"],
     ["polaris bank", "polarisbank"]),

    ("Wema Bank",
     ["wemabank.com"],
     ["wema bank", "alat"]),

    ("Kuda Bank",
     ["kuda.com"],
     ["kuda bank", "kuda microfinance"]),

    ("Opay",
     ["opay.com.ng"],
     ["opay", "o-pay", "opay digital services"]),

    ("Palmpay",
     ["palmpay.com"],
     ["palmpay", "palm pay"]),

    # ── CBN & Regulators ─────────────────────────────────────────
    ("CBN (Central Bank of Nigeria)",
     ["cbn.gov.ng"],
     ["central bank of nigeria", "cbn nigeria"]),

    ("NDIC (Nigeria Deposit Insurance Corporation)",
     ["ndic.gov.ng"],
     ["ndic", "nigeria deposit insurance"]),

    # ── Nigerian Government Agencies ──────────────────────────────
    ("EFCC (Economic and Financial Crimes Commission)",
     ["efcc.gov.ng"],
     ["efcc", "economic and financial crimes commission"]),

    ("NAFDAC",
     ["nafdac.gov.ng"],
     ["nafdac", "national agency food drug"]),

    ("FIRS (Federal Inland Revenue Service)",
     ["firs.gov.ng"],
     ["firs", "federal inland revenue", "nigerian tax"]),

    ("INEC (Independent National Electoral Commission)",
     ["inec.gov.ng"],
     ["inec", "electoral commission nigeria"]),

    ("NCC (Nigerian Communications Commission)",
     ["ncc.gov.ng"],
     ["ncc", "nigerian communications commission"]),

    ("NIMC (National Identity Management Commission)",
     ["nimc.gov.ng"],
     ["nimc", "national identity management", "nin registration"]),

    # ── Nigerian Telecoms ──────────────────────────────────────────
    ("MTN Nigeria",
     ["mtn.ng", "mtnonline.com"],
     ["mtn nigeria", "mtn telecom"]),

    ("Airtel Nigeria",
     ["airtel.com.ng"],
     ["airtel nigeria", "airtel africa"]),

    ("Glo (Globacom Nigeria)",
     ["gloworld.com"],
     ["glo mobile", "globacom", "glo nigeria"]),

    ("9mobile Nigeria",
     ["9mobile.com.ng"],
     ["9mobile", "etisalat nigeria"]),

    # ── Nigerian Fintechs ──────────────────────────────────────────
    ("Paystack",
     ["paystack.com"],
     ["paystack payments"]),

    ("Flutterwave",
     ["flutterwave.com"],
     ["flutterwave payments", "rave by flutterwave"]),

    ("Interswitch",
     ["interswitchgroup.com", "quickteller.com"],
     ["interswitch", "quickteller", "verve card"]),

    ("Cowrywise",
     ["cowrywise.com"],
     ["cowrywise investments"]),

    ("PiggyVest",
     ["piggyvest.com"],
     ["piggyvest savings", "piggy bank"]),

    # ── Nigerian E-Commerce / Logistics ────────────────────────────
    ("Jumia Nigeria",
     ["jumia.com.ng"],
     ["jumia nigeria", "jumia delivery"]),

    ("Konga",
     ["konga.com"],
     ["konga nigeria", "konga delivery"]),

    # ── Nigerian Energy ────────────────────────────────────────────
    ("Dangote Group",
     ["dangote.com"],
     ["dangote cement", "dangote refinery", "alhaji dangote"]),

    # ── International — Delivery / Logistics ──────────────────────
    ("DHL",
     ["dhl.com", "dhl.com.ng"],
     ["dhl express", "dhl courier", "dhl delivery"]),

    ("FedEx",
     ["fedex.com"],
     ["fedex express", "fedex delivery", "federal express"]),

    ("UPS",
     ["ups.com"],
     ["united parcel service", "ups delivery"]),

    ("NIPOST (Nigeria Postal Service)",
     ["nipost.gov.ng"],
     ["nipost", "nigeria postal service", "nigerian post"]),

    # ── International — Tech ──────────────────────────────────────
    ("Google",
     ["google.com", "googleapis.com"],
     ["google inc", "google llc", "alphabet"]),

    ("Apple",
     ["apple.com"],
     ["apple inc", "apple store", "icloud", "itunes"]),

    ("Microsoft",
     ["microsoft.com", "outlook.com", "live.com"],
     ["microsoft corporation", "office 365", "windows support"]),

    ("Meta (Facebook / WhatsApp / Instagram)",
     ["facebook.com", "meta.com", "whatsapp.com", "instagram.com"],
     ["facebook inc", "meta platforms", "whatsapp support", "instagram support"]),

    ("Amazon",
     ["amazon.com", "amazon.co.uk"],
     ["amazon inc", "amazon delivery", "amazon prime", "aws"]),

    ("Netflix",
     ["netflix.com"],
     ["netflix streaming", "netflix support"]),

    ("PayPal",
     ["paypal.com"],
     ["paypal holdings", "paypal payment"]),

    ("Binance",
     ["binance.com"],
     ["binance exchange", "binance nigeria"]),

    # ── Banks (International commonly impersonated) ───────────────
    ("Citibank",
     ["citibank.com", "citi.com"],
     ["citibank international", "citi bank"]),

    ("HSBC",
     ["hsbc.com"],
     ["hsbc bank", "hsbc holdings"]),

    ("Barclays",
     ["barclays.com"],
     ["barclays bank", "barclays plc"]),
]


def _build_lookup():
    lookup = {}
    for name, domains, aliases in VERIFIED_BUSINESSES:
        for d in domains:
            lookup[d.lower()] = name
        for a in aliases:
            lookup[a.lower()] = name
    return lookup


_LOOKUP = _build_lookup()


def _extract_domain(text: str) -> str | None:
    """Pull the bare domain from a URL or domain string."""
    text = text.strip().lower()
    text = re.sub(r'^https?://', '', text)
    text = text.split('/')[0].split('?')[0].split('#')[0]
    # Strip www.
    text = re.sub(r'^www\.', '', text)
    return text if '.' in text else None


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _find_impersonation(query: str, domain: str | None):
    """
    Returns (suspected_company, confidence) if the input looks like
    it's impersonating a known business.
    """
    query_lower = query.lower()
    best_match  = None
    best_score  = 0.0

    for name, official_domains, aliases in VERIFIED_BUSINESSES:
        # Exact alias match
        for alias in aliases:
            if alias in query_lower:
                # Check if official domain is present → legit
                if domain and any(domain == d or domain.endswith('.' + d) for d in official_domains):
                    return None, 1.0   # legitimate
                return name, 0.92

        # Fuzzy domain match — is a domain very similar to an official one?
        if domain:
            for od in official_domains:
                score = _similarity(domain, od)
                if 0.7 < score < 1.0 and score > best_score:
                    best_match = name
                    best_score = score

        # Typosquatting patterns: official domain keyword inside sketchy domain
        if domain:
            for od in official_domains:
                base = od.split('.')[0]   # e.g. "gtbank" from "gtbank.com"
                if base in domain and domain != od:
                    # Domain contains brand name but isn't the official domain
                    return name, 0.95

    if best_match:
        return best_match, round(best_score, 2)
    return None, 0.0


def _check_query(text: str) -> dict:
    """Core business check logic. Returns a structured verdict."""
    text   = text.strip()
    domain = _extract_domain(text)

    # 1 — Is the query or domain directly in our lookup?
    if domain and domain in _LOOKUP:
        return {
            "verdict":   "verified",
            "company":   _LOOKUP[domain],
            "message":   f"✅ This is the official domain for {_LOOKUP[domain]}.",
            "score":     100,
            "tips":      [],
        }

    # Check plain-text aliases
    text_lower = text.lower()
    for alias, company in _LOOKUP.items():
        if text_lower == alias:
            return {
                "verdict":   "verified",
                "company":   company,
                "message":   f"✅ '{text}' is a known alias for the verified company {company}.",
                "score":     95,
                "tips":      [],
            }

    # 2 — Check for impersonation
    suspected, confidence = _find_impersonation(text, domain)
    if suspected and confidence >= 0.85:
        return {
            "verdict":   "impersonation",
            "company":   suspected,
            "message":   f"🚨 This appears to be impersonating {suspected}. The official website and contact details are not from this source.",
            "score":     max(0, int((1 - confidence) * 100)),
            "tips": [
                f"The official {suspected} website does NOT match this source.",
                "Never send money, OTP, or personal details through unverified channels.",
                "Contact the real company directly using details from their official website.",
            ],
        }

    if suspected and confidence >= 0.65:
        return {
            "verdict":   "suspicious",
            "company":   suspected,
            "message":   f"⚠️ This may be impersonating {suspected}. Verify through official channels before proceeding.",
            "score":     40,
            "tips": [
                f"If this claims to be {suspected}, verify at their official website.",
                "Do not share personal or financial information without verification.",
            ],
        }

    # 3 — Not found
    return {
        "verdict":   "unknown",
        "company":   None,
        "message":   "❓ This business was not found in our verified database. Exercise caution.",
        "score":     50,
        "tips": [
            "Search for the company name independently to verify.",
            "Check official regulatory websites (CAC Nigeria for businesses).",
            "If they're asking for money or data, verify first.",
        ],
    }


@business_bp.route("/check", methods=["POST"])
@limiter.limit("30 per minute")
def check_business():
    data  = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"message": "Enter a company name, domain, or URL to check."}), 400
    if len(query) > 300:
        return jsonify({"message": "Query too long."}), 400

    result = _check_query(query)
    return jsonify(result), 200


@business_bp.route("/check/batch", methods=["POST"])
@limiter.limit("10 per minute")
def check_business_batch():
    """Check multiple names/domains at once (max 5)."""
    data    = request.get_json(silent=True) or {}
    queries = data.get("queries") or []
    if not isinstance(queries, list) or not queries:
        return jsonify({"message": "Provide a list of queries."}), 400
    queries = [str(q).strip() for q in queries[:5]]
    results = {q: _check_query(q) for q in queries}
    return jsonify({"results": results}), 200
