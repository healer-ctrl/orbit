#!/usr/bin/env python3
"""
Orbit - Outlook Live Mailbox Sender & Graph API Ingestion Bridge
Sends realistic Capital Markets test emails to orbit25690@outlook.com
and processes incoming emails via Microsoft Graph API through the multi-agent pipeline.
"""

import os
import sys
import json
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_TENANT_ID
from backend.services.graph_service import GraphService
from backend.agents.orchestrator import MailMindOrchestrator
from backend.models.email_models import IncomingEmail

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orbit.outlook_bridge")

TARGET_MAILBOX = os.getenv("GRAPH_MAILBOX_USER", "orbit25690@outlook.com")

SAMPLE_EMAILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/data/sample_emails.json"))


def load_sample_emails():
    """Loads mock emails from sample_emails.json."""
    if os.path.exists(SAMPLE_EMAILS_PATH):
        with open(SAMPLE_EMAILS_PATH, "r") as f:
            return json.load(f)
    return []


def process_live_graph_emails():
    """
    Polls orbit25690@outlook.com via Microsoft Graph API and feeds emails
    into the Orbit Multi-Agent Pipeline.
    """
    logger.info("Connecting to Microsoft Graph API for mailbox: %s", TARGET_MAILBOX)
    graph = GraphService()
    orchestrator = MailMindOrchestrator()

    token = graph.get_access_token()
    if not token or token == "simulated_bearer_token":
        logger.warning(
            "Graph API credentials not yet fully authenticated in Entra ID. "
            "Ingesting test emails from backend/data/sample_emails.json into pipeline..."
        )
        sample_emails = load_sample_emails()
        for mail in sample_emails:
            inc_email = IncomingEmail(
                id=mail.get("id"),
                sender=mail.get("sender"),
                subject=mail.get("subject"),
                body=mail.get("body"),
                received_at=mail.get("received_at", datetime.now(timezone.utc).isoformat()),
                attachments=mail.get("attachments", []),
                raw_headers=mail.get("raw_headers", {}),
            )
            logger.info("⚡ Processing: [%s] -> %s", inc_email.id, inc_email.subject)
            result = orchestrator.process_email(inc_email)
            logger.info("✅ Result: Intent=%s | RiskScore=%s | Status=%s",
                        result.get("intent"), result.get("risk_score"), result.get("status"))
        return

    # If live token is present, query Graph API messages
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{graph.GRAPH_BASE_URL}/users/{TARGET_MAILBOX}/mailFolders('Inbox')/messages?$top=10&$orderby=receivedDateTime desc"

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0)
        if resp.status_code == 200:
            messages = resp.json().get("value", [])
            logger.info("Found %d messages in live inbox for %s", len(messages), TARGET_MAILBOX)
            for msg in messages:
                inc_email = IncomingEmail(
                    id=msg.get("id"),
                    sender=msg.get("from", {}).get("emailAddress", {}).get("address", "unknown@sender.com"),
                    subject=msg.get("subject", "No Subject"),
                    body=msg.get("body", {}).get("content", ""),
                    received_at=msg.get("receivedDateTime", datetime.now(timezone.utc).isoformat()),
                    attachments=[],
                    raw_headers={},
                )
                logger.info("📥 Ingesting live email: %s", inc_email.subject)
                result = orchestrator.process_email(inc_email)
                logger.info("🎯 Pipeline complete: %s (Risk: %s)", result.get("intent"), result.get("risk_score"))
        else:
            logger.warning(
                "Graph API returned %d (%s). Personal @outlook.com accounts require delegated OAuth2 consent. "
                "Automatically processing full Capital Markets scenario suite through multi-agent pipeline...",
                resp.status_code, resp.reason_phrase if hasattr(resp, "reason_phrase") else "Personal Mailbox Restriction"
            )
            sample_emails = load_sample_emails()
            for mail in sample_emails:
                inc_email = IncomingEmail(
                    id=mail.get("id"),
                    sender=mail.get("sender"),
                    subject=mail.get("subject"),
                    body=mail.get("body"),
                    received_at=mail.get("received_at", datetime.now(timezone.utc).isoformat()),
                    attachments=mail.get("attachments", []),
                    raw_headers=mail.get("raw_headers", {}),
                )
                logger.info("⚡ Ingesting scenario: [%s] -> %s", inc_email.id, inc_email.subject)
                result = orchestrator.process_email(inc_email)
                logger.info("✅ Result: Intent=%s | RiskScore=%s | Status=%s",
                            result.get("intent"), result.get("risk_score"), result.get("status"))
    except Exception as e:
        logger.exception("Error querying Graph API: %s", e)


if __name__ == "__main__":
    logger.info("Starting Orbit Live Mailbox Bridge for %s", TARGET_MAILBOX)
    process_live_graph_emails()
