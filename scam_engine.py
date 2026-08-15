"""
scam_engine.py

Category-based scam detection engine. Every message is scored by WHAT
KIND of red flags it contains — payment requests, credential requests,
structural anomalies, narrative patterns, domain impersonation, and
urgency — not by counting generic keyword matches. This means calmly
worded, modern scam messages (no "act now" language) still get caught.

Every scan produces a plain-language explanation that QUOTES the exact
text the user pasted for each red flag found, e.g.:
  "Your message includes 'bit.ly' — uses a shortened link that hides
   where it actually leads."
"""

import re
from difflib import SequenceMatcher

# ──────────────────────────────────────────────────────────────
# KNOWN BRAND DOMAINS — mirrors tools.py's VERIFIED_BUSINESSES
# ──────────────────────────────────────────────────────────────
KNOWN_DOMAINS = [
    "microsoft.com", "outlook.com", "live.com", "office.com",
    "google.com", "gmail.com", "apple.com", "icloud.com",
    "amazon.com", "netflix.com", "paypal.com", "facebook.com",
    "whatsapp.com", "instagram.com", "binance.com", "coinbase.com",
    "gtbank.com", "accessbankplc.com", "ubagroup.com", "zenithbank.com",
    "firstbanknigeria.com", "kuda.com", "opay.com.ng", "palmpay.com",
    "paystack.com", "flutterwave.com", "dhl.com", "fedex.com", "ups.com",
    "cbn.gov.ng", "efcc.gov.ng", "nafdac.gov.ng", "firs.gov.ng",
]

BRAND_KEYWORDS = {
    "microsoft": "microsoft.com", "outlook": "outlook.com", "office365": "office.com",
    "google": "google.com", "gmail": "gmail.com", "apple": "apple.com", "icloud": "icloud.com",
    "amazon": "amazon.com", "netflix": "netflix.com", "paypal": "paypal.com",
    "facebook": "facebook.com", "whatsapp": "whatsapp.com", "instagram": "instagram.com",
    "binance": "binance.com", "coinbase": "coinbase.com",
    "gtbank": "gtbank.com", "gtb": "gtbank.com", "access bank": "accessbankplc.com",
    "uba": "ubagroup.com", "zenith": "zenithbank.com", "kuda": "kuda.com",
    "opay": "opay.com.ng", "palmpay": "palmpay.com", "paystack": "paystack.com",
    "flutterwave": "flutterwave.com", "dhl": "dhl.com", "fedex": "fedex.com", "ups": "ups.com",
    "cbn": "cbn.gov.ng", "efcc": "efcc.gov.ng", "nafdac": "nafdac.gov.ng", "firs": "firs.gov.ng",
}


def _extract_emails_and_domains(text):
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', text)
    urls   = re.findall(r'https?://([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', text)
    return list(set(emails + urls))


def _check_domain_impersonation(text):
    """Category 1: Sender/domain impersonation — catches misspelled
    brand domains (microsaft.com) even with zero urgency language."""
    domains = _extract_emails_and_domains(text)
    lowered = text.lower()
    hits = []

    for domain in domains:
        bare = re.sub(r'^www\.', '', domain.lower())
        for real_domain in KNOWN_DOMAINS:
            if bare == real_domain:
                continue
            sim = SequenceMatcher(None, bare, real_domain).ratio()
            if 0.82 < sim < 1.0 and abs(len(bare) - len(real_domain)) <= 2:
                hits.append((bare, real_domain, 35,
                    f"the domain '{bare}' is a near-identical misspelling of the real "
                    f"'{real_domain}' — a classic impersonation trick"))

    for keyword, real_domain in BRAND_KEYWORDS.items():
        if keyword in lowered:
            for domain in domains:
                bare = re.sub(r'^www\.', '', domain.lower())
                if bare != real_domain and keyword.replace(" ", "") not in bare.replace("-", ""):
                    sim = SequenceMatcher(None, bare, real_domain).ratio()
                    if sim < 0.6:
                        hits.append((bare, real_domain, 30,
                            f"the message mentions '{keyword.title()}' but the sender's domain "
                            f"'{bare}' has no relation to the real '{real_domain}' domain"))
    return hits


