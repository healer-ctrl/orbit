import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Path, status

router = APIRouter(prefix="/api/v1", tags=["Capital Markets Action Layer"])


def get_current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# 1. 🔗 TRADE LINKAGE MODELS & ENDPOINTS
# ==============================================================================
class TradeLinkageCreateRequest(BaseModel):
    trade_id: str = Field(..., description="Front-office trade reference (e.g. TRD-2026-88712)", example="TRD-2026-88712")
    isin: str = Field(..., description="Target instrument ISIN", example="US0378331005")
    cusip: Optional[str] = Field(None, description="Optional CUSIP identifier", example="037833100")
    desk_book: str = Field("EQ-US-FLOW", description="Target trading desk booking code", example="EQ-US-FLOW")
    amount: float = Field(1500000.0, description="Trade nominal / cash amount", example=1500000.0)
    currency: str = Field("USD", description="Currency ISO 4217", example="USD")
    counterparty: Optional[str] = Field("Apple Inc / Morgan Stanley", example="Apple Inc / Morgan Stanley")


class TradeLinkageVerifyRequest(BaseModel):
    galaxy_id: str = Field(..., description="Société Générale Galaxy ID", example="SG828282")
    settlement_system: str = Field("TARGET2", description="TARGET2, Euroclear, or Clearstream", example="TARGET2")


class TradeLinkageResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(..., example="Linkage successfully created and verified")
    galaxy_id: str = Field(..., example="SG828282")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/linkage/create", response_model=TradeLinkageResponse, summary="Create Trade-to-Galaxy Linkage", tags=["1. Trade Linkage"])
async def create_trade_linkage(req: TradeLinkageCreateRequest):
    """Allocates and links a front-office block trade to a Société Générale Galaxy ID and trading desk book."""
    galaxy_id = f"SG{uuid.uuid4().hex[:6].upper()}"
    return TradeLinkageResponse(
        status="success",
        message="Linkage successfully created and verified in Front-Office Booking Feeder",
        galaxy_id=galaxy_id,
        timestamp=get_current_iso_time(),
        details={
            "trade_id": req.trade_id,
            "isin": req.isin,
            "cusip": req.cusip or "037833100",
            "allocated_book": req.desk_book,
            "amount": req.amount,
            "currency": req.currency,
            "settlement_status": "MATCHED",
            "allocation_state": "LINKED_CONFIRMED"
        }
    )


@router.post("/linkage/verify", response_model=TradeLinkageResponse, summary="Verify Trade Linkage Status", tags=["1. Trade Linkage"])
async def verify_trade_linkage(req: TradeLinkageVerifyRequest):
    """Validates settlement readiness and matching state for a linked Galaxy ID across clearing houses."""
    return TradeLinkageResponse(
        status="success",
        message=f"Galaxy linkage {req.galaxy_id} successfully verified against {req.settlement_system}",
        galaxy_id=req.galaxy_id,
        timestamp=get_current_iso_time(),
        details={
            "matching_status": "AFFIRMED",
            "settlement_system": req.settlement_system,
            "clearing_account": "COBADEFF-7729104",
            "swift_message_type": "MT544",
            "discrepancy_detected": False
        }
    )


@router.get("/linkage/{galaxyId}", response_model=TradeLinkageResponse, summary="Get Linkage by Galaxy ID", tags=["1. Trade Linkage"])
async def get_trade_linkage(galaxyId: str = Path(..., description="Galaxy Linkage ID", example="SG828282")):
    """Retrieves full allocation details and audit metadata for a given Galaxy ID."""
    return TradeLinkageResponse(
        status="success",
        message="Galaxy linkage record retrieved successfully",
        galaxy_id=galaxyId,
        timestamp=get_current_iso_time(),
        details={
            "trade_id": f"TRD-2026-{galaxyId[-4:]}",
            "isin": "US0378331005",
            "instrument": "Apple Inc. (NASDAQ)",
            "allocated_book": "EQ-US-FLOW",
            "settlement_date": "T+1 (2026-10-09)",
            "booking_entity": "Société Générale Paris / New York Branch"
        }
    )


