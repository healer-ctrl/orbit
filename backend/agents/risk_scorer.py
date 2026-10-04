from backend.models.email_models import ClassifiedEmail, ExtractedEntities
from backend.services.openai_service import OpenAIService
import time

class RiskScorerAgent:
    def __init__(self, openai_service: OpenAIService):
        self.llm = openai_service

    def run(self, email: ClassifiedEmail, entities: ExtractedEntities, actions: list) -> tuple:
        start_time = time.time()
        base_risk = self.llm.score_risk(email, entities, {})
        
        # Rule based overlays
        if entities.amount and entities.amount > 1000000:
            base_risk += 0.3
        if email.confidence < 0.8:
            base_risk += 0.2
            
        final_risk = min(1.0, base_risk)
        risk_level = "HIGH" if final_risk >= 0.7 else ("MEDIUM" if final_risk >= 0.4 else "LOW")
        
        duration = int((time.time() - start_time) * 1000)
        return final_risk, risk_level, duration
