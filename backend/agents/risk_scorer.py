from typing import Optional, Tuple
import time
import logging

from backend.models.email_models import ClassifiedEmail, ExtractedEntities
from backend.services.openai_service import OpenAIService
from backend.services.anomaly_detector import AnomalyDetector, AnomalyEvaluationResult

logger = logging.getLogger("mailmind.risk_scorer")


class RiskScorerAgent:
    """
    Operational & Financial Risk Scorer Agent with Integrated Counterparty Fraud Shield.
    Combines LLM heuristic assessment with real-time multi-dimensional quantitative anomaly detection:
      1. Off-market trade size deviation (>3 sigma from counterparty baseline)
      2. SSI beneficiary changes & offshore routing fraud
      3. Settlement cutoff deadline countdown (<30m / <15m)
    """

    def __init__(
        self,
        openai_service: OpenAIService,
        anomaly_detector: Optional[AnomalyDetector] = None,
    ):
        self.llm = openai_service
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.last_anomaly_result: Optional[AnomalyEvaluationResult] = None

    def run(
        self, email: ClassifiedEmail, entities: ExtractedEntities, actions: list
    ) -> Tuple[float, str, int]:
        """
        Executes unified risk scoring.
        Returns:
            (final_risk: float, risk_level: str, duration_ms: int)
        """
        start_time = time.time()

        # 1. Base LLM Risk Scoring
        base_risk = self.llm.score_risk(email, entities, {})

        # 2. Quantitative Financial Anomaly & Counterparty Fraud Shield Evaluation
        anomaly_res = self.anomaly_detector.evaluate(email, entities)
        self.last_anomaly_result = anomaly_res

        # 3. Blended Composite Risk Computation
        # If anomaly detector flags critical fraud or off-market deviation, elevate immediately
        if anomaly_res.risk_category == "CRITICAL" or anomaly_res.anomaly_score >= 0.85:
            final_risk = max(base_risk, anomaly_res.anomaly_score)
        else:
            # Weighted synthesis: 40% LLM contextual risk + 60% quantitative anomaly detector
            synthesized = (0.40 * base_risk) + (0.60 * anomaly_res.anomaly_score)
            final_risk = max(base_risk, synthesized)

        # Rule-based overlay adjustments
        if entities.amount and entities.amount > 5_000_000:
            final_risk = max(final_risk, 0.85)
        elif entities.amount and entities.amount > 1_000_000:
            final_risk = max(final_risk, 0.65)

        if email.confidence < 0.80:
            final_risk = min(1.0, final_risk + 0.15)

        final_risk = round(min(1.0, max(0.0, final_risk)), 3)

        # 4. Risk Level Categorization
        if final_risk >= 0.85:
            risk_level = "CRITICAL"
        elif final_risk >= 0.70:
            risk_level = "HIGH"
        elif final_risk >= 0.40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Risk evaluation complete for email %s: Score=%.3f, Level=%s, AnomalyScore=%.3f, Tags=%s",
            email.id,
            final_risk,
            risk_level,
            anomaly_res.anomaly_score,
            anomaly_res.risk_tags,
        )

        return final_risk, risk_level, duration_ms

    def run_detailed(
        self, email: ClassifiedEmail, entities: ExtractedEntities, actions: list
    ) -> Tuple[float, str, int, AnomalyEvaluationResult]:
        """
        Executes risk scoring and returns the full AnomalyEvaluationResult artifact.
        """
        risk_score, risk_level, duration_ms = self.run(email, entities, actions)
        return risk_score, risk_level, duration_ms, self.last_anomaly_result
