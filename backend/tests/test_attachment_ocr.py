import io
import os
import pytest
from datetime import datetime
from pathlib import Path
from PIL import Image, TiffImagePlugin
from pypdf import PdfWriter

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

from backend.services.attachment_ocr_service import (
    AttachmentOCRService,
    TradeConfirmationRecord,
    SignatureValidationResult,
    AttachmentParseResult,
    normalize_date,
    normalize_numeric,
    validate_isin_checksum
)
from backend.agents.parser_agent import ParserAgent
from backend.models.email_models import ClassifiedEmail, Intent, Urgency, ExtractedEntities
from backend.services.openai_service import OpenAIService
from backend.services.search_service import SearchService


# ── Fixtures & Mock Helpers ──────────────────────────────────────────────────

@pytest.fixture
def ocr_service():
    return AttachmentOCRService()


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    return private_key, pub_pem


def create_sample_pdf(text_lines: list) -> bytes:
    """Creates a valid PDF containing financial trade confirmation text in document info and page content."""
    combined_text = "\n".join(text_lines)
    
    # Construct a minimal standard PDF with document subject metadata and stream content
    content_stream = f"BT /F1 12 Tf 50 700 Td ({combined_text}) Tj ET"
    stream_bytes = content_stream.encode("latin1")
    stream_len = len(stream_bytes)
    
    pdf_template = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(stream_len).encode("ascii") + b" >>\nstream\n"
        + stream_bytes + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Title (Trade Confirmation) /Subject (" + combined_text.encode("latin1") + b") /Author (Societe Generale) >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000280 00000 n \n"
        b"0000000400 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R /Info 5 0 R >>\nstartxref\n500\n%%EOF"
    )
    return pdf_template


def create_sample_tiff(metadata_text: str) -> bytes:
    """Creates a synthetic TIFF image with embedded metadata."""
    img = Image.new("RGB", (300, 150), color=(255, 255, 255))
    buf = io.BytesIO()
    
    # Set TIFF header tag 270 (ImageDescription) with trade metadata text
    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    ifd[270] = metadata_text
    img.save(buf, format="TIFF", tiffinfo=ifd)
    return buf.getvalue()


# ── Unit Tests: Field Normalization & Checksum Helpers ───────────────────────

class TestNormalizationHelpers:

    def test_normalize_date_formats(self):
        assert normalize_date("2024-05-18") == "2024-05-18"
        assert normalize_date("18/05/2024") == "2024-05-18"
        assert normalize_date("18-May-2024") == "2024-05-18"
        assert normalize_date("May 18, 2024") == "2024-05-18"
        assert normalize_date("2024/05/18") == "2024-05-18"
        assert normalize_date(None) is None
        assert normalize_date("") is None

    def test_normalize_numeric_values(self):
        assert normalize_numeric("5,122,500.00") == 5122500.00
        assert normalize_numeric("EUR 5,122,500.00") == 5122500.00
        assert normalize_numeric("$2.45M") == 2450000.00
        assert normalize_numeric("USD 2,842,500.00") == 2842500.00
        assert normalize_numeric("102.450%") == 102.45
        assert normalize_numeric("50,000") == 50000.00
        assert normalize_numeric(125000) == 125000.0
        assert normalize_numeric(None) is None

    def test_isin_checksum_validation(self):
        assert validate_isin_checksum("FR0000120271") is True    # TotalEnergies
        assert validate_isin_checksum("DE0007164600") is True    # SAP SE
        assert validate_isin_checksum("US0378331005") is True    # Apple Inc
        assert validate_isin_checksum("DE0007164609") is False   # Bad check digit
        assert validate_isin_checksum("INVALID") is False


# ── Unit Tests: CSV Trade Confirmation Parser ────────────────────────────────

