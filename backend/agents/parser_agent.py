from backend.models.email_models import ClassifiedEmail, ExtractedEntities
from backend.services.openai_service import OpenAIService
from backend.services.search_service import SearchService
import time

class ParserAgent:
    def __init__(self, openai_service: OpenAIService, search_service: SearchService):
        self.llm = openai_service
        self.search = search_service

    def run(self, email: ClassifiedEmail) -> tuple:
        start_time = time.time()
        entities = self.llm.extract_entities(email)
        # Search for enrichment
        if entities.isin:
            self.search.search_reference_data(entities.isin)
        duration = int((time.time() - start_time) * 1000)
        return entities, duration