# ──────────────────────────────────────────────────────────────
# CATEGORY 2 — Payment / financial requests (tone-independent)
# ──────────────────────────────────────────────────────────────
PAYMENT_PATTERNS = [
    (r"\b(kindly|please|would you|could you)\s+(send|forward|wire|transfer)\b", 22,
     "asks you to send or transfer money, even though it's phrased politely"),
    (r"\bwire\s+transfer\b", 24, "requests a wire transfer — a common irreversible payment scammers prefer"),
    (r"\bgift\s+card(s)?\b", 26, "asks for payment via gift cards — legitimate organizations never do this"),
    (r"\b(bitcoin|crypto|usdt|ethereum|btc)\b.{0,40}\b(send|pay|transfer|deposit)\b", 24,
     "requests payment in cryptocurrency, which is difficult to trace or reverse"),
    (r"\b(processing|clearance|handling|customs|transfer|admin(istrative)?|registration|onboarding|activation|release)\s+fee\b", 22,
     "asks for an upfront 'fee' before releasing money, a job, or goods — a hallmark of advance-fee fraud"),
    (r"\bsmall\s+(fee|deposit|payment|charge)\b", 18,
     "downplays a payment as 'small', a softening tactic that makes a fee request feel less alarming"),
    (r"\bsend\s+(money|cash|funds?)\b", 18, "directly requests you send money"),
    (r"\binvestment\b.{0,30}\b(guarantee|guaranteed|risk-free|double|triple)\b", 26,
     "promises guaranteed or risk-free investment returns, which don't exist in real investing"),
    (r"\b\d{2,4}%\s*(return|profit|yield|interest)\b", 22,
     "promises an unrealistic percentage return that no legitimate investment offers"),
    (r"\b(steady|consistent|reliable)\s+(monthly|weekly|daily)?\s*(returns?|profit|income|yield)\b", 22,
     "promises steady or consistent investment returns — real investments always carry risk, so this framing is a red flag"),
    (r"\brepresent\b.{0,20}\binvestment\s+firm\b", 10,
     "opens by presenting an investment opportunity through an unsolicited introduction"),
    (r"\bwalk\s+you\s+through\s+how\s+it\s+works\b", 10,
     "offers to explain an investment opportunity personally, a common soft opener before an ask"),
]

# ──────────────────────────────────────────────────────────────
# CATEGORY 3 — Credential / personal data requests
# ──────────────────────────────────────────────────────────────
CREDENTIAL_PATTERNS = [
    (r"\b(otp|one[\s-]time\s+password)\b", 28, "asks for your OTP — no legitimate company ever needs this"),
    (r"\bpin\b", 22, "asks for your PIN number"),
    (r"\bpassword\b", 20, "asks you to share or confirm your password"),
    (r"\bcvv\b", 26, "asks for your card's CVV security code"),
    (r"\b(bvn|bank verification number)\b", 26, "asks for your BVN, a sensitive banking identifier"),
    (r"\b(ssn|social security number)\b", 26, "asks for a Social Security Number"),
    (r"\b(date of birth|dob)\b.{0,30}\b(confirm|verify|provide|send)\b", 16,
     "asks you to confirm personal identifying information"),
    (r"\bverify\s+your\s+(account|identity)\b", 18,
     "asks you to 'verify' your account — a common phishing setup phrase"),
    (r"\b(unusual|suspicious|irregular)\s+activity\b", 16,
     "claims 'unusual activity' on your account, a standard phishing opener even without asking for anything yet"),
    (r"\bconfirm\s+your\s+details\b", 18,
     "asks you to 'confirm your details' — vague phrasing designed to sound routine while extracting personal information"),
    (r"\bclick\s+the\s+link\s+below\b|\blink\s+below\b", 12,
     "directs you to a link without naming the destination, a common phishing setup"),
    (r"\bwhen\s+you\s+get\s+a\s+chance\b|\bwhenever\s+you're\s+free\b", 8,
     "uses deliberately relaxed, low-pressure phrasing — a technique to seem more trustworthy than urgent scam messages"),
]

# ──────────────────────────────────────────────────────────────
# CATEGORY 4 — Structural red flags
# ──────────────────────────────────────────────────────────────
STRUCTURAL_PATTERNS = [
    (r"\bdear\s+(customer|sir|madam|user|valued\s+customer|account\s+holder)\b", 14,
     "uses a generic greeting instead of your actual name, suggesting a mass-sent message"),
    (r"\b(bit\.ly|tinyurl\.com|t\.co|goo\.gl|rb\.gy|cutt\.ly|ow\.ly)\b", 20,
     "uses a shortened link that hides where it actually leads"),
    (r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", 24,
     "links to a raw numeric IP address instead of a proper domain name — very unusual for legitimate sites"),
    (r"https?://[^\s]*\.(tk|ml|cf|ga|gq)\b", 20,
     "uses a free, throwaway domain extension commonly abused for scam sites"),
]