class TestCSVTradeConfirmationParser:

    def test_parse_standard_csv(self, ocr_service):
        csv_content = """Trade Date,Settlement Date,ISIN,Quantity,Clean Price,Gross Amount,Counterparty BIC,Beneficiary Account
2024-05-18,2024-05-20,FR0000120271,50000,102.450,5122500.00,SOGEUS33XXX,FR7630006000011234567890189
2024-05-18,2024-05-20,DE0007164600,10000,175.500,1755000.00,DBEUMM21XXX,DE89370400440532013000
"""
        result = ocr_service.parse_attachment(csv_content.encode("utf-8"), filename="trades_batch.csv")

        assert result.file_type == "CSV"
        assert len(result.records) == 2
        assert result.errors == []

        rec1 = result.records[0]
        assert rec1.trade_date == "2024-05-18"
        assert rec1.settlement_date == "2024-05-20"
        assert rec1.isin == "FR0000120271"
        assert rec1.quantity == 50000.0
        assert rec1.clean_price == 102.450
        assert rec1.gross_amount == 5122500.00
        assert rec1.counterparty_bic == "SOGEUS33XXX"
        assert rec1.beneficiary_account == "FR7630006000011234567890189"

        rec2 = result.records[1]
        assert rec2.isin == "DE0007164600"
        assert rec2.quantity == 10000.0
        assert rec2.gross_amount == 1755000.00
        assert rec2.counterparty_bic == "DBEUMM21XXX"

    def test_parse_semicolon_delimited_csv(self, ocr_service):
        csv_content = """Deal Date;Value Date;Security ISIN;Nominal;Price;Total Amount;SWIFT BIC;IBAN
18/05/2024;20/05/2024;US0378331005;25000;185.20;4630000.00;CHASUS33XXX;US64CHAS00012345678901
"""
        result = ocr_service.parse_attachment(csv_content.encode("utf-8"), filename="eu_confirmation.csv")

        assert result.file_type == "CSV"
        assert len(result.records) == 1
        rec = result.records[0]
        assert rec.trade_date == "2024-05-18"
        assert rec.settlement_date == "2024-05-20"
        assert rec.isin == "US0378331005"
        assert rec.quantity == 25000.0
        assert rec.clean_price == 185.20
        assert rec.gross_amount == 4630000.00
        assert rec.counterparty_bic == "CHASUS33XXX"


# ── Unit Tests: PDF Trade Confirmation Parser ────────────────────────────────

class TestPDFTradeConfirmationParser:

    def test_parse_pdf_trade_confirmation(self, ocr_service):
        lines = [
            "CONFIRMATION OF OVER-THE-COUNTER TRADE",
            "Trade ID: TRD-2024-998822",
            "Trade Date: 2024-05-18",
            "Settlement Date: 2024-05-20",
            "Security ISIN: FR0000120271",
            "Quantity: 50,000",
            "Clean Price: 102.450",
            "Gross Amount: EUR 5,122,500.00",
            "Counterparty BIC: SOGEUS33XXX",
            "Beneficiary Account: FR7630006000011234567890189",
            "Counterparty: Société Générale Paris"
        ]
        pdf_bytes = create_sample_pdf(lines)
        result = ocr_service.parse_attachment(pdf_bytes, filename="trade_conf_TRD998822.pdf")

        assert result.file_type == "PDF"
        assert len(result.records) >= 1
        rec = result.records[0]
        assert rec.isin == "FR0000120271"
        assert rec.trade_date == "2024-05-18"
        assert rec.settlement_date == "2024-05-20"
        assert rec.quantity == 50000.0
        assert rec.clean_price == 102.450
        assert rec.gross_amount == 5122500.00
        assert rec.counterparty_bic == "SOGEUS33XXX"
        assert rec.beneficiary_account == "FR7630006000011234567890189"

    def test_detect_embedded_pdf_signature(self, ocr_service):
        lines = [
            "BANK STATEMENT - OFFICIAL AUDIT COPY",
            "ISIN: DE0007164600",
            "Gross Amount: EUR 2,500,000.00"
        ]
        raw_pdf = create_sample_pdf(lines)
        # Append mock PDF signature dictionary bytes
        signed_pdf = raw_pdf + b"\n/Type /Sig /ByteRange [ 0 1000 1050 500 ] /Name (Societe Generale Trust CA) /Contents <308201...>\n"
        
        result = ocr_service.parse_attachment(signed_pdf, filename="signed_statement.pdf")
        assert result.signature_result is not None
        assert result.signature_result.is_valid is True
        assert result.signature_result.method == "PDF-PKCS7-EMBEDDED"
        assert "Societe Generale" in result.signature_result.signer_identity


# ── Unit Tests: TIFF Image Trade Confirmation Parser ─────────────────────────

