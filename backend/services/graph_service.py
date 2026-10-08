import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import msal
import httpx

from backend.config import GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_TENANT_ID
from backend.resilience import resilience_registry, retry_with_backoff, CircuitBreakerOpenException
from backend.telemetry import get_tracer, inject_traceparent

logger = logging.getLogger("mailmind.services.graph")


class GraphService:
    """
    Microsoft Graph API Service for Outlook M365 integration.
    Equipped with OpenTelemetry distributed tracing, W3C traceparent injection,
    and resilient Circuit Breakers with exponential backoff retries.
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self.client_id = GRAPH_CLIENT_ID
        self.client_secret = GRAPH_CLIENT_SECRET
        self.tenant_id = GRAPH_TENANT_ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}" if self.tenant_id else ""
        self.scopes = ["https://graph.microsoft.com/.default"]
        self.breaker = resilience_registry.get_breaker("graph_api")
        self.tracer = get_tracer()

    def ping(self) -> Dict[str, Any]:
        """Health check probe for Microsoft Graph connectivity."""
        start = time.time()
        if not (self.client_id and self.client_secret and self.tenant_id):
            return {"status": "simulated_mode", "latency_ms": 0, "details": "Graph credentials not configured"}

        if self.breaker.state.value == "OPEN":
            return {
                "status": "circuit_open",
                "latency_ms": int((time.time() - start) * 1000),
                "details": "Graph API circuit breaker is OPEN",
            }

        token = self.get_access_token()
        latency = int((time.time() - start) * 1000)
        if token and token != "simulated_bearer_token":
            return {"status": "healthy", "latency_ms": latency, "authority": self.authority}
        return {"status": "simulated_mode", "latency_ms": latency}

    def get_access_token(self) -> Optional[str]:
        """Acquires an app-only token from Microsoft Entra ID with Circuit Breaker protection."""
        if not (self.client_id and self.client_secret and self.tenant_id and self.client_id != "00000000-0000-0000-0000-000000000000"):
            logger.info("Graph credentials not configured — running Graph in simulated mode.")
            return "simulated_bearer_token"

        with self.tracer.start_as_current_span("graph.get_access_token") as span:
            span.set_attribute("graph.tenant_id", self.tenant_id)
            try:
                def _acquire():
                    app = msal.ConfidentialClientApplication(
                        self.client_id,
                        authority=self.authority,
                        client_credential=self.client_secret,
                    )
                    result = app.acquire_token_for_client(scopes=self.scopes)
                    if "access_token" in result:
                        return result["access_token"]
                    else:
                        err = result.get("error_description", "Unknown error")
                        raise RuntimeError(f"Failed to acquire Graph token: {err}")

                return self.breaker.call(_acquire)
            except CircuitBreakerOpenException as cbe:
                logger.warning("Graph API Circuit Breaker OPEN (%s). Using simulated fallback.", cbe)
                return "simulated_bearer_token"
            except Exception as e:
                logger.error("Exception during token acquisition: %s", e)
                return None

    def subscribe_to_inbox(self, webhook_url: str, mailbox_user: str = "operations@socgen.com") -> Dict[str, Any]:
        """Creates a Graph API subscription to receive push notifications."""
        with self.tracer.start_as_current_span("graph.subscribe_inbox") as span:
            span.set_attribute("graph.mailbox", mailbox_user)
            span.set_attribute("graph.webhook_url", webhook_url)

            token = self.get_access_token()
            if token == "simulated_bearer_token" or not token:
                return {
                    "id": "sub_m365_ops_001",
                    "resource": f"/users/{mailbox_user}/mailFolders('Inbox')/messages",
                    "changeType": "created",
                    "notificationUrl": webhook_url,
                    "expirationDateTime": "2026-10-31T23:59:59Z",
                    "status": "ACTIVE_SIMULATED",
                }

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            inject_traceparent(headers)

            subscription_payload = {
                "changeType": "created",
                "notificationUrl": webhook_url,
                "resource": f"/users/{mailbox_user}/mailFolders('Inbox')/messages",
                "expirationDateTime": (datetime.utcnow() + timedelta(hours=48)).isoformat() + "Z",
                "clientState": "MailMindSecureState2024",
            }

            try:
                @retry_with_backoff(max_retries=2, base_delay=0.5)
                def _post_sub():
                    return self.breaker.call(
                        lambda: httpx.post(
                            f"{self.GRAPH_BASE_URL}/subscriptions",
                            headers=headers,
                            json=subscription_payload,
                            timeout=10.0,
                        ).json()
                    )
                return _post_sub()
            except Exception as e:
                logger.error("Error creating Graph subscription: %s", e)
                return {"status": "error", "error": str(e)}

    def fetch_email_by_id(self, message_id: str, mailbox_user: str = "operations@socgen.com") -> Dict[str, Any]:
        """Fetches full message details with W3C trace propagation and circuit breaker."""
        with self.tracer.start_as_current_span("graph.fetch_email") as span:
            span.set_attribute("graph.message_id", message_id)
            token = self.get_access_token()
            if token == "simulated_bearer_token" or not token:
                return {
                    "id": message_id,
                    "subject": "Mock Outlook Message",
                    "sender": "settlements@clearstream.com",
                    "body": "Mock content",
                    "received_at": datetime.utcnow().isoformat(),
                }

            headers = {"Authorization": f"Bearer {token}"}
            inject_traceparent(headers)

            try:
                url = f"{self.GRAPH_BASE_URL}/users/{mailbox_user}/messages/{message_id}?$select=id,subject,body,from,receivedDateTime,hasAttachments"
                
                @retry_with_backoff(max_retries=2, base_delay=0.5)
                def _fetch():
                    return self.breaker.call(lambda: httpx.get(url, headers=headers, timeout=10.0))

                resp = _fetch()
                data = resp.json()
                return {
                    "id": data.get("id"),
                    "subject": data.get("subject"),
                    "sender": data.get("from", {}).get("emailAddress", {}).get("address"),
                    "body": data.get("body", {}).get("content", ""),
                    "received_at": data.get("receivedDateTime"),
                }
            except Exception as e:
                logger.error("Error fetching email from Graph API: %s", e)
                return {}

    def send_reply(self, message_id: str, reply_body: str, mailbox_user: str = "operations@socgen.com") -> bool:
        """Sends an automated reply with W3C trace headers."""
        with self.tracer.start_as_current_span("graph.send_reply") as span:
            span.set_attribute("graph.message_id", message_id)
            token = self.get_access_token()
            if token == "simulated_bearer_token" or not token:
                logger.info("Simulated Outlook Reply sent to message %s: %s", message_id, reply_body[:60])
                return True

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            inject_traceparent(headers)
            payload = {"comment": reply_body}

            try:
                @retry_with_backoff(max_retries=2, base_delay=0.5)
                def _send():
                    return self.breaker.call(
                        lambda: httpx.post(
                            f"{self.GRAPH_BASE_URL}/users/{mailbox_user}/messages/{message_id}/reply",
                            headers=headers,
                            json=payload,
                            timeout=10.0,
                        )
                    )
                resp = _send()
                return resp.status_code in [200, 202]
            except Exception as e:
                logger.error("Error sending reply via Graph API: %s", e)
                return False

    def fetch_recent_inbox_messages(self, limit: int = 10, mailbox_user: str = "orbit25690@outlook.com") -> List[Dict[str, Any]]:
        """Fetches latest unread/recent messages from inbox."""
        token = self.get_access_token()
        if not token or token == "simulated_bearer_token":
            return []

        headers = {"Authorization": f"Bearer {token}"}
        inject_traceparent(headers)
        url = f"{self.GRAPH_BASE_URL}/users/{mailbox_user}/mailFolders('Inbox')/messages?$top={limit}&$orderby=receivedDateTime desc"

        try:
            resp = httpx.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                messages = resp.json().get("value", [])
                formatted = []
                for msg in messages:
                    formatted.append({
                        "id": msg.get("id"),
                        "subject": msg.get("subject", "No Subject"),
                        "sender": msg.get("from", {}).get("emailAddress", {}).get("address", "unknown@sender.com"),
                        "body": msg.get("body", {}).get("content", "") or msg.get("bodyPreview", ""),
                        "received_at": msg.get("receivedDateTime", datetime.utcnow().isoformat()),
                    })
                return formatted
            else:
                logger.debug("Graph fetch messages status: %d", resp.status_code)
                return []
        except Exception as e:
            logger.debug("Error querying recent messages from Graph: %s", e)
            return []

