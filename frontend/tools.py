import re, ipaddress
from difflib import SequenceMatcher
from urllib.parse import urlparse, unquote
from flask import Blueprint, request, jsonify
from extensions import limiter

tools_bp = Blueprint("tools", __name__, url_prefix="/api")

VERIFIED_BUSINESSES = [
    ("GTBank",             ["gtbank.com","gtco.com"],                  ["guaranty trust","gtb","gtbank"]),
    ("Access Bank",        ["accessbankplc.com"],                      ["access bank","accessbank"]),
    ("UBA",                ["ubagroup.com"],                           ["united bank for africa","uba bank"]),
    ("Zenith Bank",        ["zenithbank.com"],                         ["zenith bank"]),
    ("First Bank Nigeria", ["firstbanknigeria.com"],                   ["first bank","fbn"]),
    ("Fidelity Bank",      ["fidelitybank.ng"],                        ["fidelity bank"]),
    ("Stanbic IBTC",       ["stanbicibtc.com"],                        ["stanbic","ibtc"]),
    ("Kuda Bank",          ["kuda.com"],                               ["kuda bank"]),
    ("Opay",               ["opay.com.ng"],                            ["opay","o-pay"]),
    ("Palmpay",            ["palmpay.com"],                            ["palmpay","palm pay"]),
    ("CBN",                ["cbn.gov.ng"],                             ["central bank of nigeria","cbn nigeria"]),
    ("EFCC",               ["efcc.gov.ng"],                            ["efcc","economic and financial crimes"]),
    ("NAFDAC",             ["nafdac.gov.ng"],                          ["nafdac"]),
    ("FIRS",               ["firs.gov.ng"],                            ["firs","federal inland revenue"]),
    ("INEC",               ["inec.gov.ng"],                            ["inec","electoral commission"]),
    ("NIMC",               ["nimc.gov.ng"],                            ["nimc","nin registration"]),
    ("NCC",                ["ncc.gov.ng"],                             ["nigerian communications commission"]),
    ("MTN Nigeria",        ["mtn.ng","mtnonline.com"],                 ["mtn nigeria","mtn telecom"]),
    ("Airtel Nigeria",     ["airtel.com.ng"],                          ["airtel nigeria"]),
    ("Glo",                ["gloworld.com"],                           ["glo mobile","globacom"]),
    ("9mobile",            ["9mobile.com.ng"],                         ["9mobile","etisalat nigeria"]),
    ("Paystack",           ["paystack.com"],                           ["paystack payments"]),
    ("Flutterwave",        ["flutterwave.com"],                        ["flutterwave","rave"]),
    ("Interswitch",        ["interswitchgroup.com","quickteller.com"], ["interswitch","quickteller","verve"]),
    ("PiggyVest",          ["piggyvest.com"],                          ["piggyvest","piggy bank"]),
    ("Cowrywise",          ["cowrywise.com"],                          ["cowrywise"]),
    ("Jumia Nigeria",      ["jumia.com.ng"],                           ["jumia nigeria","jumia delivery"]),
    ("Konga",              ["konga.com"],                              ["konga nigeria"]),
    ("DHL",                ["dhl.com","dhl.com.ng"],                   ["dhl express","dhl courier","dhl delivery"]),
    ("FedEx",              ["fedex.com"],                              ["fedex express","federal express"]),
    ("UPS",                ["ups.com"],                                ["united parcel service","ups delivery"]),
    ("NIPOST",             ["nipost.gov.ng"],                          ["nipost","nigeria postal service"]),
    ("Google",             ["google.com","googleapis.com"],            ["google inc","google llc","alphabet"]),
    ("Apple",              ["apple.com"],                              ["apple inc","icloud","itunes"]),
    ("Microsoft",          ["microsoft.com","outlook.com","live.com"], ["microsoft corporation","office 365"]),
    ("Meta",               ["facebook.com","meta.com","whatsapp.com","instagram.com"], ["facebook","whatsapp","instagram"]),
    ("Amazon",             ["amazon.com","amazon.co.uk"],              ["amazon inc","amazon prime","aws"]),
    ("Netflix",            ["netflix.com"],                            ["netflix streaming"]),
    ("PayPal",             ["paypal.com"],                             ["paypal holdings"]),
    ("Binance",            ["binance.com"],                            ["binance exchange","binance nigeria"]),
]

_LOOKUP = {}
for _name, _domains, _aliases in VERIFIED_BUSINESSES:
    for _d in _domains: _LOOKUP[_d.lower()] = _name
    for _a in _aliases: _LOOKUP[_a.lower()] = _name


def _extract_domain(text):
    text = re.sub(r'^https?://', '', text.strip().lower())
    text = text.split('/')[0].split('?')[0].split('#')[0]
    return re.sub(r'^www\.', '', text) if '.' in text else None


