"""
Unit Tests for SWIFT ISO 15022 & ISO 20022 Financial Messaging Engine
Société Générale Global Markets Back-Office Systems
"""

import json
import pytest
from backend.services.swift_engine import (
    SWIFTEngine,
    compute_isin_check_digit,
    validate_isin,
    validate_tag_20,
    validate_tag_19a,
    validate_tag_22f,
    validate_tag_70e,
    format_swift_amount,
    format_swift_date,
)
from backend.models.action_models import ActionRequest
from backend.actions.corporate_action import CorporateActionHandler
from backend.actions.settlement import SettlementHandler
from backend.actions.trade_linkage import TradeLinkageHandler
from backend.actions.instrument_correction import InstrumentCorrectionHandler
from backend.actions.ticket_creator import TicketCreatorHandler


@pytest.fixture
def swift_engine():
    return SWIFTEngine(default_sender_bic="SOGEFRPAAXXX")


# ── 1. ISIN Validation & Luhn Checksum Tests ─────────────────────────────────

def test_isin_luhn_checksum_valid():
    """Verify ISO 6166 ISIN Luhn check digit computation on benchmark instruments."""
    assert compute_isin_check_digit("DE000716460") == "0"  # SAP SE
    assert compute_isin_check_digit("US037833100") == "5"  # Apple Inc
    assert compute_isin_check_digit("GB000263494") == "6"  # BAE Systems
    assert compute_isin_check_digit("FR000012027") == "1"  # TotalEnergies

    assert validate_isin("DE0007164600", strict_checksum=True) is True
    assert validate_isin("US0378331005", strict_checksum=True) is True
    assert validate_isin("FR0000120271", strict_checksum=True) is True


def test_isin_validation_invalid():
    """Verify invalid ISIN formats and wrong check digits are rejected."""
    # Wrong check digit
    assert validate_isin("DE0007164609", strict_checksum=True) is False
    assert validate_isin("US0378331001", strict_checksum=True) is False
    # Invalid length
    assert validate_isin("DE000716460", strict_checksum=False) is False
    assert validate_isin("DE0007164600123", strict_checksum=False) is False
    # Invalid characters
    assert validate_isin("DE000716460$", strict_checksum=False) is False
    assert validate_isin(None, strict_checksum=False) is False


# ── 2. Tag Syntax and Field Validators ───────────────────────────────────────

def test_tag_20_validation():
    """Verify Tag 20 / :20C: transaction reference rules."""
    ok, err = validate_tag_20("TRD202488712")
    assert ok is True
    assert err is None

    # Starts or ends with slash
    ok, err = validate_tag_20("/TRD123")
    assert ok is False
    assert "start or end with a slash" in err

    ok, err = validate_tag_20("TRD123/")
    assert ok is False
    assert "start or end with a slash" in err

    # Consecutive slashes
    ok, err = validate_tag_20("TRD//123")
    assert ok is False
    assert "consecutive slashes" in err

    # Length > 16
    ok, err = validate_tag_20("TRD1234567890123456789")
    assert ok is False
    assert "exceeds max 16" in err

    # Empty
    ok, err = validate_tag_20("")
    assert ok is False


def test_tag_19a_validation():
    """Verify Tag 19A / 19B amount and currency formatting."""
    ok, err = validate_tag_19a(":19A::SETT//USD2450000,00")
    assert ok is True

    ok, err = validate_tag_19a("EUR30800,00")
    assert ok is True

    ok, err = validate_tag_19a("INVALID_AMOUNT")
    assert ok is False


def test_tag_22f_validation():
    """Verify Tag 22F indicator qualifier and 4-character code syntax."""
    ok, err = validate_tag_22f(":22F::CAEV//DIVI")
    assert ok is True

    ok, err = validate_tag_22f("SETR//TRAD")
    assert ok is True

    ok, err = validate_tag_22f("INVALID")
    assert ok is False


def test_tag_70e_validation():
    """Verify Tag 70E narrative character set and line wrapping limits."""
    ok, err = validate_tag_70e(":70E::ADTX//SHORT LINE 1\nSHORT LINE 2")
    assert ok is True

    # Line exceeding 35 chars
    long_line = "A" * 40
    ok, err = validate_tag_70e(f":70E::ADTX//{long_line}")
    assert ok is False
    assert "exceeds max 35 characters" in err


# ── 3. SWIFT Block Formatting & Parsing ──────────────────────────────────────

