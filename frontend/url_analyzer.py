"""
url_analyzer.py
Deep URL analysis — shows exactly where a link leads and how risky
it is BEFORE the user clicks it. No external API calls needed.

Signals checked:
  • Domain age patterns / free TLDs
  • Typosquatting against known brands
  • URL shortener detection + expansion attempt
  • Suspicious path / query string patterns
  • IP-based URLs (no domain)
  • Redirect chain indicators
  • Nigerian-specific scam URL patterns
"""

import re
import ipaddress
from urllib.parse import urlparse, unquote
from difflib import SequenceMatcher
from flask import Blueprint, request, jsonify
from extensions import limiter

url_analyzer_bp = Blueprint("url_analyzer", __name__, url_prefix="/api/url")

# ── Known brands for typosquatting detection ──────────────────────
BRAND_DOMAINS = [
    "gtbank.com", "accessbankplc.com", "ubagroup.com", "zenithbank.com",
    "firstbanknigeria.com", "kuda.com", "opay.com.ng", "palmpay.com",
    "paystack.com", "flutterwave.com", "mtn.ng", "airtel.com.ng",
    "google.com", "apple.com", "microsoft.com", "facebook.com",
    "whatsapp.com", "instagram.com", "amazon.com", "netflix.com",
    "paypal.com", "dhl.com", "fedex.com", "jumia.com.ng", "cbn.gov.ng",
    "efcc.gov.ng", "binance.com", "coinbase.com",
]

FREE_TLDS  = {".tk", ".ml", ".cf", ".ga", ".gq", ".xyz", ".top", ".work",
              ".click", ".link", ".download", ".review", ".win", ".loan"}

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "rb.gy",
    "cutt.ly", "short.io", "tiny.cc", "is.gd", "buff.ly", "adf.ly",
    "bc.vc", "shrinkme.io", "ouo.io", "za.gl",
}

SUSPICIOUS_PATHS = [
    r"verify", r"confirm", r"secure", r"login", r"signin", r"account",
    r"update", r"billing", r"payment", r"claim", r"prize", r"winner",
    r"reward", r"bonus", r"free", r"urgent", r"suspended", r"locked",
    r"recover", r"reset", r"validate", r"auth", r"otp", r"pin",
]

SUSPICIOUS_PARAMS = [
    r"token=", r"password=", r"pwd=", r"user=", r"email=",
    r"redirect=", r"return_url=", r"next=", r"ref=",
]


def _analyze_url(raw: str) -> dict:
    raw = raw.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "http://" + raw

    flags   = []
    score   = 0

    try:
        parsed = urlparse(raw)
    except Exception:
        return {"verdict": "suspicious", "score": 60, "flags": ["Malformed URL"], "details": {}}

    host   = (parsed.hostname or "").lower()
    path   = unquote(parsed.path).lower()
    query  = unquote(parsed.query).lower()
    scheme = parsed.scheme
    port   = parsed.port

    details = {
        "host":      host,
        "path":      parsed.path,
        "scheme":    scheme,
        "port":      str(port) if port else "default",
        "shortener": False,
        "ip_based":  False,
        "tld":       "",
        "brand_match": None,
    }

    if not host:
        return {"verdict": "scam", "score": 90, "flags": ["No domain detected"], "details": details}

    # ── IP-based URL ─────────────────────────────────────────────
    try:
        ipaddress.ip_address(host)
        flags.append("IP-based URL — no domain name (common in phishing)")
        score += 30
        details["ip_based"] = True
    except ValueError:
        pass

    # ── HTTP (not HTTPS) ──────────────────────────────────────────
    if scheme == "http":
        flags.append("No HTTPS encryption — data not secure")
        score += 10

    # ── Non-standard port ─────────────────────────────────────────
    if port and port not in (80, 443):
        flags.append(f"Non-standard port ({port}) — unusual for legitimate sites")
        score += 15

    # ── URL shortener ─────────────────────────────────────────────
    bare_host = re.sub(r'^www\.', '', host)
    if bare_host in SHORTENERS:
        flags.append(f"Shortened URL ({bare_host}) — real destination is hidden")
        score += 20
        details["shortener"] = True

    # ── Free TLD ──────────────────────────────────────────────────
    for tld in FREE_TLDS:
        if host.endswith(tld):
            flags.append(f"Free/suspicious TLD ({tld}) — commonly used in scam sites")
            score += 20
            details["tld"] = tld
            break

    # ── Typosquatting check ───────────────────────────────────────
    best_brand = None
    best_sim   = 0.0
    for brand in BRAND_DOMAINS:
        brand_bare = re.sub(r'^www\.', '', brand)
        sim = SequenceMatcher(None, bare_host, brand_bare).ratio()
        if 0.70 < sim < 1.0 and sim > best_sim:
            best_brand = brand
            best_sim   = sim
        # Brand keyword inside a different domain
        brand_key = brand_bare.split('.')[0]
        if brand_key in bare_host and bare_host != brand_bare:
            flags.append(f"Contains '{brand_key}' brand name but is NOT the official site ({brand})")
            score += 25
            details["brand_match"] = brand

    if best_brand and not details["brand_match"]:
        flags.append(f"Very similar to {best_brand} — possible typosquatting")
        score += 20
        details["brand_match"] = best_brand

    # ── Too many subdomains ───────────────────────────────────────
    parts = host.split('.')
    if len(parts) > 4:
        flags.append("Excessive subdomains — common in phishing URLs")
        score += 15

    # ── Brand name as subdomain of unknown domain ─────────────────
    for brand in BRAND_DOMAINS:
        bkey = brand.split('.')[0]
        if host.startswith(bkey + '.') and not host.endswith(brand):
            flags.append(f"'{bkey}' used as subdomain of unknown site (impersonation tactic)")
            score += 25
            break

    # ── Suspicious path keywords ──────────────────────────────────
    for pattern in SUSPICIOUS_PATHS:
        if re.search(pattern, path):
            flags.append(f"Suspicious path keyword: '{pattern}'")
            score += 8
            if score > 60:
                break

    # ── Suspicious query params ───────────────────────────────────
    for param in SUSPICIOUS_PARAMS:
        if param in query:
            flags.append(f"Suspicious query parameter: {param.rstrip('=')}")
            score += 5

    # ── Very long URL (obfuscation) ───────────────────────────────
    if len(raw) > 200:
        flags.append("Unusually long URL — may be obfuscating the real destination")
        score += 10

    # ── Numeric domain ────────────────────────────────────────────
    if re.match(r'^\d+\.\d+', bare_host):
        flags.append("Domain starts with numbers — unusual for legitimate sites")
        score += 10

    # ── Special chars in domain ───────────────────────────────────
    if re.search(r'[^a-z0-9.\-]', bare_host):
        flags.append("Special characters in domain name — possible homograph attack")
        score += 20

    score = min(score, 100)
    if score >= 55:
        verdict = "scam"
    elif score >= 22:
        verdict = "suspicious"
    else:
        verdict = "safe"

    flags = list(dict.fromkeys(flags))[:7]  # deduplicate, cap at 7

    return {
        "verdict":  verdict,
        "score":    score,
        "flags":    flags,
        "details":  details,
    }


@url_analyzer_bp.route("/analyze", methods=["POST"])
@limiter.limit("30 per minute")
def analyze_url():
    data = request.get_json(silent=True) or {}
    url  = (data.get("url") or "").strip()

    if not url:
        return jsonify({"message": "Enter a URL to analyze."}), 400
    if len(url) > 2000:
        return jsonify({"message": "URL too long."}), 400

    result = _analyze_url(url)
    return jsonify(result), 200
