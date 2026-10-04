from backend.models.email_models import IncomingEmail, ClassifiedEmail
from backend.services.openai_service import OpenAIService
import time

class ClassifierAgent:
    def __init__(self, openai_service: OpenAIService):
        self.llm = openai_service

    def run(self, email: IncomingEmail) -> tuple:
        start_time = time.time()
        classified = self.llm.classify_email(email)
        duration = int((time.time() - start_time) * 1000)
        return classified, duration