def test_swift_block_formatting_and_parsing(swift_engine):
    """Verify export and round-trip parsing of standard SWIFT FIN blocks (1-5)."""
    b4 = ":16R:GENL\n:20C::SEME//REF12345\n:23G:NEWM\n:16S:GENL\n-"
    raw_fin = swift_engine.format_swift_blocks(
        message_type="564",
        block4_text=b4,
        sender_bic="SOGEFRPAAXXX",
        receiver_bic="CHASUS33XXXX",
        mur="MUR123456",
        uetr="d3b07384-d113-404c-a1e6-4221a9a834e5",
    )

    assert "{1:F01SOGEFRPAAXXX0000000000}" in raw_fin
    assert "{2:I564CHASUS33XXXXN}" in raw_fin
    assert "{108:MUR123456}" in raw_fin
    assert "{121:d3b07384-d113-404c-a1e6-4221a9a834e5}" in raw_fin
    assert "{4:\n:16R:GENL" in raw_fin
    assert "{5:{CHK:" in raw_fin

    parsed = swift_engine.parse_swift_blocks(raw_fin)
    assert parsed["headers"]["sender_bic"] == "SOGEFRPAAXXX"
    assert parsed["headers"]["receiver_bic"] == "CHASUS33XXXX"
    assert parsed["headers"]["message_type"] == "MT564"
    assert parsed["headers"]["mur"] == "MUR123456"
    assert parsed["headers"]["uetr"] == "d3b07384-d113-404c-a1e6-4221a9a834e5"
    assert "20C" in parsed["tag_map"]


# ── 4. ISO 15022 Generation & Reverse Parsing (MT564 / MT544 / MT566 / MT599)

def test_generate_and_parse_mt564(swift_engine):
    """Verify MT564 Corporate Action Notification generation and reverse parsing."""
    raw_mt564 = swift_engine.generate_mt564(
        corporate_action_ref="CA-SAP-2024",
        isin="DE0007164600",
        instrument_name="SAP SE",
        event_type="DIVI",
        mandatory_flag="MAND",
        ex_date="2024-05-18",
        record_date="2024-05-19",
        payment_date="2024-05-22",
        rate_per_share=2.20,
        currency="EUR",
        narrative="SAP SE MANDATORY CASH DIVIDEND",
    )

    validation = swift_engine.validate_swift_message(raw_mt564)
    assert validation["is_valid"] is True
    assert validation["message_type"] == "MT564"

    extracted = swift_engine.swift_mt_to_entity(raw_mt564)
    assert extracted["isin"] == "DE0007164600"
    assert extracted["instrument_name"] == "SAP SE"
    assert extracted["event_type"] == "DIVI"
    assert extracted["amount"] == 2.20
    assert extracted["currency"] == "EUR"
    assert extracted["dates"]["XDTE"] == "20240518"
    assert extracted["dates"]["RDTE"] == "20240519"
    assert extracted["dates"]["PAYD"] == "20240522"


def test_generate_and_parse_mt544(swift_engine):
    """Verify MT544 Settlement / SSI Confirmation generation and reverse parsing."""
    raw_mt544 = swift_engine.generate_mt544(
        trade_id="TRD998822",
        isin="US0378331005",
        instrument_name="Apple Inc",
        amount=2450000.00,
        currency="USD",
        settlement_date="2024-05-11",
        trade_date="2024-05-10",
        counterparty_bic="CHASUS33XXX",
        safekeeping_account="COBADEFF",
        beneficiary_iban="DE44500105175407324931",
        narrative="SSI CORRECTION TARGET2 RESUBMISSION",
    )

    validation = swift_engine.validate_swift_message(raw_mt544)
    assert validation["is_valid"] is True
    assert validation["message_type"] == "MT544"

    extracted = swift_engine.swift_mt_to_entity(raw_mt544)
    assert extracted["isin"] == "US0378331005"
    assert extracted["amount"] == 2450000.00
    assert extracted["currency"] == "USD"
    assert extracted["dates"]["SETT"] == "20240511"
    assert extracted["dates"]["TRAD"] == "20240510"


def test_generate_mt566(swift_engine):
    """Verify MT566 Corporate Action Confirmation generation."""
    raw_mt566 = swift_engine.generate_mt566(
        corporate_action_ref="CA-SAP-2024",
        isin="DE0007164600",
        payment_date="2024-05-22",
        total_entitlement=30800.00,
        currency="EUR",
    )
    validation = swift_engine.validate_swift_message(raw_mt566)
    assert validation["is_valid"] is True
    assert validation["message_type"] == "MT566"


