from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class Intent(str, Enum):
    CORPORATE_ACTION = "CORPORATE_ACTION"
    SETTLEMENT = "SETTLEMENT"
    TRADE_LINKAGE = "TRADE_LINKAGE"
    INSTRUMENT_CORRECTION = "INSTRUMENT_CORRECTION"
    SUPPORT_TICKET = "SUPPORT_TICKET"

class Urgency(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class IncomingEmail(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    received_at: str
    attachments: List[str] = []
    raw_headers: dict = {}

class ClassifiedEmail(IncomingEmail):
    intent: Intent
    confidence: float
    urgency: Urgency

class ExtractedEntities(BaseModel):
    isin: Optional[str] = None
    cusip: Optional[str] = None
    counterparty: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    trade_date: Optional[str] = None
    settlement_date: Optional[str] = None
    deadline: Optional[str] = None
    instrument_name: Optional[str] = None
    trade_id: Optional[str] = None
    action_type: Optional[str] = None
    quantity: Optional[float] = None
    clean_price: Optional[float] = None
    gross_amount: Optional[float] = None
    counterparty_bic: Optional[str] = None
    beneficiary_account: Optional[str] = None
    attachment_records: Optional[List[dict]] = None
    signature_valid: Optional[bool] = None
    attachment_checksum: Optional[str] = None
    attachment_parsed: Optional[bool] = None

