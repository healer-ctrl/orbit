from backend.models.email_models import ClassifiedEmail, ExtractedEntities
from backend.models.action_models import ActionRequest
from backend.services.openai_service import OpenAIService
from backend.services.search_service import SearchService
import time
import uuid

class DecisionAgent:
    def __init__(self, openai_service: OpenAIService, search_service: SearchService):
        self.llm = openai_service
        self.search = search_service

    def run(self, email: ClassifiedEmail, entities: ExtractedEntities) -> tuple:
        start_time = time.time()
        similar = self.search.search_similar_emails(email.body)
        sops = self.search.search_sops(email.intent.value)
        decision = self.llm.make_decision(email, entities, similar, sops)
        
        # Formulate Action Requests based on decision
        actions = []
        actions.append(ActionRequest(
            action_type=email.intent.value,
            payload=entities.model_dump(),
            priority=email.urgency.value,
            trace_id=str(uuid.uuid4())
        ))
        duration = int((time.time() - start_time) * 1000)
        return actions, duration
