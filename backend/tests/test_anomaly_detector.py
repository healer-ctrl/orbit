"""
Unit tests for the Real-Time Financial Anomaly & Counterparty Fraud Shield.
Société Générale Capital Markets & Post-Trade Operations.
"""

from datetime import datetime, timezone, timedelta
import pytest

from backend.models.email_models import ClassifiedEmail, ExtractedEntities, Intent, Urgency
from backend.services.anomaly_detector import (
    AnomalyDetector,
    CounterpartyProfile,
    AnomalyEvaluationResult,
    OFFSHORE_SECRECY_JURISDICTIONS,
)
from backend.agents.risk_scorer import RiskScorerAgent
from backend.services.openai_service import OpenAIService


@pytest.fixture
def detector():
    return AnomalyDetector()


@pytest.fixture
def base_email():
    return ClassifiedEmail(
        id="EML-TEST-001",
        sender="settlements@jpmorgan.com",
        subject="Trade Matching Confirmation TRD-2024-8891",
        body="Please confirm settlement for trade TRD-2024-8891. BIC CHASUS33 Account 4009210088.",
        received_at="2026-10-05T10:00:00Z",
        intent=Intent.SETTLEMENT,
        confidence=0.98,
        urgency=Urgency.LOW,
    )


@pytest.fixture
def base_entities():
    return ExtractedEntities(
        isin="US0378331005",
        counterparty="JPMorgan Chase",
        amount=2_500_000.0,
        currency="USD",
        trade_id="TRD-2024-8891",
        settlement_date="2026-10-06",
    )


# ── 1. Notional Anomaly & Z-Score Tests ───────────────────────────────────────

def test_normal_trade_within_tolerance(detector, base_email, base_entities):
    """A trade near historical mean (2.5M, Z~0.0) should have low anomaly score and clean tags."""
    result = detector.evaluate(base_email, base_entities)

    assert result.anomaly_score < 0.40
    assert result.risk_category == "LOW"
    assert "NOTIONAL_WITHIN_NORMAL_BOUNDS" in result.risk_tags
    assert not result.notional_analysis["is_3sigma_breach"]
    assert result.recommendation == "AUTO_APPROVE"


def test_off_market_trade_deviation_3sigma(detector, base_email, base_entities):
    """
    JPMorgan baseline: Mean = 2.5M, Std = 750k.
    Trade Amount = 5.2M -> Z = (5.2M - 2.5M) / 750k = 3.6 sigma (>3 sigma deviation).
    Must flag OFF_MARKET_TRADE_DEVIATION_3SIGMA.
    """
    base_entities.amount = 5_200_000.0
    result = detector.evaluate(base_email, base_entities)

    assert result.is_anomaly is True
    assert result.notional_analysis["is_3sigma_breach"] is True
    assert result.notional_analysis["z_score"] >= 3.0
    assert "OFF_MARKET_TRADE_DEVIATION_3SIGMA" in result.risk_tags
    assert result.dimension_scores["notional_deviation"] >= 0.80
    assert result.anomaly_score >= 0.80
    assert any("deviates >3 std deviations" in exp for exp in result.explanations)


def test_extreme_notional_anomaly_5sigma(detector, base_email, base_entities):
    """
    Trade Amount = 12M on JPMorgan profile (Mean 2.5M, Std 750k, Max 6M).
    Z = 12.67 sigma.
    Must flag EXTREME_NOTIONAL_ANOMALY_5SIGMA and HISTORICAL_MAX_CEILING_BREACHED.
    """
    base_entities.amount = 12_000_000.0
    result = detector.evaluate(base_email, base_entities)

    assert result.anomaly_score >= 0.90
    assert result.risk_category in ["HIGH", "CRITICAL"]
    assert "EXTREME_NOTIONAL_ANOMALY_5SIGMA" in result.risk_tags
    assert "HISTORICAL_MAX_CEILING_BREACHED" in result.risk_tags


# ── 2. SSI & Counterparty Fraud Shield Tests ─────────────────────────────────

def test_unrecognized_bic_routing(detector, base_email, base_entities):
    """
    JPMorgan authorized BICs are CHASUS33, CHASGB2L, etc.
    Providing an unrecognized BIC (e.g. UNKNOWNBIC1) must flag UNRECOGNIZED_BIC_ROUTING.
    """
    base_email.body = "Settlement instructions: Route to BIC UNKNUS33, Account 4009210088."
    result = detector.evaluate(base_email, base_entities)

    assert result.is_anomaly is True
    assert result.dimension_scores["ssi_fraud_risk"] >= 0.70
    assert any("UNRECOGNIZED_BIC_ROUTING_UNKNUS33" in tag for tag in result.risk_tags)