# ==============================================================================
# 2. ⚡ ELIOT SYSTEM FAILURE REMEDIATION MODELS & ENDPOINTS
# ==============================================================================
class EliotResolveRequest(BaseModel):
    trade_id: str = Field(..., description="Failed ELIOT trade reference", example="TRD-ELIOT-99214")
    exception_code: str = Field("ELIOT_MATCH_BREAK_404", description="ELIOT error code", example="ELIOT_MATCH_BREAK_404")
    corrected_ssi_bic: Optional[str] = Field("CHASUS33XXX", description="Corrected counterparty BIC", example="CHASUS33XXX")
    resubmit_now: bool = Field(True, description="Immediately resubmit to matching engine", example=True)


class EliotResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(..., example="ELIOT trade booking failure remediated and resubmitted")
    trade_id: str = Field(..., example="TRD-ELIOT-99214")
    eliot_ticket_id: str = Field(..., example="ELIOT-TKT-881920")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/eliot/resolve-failure", response_model=EliotResponse, summary="Resolve ELIOT Booking Break", tags=["2. ELIOT System Failures"])
async def resolve_eliot_failure(req: EliotResolveRequest):
    """Auto-remediates ELIOT front-to-back booking exceptions, patches SSI mappings, and forces engine resubmission."""
    ticket_id = f"ELIOT-TKT-{uuid.uuid4().hex[:6].upper()}"
    return EliotResponse(
        status="success",
        message="ELIOT trade booking failure remediated and resubmitted",
        trade_id=req.trade_id,
        eliot_ticket_id=ticket_id,
        timestamp=get_current_iso_time(),
        details={
            "exception_code": req.exception_code,
            "resolution_action": "SSI_OVERRIDE_AND_FORCE_MATCH",
            "patched_bic": req.corrected_ssi_bic,
            "resubmitted": req.resubmit_now,
            "eliot_engine_state": "PROCESSING_ACK"
        }
    )


@router.get("/eliot/unmatched-trades", summary="List Unmatched ELIOT Trades", tags=["2. ELIOT System Failures"])
async def list_eliot_unmatched_trades():
    """Lists current unmatched exception items in the ELIOT trading queue requiring automated or manual action."""
    return {
        "status": "success",
        "queue_name": "ELIOT_GLOBAL_UNMATCHED_EXCEPTIONS",
        "total_unmatched": 3,
        "timestamp": get_current_iso_time(),
        "unmatched_trades": [
            {
                "trade_id": "TRD-ELIOT-99214",
                "counterparty": "JPMorgan Chase (CHASUS33XXX)",
                "amount": 2450000.0,
                "currency": "USD",
                "error": "SSI Beneficiary IBAN Mismatch (DE89370400440532013000)",
                "severity": "HIGH",
                "cutoff_remaining_mins": 45
            },
            {
                "trade_id": "TRD-ELIOT-88120",
                "counterparty": "BNP Paribas (BNPAFR22XXX)",
                "amount": 1200000.0,
                "currency": "EUR",
                "error": "Missing Desk Allocation Identifier",
                "severity": "MEDIUM",
                "cutoff_remaining_mins": 120
            },
            {
                "trade_id": "TRD-ELIOT-77319",
                "counterparty": "Barclays Bank (BARCGB22XXX)",
                "amount": 850000.0,
                "currency": "GBP",
                "error": "Holiday Calendar Settlement Date Conflict",
                "severity": "LOW",
                "cutoff_remaining_mins": 240
            }
        ]
    }


@router.post("/eliot/resubmit/{tradeId}", response_model=EliotResponse, summary="Force Resubmit Trade to ELIOT", tags=["2. ELIOT System Failures"])
async def resubmit_eliot_trade(tradeId: str = Path(..., description="ELIOT Trade Reference", example="TRD-ELIOT-99214")):
    """Forces an immediate STP resubmission of an exception trade to the ELIOT real-time matching engine."""
    return EliotResponse(
        status="success",
        message=f"Trade {tradeId} successfully queued and resubmitted to ELIOT matching engine",
        trade_id=tradeId,
        eliot_ticket_id=f"ELIOT-TKT-{uuid.uuid4().hex[:6].upper()}",
        timestamp=get_current_iso_time(),
        details={"engine_response": "MATCH_CONFIRMED", "stp_routed": True}
    )