def _check_business(query):
    query  = query.strip()
    domain = _extract_domain(query)
    ql     = query.lower()

    if domain and domain in _LOOKUP:
        return {"verdict":"verified","company":_LOOKUP[domain],"message":f"✅ Official domain for {_LOOKUP[domain]}.","score":100,"tips":[]}
    for alias, company in _LOOKUP.items():
        if ql == alias:
            return {"verdict":"verified","company":company,"message":f"✅ '{query}' is a verified alias for {company}.","score":95,"tips":[]}

    best_name, best_conf = None, 0.0
    for name, domains, aliases in VERIFIED_BUSINESSES:
        for alias in aliases:
            if alias in ql:
                if domain and any(domain==d or domain.endswith('.'+d) for d in domains):
                    return {"verdict":"verified","company":name,"message":f"✅ This is a verified {name} channel.","score":100,"tips":[]}
                return {"verdict":"impersonation","company":name,"message":f"🚨 Impersonating {name}. The official website does NOT match this source.","score":10,"tips":[f"The real {name} site is {domains[0]}.","Never share OTP, PIN, or personal data through unverified channels."]}
        if domain:
            for od in domains:
                bare = re.sub(r'^www\.', '', od)
                sim = SequenceMatcher(None, domain, bare).ratio()
                if 0.70 < sim < 1.0 and sim > best_conf:
                    best_name, best_conf = name, sim
                key = bare.split('.')[0]
                if key in domain and domain != bare:
                    return {"verdict":"impersonation","company":name,"message":f"🚨 Contains '{key}' but is NOT the official {name} site ({od}).","score":8,"tips":[f"Official {name}: {od}","Do not enter any personal or financial information."]}

    if best_name:
        return {"verdict":"suspicious","company":best_name,"message":f"⚠️ Looks similar to {best_name}. Verify before proceeding.","score":40,"tips":[f"Official {best_name} site: check via a search engine.","Do not share sensitive data without verifying."]}
    return {"verdict":"unknown","company":None,"message":"❓ Not found in our verified database. Exercise caution.","score":50,"tips":["Search independently to verify.","Check CAC Nigeria for registered businesses."]}


@tools_bp.route("/business/check", methods=["POST"])
@limiter.limit("30 per minute")
def check_business():
    data  = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query: return jsonify({"message":"Enter a company name, domain, or URL."}), 400
    if len(query)>300: return jsonify({"message":"Query too long."}), 400
    return jsonify(_check_business(query)), 200


BRAND_DOMAINS = [d for _,domains,_ in VERIFIED_BUSINESSES for d in domains]
FREE_TLDS  = {".tk",".ml",".cf",".ga",".gq",".xyz",".top",".work",".click",".link",".download",".review",".win",".loan"}
SHORTENERS = {"bit.ly","tinyurl.com","t.co","goo.gl","ow.ly","rb.gy","cutt.ly","short.io","tiny.cc","is.gd","buff.ly","adf.ly","bc.vc","ouo.io","za.gl"}
SUSPICIOUS_PATHS  = ["verify","confirm","secure","login","signin","account","update","billing","payment","claim","prize","winner","reward","bonus","free","urgent","suspended","locked","recover","reset","validate","auth","otp","pin"]
SUSPICIOUS_PARAMS = ["token=","password=","pwd=","user=","email=","redirect=","return_url=","next=","ref="]


def _analyze_url(raw):
    raw = raw.strip()
    if not raw.startswith(("http://","https://")): raw = "http://" + raw
    flags, score = [], 0
    try:
        p = urlparse(raw)
    except Exception:
        return {"verdict":"suspicious","score":60,"flags":["Malformed URL"],"details":{}}

    host   = (p.hostname or "").lower()
    path   = unquote(p.path).lower()
    query  = unquote(p.query).lower()
    scheme = p.scheme
    port   = p.port
    bare   = re.sub(r'^www\.', '', host)
    details = {"host":host,"path":p.path,"scheme":scheme,"port":str(port) if port else "default","shortener":False,"ip_based":False,"tld":"","brand_match":None}

    if not host:
        return {"verdict":"scam","score":90,"flags":["No domain detected"],"details":details}

    try:
        ipaddress.ip_address(host)
        flags.append("IP-based URL — no domain name (common in phishing)"); score+=30; details["ip_based"]=True
    except ValueError:
        pass

    if scheme == "http": flags.append("No HTTPS encryption"); score+=10
    if port and port not in (80,443): flags.append(f"Non-standard port ({port})"); score+=15
    if bare in SHORTENERS:
        flags.append(f"Shortened URL ({bare}) — real destination hidden"); score+=20; details["shortener"]=True
    for tld in FREE_TLDS:
        if host.endswith(tld):
            flags.append(f"Free/suspicious TLD ({tld})"); score+=20; details["tld"]=tld; break
    for bd in BRAND_DOMAINS:
        b = re.sub(r'^www\.', '', bd)
        sim = SequenceMatcher(None, bare, b).ratio()
        if 0.70 < sim < 1.0 and not details["brand_match"]:
            flags.append(f"Very similar to {bd} — possible typosquatting"); score+=20; details["brand_match"]=bd
        key = b.split('.')[0]
        if key in bare and bare != b and not details["brand_match"]:
            flags.append(f"Contains '{key}' brand name but is not {bd}"); score+=25; details["brand_match"]=bd
    if len(host.split('.')) > 4: flags.append("Excessive subdomains — common in phishing"); score+=15
    for pat in SUSPICIOUS_PATHS:
        if pat in path: flags.append(f"Suspicious path: '{pat}'"); score+=8
        if score > 65: break
    for par in SUSPICIOUS_PARAMS:
        if par in query: flags.append(f"Suspicious param: {par.rstrip('=')}"); score+=5
    if len(raw) > 200: flags.append("Unusually long URL — may be obfuscating destination"); score+=10
    if re.search(r'[^a-z0-9.\-]', bare): flags.append("Special characters in domain name"); score+=20

    score   = min(score, 100)
    verdict = "scam" if score >= 55 else ("suspicious" if score >= 22 else "safe")
    return {"verdict":verdict,"score":score,"flags":list(dict.fromkeys(flags))[:7],"details":details}


@tools_bp.route("/url/analyze", methods=["POST"])
@limiter.limit("30 per minute")
def analyze_url():
    data = request.get_json(silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url: return jsonify({"message":"Enter a URL to analyze."}), 400
    if len(url) > 2000: return jsonify({"message":"URL too long."}), 400
    return jsonify(_analyze_url(url)), 200