def test_generate_mt599(swift_engine):
    """Verify MT599 Free Format operational messaging."""
    raw_mt599 = swift_engine.generate_mt599(
        reference="INC-883921",
        narrative="SUPPORT TICKET PROVISIONING: Access request for analyst",
    )
    validation = swift_engine.validate_swift_message(raw_mt599)
    assert validation["is_valid"] is True
    assert validation["message_type"] == "MT599"


# ── 5. ISO 20022 XML Generation & Parsing (seev.031 / pacs.008 / camt.053) ─

def test_iso20022_seev_031(swift_engine):
    """Verify seev.031.001.08 XML generation and reverse parsing."""
    xml = swift_engine.generate_seev_031(
        corporate_action_ref="CA-SAP-2024",
        isin="DE0007164600",
        instrument_name="SAP SE",
        event_type="DVCA",
        ex_date="2024-05-18",
        record_date="2024-05-19",
        payment_date="2024-05-22",
        rate_per_share=2.20,
        currency="EUR",
    )

    assert 'xmlns="urn:iso:std:iso:20022:tech:xsd:seev.031.001.08"' in xml
    assert "<CorpActnEvtId>CA-SAP-2024</CorpActnEvtId>" in xml
    assert "<ISIN>DE0007164600</ISIN>" in xml

    parsed = swift_engine.iso20022_to_entity(xml)
    assert parsed["root_tag"] == "Document"
    assert parsed["isin"] == "DE0007164600"
    assert parsed["instrument_name"] == "SAP SE"
    assert parsed["trade_id"] == "CA-SAP-2024"
    assert parsed["amount"] == 2.20
    assert parsed["currency"] == "EUR"
    assert parsed["event_type"] == "DVCA"
    assert parsed["dates"]["ExDt"] == "2024-05-18"


def test_iso20022_pacs_008(swift_engine):
    """Verify pacs.008.001.08 FI Customer Credit Transfer XML generation."""
    xml = swift_engine.generate_pacs_008(
        transaction_id="TRD-998822",
        amount=2450000.00,
        currency="USD",
        settlement_date="2024-05-11",
        debtor_name="Société Générale Paris",
        creditor_name="JPMorgan Chase NY",
        remittance_info="TARGET2 Settlement Correction",
    )

    assert 'xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"' in xml
    assert "<EndToEndId>TRD-998822</EndToEndId>" in xml
    assert 'Ccy="USD">2450000.00</IntrBkSttlmAmt>' in xml

    parsed = swift_engine.iso20022_to_entity(xml)
    assert parsed["trade_id"] == "TRD-998822"
    assert parsed["amount"] == 2450000.00
    assert parsed["currency"] == "USD"
    assert parsed["debtor"] == "Société Générale Paris"
    assert parsed["creditor"] == "JPMorgan Chase NY"


def test_iso20022_camt_053(swift_engine):
    """Verify camt.053.001.08 Bank-to-Customer Statement XML generation."""
    xml = swift_engine.generate_camt_053(
        account_id="ACC-884729104829",
        opening_balance=100000.00,
        closing_balance=130800.00,
        currency="EUR",
        entries=[{"amount": 30800.00, "currency": "EUR", "type": "CRDT", "ref": "DIVI-001"}],
    )

    assert 'xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"' in xml
    assert "<Id>ACC-884729104829</Id>" in xml

    parsed = swift_engine.iso20022_to_entity(xml)
    assert parsed["root_tag"] == "Document"
    assert parsed["currency"] == "EUR"


# ── 6. Batch Conversion on All 5 Sample Emails in Data ───────────────────────

def test_generate_all_sample_messages(swift_engine):
    """Verify all 5 sample emails in data convert cleanly to valid MT and MX messages."""
    samples = swift_engine.generate_all_sample_messages("backend/data/sample_emails.json")
    assert len(samples) == 5

    # Email 1: SAP Dividend
    assert samples[0]["email_id"] == "email_1"
    assert samples[0]["swift_mt"]["message_type"] == "MT564"
    assert samples[0]["swift_mt"]["validation"]["is_valid"] is True
    assert samples[0]["iso20022_mx"]["mx_type"] == "seev.031.001.08"
    assert samples[0]["iso20022_mx"]["is_valid_xml"] is True

    # Email 2: Failed Settlement
    assert samples[1]["email_id"] == "email_2"
    assert samples[1]["swift_mt"]["message_type"] == "MT544"
    assert samples[1]["swift_mt"]["validation"]["is_valid"] is True
    assert samples[1]["iso20022_mx"]["mx_type"] == "pacs.008.001.08"

    # Email 3: Apple Trade Linkage
    assert samples[2]["email_id"] == "email_3"
    assert samples[2]["swift_mt"]["message_type"] == "MT544"
    assert samples[2]["swift_mt"]["validation"]["is_valid"] is True
    assert samples[2]["iso20022_mx"]["mx_type"] == "pacs.008.001.08"

    # Email 4: Reference Data Restructuring
    assert samples[3]["email_id"] == "email_4"
    assert samples[3]["swift_mt"]["message_type"] == "MT564"
    assert samples[3]["swift_mt"]["validation"]["is_valid"] is True
    assert samples[3]["iso20022_mx"]["mx_type"] == "seev.031.001.08"

    # Email 5: HR Access Provisioning
    assert samples[4]["email_id"] == "email_5"
    assert samples[4]["swift_mt"]["message_type"] == "MT599"
    assert samples[4]["swift_mt"]["validation"]["is_valid"] is True
    assert samples[4]["iso20022_mx"]["mx_type"] == "camt.053.001.08"