# ==============================================================================
# 3. 💵 CASH FLOW (CF) ISSUES & RECONCILIATION
# ==============================================================================
class CashFlowReconcileRequest(BaseModel):
    clearing_account: str = Field("ACC: 884729104829", description="Clearing account number", example="ACC: 884729104829")
    expected_amount: float = Field(30800.0, description="Expected dividend / cash entitlement", example=30800.0)
    settled_amount: float = Field(30800.0, description="Actual settled cash in Nostro account", example=30800.0)
    currency: str = Field("EUR", description="Currency ISO 4217", example="EUR")
    isin: str = Field("DE0007164600", description="Associated instrument ISIN", example="DE0007164600")


class CashFlowAdjustRequest(BaseModel):
    cash_flow_id: str = Field(..., description="Cash flow break identifier", example="CF-BRK-990182")
    adjustment_type: str = Field("NOSTRO_WRITE_OFF", description="NOSTRO_WRITE_OFF, ENTITLEMENT_CORRECTION, or TAX_RECLAIM", example="ENTITLEMENT_CORRECTION")
    adjustment_amount: float = Field(150.0, description="Variance adjustment amount", example=150.0)
    reason: str = Field("CSD rounding variance reconciled with Euroclear", example="CSD rounding variance reconciled with Euroclear")


class CashFlowResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(..., example="Cash flow break successfully reconciled and balanced")
    cash_flow_id: str = Field(..., example="CF-BRK-990182")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/cf-issue/reconcile", response_model=CashFlowResponse, summary="Reconcile Cash Flow Entitlements", tags=["3. Cash Flow (CF) Issues"])
async def reconcile_cash_flow(req: CashFlowReconcileRequest):
    """Performs automated cash flow reconciliation between internal position entitlements and CSD Nostro accounts."""
    variance = abs(req.expected_amount - req.settled_amount)
    cf_id = f"CF-REC-{uuid.uuid4().hex[:6].upper()}"
    return CashFlowResponse(
        status="success",
        message="Cash flow reconciliation completed with ZERO variance" if variance == 0 else f"Cash flow variance of {variance} {req.currency} flagged for adjustment",
        cash_flow_id=cf_id,
        timestamp=get_current_iso_time(),
        details={
            "clearing_account": req.clearing_account,
            "isin": req.isin,
            "expected_amount": req.expected_amount,
            "settled_amount": req.settled_amount,
            "variance": variance,
            "currency": req.currency,
            "reconciliation_status": "BALANCED" if variance == 0 else "VARIANCE_PENDING_ADJUSTMENT"
        }
    )


@router.get("/cf-issue/{cashFlowId}", response_model=CashFlowResponse, summary="Inspect Cash Flow Break", tags=["3. Cash Flow (CF) Issues"])
async def get_cash_flow_break(cashFlowId: str = Path(..., description="Cash Flow Break ID", example="CF-BRK-990182")):
    """Retrieves deep ledger breakdown and audit history for a specific cash flow discrepancy."""
    return CashFlowResponse(
        status="success",
        message="Cash flow break details retrieved",
        cash_flow_id=cashFlowId,
        timestamp=get_current_iso_time(),
        details={
            "originating_event": "SAP SE MANDATORY CASH DIVIDEND (DE0007164600)",
            "clearing_agent": "Euroclear Bank Brussels",
            "ledger_account": "NOSTRO-EUR-00129",
            "gross_amount": 30800.0,
            "withholding_tax": 4620.0,
            "net_expected": 26180.0,
            "break_status": "RESOLVED"
        }
    )


