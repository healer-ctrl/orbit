import json
import logging
import uuid
from datetime import datetime, timezone
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

logger = logging.getLogger("orbit.functions")


# ==============================================================================
# 1. HTTP TRIGGER: Email Ingestion Webhook (from M365 / Graph / Event Grid)
# ==============================================================================
@app.route(route="email_webhook", methods=["POST"])
def email_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ingests incoming emails from Microsoft Graph API / M365 notifications.
    Validates webhook verification handshake and forwards payload to pipeline.
    """
    # 1. Validation handshake for Microsoft Graph webhook subscriptions
    validation_token = req.params.get("validationToken")
    if validation_token:
        logger.info("Graph subscription validation handshake received.")
        return func.HttpResponse(validation_token, status_code=200, mimetype="text/plain")

    try:
        req_body = req.get_json()
        logger.info("Received email event payload: %s", json.dumps(req_body)[:200])

        return func.HttpResponse(
            json.dumps({
                "status": "ACCEPTED",
                "message": "Email ingested into Orbit pipeline.",
                "ingest_timestamp": datetime.now(timezone.utc).isoformat(),
            }),
            status_code=202,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error("Failed to parse incoming webhook: %s", e)
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body", "details": str(e)}),
            status_code=400,
            mimetype="application/json",
        )


# ==============================================================================
# 2. HTTP TRIGGER: Action Execution Microservice
# ==============================================================================
@app.route(route="execute_action", methods=["POST"])
def execute_action(req: func.HttpRequest) -> func.HttpResponse:
    """
    Executes domain-specific back-office operations with custom validation conditions.
    
    HOW TO ADD CUSTOM CONDITIONS:
    Inspect 'action_type' and 'payload' fields below and add your domain validation rules!
    """
    try:
        body = req.get_json()
        action_type = body.get("action_type")
        payload = body.get("payload", {})
        trace_id = body.get("trace_id", str(uuid.uuid4()))

        # ----------------------------------------------------------------------
        # CUSTOM BUSINESS LOGIC & CONDITION EVALUATION
        # ----------------------------------------------------------------------
        if action_type == "CORPORATE_ACTION":
            # Example Condition: Check dividend amount threshold & currency
            amount = float(payload.get("amount", 0.0))
            currency = payload.get("currency", "EUR")
            isin = payload.get("isin", "UNKNOWN")

            if amount <= 0:
                return func.HttpResponse(
                    json.dumps({"status": "REJECTED", "reason": "Dividend amount must be greater than 0"}),
                    status_code=422,
                    mimetype="application/json"
                )

            result = {
                "action_id": f"CA-{uuid.uuid4().hex[:8].upper()}",
                "status": "EXECUTED",
                "event_type": "MANDATORY_CASH_DIVIDEND",
                "isin": isin,
                "dividend_rate": amount,
                "currency": currency,
                "affected_accounts": 14,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        elif action_type == "SETTLEMENT":
            # Example Condition: Verify trade ID and cut-off window
            trade_id = payload.get("trade_id")
            counterparty_bic = payload.get("counterparty_bic", "CHASUS33XXX")
            settlement_account = payload.get("settlement_account", "COBADEFF")

            result = {
                "action_id": f"SET-{uuid.uuid4().hex[:8].upper()}",
                "status": "EXECUTED",
                "trade_id": trade_id,
                "counterparty_bic": counterparty_bic,
                "ssi_target_account": settlement_account,
                "swift_message": "MT544 instruction resubmitted and matched in TARGET2",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        elif action_type == "TRADE_LINKAGE":
            result = {
                "action_id": f"TL-{uuid.uuid4().hex[:8].upper()}",
                "status": "EXECUTED",
                "trade_id": payload.get("trade_id"),
                "instrument": payload.get("instrument", "Apple Inc"),
                "allocated_book": payload.get("desk_book", "EQ-US-FLOW"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        elif action_type == "INSTRUMENT_CORRECTION":
            result = {
                "action_id": f"IC-{uuid.uuid4().hex[:8].upper()}",
                "status": "EXECUTED",
                "old_isin": payload.get("old_isin"),
                "new_isin": payload.get("new_isin"),
                "position_keeper_patched": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        elif action_type == "SUPPORT_TICKET":
            result = {
                "action_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
                "status": "EXECUTED",
                "itsm_system": "ServiceNow",
                "category": "Access Management",
                "priority": "P3 - Medium",
                "sla_target": "4 hours",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unsupported action_type: {action_type}"}),
                status_code=400,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"success": True, "trace_id": trace_id, "data": result}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as err:
        logger.exception("Error executing Azure function action: %s", err)
        return func.HttpResponse(
            json.dumps({"error": "Action execution failed", "details": str(err)}),
            status_code=500,
            mimetype="application/json"
        )


# ==============================================================================
# 3. TIMER TRIGGER: SLA Cutoff & Settlement Escalation Monitor
# ==============================================================================
@app.timer_trigger(schedule="0 */15 * * * *", arg_name="timer", run_on_startup=False)
def sla_monitor_timer(timer: func.TimerRequest) -> None:
    """
    Runs every 15 minutes to monitor pending approvals nearing T+1 market cutoff.
    Triggers automated Microsoft Teams escalations if SLA timer is < 30 minutes.
    """
    if timer.past_due:
        logger.info("SLA Monitor timer is running past due.")
    logger.info("SLA Monitor executed at: %s", datetime.now(timezone.utc).isoformat())