def test_offshore_secrecy_jurisdiction_flag(detector, base_email, base_entities):
    """
    BIC with country code 'KY' (Cayman Islands) or 'PA' (Panama) represents
    a high-risk offshore secrecy jurisdiction and must trigger critical fraud alerts.
    """
    base_email.body = "Settlement instructions update: Transfer to BIC CAYMKY33, account 4009210088."
    result = detector.evaluate(base_email, base_entities)

    assert result.is_anomaly is True
    assert result.anomaly_score >= 0.85
    assert result.risk_category == "CRITICAL"
    assert "OFFSHORE_JURISDICTION_ROUTING_KY" in result.risk_tags
    assert "CRITICAL_OFFSHORE_BIC_DETECTED" in result.risk_tags
    assert result.ssi_analysis["offshore_jurisdiction"] == "Cayman Islands"
    assert result.recommendation == "FREEZE_AND_ESCALATE_FRAUD_DESK"


def test_unexpected_beneficiary_account_change(detector, base_email, base_entities):
    """
    JPMorgan authorized accounts: 4009210088, 1002938841, etc.
    Providing an unverified account (e.g. 999988887777) must flag UNEXPECTED_SSI_BENEFICIARY_CHANGE.
    """
    base_email.body = "Please settle via CHASUS33 to Beneficiary A/C: 999988887777"
    result = detector.evaluate(base_email, base_entities)

    assert "UNEXPECTED_SSI_BENEFICIARY_CHANGE" in result.risk_tags
    assert "UNVERIFIED_BENEFICIARY_ACCOUNT" in result.risk_tags
    assert "999988887777" in result.ssi_analysis["unverified_accounts"]


def test_phishing_ssi_divert_keywords(detector, base_email, base_entities):
    """Emails containing urgent phrases like 'divert funds to new account' or 'urgent change of beneficiary'."""
    base_email.body = "URGENT change of beneficiary: divert funds to new account immediately."
    result = detector.evaluate(base_email, base_entities)

    assert "SUSPICIOUS_SSI_UPDATE_PHRASING_DETECTED" in result.risk_tags
    assert result.ssi_analysis["has_suspicious_phrasing"] is True
    assert result.dimension_scores["ssi_fraud_risk"] >= 0.80


# ── 3. Settlement Cutoff Countdown Tests ─────────────────────────────────────

def test_cutoff_countdown_sub_15_mins(detector, base_email, base_entities):
    """Deadline within 12 minutes must trigger CRITICAL_CUTOFF_BREACH_IMMINENT."""
    base_email.body = "URGENT - TARGET2 cutoff in 12 minutes! Resubmit immediately."
    base_email.urgency = Urgency.HIGH
    base_entities.deadline = "in 12 minutes"

    result = detector.evaluate(base_email, base_entities)

    assert result.dimension_scores["cutoff_countdown"] >= 0.90
    assert "CRITICAL_CUTOFF_BREACH_IMMINENT" in result.risk_tags
    assert result.cutoff_analysis["is_sub_15_mins"] is True
    assert result.cutoff_analysis["minutes_remaining"] == 12.0


def test_cutoff_countdown_sub_30_mins(detector, base_email, base_entities):
    """Euroclear deadline within 25 minutes must trigger URGENT_CUTOFF_WARNING_SUB_30M."""
    base_email.body = "Euroclear settlement cutoff in 25 mins. Please expedite."
    result = detector.evaluate(base_email, base_entities)

    assert "URGENT_CUTOFF_WARNING_SUB_30M" in result.risk_tags
    assert result.cutoff_analysis["is_sub_30_mins"] is True
    assert result.cutoff_analysis["minutes_remaining"] == 25.0


def test_cutoff_countdown_iso_datetime(detector, base_email, base_entities):
    """Explicit ISO deadline timestamp evaluated against current mock time."""
    now = datetime(2026, 10, 5, 15, 40, 0, tzinfo=timezone.utc)
    # Target cutoff at 16:00 UTC -> 20 mins remaining (<30m)
    base_entities.deadline = "2026-10-05T16:00:00Z"

    result = detector.evaluate(base_email, base_entities, current_time_utc=now)

    assert result.cutoff_analysis["is_sub_30_mins"] is True
    assert result.cutoff_analysis["minutes_remaining"] == 20.0
    assert "URGENT_CUTOFF_WARNING_SUB_30M" in result.risk_tags