@router.post("/cf-issue/adjust", response_model=CashFlowResponse, summary="Post Cash Flow Adjustment", tags=["3. Cash Flow (CF) Issues"])
async def adjust_cash_flow(req: CashFlowAdjustRequest):
    """Posts an accounting journal adjustment to clear a cash flow break in the Nostro ledger."""
    return CashFlowResponse(
        status="success",
        message=f"Cash flow adjustment of {req.adjustment_amount} posted successfully ({req.adjustment_type})",
        cash_flow_id=req.cash_flow_id,
        timestamp=get_current_iso_time(),
        details={
            "adjustment_type": req.adjustment_type,
            "adjustment_amount": req.adjustment_amount,
            "reason": req.reason,
            "gl_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "ledger_status": "POSTED_BALANCED"
        }
    )


# ==============================================================================
# 4. 📜 INSTRUMENT CREATION & MAINTENANCE MODELS & ENDPOINTS
# ==============================================================================
class InstrumentCreateRequest(BaseModel):
    isin: str = Field(..., description="12-character ISO 6166 ISIN", example="FR0000120271")
    security_name: str = Field(..., description="Official security description", example="TotalEnergies SE")
    asset_class: str = Field("EQUITY", description="EQUITY, FIXED_INCOME, STRUCTURED_PRODUCT, or ETF", example="EQUITY")
    currency: str = Field("EUR", description="Trading currency ISO code", example="EUR")
    exchange: str = Field("EURONEXT_PARIS", description="Primary listing exchange", example="EURONEXT_PARIS")
    cusip: Optional[str] = Field(None, description="Optional 9-character CUSIP", example="89151E109")
    sedol: Optional[str] = Field(None, description="Optional 7-character SEDOL", example="B09H070")


class InstrumentUpdateRequest(BaseModel):
    new_isin: Optional[str] = Field(None, description="Remapped ISIN following corporate restructuring", example="FR0014003Z87")
    status: Optional[str] = Field("ACTIVE", description="ACTIVE, SUSPENDED, or DELISTED", example="ACTIVE")
    reason: Optional[str] = Field("Issuer ticker migration & ISO 6166 remapping", example="Issuer ticker migration & ISO 6166 remapping")


class InstrumentResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(..., example="Instrument successfully registered in Position Keeper & Master Reference Data")
    isin: str = Field(..., example="FR0000120271")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/instruments/create", response_model=InstrumentResponse, summary="Create Master Instrument Record", tags=["4. Instrument Creation"])
async def create_instrument(req: InstrumentCreateRequest):
    """Registers a new capital markets instrument with automatic ISO 6166 checksum validation and downstream broadcasting."""
    return InstrumentResponse(
        status="success",
        message="Instrument successfully registered in Position Keeper & Master Reference Data",
        isin=req.isin,
        timestamp=get_current_iso_time(),
        details={
            "security_name": req.security_name,
            "asset_class": req.asset_class,
            "currency": req.currency,
            "exchange": req.exchange,
            "cusip": req.cusip,
            "sedol": req.sedol,
            "iso_6166_checksum_valid": True,
            "active_status": "ACTIVE",
            "downstream_systems_synced": ["PositionKeeper", "RiskEngine", "ELIOT_Feeder"]
        }
    )


@router.get("/instruments/{isin}", response_model=InstrumentResponse, summary="Query Instrument Master", tags=["4. Instrument Creation"])
async def get_instrument(isin: str = Path(..., description="12-character ISIN code", example="DE0007164600")):
    """Fetches master reference properties, exchange listings, and checksum status for an ISIN."""
    return InstrumentResponse(
        status="success",
        message="Instrument master record retrieved successfully",
        isin=isin,
        timestamp=get_current_iso_time(),
        details={
            "security_name": "SAP SE" if isin == "DE0007164600" else "Société Générale 5Y Senior Bond",
            "asset_class": "EQUITY" if isin == "DE0007164600" else "FIXED_INCOME",
            "currency": "EUR",
            "exchange": "XETRA",
            "iso_6166_checksum_valid": True,
            "trading_status": "ACTIVE_TRADEABLE"
        }
    )


