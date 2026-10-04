import time
import logging
from typing import Optional, Dict, Any, Tuple
from backend.models.email_models import ClassifiedEmail, ExtractedEntities
from backend.services.openai_service import OpenAIService
from backend.services.search_service import SearchService
from backend.services.attachment_ocr_service import AttachmentOCRService

logger = logging.getLogger("mailmind.parser_agent")


class ParserAgent:
    """
    Multi-Modal Entity & Attachment Parser Agent.
    Coordinates text-based financial entity extraction via LLM/Regex,
    multi-modal OCR parsing of trade confirmation attachments (PDF, TIFF, CSV),
    and reference data enrichment via Azure AI Search.
    """

    def __init__(
        self,
        openai_service: OpenAIService,
        search_service: SearchService,
        attachment_ocr_service: Optional[AttachmentOCRService] = None
    ):
        self.llm = openai_service
        self.search = search_service
        self.ocr = attachment_ocr_service or AttachmentOCRService()

    def run(self, email: ClassifiedEmail, auth_context: Optional[Dict[str, Any]] = None) -> Tuple[ExtractedEntities, int]:
        """
        Executes entity extraction across the email body and any attached trade confirmations.
        
        Args:
            email: ClassifiedEmail object containing subject, body, and attachments list.
            auth_context: Optional cryptographic validation parameters (expected_checksum, public_key, etc.).
            
        Returns:
            Tuple of (ExtractedEntities, execution_duration_ms)
        """
        start_time = time.time()

        # Step 1: Base Entity Extraction from Email Text / Headers
        entities = self.llm.extract_entities(email)
        entities_dict = entities.model_dump()

        # Step 2: Multi-Modal Attachment Parsing & Table Extraction
        if email.attachments:
            try:
                entities_dict = self.ocr.enrich_entities_from_attachments(
                    entities_dict=entities_dict,
                    attachments=email.attachments,
                    auth_context=auth_context
                )
                entities = ExtractedEntities(**entities_dict)
            except Exception as e:
                logger.warning(f"Attachment parsing warning for email {email.id}: {e}", exc_info=True)

        # Step 3: Reference Data Lookup & Security Enrichment
        if entities.isin:
            try:
                self.search.search_reference_data(entities.isin)
            except Exception as e:
                logger.debug(f"Reference data lookup note: {e}")
        elif entities.cusip:
            try:
                self.search.search_reference_data(entities.cusip)
            except Exception as e:
                logger.debug(f"Reference data lookup note: {e}")

        duration = int((time.time() - start_time) * 1000)
        return entities, duration