def test_cutoff_already_breached(detector, base_email, base_entities):
    """Deadline that has already passed must trigger CUTOFF_ALREADY_BREACHED."""
    now = datetime(2026, 10, 5, 16, 30, 0, tzinfo=timezone.utc)
    base_entities.deadline = "2026-10-05T16:00:00Z"

    result = detector.evaluate(base_email, base_entities, current_time_utc=now)

    assert "CUTOFF_ALREADY_BREACHED" in result.risk_tags
    assert result.cutoff_analysis["minutes_remaining"] == -30.0


# ── 4. Compound Fraud & Multi-Factor Scenario ────────────────────────────────

def test_compound_fraud_attack_scenario(detector, base_email, base_entities):
    """
    Compound attack:
      1. Off-market notional (6.5M vs 2.5M mean -> >3 sigma)
      2. Offshore Cayman Islands BIC (CAYMKY33)
      3. Rushed cutoff pressure (cutoff in 10 minutes)
    Must trigger composite score >= 0.95, CRITICAL risk, and FREEZE recommendation.
    """
    base_entities.amount = 6_500_000.0
    base_email.subject = "URGENT TARGET2: Expedited diversion of settlement funds"
    base_email.body = "Settlement instructions: BIC CAYMKY33, A/C 987654321. TARGET2 cutoff in 10 minutes!"
    base_email.urgency = Urgency.HIGH

    result = detector.evaluate(base_email, base_entities)

    assert result.is_anomaly is True
    assert result.anomaly_score >= 0.95
    assert result.risk_category == "CRITICAL"
    assert result.recommendation == "FREEZE_AND_ESCALATE_FRAUD_DESK"
    assert "CRITICAL_OFFSHORE_BIC_DETECTED" in result.risk_tags
    assert "OFF_MARKET_TRADE_DEVIATION_3SIGMA" in result.risk_tags
    assert "CRITICAL_CUTOFF_BREACH_IMMINENT" in result.risk_tags
    assert any("CRITICAL COMPOUND FRAUD SIGNATURE" in exp for exp in result.explanations)


# ── 5. Integration with RiskScorerAgent ──────────────────────────────────────

def test_risk_scorer_agent_integration(detector, base_email, base_entities):
    """Verify RiskScorerAgent runs seamlessly with AnomalyDetector and yields unified score."""
    llm_service = OpenAIService()
    agent = RiskScorerAgent(openai_service=llm_service, anomaly_detector=detector)

    # Clean scenario
    risk_score, risk_level, duration = agent.run(base_email, base_entities, [])
    assert 0.0 <= risk_score <= 1.0
    assert risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert duration >= 0
    assert agent.last_anomaly_result is not None
    assert isinstance(agent.last_anomaly_result, AnomalyEvaluationResult)

    # Detailed method test
    r_score, r_lvl, dur, anomaly_res = agent.run_detailed(base_email, base_entities, [])
    assert anomaly_res.anomaly_score == agent.last_anomaly_result.anomaly_score


def test_risk_scorer_agent_flags_critical_fraud(detector, base_email, base_entities):
    """Verify RiskScorerAgent elevates to CRITICAL risk when fraud is detected."""
    llm_service = OpenAIService()
    agent = RiskScorerAgent(openai_service=llm_service, anomaly_detector=detector)

    # Fraudulent email payload
    base_entities.amount = 8_000_000.0  # >3 sigma
    base_email.body = "URGENT change of beneficiary: Transfer to BIC PAANPA22, A/C 888777666. Cutoff in 10m."

    risk_score, risk_level, duration = agent.run(base_email, base_entities, [])
    assert risk_score >= 0.85
    assert risk_level == "CRITICAL"


# ── 6. Custom Counterparty Profile Registration ──────────────────────────────

def test_custom_counterparty_registration():
    """Verify custom counterparty profile creation with specialized mean and std dev."""
    custom_profile = CounterpartyProfile(
        counterparty_id="BOFA",
        name="Bank of America Merrill Lynch",
        mean_notional=10_000_000.0,
        std_dev_notional=2_000_000.0,
        min_notional=500_000.0,
        max_historical_notional=25_000_000.0,
        sample_size=500,
        primary_currency="USD",
        authorized_bics=["BOFAUS3N"],
        authorized_accounts=["US123456789"],
        domicile_country="US",
    )

    custom_detector = AnomalyDetector(custom_profiles={"BOFA": custom_profile})
    profile = custom_detector.get_counterparty_profile("Bank of America")
    assert profile.counterparty_id == "BOFA"
    assert profile.mean_notional == 10_000_000.0

    # 12M notional is within 1 std dev for BOFA (mean 10M, std 2M) -> low deviation
    score, tags, analysis = custom_detector.analyze_notional_deviation(12_000_000.0, profile)
    assert analysis["z_score"] == 1.0
    assert not analysis["is_3sigma_breach"]
