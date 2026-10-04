"""
Real-Time Financial Anomaly & Counterparty Fraud Shield.
Société Générale Capital Markets & Post-Trade Operations Gateway.

Capabilities:
1. Off-market trade deviation detection (>3 sigma from historical counterparty notional mean).
2. SSI (Standard Settlement Instructions) anomaly & beneficiary fraud detection (BIC validation, offshore routing, account novelty).
3. Settlement cutoff countdown monitoring (<30 mins / <15 mins to TARGET2 / Euroclear / Fedwire / Clearstream cutoffs).
4. Multi-dimensional Anomaly Scoring (0.0 to 1.0) with granular risk explanation tags and escalation recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timezone
from typing import Any, Dict, List, Optional, Tuple
import logging
import math
import re

from backend.models.email_models import ClassifiedEmail, ExtractedEntities, Urgency, Intent

logger = logging.getLogger("mailmind.anomaly_detector")


# ── High-Risk & Offshore Secrecy Jurisdictions (FATF + Tax Haven Registry) ──
OFFSHORE_SECRECY_JURISDICTIONS = {
    "KY": "Cayman Islands",
    "VG": "British Virgin Islands",
    "PA": "Panama",
    "SC": "Seychelles",
    "BZ": "Belize",
    "BS": "Bahamas",
    "CY": "Cyprus",
    "MH": "Marshall Islands",
    "VU": "Vanuatu",
    "LR": "Liberia",
    "WS": "Samoa",
    "BM": "Bermuda",
    "CW": "Curaçao",
    "GI": "Gibraltar",
    "JE": "Jersey",
    "GG": "Guernsey",
    "IM": "Isle of Man",
    "MU": "Mauritius",
    "AE": "United Arab Emirates (Free Zones)",
    "KN": "Saint Kitts and Nevis",
}

# ── Market Cutoff Schedules (UTC Hours:Minutes) ─────────────────────────────
# TARGET2: 17:00 CET = 16:00 UTC (Winter) / 15:00 UTC (Summer) -> Normalised 16:00 UTC
# Euroclear / Clearstream: 18:00 CET = 17:00 UTC
# Fedwire (Funds): 18:30 EST = 23:30 UTC
# CHAPS (Sterling): 17:00 GMT = 17:00 UTC
# CREST (Securities): 16:30 GMT = 16:30 UTC
MARKET_CUTOFF_UTC: Dict[str, dtime] = {
    "TARGET2": dtime(16, 0),
    "EUROCLEAR": dtime(17, 0),
    "CLEARSTREAM": dtime(17, 0),
    "FEDWIRE": dtime(23, 30),
    "CHAPS": dtime(17, 0),
    "CREST": dtime(16, 30),
    "DEFAULT": dtime(16, 0),
}


@dataclass
class CounterpartyProfile:
    """Historical trading baseline and verified SSI profile for a counterparty."""
    counterparty_id: str
    name: str
    mean_notional: float
    std_dev_notional: float
    min_notional: float
    max_historical_notional: float
    sample_size: int
    primary_currency: str
    authorized_bics: List[str]
    authorized_accounts: List[str]
    domicile_country: str
    risk_rating: str = "A"


@dataclass
class AnomalyEvaluationResult:
    """Structured result of multi-dimensional financial anomaly evaluation."""
    is_anomaly: bool
    anomaly_score: float
    risk_category: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_tags: List[str]
    dimension_scores: Dict[str, float]
    explanations: List[str]
    notional_analysis: Dict[str, Any]
    ssi_analysis: Dict[str, Any]
    cutoff_analysis: Dict[str, Any]
    recommendation: str  # "AUTO_APPROVE", "ENHANCED_DUAL_CONTROL", "FREEZE_AND_ESCALATE_FRAUD_DESK", "SUPERVISOR_APPROVAL_REQUIRED"


class AnomalyDetector:
    """
    Enterprise-grade Real-Time Financial Anomaly & Counterparty Fraud Shield.
    Analyzes post-trade communications for:
      - Statistical deviations in trade size (Z-Score > 3.0)
      - Fraudulent SSI alterations (unrecognized BICs, offshore routing, account hijacking)
      - Settlement deadline countdown breaches (<30m / <15m)
    """

    def __init__(self, custom_profiles: Optional[Dict[str, CounterpartyProfile]] = None):
        self.profiles: Dict[str, CounterpartyProfile] = self._init_default_profiles()
        if custom_profiles:
            self.profiles.update(custom_profiles)

    def _init_default_profiles(self) -> Dict[str, CounterpartyProfile]:
        """Initializes institutional historical profiles for major tier-1 counterparties."""
        return {
            "JPMORGAN": CounterpartyProfile(
                counterparty_id="JPMORGAN",
                name="JPMorgan Chase Bank, N.A.",
                mean_notional=2_500_000.0,
                std_dev_notional=750_000.0,
                min_notional=100_000.0,
                max_historical_notional=6_000_000.0,
                sample_size=1420,
                primary_currency="USD",
                authorized_bics=["CHASUS33", "CHASUS33XXX", "CHASGB2L", "CHASGB2LXXX", "CHASDEFF"],
                authorized_accounts=["4009210088", "1002938841", "8821900342", "US400921008800"],
                domicile_country="US",
                risk_rating="AAA",
            ),
            "BNP_PARIBAS": CounterpartyProfile(
                counterparty_id="BNP_PARIBAS",
                name="BNP Paribas S.A.",
                mean_notional=3_000_000.0,
                std_dev_notional=900_000.0,
                min_notional=150_000.0,
                max_historical_notional=7_500_000.0,
                sample_size=1180,
                primary_currency="EUR",
                authorized_bics=["BNPAFRPP", "BNPAFRPPXXX", "BNPAGB22", "BNPAFRPPFPP"],
                authorized_accounts=["FR76300040123456789018", "FR76300040000012345678", "00401234567"],
                domicile_country="FR",
                risk_rating="AA",
            ),
            "GOLDMAN_SACHS": CounterpartyProfile(
                counterparty_id="GOLDMAN_SACHS",
                name="Goldman Sachs International",
                mean_notional=4_000_000.0,
                std_dev_notional=1_200_000.0,
                min_notional=250_000.0,
                max_historical_notional=9_500_000.0,
                sample_size=950,
                primary_currency="USD",
                authorized_bics=["GSILGB2L", "GSILGB2LXXX", "GSCOUS33", "GSCOUS33XXX"],
                authorized_accounts=["9876543210", "GS881029384", "GB29GSIL98765432100000"],
                domicile_country="GB",
                risk_rating="AAA",
            ),
            "SOCIETE_GENERALE": CounterpartyProfile(
                counterparty_id="SOCIETE_GENERALE",
                name="Société Générale S.A.",
                mean_notional=3_200_000.0,
                std_dev_notional=850_000.0,
                min_notional=200_000.0,
                max_historical_notional=8_000_000.0,
                sample_size=2500,
                primary_currency="EUR",
                authorized_bics=["SOGEFRPP", "SOGEFRPPXXX", "SOGEGB2L", "SOGEUS33"],
                authorized_accounts=["FR76300030123456789019", "FR76300030000012345678", "00301234567"],
                domicile_country="FR",
                risk_rating="AA",
            ),
            "DEUTSCHE_BANK": CounterpartyProfile(
                counterparty_id="DEUTSCHE_BANK",
                name="Deutsche Bank AG",
                mean_notional=2_800_000.0,
                std_dev_notional=800_000.0,
                min_notional=100_000.0,
                max_historical_notional=7_000_000.0,
                sample_size=1050,
                primary_currency="EUR",
                authorized_bics=["DEUTDEDB", "DEUTDEDBXXX", "DEUTGB2L", "DEUTUS33"],
                authorized_accounts=["DE89500700100123456789", "5007001001234"],
                domicile_country="DE",
                risk_rating="A",
            ),
            "BARCLAYS": CounterpartyProfile(
                counterparty_id="BARCLAYS",
                name="Barclays Bank PLC",
                mean_notional=2_200_000.0,
                std_dev_notional=650_000.0,
                min_notional=100_000.0,
                max_historical_notional=5_500_000.0,
                sample_size=880,
                primary_currency="GBP",
                authorized_bics=["BARCGB22", "BARCGB22XXX", "BARCUS33"],
                authorized_accounts=["GB29BARC20000012345678", "20000012345678"],
                domicile_country="GB",
                risk_rating="A",
            ),
            "DEFAULT": CounterpartyProfile(
                counterparty_id="DEFAULT",
                name="Standard Institutional Counterparty",
                mean_notional=1_500_000.0,
                std_dev_notional=500_000.0,
                min_notional=50_000.0,
                max_historical_notional=4_000_000.0,
                sample_size=300,
                primary_currency="EUR",
                authorized_bics=[],
                authorized_accounts=[],
                domicile_country="FR",
                risk_rating="BBB",
            ),
        }

    # ── 1. Counterparty Resolution & Profile Matching ───────────────────────

    def get_counterparty_profile(self, counterparty_name: Optional[str]) -> CounterpartyProfile:
        """Resolves counterparty name or alias to a CounterpartyProfile."""
        if not counterparty_name:
            return self.profiles.get("DEFAULT", list(self.profiles.values())[0])

        cleaned = re.sub(r"[^A-Za-z0-9]", "", counterparty_name.upper())

        aliases = {
            "JPM": "JPMORGAN",
            "JPMORGAN": "JPMORGAN",
            "JPMORGANCHASE": "JPMORGAN",
            "BNP": "BNP_PARIBAS",
            "BNPP": "BNP_PARIBAS",
            "BNPPARIBAS": "BNP_PARIBAS",
            "GOLDMAN": "GOLDMAN_SACHS",
            "GOLDMANSACHS": "GOLDMAN_SACHS",
            "GS": "GOLDMAN_SACHS",
            "SOCGEN": "SOCIETE_GENERALE",
            "SOCIETEGENERALE": "SOCIETE_GENERALE",
            "SG": "SOCIETE_GENERALE",
            "DB": "DEUTSCHE_BANK",
            "DEUTSCHE": "DEUTSCHE_BANK",
            "DEUTSCHEBANK": "DEUTSCHE_BANK",
            "BARCLAYS": "BARCLAYS",
            "BARC": "BARCLAYS",
            "BOFA": "BOFA",
            "BANKOFAMERICA": "BOFA",
            "BAML": "BOFA",
        }

        for alias, profile_key in aliases.items():
            if alias in cleaned and profile_key in self.profiles:
                return self.profiles[profile_key]

        # Search in profile keys and profile names
        for key, profile in self.profiles.items():
            prof_name_clean = re.sub(r"[^A-Za-z0-9]", "", profile.name.upper())
            if key.upper() in cleaned or cleaned in key.upper():
                return profile
            if prof_name_clean in cleaned or cleaned in prof_name_clean:
                return profile

        # Word-level intersection matching
        words = [w for w in re.split(r"[^A-Za-z0-9]+", counterparty_name.upper()) if len(w) > 2]
        for key, profile in self.profiles.items():
            prof_name_upper = profile.name.upper()
            if any(w in prof_name_upper for w in words):
                return profile

        return self.profiles.get("DEFAULT", list(self.profiles.values())[0])

    # ── 2. Off-Market Notional Deviation Analysis (>3 Sigma) ─────────────────

    def analyze_notional_deviation(
        self, amount: Optional[float], profile: CounterpartyProfile
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Calculates notional deviation Z-Score:
        Z = |amount - mean| / std_dev
        Flags trades > 3 standard deviations or exceeding historical ceilings.
        """
        if amount is None or amount <= 0:
            return 0.0, [], {
                "amount": amount,
                "mean": profile.mean_notional,
                "std_dev": profile.std_dev_notional,
                "z_score": 0.0,
                "status": "NO_NOTIONAL_SPECIFIED",
            }

        mean = profile.mean_notional
        std = profile.std_dev_notional if profile.std_dev_notional > 0 else 500_000.0
        z_score = abs(amount - mean) / std
        deviation_ratio = amount / mean if mean > 0 else 1.0

        tags: List[str] = []
        score = 0.0

        if z_score >= 5.0:
            score = 1.0
            tags.append("EXTREME_NOTIONAL_ANOMALY_5SIGMA")
            tags.append("OFF_MARKET_TRADE_DEVIATION_3SIGMA")
            tags.append(f"NOTIONAL_Z_SCORE_{z_score:.1f}")
        elif z_score >= 3.0:
            # Explicit requirement: off-market trade deviations (>3 standard deviations)
            score = 0.85
            tags.append("OFF_MARKET_TRADE_DEVIATION_3SIGMA")
            tags.append(f"NOTIONAL_Z_SCORE_{z_score:.1f}")
        elif z_score >= 2.0:
            score = 0.45
            tags.append("MODERATE_NOTIONAL_DEVIATION_2SIGMA")
        elif z_score >= 1.0:
            score = 0.15
        else:
            score = 0.05
            tags.append("NOTIONAL_WITHIN_NORMAL_BOUNDS")

        # Additional check: Absolute historic ceiling breach
        if amount > profile.max_historical_notional:
            score = max(score, 0.90)
            if "HISTORICAL_MAX_CEILING_BREACHED" not in tags:
                tags.append("HISTORICAL_MAX_CEILING_BREACHED")

        analysis = {
            "amount": amount,
            "mean": mean,
            "std_dev": std,
            "z_score": round(z_score, 2),
            "deviation_ratio": round(deviation_ratio, 2),
            "max_historical": profile.max_historical_notional,
            "is_3sigma_breach": z_score >= 3.0,
        }

        return round(score, 3), tags, analysis

    # ── 3. SSI & Counterparty Beneficiary Account Fraud Detector ─────────────

    def analyze_ssi_and_beneficiary(
        self,
        email_text: str,
        entities: ExtractedEntities,
        profile: CounterpartyProfile,
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Detects SSI fraud, unrecognized BIC routing, offshore secrecy accounts,
        and unexpected beneficiary account hijacking attempts.
        """
        tags: List[str] = []
        combined_text = (
            f"{email_text} {entities.counterparty or ''} {entities.action_type or ''}"
        )

        # 1. Extract BIC / SWIFT codes
        bic_matches = re.findall(
            r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", combined_text
        )
        # Filter out common false positives (like ISIN substrings)
        candidate_bics = [b for b in bic_matches if not re.match(r"^[A-Z]{2}[0-9]{10}$", b)]

        # 2. Extract Account / IBAN numbers
        iban_matches = re.findall(
            r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}\b", combined_text
        )
        acct_matches = re.findall(
            r"(?:ACC(?:OUNT)?|IBAN|BENEFICIARY\s+A/C|A/C)[:#\s]*([A-Z0-9-]{8,24})",
            combined_text,
            flags=re.IGNORECASE,
        )
        detected_accounts = list(set(iban_matches + [a.strip() for a in acct_matches]))

        # 3. Phishing / SSI Divert keywords
        suspicious_phrases = [
            "urgent change of beneficiary",
            "divert funds to new account",
            "update settlement routing immediately",
            "temporary payment instructions",
            "new offshore account",
            "intermediary bank detour",
            "beneficiary name changed",
            "override existing ssi",
            "urgent ssi amendment",
        ]
        has_suspicious_phrasing = any(
            phrase in combined_text.lower() for phrase in suspicious_phrases
        )

        bic_score = 0.0
        acct_score = 0.0
        offshore_country: Optional[str] = None
        unrecognized_bics: List[str] = []

        # Analyze BICs
        if candidate_bics:
            for bic in candidate_bics:
                country_code = bic[4:6]
                if country_code in OFFSHORE_SECRECY_JURISDICTIONS:
                    offshore_country = OFFSHORE_SECRECY_JURISDICTIONS[country_code]
                    tags.append(f"OFFSHORE_JURISDICTION_ROUTING_{country_code}")
                    tags.append("CRITICAL_OFFSHORE_BIC_DETECTED")
                    bic_score = max(bic_score, 0.95)

                # Check if BIC is in authorized list for known profile
                if profile.authorized_bics and bic not in profile.authorized_bics:
                    unrecognized_bics.append(bic)
                    tags.append(f"UNRECOGNIZED_BIC_ROUTING_{bic}")
                    bic_score = max(bic_score, 0.70)
                elif profile.authorized_bics and bic in profile.authorized_bics:
                    tags.append(f"VERIFIED_AUTHORIZED_BIC_{bic}")

        # Analyze Beneficiary Accounts
        unverified_accounts: List[str] = []
        if detected_accounts and profile.authorized_accounts:
            for acc in detected_accounts:
                normalized_acc = acc.replace(" ", "").replace("-", "")
                is_authorized = any(
                    normalized_acc == auth_acc.replace(" ", "").replace("-", "")
                    for auth_acc in profile.authorized_accounts
                )
                if not is_authorized:
                    unverified_accounts.append(acc)
                    tags.append("UNEXPECTED_SSI_BENEFICIARY_CHANGE")
                    tags.append("UNVERIFIED_BENEFICIARY_ACCOUNT")
                    acct_score = max(acct_score, 0.80)
                else:
                    tags.append("VERIFIED_BENEFICIARY_ACCOUNT")

        # Phishing keywords penalty
        keyword_score = 0.0
        if has_suspicious_phrasing:
            keyword_score = 0.85
            tags.append("SUSPICIOUS_SSI_UPDATE_PHRASING_DETECTED")

        # Aggregate SSI fraud score
        composite_ssi_score = max(bic_score, acct_score, keyword_score)

        # Compound bonus: Offshore BIC + Unverified Account
        if offshore_country and unverified_accounts:
            composite_ssi_score = 1.0
            tags.append("CRITICAL_OFFSHORE_ACCOUNT_HIJACKING_RISK")

        if not tags:
            tags.append("SSI_PARAMETERS_CLEAN")

        analysis = {
            "candidate_bics": candidate_bics,
            "unrecognized_bics": unrecognized_bics,
            "detected_accounts": detected_accounts,
            "unverified_accounts": unverified_accounts,
            "offshore_jurisdiction": offshore_country,
            "has_suspicious_phrasing": has_suspicious_phrasing,
            "is_ssi_fraud_risk": composite_ssi_score >= 0.70,
        }

        return round(composite_ssi_score, 3), tags, analysis

    # ── 4. Settlement Cutoff Deadline Countdown Analysis ────────────────────

    def analyze_cutoff_countdown(
        self,
        email: ClassifiedEmail,
        entities: ExtractedEntities,
        current_time_utc: Optional[datetime] = None,
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Analyzes minutes remaining until TARGET2 / Euroclear / Clearstream / Fedwire cutoff.
        Flags:
          - <15 mins: CRITICAL_CUTOFF_BREACH_IMMINENT
          - <30 mins: URGENT_CUTOFF_WARNING
          - <60 mins: APPROACHING_CUTOFF_DEADLINE
        """
        tags: List[str] = []
        now = current_time_utc or datetime.now(timezone.utc)
        combined_text = f"{email.subject} {email.body} {entities.deadline or ''}".upper()

        # Identify settlement system
        system = "DEFAULT"
        if "TARGET2" in combined_text or "T2" in combined_text:
            system = "TARGET2"
        elif "EUROCLEAR" in combined_text:
            system = "EUROCLEAR"
        elif "CLEARSTREAM" in combined_text:
            system = "CLEARSTREAM"
        elif "FEDWIRE" in combined_text or (entities.currency == "USD" and "FED" in combined_text):
            system = "FEDWIRE"
        elif "CHAPS" in combined_text or entities.currency == "GBP":
            system = "CHAPS"
        elif "CREST" in combined_text:
            system = "CREST"
        elif entities.currency == "EUR":
            system = "TARGET2"

        # Determine cutoff time
        cutoff_dtime = MARKET_CUTOFF_UTC.get(system, MARKET_CUTOFF_UTC["DEFAULT"])
        minutes_remaining: Optional[float] = None

        # Check explicit deadline entity first (e.g. ISO timestamp or minutes regex)
        if entities.deadline:
            try:
                # Try parsing ISO format
                deadline_dt = datetime.fromisoformat(entities.deadline.replace("Z", "+00:00"))
                if deadline_dt.tzinfo is None:
                    deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                delta = deadline_dt - now
                minutes_remaining = delta.total_seconds() / 60.0
            except Exception:
                pass

        # Check regex for explicit "in XX minutes", "< 30 mins", "cutoff in 20m"
        if minutes_remaining is None:
            min_match = re.search(
                r"(?:cutoff\s+in|deadline\s+in|within|remaining[:\s]*)\s*(\d+)\s*(?:min|minute|m\b)",
                combined_text,
                flags=re.IGNORECASE,
            )
            if min_match:
                minutes_remaining = float(min_match.group(1))

        # Default to market schedule calculation
        if minutes_remaining is None:
            today_cutoff = datetime.combine(now.date(), cutoff_dtime, tzinfo=timezone.utc)
            delta = today_cutoff - now
            minutes_remaining = delta.total_seconds() / 60.0

        # Score & Tag Assignment
        score = 0.0
        if minutes_remaining is not None:
            if minutes_remaining < 0:
                score = 0.90
                tags.append("CUTOFF_ALREADY_BREACHED")
                tags.append("POST_MARKET_EXCEPTION")
            elif minutes_remaining <= 15:
                score = 0.95
                tags.append("CRITICAL_CUTOFF_BREACH_IMMINENT")
                tags.append(f"CUTOFF_COUNTDOWN_{int(minutes_remaining)}M")
            elif minutes_remaining <= 30:
                score = 0.80
                tags.append("URGENT_CUTOFF_WARNING_SUB_30M")
                tags.append(f"CUTOFF_COUNTDOWN_{int(minutes_remaining)}M")
            elif minutes_remaining <= 60:
                score = 0.50
                tags.append("APPROACHING_CUTOFF_DEADLINE")
                tags.append(f"CUTOFF_COUNTDOWN_{int(minutes_remaining)}M")
            elif minutes_remaining <= 120:
                score = 0.25
                tags.append("MODERATE_CUTOFF_WINDOW")
            else:
                score = 0.05
                tags.append("SAFE_SETTLEMENT_WINDOW")

        if email.urgency == Urgency.HIGH and score < 0.70:
            score = max(score, 0.75)
            tags.append("HIGH_OPERATIONAL_URGENCY_DECLARED")

        analysis = {
            "settlement_system": system,
            "cutoff_time_utc": cutoff_dtime.strftime("%H:%M"),
            "minutes_remaining": round(minutes_remaining, 1) if minutes_remaining is not None else None,
            "is_sub_30_mins": minutes_remaining is not None and (0 <= minutes_remaining <= 30),
            "is_sub_15_mins": minutes_remaining is not None and (0 <= minutes_remaining <= 15),
        }

        return round(score, 3), tags, analysis

    # ── 5. Multi-Dimensional Anomaly Score Aggregator ───────────────────────

    def evaluate(
        self,
        email: ClassifiedEmail,
        entities: ExtractedEntities,
        current_time_utc: Optional[datetime] = None,
    ) -> AnomalyEvaluationResult:
        """
        Executes full multi-dimensional anomaly detection and returns an AnomalyEvaluationResult.
        Dimensions:
          - Notional Deviation (Weight: 0.35)
          - SSI Fraud & Beneficiary Hijacking (Weight: 0.40)
          - Cutoff Countdown Pressure (Weight: 0.25)
        """
        profile = self.get_counterparty_profile(entities.counterparty)
        email_text = f"{email.subject} {email.body}"

        # 1. Run dimensional analyses
        notional_score, notional_tags, notional_analysis = self.analyze_notional_deviation(
            entities.amount, profile
        )
        ssi_score, ssi_tags, ssi_analysis = self.analyze_ssi_and_beneficiary(
            email_text, entities, profile
        )
        cutoff_score, cutoff_tags, cutoff_analysis = self.analyze_cutoff_countdown(
            email, entities, current_time_utc
        )

        # 2. Weighted Aggregation
        raw_composite = (
            (notional_score * 0.35)
            + (ssi_score * 0.40)
            + (cutoff_score * 0.25)
        )

        # 3. Compound Red Flag Multipliers / Max Overrides
        composite_score = raw_composite
        explanations: List[str] = []

        # Compound rule A: Offshore BIC / Fraud SSI
        if ssi_score >= 0.85:
            composite_score = max(composite_score, ssi_score)
            explanations.append(
                f"High-risk SSI anomaly detected (Offshore routing/unauthorized BIC: {ssi_analysis.get('offshore_jurisdiction') or 'Unverified BIC'})."
            )

        # Compound rule B: Extreme / >3-Sigma Off-Market Notional
        if notional_score >= 0.95 or notional_analysis.get("z_score", 0) >= 5.0 or "HISTORICAL_MAX_CEILING_BREACHED" in notional_tags:
            composite_score = max(composite_score, 0.92)
            explanations.append(
                f"CRITICAL OFF-MARKET NOTIONAL: Trade notional €{entities.amount:,.2f} represents a severe >5-sigma outlier (Z={notional_analysis.get('z_score')}) exceeding {profile.name} historical ceiling."
            )
        elif notional_analysis.get("is_3sigma_breach"):
            composite_score = max(composite_score, 0.80)
            explanations.append(
                f"Trade notional €{entities.amount:,.2f} deviates >3 std deviations (Z={notional_analysis.get('z_score')}) from {profile.name} historical baseline (€{profile.mean_notional:,.2f})."
            )

        # Compound rule C: Compound Fraud Attack Signature (Offshore SSI + Off-Market Notional)
        if ssi_score >= 0.70 and notional_score >= 0.70:
            composite_score = max(composite_score, 0.98)
            explanations.append(
                "CRITICAL COMPOUND FRAUD SIGNATURE: Concurrently observed unverified/offshore SSI and severe off-market notional deviation."
            )

        # Compound rule D: Urgent Cutoff Exploitation (<30 mins rush + SSI Change)
        if cutoff_analysis.get("is_sub_30_mins") and ssi_score >= 0.60:
            composite_score = max(composite_score, 0.92)
            explanations.append(
                "RUSHED SETTLEMENT ATTACK: SSI modification combined with imminent market cutoff (<30 mins) represents an urgent social engineering vector."
            )

        final_score = round(min(1.0, composite_score), 3)

        # 4. Determine Risk Category and Recommendation
        all_tags = list(dict.fromkeys(notional_tags + ssi_tags + cutoff_tags))

        if final_score >= 0.85:
            risk_category = "CRITICAL"
            recommendation = "FREEZE_AND_ESCALATE_FRAUD_DESK"
        elif final_score >= 0.65:
            risk_category = "HIGH"
            recommendation = "ENHANCED_DUAL_CONTROL_REQUIRED"
        elif final_score >= 0.40:
            risk_category = "MEDIUM"
            recommendation = "SUPERVISOR_APPROVAL_REQUIRED"
        else:
            risk_category = "LOW"
            recommendation = "AUTO_APPROVE"

        if not explanations:
            explanations.append(
                f"Parameters aligned within standard operational tolerance for {profile.name}."
            )

        is_anomaly = final_score >= 0.50 or notional_analysis.get("is_3sigma_breach", False) or ssi_score >= 0.70

        return AnomalyEvaluationResult(
            is_anomaly=is_anomaly,
            anomaly_score=final_score,
            risk_category=risk_category,
            risk_tags=all_tags,
            dimension_scores={
                "notional_deviation": notional_score,
                "ssi_fraud_risk": ssi_score,
                "cutoff_countdown": cutoff_score,
                "composite": final_score,
            },
            explanations=explanations,
            notional_analysis=notional_analysis,
            ssi_analysis=ssi_analysis,
            cutoff_analysis=cutoff_analysis,
            recommendation=recommendation,
        )