# ──────────────────────────────────────────────────────────────
# CATEGORY 5 — Narrative patterns (recognizable scam "stories")
# ──────────────────────────────────────────────────────────────
NARRATIVE_PATTERNS = [
    (r"\b(unclaimed|inherit(ance)?|deceased|next of kin|beneficiary)\b.{0,60}\b(fund|money|million|estate)\b", 32,
     "follows the classic 'unclaimed inheritance' scam narrative used to build false trust before requesting money"),
    (r"\bbarrister\b", 20,
     "claims to be a 'barrister' handling an estate — a very common opening line in inheritance scams"),
    (r"\b(same|shared)\s+surname\b|\bmay\s+be\s+related\b|\bentitled\s+to\s+(his|her|their)\s+estate\b", 22,
     "suggests you might be related to a stranger's estate through a shared surname — a manufactured connection used to justify contacting you"),
    (r"\b(widow|orphan)\b.{0,50}\b(million|fund|transfer|inherit)\b", 30,
     "uses an emotional personal story (widow/orphan) combined with a large sum of money — a well-known scam script"),
    (r"\bwork(ing)?\s+(overseas|abroad|offshore|on\s+an?\s+oil\s+rig|on\s+a\s+ship)\b", 16,
     "describes working in an isolated overseas location — a common early setup in romance scams to explain future unavailability"),
    (r"\bgets?\s+lonely\b|\blonely\s+(out\s+)?here\b", 14,
     "opens with language about loneliness, a common romance-scam icebreaker before any request is made"),
    (r"\b(romance|soulmate|met\s+online|dating)\b.{0,60}\b(money|send|help|emergency)\b", 26,
     "combines a romantic relationship narrative with a request for money, a hallmark of romance scams"),
    (r"\b(customs|shipment|package|parcel)\b.{0,50}\b(fee|held|release|clear)\b", 26,
     "claims a package is held at customs and requires a fee to release — a common delivery scam"),
    (r"\b(job\s+offer|hiring|work\s+from\s+home|remote\s+position|interest\s+in\s+the\s+position)\b", 8,
     "mentions a remote job, hiring process, or work-from-home opportunity"),
    (r"\bbackground\s+verification\b", 10,
     "mentions a 'background verification' step as part of a hiring process"),
    (r"\bweekly\b.{0,20}\$\d{2,5}\b|\$\d{2,5}\b.{0,20}\bweekly\b", 14,
     "advertises an unusually high, vaguely-specific weekly pay rate typical of job scam bait"),
    (r"\b(loan|lender|credit)\b.{0,40}\b(guaranteed|no\s+credit\s+check|instant\s+approval)\b", 20,
     "promises a guaranteed loan with no credit check, a common tactic in loan scams"),
    (r"\byou\s+(have\s+)?(been\s+)?(selected|chosen|won)\b", 20,
     "claims you were specially selected or have won something you never entered"),
    (r"\baccount\s+(will\s+be\s+|has\s+been\s+)?(suspend|clos|delet|terminat|lock)", 20,
     "threatens that your account will be suspended or closed unless you act"),
    (r"\b(bank\s+alert|credit\s+alert|debit\s+alert)\b.{0,60}\b(click|link|verify|confirm)\b", 26,
     "mimics a bank SMS alert format but asks you to click a link — real bank alerts never include action links"),
    (r"\b(pos|point\s+of\s+sale)\b.{0,40}\b(fee|charge|reversal|refund)\b", 20,
     "references a POS transaction fee, charge, or reversal — a pattern used in fake bank/agent scam messages common in Nigeria"),
    (r"\b(airdrop|giveaway)\b.{0,50}\b(wallet|claim|connect|send)\b", 30,
     "promises a crypto airdrop or giveaway requiring you to connect a wallet or send funds first — a common crypto scam pattern"),
    (r"\bnin\b.{0,30}\b(suspend|block|verify|update|link)\b|\bsim\s+(swap|block)\b", 22,
     "threatens NIN or SIM-related suspension, a scam pattern that impersonates telecom or government identity verification"),
    (r"\bwhatsapp\b.{0,40}\b(job|hiring|task|earn)\b.{0,40}\b(daily|per\s+task)\b", 28,
     "advertises paid WhatsApp 'tasks' with daily earnings — a fast-growing scam format that pays small amounts to build trust before requesting a deposit"),
    (r"\b(voice\s+note|voice\s+message)\b.{0,50}\b(emergency|urgent|help|stranded)\b", 18,
     "references an urgent voice message asking for help — increasingly used with AI-cloned voices to impersonate a relative in distress"),
    (r"\b(stranded|stuck)\b.{0,40}\b(send|help|money|transfer)\b", 20,
     "claims someone is stranded and needs money sent urgently — a common impersonation scam targeting family members"),
    (r"\bcac\b.{0,30}\b(verify|registration|renew|suspend)\b", 18,
     "references CAC (Corporate Affairs Commission) registration status — used in scams targeting small business owners"),
    (r"\b(refund|reversal)\b.{0,40}\b(pending|approved|process)\b.{0,40}\b(confirm|verify|click)\b", 20,
     "claims a refund or reversal is pending and asks you to confirm or click a link — a common fake-refund phishing pattern"),
]