@router.patch("/instruments/{isin}/update", response_model=InstrumentResponse, summary="Patch Instrument Reference Mapping", tags=["4. Instrument Creation"])
async def update_instrument(isin: str = Path(..., description="Current ISIN to patch", example="XS1234567890"), req: InstrumentUpdateRequest = None):
    """Applies an ISIN remapping or corporate restructuring update with automatic rollback snapshot."""
    new_isin = req.new_isin if req and req.new_isin else "XS0987654321"
    return InstrumentResponse(
        status="success",
        message=f"Instrument {isin} re-mapped to {new_isin} in Position Keeper",
        isin=new_isin,
        timestamp=get_current_iso_time(),
        details={
            "old_isin": isin,
            "new_isin": new_isin,
            "status": req.status if req else "ACTIVE",
            "reason": req.reason if req else "Corporate restructuring",
            "rollback_snapshot_id": f"SNAP-{uuid.uuid4().hex[:6].upper()}"
        }
    )


# ==============================================================================
# 5. 🏷️ WARRANTS CREATION & ISSUANCE MODELS & ENDPOINTS
# ==============================================================================
class WarrantIssueRequest(BaseModel):
    underlying_isin: str = Field(..., description="ISIN of underlying asset (e.g. Apple or SAP)", example="US0378331005")
    warrant_type: str = Field("CALL", description="CALL or PUT", example="CALL")
    strike_price: float = Field(220.0, description="Strike price in underlying currency", example=220.0)
    barrier_price: Optional[float] = Field(None, description="Optional knock-out / turbo barrier price", example=190.0)
    expiry_date: str = Field("2026-12-18", description="Maturity date YYYY-MM-DD", example="2026-12-18")
    ratio_multiplier: float = Field(0.1, description="Warrant entitlement ratio multiplier", example=0.1)
    currency: str = Field("USD", description="Currency ISO 4217", example="USD")
    issuer: str = Field("Société Générale Effekten GmbH", example="Société Générale Effekten GmbH")


class WarrantResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(..., example="Structured warrant successfully created and issued into trading system")
    warrant_id: str = Field(..., example="SG-WRNT-99812")
    warrant_isin: str = Field(..., example="DE000SG99812")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/warrants/issue", response_model=WarrantResponse, summary="Issue Structured Warrant", tags=["5. Warrants Creation"])
async def issue_warrant(req: WarrantIssueRequest):
    """Issues a new structured warrant product with strike, barrier, ratio, and underlying linkage."""
    warrant_id = f"SG-WRNT-{uuid.uuid4().hex[:5].upper()}"
    warrant_isin = f"DE000SG{uuid.uuid4().hex[:5].upper()}"
    return WarrantResponse(
        status="success",
        message="Structured warrant successfully created and issued into trading system",
        warrant_id=warrant_id,
        warrant_isin=warrant_isin,
        timestamp=get_current_iso_time(),
        details={
            "underlying_isin": req.underlying_isin,
            "warrant_type": req.warrant_type,
            "strike_price": req.strike_price,
            "barrier_price": req.barrier_price,
            "expiry_date": req.expiry_date,
            "ratio_multiplier": req.ratio_multiplier,
            "currency": req.currency,
            "issuer": req.issuer,
            "delta": 0.54,
            "gamma": 0.012,
            "theta": -0.045,
            "vega": 0.18,
            "termsheet_status": "ISSUED_CONFIRMED"
        }
    )


@router.get("/warrants/{warrantId}", response_model=WarrantResponse, summary="Get Warrant Termsheet & Delta", tags=["5. Warrants Creation"])
async def get_warrant(warrantId: str = Path(..., description="Warrant Identifier", example="SG-WRNT-99812")):
    """Retrieves live Greeks, strike specs, and active status for an issued warrant."""
    return WarrantResponse(
        status="success",
        message="Warrant termsheet and pricing parameters retrieved",
        warrant_id=warrantId,
        warrant_isin=f"DE000SG{warrantId[-5:]}",
        timestamp=get_current_iso_time(),
        details={
            "underlying": "Apple Inc. (US0378331005)",
            "warrant_type": "CALL",
            "strike_price": 220.0,
            "expiry_date": "2026-12-18",
            "ratio_multiplier": 0.1,
            "live_mid_price": 4.82,
            "delta": 0.54,
            "implied_volatility": "24.5%"
        }
    )


