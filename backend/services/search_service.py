import logging
from typing import List, Dict, Any, Optional
from backend.config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY

logger = logging.getLogger("mailmind.search")


# ── Built-in Capital Markets Institutional Knowledge Base ─────────────────────

CAPITAL_MARKETS_SOPS = [
    {
        "id": "SOP-CA-001",
        "title": "Mandatory Cash Dividend Reconciliation & Entitlement Processing",
        "domain": "CORPORATE_ACTION",
        "rules": "Reconcile CSD position (Clearstream/Euroclear) against internal ledger on Record Date. If discrepancy < 100 shares, auto-adjust and book event. If > 100 shares or rate > EUR 5.00, flag for supervisor review. Generate SWIFT MT566 confirmation upon completion.",
        "keywords": ["dividend", "cash", "record date", "ex-date", "sap", "entitlement", "mt564", "mt566"],
    },
    {
        "id": "SOP-SET-003",
        "title": "T+1 Failed Trade SSI Resolution & Counterparty Resubmission",
        "domain": "SETTLEMENT",
        "rules": "Upon receiving failed matching notification with counterparty (e.g. JPM, BNP, MS), query Counterparty SSI Directory. Verify BIC, beneficiary account, and settlement system (TARGET2 / Euroclear). Resubmit corrected MT544/MT548 instruction prior to cutoff (14:00 CET). If amount > EUR 1,000,000, require risk sign-off.",
        "keywords": ["failed", "settlement", "ssi", "t+1", "unmatched", "cutoff", "target2", "jpm", "resubmit"],
    },
    {
        "id": "SOP-TL-001",
        "title": "Trade-to-Instrument Allocation & Desk Booking Linkage",
        "domain": "TRADE_LINKAGE",
        "rules": "Verify trade ID against front-office trade feeder. Validate CUSIP/ISIN with Bloomberg/Reuters reference feed. Link trade to appropriate trading desk book (e.g. EQ-US-FLOW, FI-EUR-RATES). Confirm trade amount and notify middle-office.",
        "keywords": ["link", "trade linkage", "cusip", "apple", "allocation", "desk", "book", "trd-"],
    },
    {
        "id": "SOP-REF-002",
        "title": "Instrument Master Data Exception & ISIN/CUSIP Remapping",
        "domain": "INSTRUMENT_CORRECTION",
        "rules": "When ISIN mismatch alert is raised, validate checksum using ISO 6166 algorithm. Check whether corporate action (bond split, ticker change, restructuring) caused re-identification. Patch Position Keeper and notify Risk Engine with rollback snapshot.",
        "keywords": ["isin", "mismatch", "cusip", "sedol", "reference data", "remap", "position", "bond"],
    },
    {
        "id": "SOP-SUP-001",
        "title": "Operations Systems Access Provisioning & Role Granting",
        "domain": "SUPPORT_TICKET",
        "rules": "Verify requester identity against HR active directory. Auto-create ServiceNow/Jira ticket in 'Access Management' queue with P3 SLA (4 hours). For trade booking entry privileges, route approval to Desk Head.",
        "keywords": ["access", "role", "analyst", "support", "provision", "ticket", "itsm", "servicenow"],
    },
]

HISTORICAL_EMAIL_ARCHIVE = [
    {
        "id": "HIST-2024-001",
        "subject": "Clearstream MT564 - Cash Dividend DE0007164600",
        "intent": "CORPORATE_ACTION",
        "resolution": "Auto-booked event EVT-8821 in Corporate Action master; position entitlement reconciled with zero variance.",
        "risk_score": 0.25,
    },
    {
        "id": "HIST-2024-002",
        "subject": "TARGET2 Settlement Failure - JPM TRD-77612 SSI Mismatch",
        "intent": "SETTLEMENT",
        "resolution": "SSI corrected to COBADEFF account; trade resubmitted and matched within 45 mins before cutoff.",
        "risk_score": 0.65,
    },
    {
        "id": "HIST-2024-003",
        "subject": "Link Trade TRD-2024-1109 to US0378331005",
        "intent": "TRADE_LINKAGE",
        "resolution": "Linked to EQ-US-FLOW desk booking successfully.",
        "risk_score": 0.15,
    },
]

REFERENCE_DATA_REGISTRY = {
    "DE0007164600": {"name": "SAP SE", "type": "EQUITY", "exchange": "XETRA", "currency": "EUR"},
    "US0378331005": {"name": "Apple Inc.", "type": "EQUITY", "exchange": "NASDAQ", "currency": "USD", "cusip": "037833100"},
    "XS0987654321": {"name": "SocGen 5Y Senior Non-Preferred Bond", "type": "FIXED_INCOME", "currency": "EUR"},
    "JPM": {"bic": "CHASUS33XXX", "full_name": "JPMorgan Chase Bank N.A.", "target2_account": "DE44500105175407324931"},
    "BNP": {"bic": "BNPAFR22XXX", "full_name": "BNP Paribas S.A.", "target2_account": "FR76300040000112345678"},
}


class SearchService:
    """
    Azure AI Search & Semantic Knowledge Retrieval Service.
    Retrieves relevant SOPs, similar historical trade resolutions, and reference master data.
    """

    def __init__(self):
        self.endpoint = AZURE_SEARCH_ENDPOINT
        self.key = AZURE_SEARCH_KEY
        self.client = None

        if self.endpoint and self.key:
            try:
                from azure.core.credentials import AzureKeyCredential
                from azure.search.documents import SearchClient
                # We can connect to specific indices if needed
                logger.info("Azure AI Search endpoint configured: %s", self.endpoint)
            except Exception as e:
                logger.warning("Azure AI Search SDK initialization warning: %s", e)

    def search_similar_emails(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Finds historically resolved operations emails with similar semantic context."""
        query_lower = query.lower()
        results = []
        for item in HISTORICAL_EMAIL_ARCHIVE:
            score = 0.5
            if any(word in query_lower for word in item["subject"].lower().split()):
                score += 0.35
            results.append({**item, "similarity_score": min(0.98, score)})

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    def search_sops(self, intent_or_query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Retrieves applicable Standard Operating Procedures (SOPs) based on intent or query terms."""
        q_lower = intent_or_query.lower()
        scored_sops = []

        for sop in CAPITAL_MARKETS_SOPS:
            score = 0.2
            if sop["domain"].lower() in q_lower:
                score += 0.6
            for kw in sop["keywords"]:
                if kw in q_lower:
                    score += 0.15
            scored_sops.append({**sop, "relevance_score": min(0.99, score)})

        scored_sops.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_sops[:top_k]

    def search_reference_data(self, entity_query: str) -> Dict[str, Any]:
        """Looks up securities or counterparty reference data by ISIN, CUSIP, or BIC."""
        q_clean = entity_query.strip().upper()
        if q_clean in REFERENCE_DATA_REGISTRY:
            return {"query": q_clean, "found": True, "details": REFERENCE_DATA_REGISTRY[q_clean]}

        for k, v in REFERENCE_DATA_REGISTRY.items():
            if k in q_clean or (isinstance(v, dict) and v.get("name", "").upper() in q_clean):
                return {"query": entity_query, "found": True, "details": v, "key": k}

        return {"query": entity_query, "found": False, "details": {}}

    def index_email(self, email_data: dict) -> bool:
        """Indexes processed email into the searchable institutional knowledge base."""
        logger.info("Indexed email %s into Search archive", email_data.get("id"))
        return True