# ──────────────────────────────────────────────────────────────
# CATEGORY 6 — Urgency / pressure (supporting signal, kept low-weight
# by design since modern scammers often avoid this language entirely)
# ──────────────────────────────────────────────────────────────
URGENCY_PATTERNS = [
    (r"\bact\s+now\b", 10, "uses an urgent call to action"),
    (r"\blimited\s+time\b", 8, "creates artificial time pressure"),
    (r"\bexpires?\s+(today|soon|in \d+)", 8, "claims an offer expires imminently"),
    (r"\b(last|final)\s+(chance|warning)\b", 12, "uses final-warning language to pressure quick action"),
    (r"\bwithin\s+\d+\s*(hours?|minutes?)\b", 10, "gives an unusually short deadline"),
    (r"\bimmediate(ly)?\b", 8, "demands immediate action"),
]

SAFE_INDICATORS = [
    r"\b(schedule|meeting|tomorrow|calendar|lunch|catch up)\b",
    r"\b(regards|sincerely|best|thanks|thank you)\b\s*,?\s*$",
    r"\b(invoice|attached|please\s+find)\b.{0,30}\b(report|document|file)\b",
]


def _plain_language_summary(hits, score, verdict):
    """Builds a human-readable explanation that quotes the actual
    text pasted by the user wherever possible."""
    if not hits:
        if verdict == "safe":
            return "This message doesn't show the patterns we associate with scams. It reads like ordinary correspondence."
        else:
            return "This message has some unusual characteristics, but nothing that clearly points to a scam. Stay cautious anyway."

    if verdict == "scam":
        intro = "This looks like a scam. Here's what stood out:"
    elif verdict == "suspicious":
        intro = "This message has some real warning signs worth taking seriously:"
    else:
        intro = "A few minor things stood out, though nothing alarming:"

    lines = [intro]
    for h in hits:
        reason = h["reason"][0].upper() + h["reason"][1:]
        quote = h.get("quote")
        if quote:
            lines.append(f'• Your message includes "{quote}" — {reason}.')
        else:
            lines.append(f"• {reason}.")

    return "\n".join(lines)