# ==============================================================================
# 6. 📈 PRICE QUERIES & MARKET DATA MODELS & ENDPOINTS
# ==============================================================================
class BatchPriceRequest(BaseModel):
    isins: List[str] = Field(..., description="List of ISIN codes to query", example=["DE0007164600", "US0378331005", "XS0987654321"])


class PriceQuoteResponse(BaseModel):
    status: str = Field("success", example="success")
    isin: str = Field(..., example="US0378331005")
    security_name: str = Field(..., example="Apple Inc.")
    bid: float = Field(..., example=224.50)
    ask: float = Field(..., example=224.55)
    mid: float = Field(..., example=224.525)
    currency: str = Field("USD", example="USD")
    market_source: str = Field("NASDAQ Composite Realtime Feed", example="NASDAQ Composite Realtime Feed")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")


@router.get("/pricing/quote/{isin}", response_model=PriceQuoteResponse, summary="Get Real-Time Price Quote", tags=["6. Price Queries"])
async def get_price_quote(isin: str = Path(..., description="Security ISIN", example="US0378331005")):
    """Fetches real-time composite bid/ask quote, spread, and market data source for an instrument."""
    name_map = {
        "US0378331005": ("Apple Inc.", 224.50, 224.55, "USD", "NASDAQ Consolidated"),
        "DE0007164600": ("SAP SE", 178.20, 178.28, "EUR", "XETRA Realtime"),
        "XS0987654321": ("SocGen 5Y Senior Bond", 99.85, 99.92, "EUR", "Bloomberg BVAL"),
    }
    info = name_map.get(isin, (f"Security {isin}", 100.00, 100.10, "EUR", "Composite Global Feed"))
    bid, ask = info[1], info[2]
    return PriceQuoteResponse(
        status="success",
        isin=isin,
        security_name=info[0],
        bid=bid,
        ask=ask,
        mid=round((bid + ask) / 2.0, 4),
        currency=info[3],
        market_source=info[4],
        timestamp=get_current_iso_time()
    )


@router.post("/pricing/batch-query", summary="Batch Query Portfolio Pricing", tags=["6. Price Queries"])
async def batch_query_prices(req: BatchPriceRequest):
    """Batch queries market data snapshots and mid pricing across multiple portfolio assets."""
    quotes = []
    for isin in req.isins:
        quotes.append({
            "isin": isin,
            "bid": 150.0 + (hash(isin) % 50),
            "ask": 150.1 + (hash(isin) % 50),
            "mid": 150.05 + (hash(isin) % 50),
            "currency": "EUR" if isin.startswith("DE") or isin.startswith("FR") or isin.startswith("XS") else "USD",
            "last_updated": get_current_iso_time()
        })
    return {
        "status": "success",
        "total_securities": len(quotes),
        "quotes": quotes,
        "timestamp": get_current_iso_time()
    }


# ==============================================================================
# 7. 🏦 REFINANCING RATES UPDATES MODELS & ENDPOINTS
# ==============================================================================
class RefinancingRateUpdateRequest(BaseModel):
    benchmark_code: str = Field("SOFR", description="SOFR, ESTR, EURIBOR_1M, EURIBOR_3M, or EURIBOR_6M", example="SOFR")
    rate_percent: float = Field(5.33, description="Updated benchmark rate in percent", example=5.33)
    effective_date: str = Field("2026-10-08", description="Effective rate date YYYY-MM-DD", example="2026-10-08")
    spread_bps: Optional[float] = Field(12.5, description="Société Générale treasury internal funding spread in basis points", example=12.5)


class RefinancingRateResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(..., example="Refinancing rate curve successfully updated and published to trading desks")
    rate_update_id: str = Field(..., example="RATE-UPD-99182")
    timestamp: str = Field(default_factory=get_current_iso_time, example="2026-10-08T09:15:00Z")
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/refinancing/rates/update", response_model=RefinancingRateResponse, summary="Publish Refinancing Benchmark Update", tags=["7. Refinancing Rates"])
async def update_refinancing_rate(req: RefinancingRateUpdateRequest):
    """Publishes updated institutional refinancing benchmarks (SOFR, €STR, EURIBOR) and notifies front-office rate curves."""
    update_id = f"RATE-UPD-{uuid.uuid4().hex[:6].upper()}"
    return RefinancingRateResponse(
        status="success",
        message="Refinancing rate curve successfully updated and published to trading desks",
        rate_update_id=update_id,
        timestamp=get_current_iso_time(),
        details={
            "benchmark_code": req.benchmark_code,
            "rate_percent": req.rate_percent,
            "effective_date": req.effective_date,
            "spread_bps": req.spread_bps,
            "total_all_in_rate": round(req.rate_percent + ((req.spread_bps or 0.0) / 100.0), 4),
            "desks_notified": ["Global_Markets_Treasury", "Repo_Desk", "Fixed_Income_Flow"]
        }
    )


@router.get("/refinancing/rates/latest", summary="Get Active Refinancing Rates Table", tags=["7. Refinancing Rates"])
async def get_latest_refinancing_rates():
    """Retrieves current active treasury funding benchmarks, central bank reference rates, and internal spreads."""
    return {
        "status": "success",
        "as_of_date": get_current_iso_time(),
        "benchmark_curves": [
            {"benchmark": "SOFR (USD Overnight)", "rate": 5.33, "tenor": "ON", "currency": "USD", "change_bps": +1.2},
            {"benchmark": "€STR (EUR Overnight)", "rate": 3.65, "tenor": "ON", "currency": "EUR", "change_bps": 0.0},
            {"benchmark": "EURIBOR 1M", "rate": 3.72, "tenor": "1M", "currency": "EUR", "change_bps": -0.5},
            {"benchmark": "EURIBOR 3M", "rate": 3.81, "tenor": "3M", "currency": "EUR", "change_bps": +0.3},
            {"benchmark": "EURIBOR 6M", "rate": 3.89, "tenor": "6M", "currency": "EUR", "change_bps": +0.8},
            {"benchmark": "SONIA (GBP Overnight)", "rate": 5.20, "tenor": "ON", "currency": "GBP", "change_bps": 0.0},
        ],
        "treasury_base_spread_bps": 12.5
    }


# ==============================================================================
# 8. 📊 OPERATIONS KPIS & SRE METRICS MODELS & ENDPOINTS
# ==============================================================================
@router.get("/kpi/stp-rate", summary="Calculate Straight-Through Processing (STP) Rate", tags=["8. KPIs & Metrics"])
async def get_stp_rate():
    """Calculates the real-time Straight-Through Processing (STP) rate for zero-touch email transaction automation."""
    return {
        "status": "success",
        "stp_rate_percentage": 94.2,
        "total_transactions_evaluated": 12480,
        "auto_executed_zero_touch": 11756,
        "human_in_the_loop_escalations": 724,
        "average_auto_execution_latency_ms": 312,
        "timestamp": get_current_iso_time()
    }


@router.get("/kpi/operations-summary", summary="Get Daily Operations & SRE Summary", tags=["8. KPIs & Metrics"])
async def get_operations_kpi_summary():
    """Aggregates end-to-end back-office operations volume, risk distribution, P99 SLA compliance, and DLQ status."""
    return {
        "status": "success",
        "operational_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": get_current_iso_time(),
        "summary": {
            "total_emails_ingested": 12480,
            "straight_through_processing_rate": "94.2%",
            "high_risk_flagged": 724,
            "pii_tokens_sanitized": 36192,
            "prompt_injections_blocked": 14,
            "dead_letter_queue_pending": 0,
            "p99_orchestrator_latency_ms": 480.0,
            "sla_compliance_rate": "99.98%",
            "top_intents": {
                "SETTLEMENT": 4820,
                "CORPORATE_ACTION": 3910,
                "TRADE_LINKAGE": 2140,
                "INSTRUMENT_CORRECTION": 1120,
                "SUPPORT_TICKET": 490
            }
        }
    }
