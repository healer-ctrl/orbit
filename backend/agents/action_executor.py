from backend.models.action_models import ActionRequest, ActionResult, ActionStatus
from backend.actions.corporate_action import CorporateActionHandler
from backend.actions.settlement import SettlementHandler
from backend.actions.trade_linkage import TradeLinkageHandler
from backend.actions.instrument_correction import InstrumentCorrectionHandler
from backend.actions.ticket_creator import TicketCreatorHandler
import time

class ActionExecutorAgent:
    def __init__(self):
        self.handlers = {
            "CORPORATE_ACTION": CorporateActionHandler(),
            "SETTLEMENT": SettlementHandler(),
            "TRADE_LINKAGE": TradeLinkageHandler(),
            "INSTRUMENT_CORRECTION": InstrumentCorrectionHandler(),
            "SUPPORT_TICKET": TicketCreatorHandler()
        }

    def run(self, request: ActionRequest) -> tuple:
        start_time = time.time()
        handler = self.handlers.get(request.action_type)
        if handler:
            result = handler.execute(request)
        else:
            result = ActionResult(
                action_id=f"UNKNOWN-{request.trace_id}",
                action_type=request.action_type,
                status=ActionStatus.FAILED,
                result_data={},
                error_message="Unknown action type",
                executed_at=str(time.time())
            )
        duration = int((time.time() - start_time) * 1000)
        return result, duration
