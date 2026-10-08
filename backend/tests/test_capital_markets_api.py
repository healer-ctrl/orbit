import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestCapitalMarketsActionLayerAPI:
    """Comprehensive test suite for the 8 Capital Markets Action Layer topics."""

    # 1. Trade Linkage
    def test_linkage_create(self):
        resp = client.post("/api/v1/linkage/create", json={
            "trade_id": "TRD-2026-88712",
            "isin": "US0378331005",
            "cusip": "037833100",
            "desk_book": "EQ-US-FLOW",
            "amount": 1500000.0,
            "currency": "USD",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "SG" in data["galaxy_id"]
        assert data["details"]["allocated_book"] == "EQ-US-FLOW"

    def test_linkage_verify(self):
        resp = client.post("/api/v1/linkage/verify", json={
            "galaxy_id": "SG828282",
            "settlement_system": "TARGET2"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["details"]["matching_status"] == "AFFIRMED"

    def test_linkage_get_by_id(self):
        resp = client.get("/api/v1/linkage/SG828282")
        assert resp.status_code == 200
        data = resp.json()
        assert data["galaxy_id"] == "SG828282"
        assert data["details"]["allocated_book"] == "EQ-US-FLOW"

    # 2. ELIOT System Failures
    def test_eliot_resolve_failure(self):
        resp = client.post("/api/v1/eliot/resolve-failure", json={
            "trade_id": "TRD-ELIOT-99214",
            "exception_code": "ELIOT_MATCH_BREAK_404",
            "corrected_ssi_bic": "CHASUS33XXX",
            "resubmit_now": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "ELIOT-TKT-" in data["eliot_ticket_id"]

    def test_eliot_unmatched_trades(self):
        resp = client.get("/api/v1/eliot/unmatched-trades")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["unmatched_trades"]) >= 1

    def test_eliot_resubmit(self):
        resp = client.post("/api/v1/eliot/resubmit/TRD-ELIOT-99214")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trade_id"] == "TRD-ELIOT-99214"

    # 3. Cash Flow (CF) Issues
    def test_cf_issue_reconcile(self):
        resp = client.post("/api/v1/cf-issue/reconcile", json={
            "clearing_account": "ACC: 884729104829",
            "expected_amount": 30800.0,
            "settled_amount": 30800.0,
            "currency": "EUR",
            "isin": "DE0007164600"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["details"]["variance"] == 0.0

    def test_cf_issue_get_break(self):
        resp = client.get("/api/v1/cf-issue/CF-BRK-990182")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cash_flow_id"] == "CF-BRK-990182"

    def test_cf_issue_adjust(self):
        resp = client.post("/api/v1/cf-issue/adjust", json={
            "cash_flow_id": "CF-BRK-990182",
            "adjustment_type": "ENTITLEMENT_CORRECTION",
            "adjustment_amount": 150.0,
            "reason": "CSD rounding variance reconciled"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "GL-" in data["details"]["gl_entry_id"]

    # 4. Instrument Creation
    def test_instrument_create(self):
        resp = client.post("/api/v1/instruments/create", json={
            "isin": "FR0000120271",
            "security_name": "TotalEnergies SE",
            "asset_class": "EQUITY",
            "currency": "EUR",
            "exchange": "EURONEXT_PARIS"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["isin"] == "FR0000120271"

    def test_instrument_get(self):
        resp = client.get("/api/v1/instruments/DE0007164600")
        assert resp.status_code == 200
        data = resp.json()
        assert data["isin"] == "DE0007164600"
        assert data["details"]["security_name"] == "SAP SE"

    def test_instrument_patch(self):
        resp = client.patch("/api/v1/instruments/XS1234567890/update", json={
            "new_isin": "XS0987654321",
            "status": "ACTIVE",
            "reason": "Corporate restructuring"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["isin"] == "XS0987654321"

    # 5. Warrants Creation
    def test_warrant_issue(self):
        resp = client.post("/api/v1/warrants/issue", json={
            "underlying_isin": "US0378331005",
            "warrant_type": "CALL",
            "strike_price": 220.0,
            "expiry_date": "2026-12-18",
            "ratio_multiplier": 0.1,
            "currency": "USD"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "SG-WRNT-" in data["warrant_id"]
        assert data["details"]["delta"] == 0.54

    def test_warrant_get(self):
        resp = client.get("/api/v1/warrants/SG-WRNT-99812")
        assert resp.status_code == 200
        data = resp.json()
        assert data["warrant_id"] == "SG-WRNT-99812"

    # 6. Price Queries
    def test_price_quote(self):
        resp = client.get("/api/v1/pricing/quote/US0378331005")
        assert resp.status_code == 200
        data = resp.json()
        assert data["isin"] == "US0378331005"
        assert data["security_name"] == "Apple Inc."
        assert data["mid"] > 0

    def test_price_batch_query(self):
        resp = client.post("/api/v1/pricing/batch-query", json={
            "isins": ["DE0007164600", "US0378331005"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_securities"] == 2
        assert len(data["quotes"]) == 2

    # 7. Refinancing Rates
    def test_refinancing_rates_update(self):
        resp = client.post("/api/v1/refinancing/rates/update", json={
            "benchmark_code": "SOFR",
            "rate_percent": 5.33,
            "effective_date": "2026-10-08",
            "spread_bps": 12.5
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["details"]["total_all_in_rate"] == 5.455

    def test_refinancing_rates_latest(self):
        resp = client.get("/api/v1/refinancing/rates/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["benchmark_curves"]) >= 4

    # 8. KPIs & Metrics
    def test_kpi_stp_rate(self):
        resp = client.get("/api/v1/kpi/stp-rate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stp_rate_percentage"] > 90.0

    def test_kpi_operations_summary(self):
        resp = client.get("/api/v1/kpi/operations-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "SETTLEMENT" in data["summary"]["top_intents"]