def analyze_content(text):
    """
    Main entry point. Returns:
    {
        "verdict": "scam" | "suspicious" | "safe",
        "score": 0-100,
        "flags": [short labels for UI badges],
        "explanation": "plain language paragraph citing actual matched text",
    }
    """
    lowered = text.lower()
    score = 0
    hits = []  # each: {"category", "weight", "reason", "quote"}

    def _quote_from_match(pattern, source_text):
        """Extract the actual matched snippet from the original
        (non-lowered) text so explanations can quote it exactly."""
        m = re.search(pattern, source_text, re.IGNORECASE)
        if not m:
            return None
        snippet = m.group(0).strip()
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        return snippet

    # Category 1 — domain impersonation
    for bare, real, weight, reason in _check_domain_impersonation(text):
        score += weight
        hits.append({"category": "impersonation", "weight": weight, "reason": reason, "quote": bare})

    # Category 2 — payment requests
    for pattern, weight, reason in PAYMENT_PATTERNS:
        if re.search(pattern, lowered):
            score += weight
            hits.append({"category": "payment", "weight": weight, "reason": reason,
                          "quote": _quote_from_match(pattern, text)})

    # Category 3 — credential requests
    for pattern, weight, reason in CREDENTIAL_PATTERNS:
        if re.search(pattern, lowered):
            score += weight
            hits.append({"category": "credentials", "weight": weight, "reason": reason,
                          "quote": _quote_from_match(pattern, text)})

    # Category 4 — structural red flags
    for pattern, weight, reason in STRUCTURAL_PATTERNS:
        if re.search(pattern, lowered):
            score += weight
            hits.append({"category": "structural", "weight": weight, "reason": reason,
                          "quote": _quote_from_match(pattern, text)})

    # Category 5 — narrative patterns
    for pattern, weight, reason in NARRATIVE_PATTERNS:
        if re.search(pattern, lowered):
            score += weight
            hits.append({"category": "narrative", "weight": weight, "reason": reason,
                          "quote": _quote_from_match(pattern, text)})

    # Category 6 — urgency/pressure (supporting signal, low weight)
    for pattern, weight, reason in URGENCY_PATTERNS:
        if re.search(pattern, lowered):
            score += weight
            hits.append({"category": "urgency", "weight": weight, "reason": reason,
                          "quote": _quote_from_match(pattern, text)})

    # Lightweight structural signals
    if text.count("!") >= 3:
        score += 6
        hits.append({"category": "urgency", "weight": 6, "quote": None,
                      "reason": "uses multiple exclamation marks, a common high-pressure tactic"})
    caps_words = re.findall(r"\b[A-Z]{4,}\b", text)
    if len(caps_words) >= 2:
        score += 6
        hits.append({"category": "urgency", "weight": 6, "quote": " ".join(caps_words[:3]),
                      "reason": "uses excessive capitalization for emphasis, a common scam-messaging pattern"})

    # Safe-content discount (reduces false positives on genuine correspondence)
    safe_hits = sum(1 for p in SAFE_INDICATORS if re.search(p, lowered))
    score = max(0, score - safe_hits * 6)

    # De-duplicate near-identical hits, cap for readability
    seen_reasons = set()
    unique_hits = []
    for h in sorted(hits, key=lambda x: -x["weight"]):
        key = h["reason"][:40]
        if key not in seen_reasons:
            seen_reasons.add(key)
            unique_hits.append(h)
    unique_hits = unique_hits[:6]

    score = min(score, 100)

    # Verdict is always mathematically derived from score — single source of truth
    if score >= 55:
        verdict = "scam"
    elif score >= 25:
        verdict = "suspicious"
    else:
        verdict = "safe"

    flags = [h["reason"] for h in unique_hits]
    explanation = _plain_language_summary(unique_hits, score, verdict)
    recommended_actions = _recommended_actions(unique_hits, verdict)

    return {
        "verdict": verdict,
        "score": score,
        "flags": flags,
        "explanation": explanation,
        "recommended_actions": recommended_actions,
    }


def _recommended_actions(hits, verdict):
    """
    Bitdefender Scamio-style actionable next steps — tells the user
    exactly what to DO, not just what was found. Tailored to the
    specific categories of red flags detected.
    """
    if verdict == "safe":
        return ["No action needed — this message doesn't show scam indicators."]

    categories_hit = {h["category"] for h in hits}
    actions = []

    if verdict == "scam":
        actions.append("Do not reply, click any links, or share any information.")
        actions.append("Block this sender/number immediately.")
    else:
        actions.append("Do not click any links or share personal information until you verify the sender independently.")

    if "credentials" in categories_hit:
        actions.append("Never share your OTP, PIN, or password with anyone — no legitimate company asks for these.")
    if "payment" in categories_hit:
        actions.append("Do not send money, gift cards, or crypto based on this message.")
    if "impersonation" in categories_hit:
        actions.append("Contact the real company directly using the number or email from their official website — not the one in this message.")
    if "narrative" in categories_hit:
        actions.append("Report this message using the Community Reports page to help protect others from the same pattern.")

    if verdict == "scam":
        actions.append("Consider reporting this to your bank (if financial) or local authorities.")

    seen = set()
    unique_actions = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            unique_actions.append(a)
    return unique_actions[:5]