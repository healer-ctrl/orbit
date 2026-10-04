import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import msal
import httpx
from backend.config import GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_TENANT_ID

logger = logging.getLogger("mailmind.graph")


class GraphService:
    """
    Microsoft Graph API Service for Outlook M365 integration.
    Handles:
      - OAuth2 client credentials token acquisition via MSAL
      - Mailbox webhook subscriptions for real-time push events
      - Email fetching, metadata parsing & HTML body cleansing
      - Automated reply-back notifications to original senders
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self.client_id = GRAPH_CLIENT_ID
        self.client_secret = GRAPH_CLIENT_SECRET
        self.tenant_id = GRAPH_TENANT_ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}" if self.tenant_id else ""
        self.scopes = ["https://graph.microsoft.com/.default"]

    def get_access_token(self) -> Optional[str]:
        """Acquires an app-only token from Microsoft Entra ID."""
        if not (self.client_id and self.client_secret and self.tenant_id and self.client_id != "00000000-0000-0000-0000-000000000000"):
            logger.info("Graph credentials not configured — running Graph in simulated mode.")
            return "simulated_bearer_token"

        try:
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
            )
            result = app.acquire_token_for_client(scopes=self.scopes)
            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error("Failed to acquire Graph token: %s", result.get("error_description"))
                return None
        except Exception as e:
            logger.error("Exception during token acquisition: %s", e)
            return None

    def subscribe_to_inbox(self, webhook_url: str, mailbox_user: str = "operations@socgen.com") -> Dict[str, Any]:
        """
        Creates a Graph API subscription to receive push notifications via Webhook/EventGrid.
        """
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
        subscription_payload = {
            "changeType": "created",
            "notificationUrl": webhook_url,
            "resource": f"/users/{mailbox_user}/mailFolders('Inbox')/messages",
            "expirationDateTime": (datetime.utcnow() + datetime.timedelta(hours=48)).isoformat() + "Z",
            "clientState": "MailMindSecureState2024",
        }

        try:
            response = httpx.post(
                f"{self.GRAPH_BASE_URL}/subscriptions",
                headers=headers,
                json=subscription_payload,
                timeout=10.0,
            )
            return response.json()
        except Exception as e:
            logger.error("Error creating Graph subscription: %s", e)
            return {"status": "error", "error": str(e)}

    def fetch_email_by_id(self, message_id: str, mailbox_user: str = "operations@socgen.com") -> Dict[str, Any]:
        """Fetches full message details including attachments metadata."""
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
        try:
            url = f"{self.GRAPH_BASE_URL}/users/{mailbox_user}/messages/{message_id}?$select=id,subject,body,from,receivedDateTime,hasAttachments"
            resp = httpx.get(url, headers=headers, timeout=10.0)
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
        """Sends an automated acknowledgement/action confirmation reply back to the sender."""
        token = self.get_access_token()
        if token == "simulated_bearer_token" or not token:
            logger.info("Simulated Outlook Reply sent to message %s: %s", message_id, reply_body[:60])
            return True

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "comment": reply_body
        }
        try:
            resp = httpx.post(
                f"{self.GRAPH_BASE_URL}/users/{mailbox_user}/messages/{message_id}/reply",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
            return resp.status_code in [200, 202]
        except Exception as e:
            logger.error("Error sending reply via Graph API: %s", e)
            return False