class TestTIFFTradeConfirmationParser:

    def test_parse_tiff_trade_confirmation(self, ocr_service):
        metadata_str = (
            "Trade ID: TRD-2024-774411 | ISIN: US0378331005 | Trade Date: 2024-05-18 | "
            "Settlement Date: 2024-05-20 | Quantity: 15,000 | Clean Price: 189.50 | "
            "Gross Amount: USD 2,842,500.00 | BIC: CHASUS33XXX | Beneficiary Account: US64CHAS00012345678901"
        )
        tiff_bytes = create_sample_tiff(metadata_str)
        result = ocr_service.parse_attachment(tiff_bytes, filename="scanned_trade_doc.tiff")

        assert result.file_type == "TIFF"
        assert len(result.records) >= 1
        rec = result.records[0]
        assert rec.isin == "US0378331005"
        assert rec.trade_date == "2024-05-18"
        assert rec.settlement_date == "2024-05-20"
        assert rec.quantity == 15000.0
        assert rec.clean_price == 189.50
        assert rec.gross_amount == 2842500.00
        assert rec.counterparty_bic == "CHASUS33XXX"
        assert rec.beneficiary_account == "US64CHAS00012345678901"


# ── Unit Tests: Cryptographic Checksum & Digital Signatures ──────────────────