# ── 7. Action Handlers Integration Tests ─────────────────────────────────────

def test_corporate_action_handler_swift_integration():
    """Verify CorporateActionHandler generates SWIFT MT564, MT566, and seev.031."""
    handler = CorporateActionHandler()
    req = ActionRequest(
        action_type="CORPORATE_ACTION",
        payload={
            "isin": "DE0007164600",
            "instrument_name": "SAP SE",
            "amount": 2.20,
            "currency": "EUR",
        },
        priority="HIGH",
        trace_id="trace-test-ca-12345",
    )
    result = handler.execute(req)
    assert result.status == "SUCCESS"
    assert "swift_mt564" in result.result_data
    assert "swift_mt566" in result.result_data
    assert "iso20022_seev031" in result.result_data
    assert "{1:F01SOGEFRPAAXXX" in result.result_data["swift_mt564"]
    assert result.result_data["swift_validation"]["is_valid"] is True


def test_settlement_handler_swift_integration():
    """Verify SettlementHandler generates SWIFT MT544 and pacs.008."""
    handler = SettlementHandler()
    req = ActionRequest(
        action_type="SETTLEMENT",
        payload={
            "trade_id": "TRD-998822",
            "amount": 2450000.00,
            "currency": "USD",
            "counterparty": "JPMorgan Chase",
        },
        priority="CRITICAL",
        trace_id="trace-test-settle-12345",
    )
    result = handler.execute(req)
    assert result.status == "SUCCESS"
    assert "swift_mt544" in result.result_data
    assert "iso20022_pacs008" in result.result_data
    assert "{2:I544CHASUS33XXXXN}" in result.result_data["swift_mt544"]
    assert result.result_data["swift_validation"]["is_valid"] is True


def test_trade_linkage_handler_swift_integration():
    """Verify TradeLinkageHandler generates SWIFT MT544 and pacs.008."""
    handler = TradeLinkageHandler()
    req = ActionRequest(
        action_type="TRADE_LINKAGE",
        payload={
            "trade_id": "TRD-2024-88712",
            "isin": "US0378331005",
            "instrument_name": "Apple Inc",
            "amount": 1500000.00,
            "currency": "USD",
        },
        priority="MEDIUM",
        trace_id="trace-test-tl-12345",
    )
    result = handler.execute(req)
    assert result.status == "SUCCESS"
    assert "swift_mt544" in result.result_data
    assert "iso20022_pacs008" in result.result_data


def test_instrument_correction_handler_swift_integration():
    """Verify InstrumentCorrectionHandler generates SWIFT MT564 and seev.031."""
    handler = InstrumentCorrectionHandler()
    req = ActionRequest(
        action_type="INSTRUMENT_CORRECTION",
        payload={
            "isin": "XS0987654323",
            "instrument_name": "SocGen 5Y Senior Bond",
        },
        priority="HIGH",
        trace_id="trace-test-ic-12345",
    )
    result = handler.execute(req)
    assert result.status == "SUCCESS"
    assert "swift_mt564" in result.result_data
    assert "iso20022_seev031" in result.result_data


def test_ticket_creator_handler_swift_integration():
    """Verify TicketCreatorHandler generates SWIFT MT599."""
    handler = TicketCreatorHandler()
    req = ActionRequest(
        action_type="SUPPORT_TICKET",
        payload={
            "counterparty": "John Doe",
            "action_type": "Trade Entry",
        },
        priority="LOW",
        trace_id="trace-test-tkt-12345",
    )
    result = handler.execute(req)
    assert result.status == "SUCCESS"
    assert "swift_mt599" in result.result_data
    assert ":20:REF" in result.result_data["swift_mt599"]