class TestCryptographicValidation:

    def test_sha256_checksum_verification(self, ocr_service):
        payload = b"CRITICAL_TRADE_SETTLEMENT_PAYLOAD_EUR_5M"
        expected_hash = ocr_service.compute_checksum(payload, algorithm="sha256")
        
        # Valid checksum
        res_valid = ocr_service.validate_checksum(payload, expected_hash, algorithm="sha256")
        assert res_valid.is_valid is True
        assert res_valid.status == "CHECKSUM_MATCH"

        # Tampered checksum
        res_tampered = ocr_service.validate_checksum(payload, "0000000000000000000000000000000000000000000000000000000000000000")
        assert res_tampered.is_valid is False
        assert res_tampered.status == "CHECKSUM_MISMATCH"

    def test_hmac_sha256_verification(self, ocr_service):
        payload = b"TRADE_CONFIRMATION_DATA"
        secret = "capital_markets_secret_key_2024"
        
        valid_res = ocr_service.validate_hmac(
            payload,
            signature_hex="",
            secret_key=secret
        )
        computed_sig = valid_res.computed_hash
        res_verified = ocr_service.validate_hmac(payload, computed_sig, secret)
        assert res_verified.is_valid is True
        assert res_verified.status == "VALID"

        # Wrong secret key
        res_wrong_secret = ocr_service.validate_hmac(payload, computed_sig, "wrong_secret_key")
        assert res_wrong_secret.is_valid is False
        assert res_wrong_secret.status == "INVALID"

    def test_rsa_digital_signature_verification(self, ocr_service, rsa_keypair):
        private_key, pub_pem = rsa_keypair
        payload = b"SOCIETE_GENERALE_BANK_STATEMENT_OCTOBER_2024"

        # Sign payload with private key
        signature = private_key.sign(
            payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # 1. Validate authentic signature
        res_valid = ocr_service.validate_rsa_signature(
            payload,
            signature=signature,
            public_key_pem=pub_pem,
            padding_scheme="pkcs1v15",
            hash_algo="sha256"
        )
        assert res_valid.is_valid is True
        assert res_valid.status == "VALID"
        assert res_valid.method == "RSA-PKCS1V15-SHA256"

        # 2. Tampered payload with original signature
        tampered_payload = b"SOCIETE_GENERALE_BANK_STATEMENT_OCTOBER_2024_MODIFIED"
        res_tampered = ocr_service.validate_rsa_signature(
            tampered_payload,
            signature=signature,
            public_key_pem=pub_pem,
            padding_scheme="pkcs1v15",
            hash_algo="sha256"
        )
        assert res_tampered.is_valid is False
        assert res_tampered.status == "INVALID"

    def test_unified_bank_statement_validation(self, ocr_service, rsa_keypair):
        private_key, pub_pem = rsa_keypair
        statement_bytes = b"SWIFT_MT940_CUSTOMER_STATEMENT_MESSAGE"
        
        sig = private_key.sign(statement_bytes, padding.PKCS1v15(), hashes.SHA256())
        auth_context = {
            "signature": sig.hex(),
            "public_key": pub_pem,
            "padding": "pkcs1v15",
            "hash_algo": "sha256"
        }
        
        result = ocr_service.validate_bank_statement_attachment(statement_bytes, auth_context)
        assert result.is_valid is True
        assert result.status == "VALID"


# ── Unit Tests: ParserAgent Integration ──────────────────────────────────────

class TestParserAgentIntegration:

    def test_parser_agent_enriches_with_csv_attachment(self, ocr_service, monkeypatch):
        openai_mock = OpenAIService()
        # Mock LLM extract_entities to return base entities without network call
        monkeypatch.setattr(
            openai_mock,
            "extract_entities",
            lambda email: ExtractedEntities(counterparty="Société Générale")
        )
        search_mock = SearchService()
        monkeypatch.setattr(search_mock, "search_reference_data", lambda isin: {"isin": isin, "name": "TotalEnergies"})

        agent = ParserAgent(openai_service=openai_mock, search_service=search_mock, attachment_ocr_service=ocr_service)

        csv_attachment = """Trade Date,Settlement Date,ISIN,Quantity,Clean Price,Gross Amount,Counterparty BIC,Beneficiary Account
2024-05-18,2024-05-20,FR0000120271,50000,102.450,5122500.00,SOGEUS33XXX,FR7630006000011234567890189
"""
        email = ClassifiedEmail(
            id="email_trade_conf_01",
            sender="operations@socgen.com",
            subject="Trade Confirmation Attached",
            body="Please find attached trade confirmation for execution today.",
            received_at="2024-05-18T10:00:00Z",
            attachments=[csv_attachment],
            intent=Intent.SETTLEMENT,
            confidence=0.98,
            urgency=Urgency.MEDIUM
        )

        entities, duration = agent.run(email)

        assert isinstance(entities, ExtractedEntities)
        assert duration >= 0
        assert entities.isin == "FR0000120271"
        assert entities.trade_date == "2024-05-18"
        assert entities.settlement_date == "2024-05-20"
        assert entities.quantity == 50000.0
        assert entities.clean_price == 102.450
        assert entities.gross_amount == 5122500.00
        assert entities.counterparty_bic == "SOGEUS33XXX"
        assert entities.beneficiary_account == "FR7630006000011234567890189"
        assert entities.attachment_parsed is True
        assert len(entities.attachment_records) == 1

    def test_parser_agent_with_no_attachments(self, ocr_service, monkeypatch):
        openai_mock = OpenAIService()
        monkeypatch.setattr(
            openai_mock,
            "extract_entities",
            lambda email: ExtractedEntities(isin="DE0007164600", amount=2.20)
        )
        search_mock = SearchService()
        monkeypatch.setattr(search_mock, "search_reference_data", lambda isin: {"isin": isin, "name": "SAP SE"})

        agent = ParserAgent(openai_service=openai_mock, search_service=search_mock, attachment_ocr_service=ocr_service)

        email = ClassifiedEmail(
            id="email_no_att",
            sender="client@jpmorgan.com",
            subject="Corporate Action: SAP SE (ISIN: DE0007164600)",
            body="Mandatory cash dividend EUR 2.20 per share for ISIN DE0007164600.",
            received_at="2024-05-18T10:00:00Z",
            attachments=[],
            intent=Intent.CORPORATE_ACTION,
            confidence=0.99,
            urgency=Urgency.LOW
        )

        entities, duration = agent.run(email)
        assert entities.isin == "DE0007164600"
        assert entities.attachment_records is None


# ── Unit Tests: Error Handling & Resilience ──────────────────────────────────

class TestErrorHandlingAndEdgeCases:

    def test_empty_attachment(self, ocr_service):
        result = ocr_service.parse_attachment(b"", filename="empty.pdf")
        assert len(result.errors) > 0
        assert result.records == []

    def test_corrupted_format(self, ocr_service):
        corrupted_bytes = b"\x00\x01\x02CORRUPTED_NON_STRUCTURED_BINARY"
        result = ocr_service.parse_attachment(corrupted_bytes, filename="unknown.xyz")
        assert result.file_type == "UNKNOWN" or len(result.records) == 0
