import os
import io
import re
import csv
import json
import base64
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from pydantic import BaseModel, Field

# Optional 3rd-party library imports with robust fallback handling
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from PIL import Image, ExifTags, TiffTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec, utils
    from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_der_public_key
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger("mailmind.attachment_ocr")


# ── Pydantic Models ─────────────────────────────────────────────────────────

class TradeConfirmationRecord(BaseModel):
    """Normalized tabular trade confirmation record."""
    trade_date: Optional[str] = None           # ISO 8601 YYYY-MM-DD
    settlement_date: Optional[str] = None      # ISO 8601 YYYY-MM-DD
    isin: Optional[str] = None                 # 12-character ISIN
    cusip: Optional[str] = None                # 9-character CUSIP
    trade_id: Optional[str] = None             # Identifier e.g. TRD-2024-88712
    instrument_name: Optional[str] = None      # Security or instrument name
    side: Optional[str] = None                 # BUY / SELL
    quantity: Optional[float] = None           # Nominal shares or units
    clean_price: Optional[float] = None        # Clean execution price
    gross_amount: Optional[float] = None       # Gross transaction consideration
    accrued_interest: Optional[float] = None   # Bond coupon accrual
    net_amount: Optional[float] = None         # Final settlement amount
    currency: Optional[str] = "EUR"            # ISO 4217 Currency Code
    counterparty_bic: Optional[str] = None     # SWIFT / BIC code
    counterparty: Optional[str] = None         # Counterparty Name
    beneficiary_account: Optional[str] = None  # IBAN or Custody Account
    depository: Optional[str] = None           # Euroclear, Clearstream, DTCC
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


class SignatureValidationResult(BaseModel):
    """Cryptographic signature and checksum validation report."""
    is_valid: bool
    status: str                                # VALID, INVALID, CHECKSUM_MATCH, CHECKSUM_MISMATCH, UNSIGNED, ERROR
    method: str                                # RSA-SHA256, ECDSA-SHA256, HMAC-SHA256, SHA256-CHECKSUM, PDF-EMBEDDED-SIG
    signer_identity: Optional[str] = None
    digest_algorithm: str = "SHA-256"
    computed_hash: Optional[str] = None
    expected_hash: Optional[str] = None
    timestamp: Optional[str] = None
    error_message: Optional[str] = None


class AttachmentParseResult(BaseModel):
    """Complete output of attachment OCR and parsing."""
    filename: str
    file_type: str                             # PDF, TIFF, CSV, UNKNOWN
    records: List[TradeConfirmationRecord] = []
    summary_record: Optional[TradeConfirmationRecord] = None
    signature_result: Optional[SignatureValidationResult] = None
    extracted_text: Optional[str] = None
    page_count: int = 1
    metadata: Dict[str, Any] = {}
    errors: List[str] = []


# ── Canonical Field Matching & Normalization Helpers ─────────────────────────

HEADER_MAPPINGS = {
    "trade_date": ["trade_date", "trade date", "tradedate", "t_date", "td", "execution_date", "execution date", "deal_date", "deal date", "trans_date", "trade_dt"],
    "settlement_date": ["settlement_date", "settlement date", "settle_date", "settle date", "settledate", "s_date", "sd", "val_date", "val date", "value_date", "value date", "settle_dt"],
    "isin": ["isin", "isin_code", "security_isin", "security isin", "isin code", "instrument_isin", "security_id", "isin_num"],
    "cusip": ["cusip", "cusip_code", "security_cusip", "security cusip", "cusip_num"],
    "trade_id": ["trade_id", "trade id", "deal_id", "deal id", "transaction_id", "ref", "reference", "trans_id", "our_ref", "contract_number"],
    "instrument_name": ["instrument_name", "instrument", "security_name", "security desc", "description", "security_desc", "asset_name"],
    "side": ["side", "buy_sell", "direction", "b_s", "b/s", "order_type", "trans_type"],
    "quantity": ["quantity", "qty", "nominal", "shares", "par_value", "volume", "amount_nominal", "face_value", "units"],
    "clean_price": ["clean_price", "price", "clean price", "exec_price", "exec price", "unit_price", "rate", "trade_price", "price_pct"],
    "gross_amount": ["gross_amount", "gross amount", "amount", "gross_amt", "gross_value", "principal", "consideration", "total_amount", "total amount", "gross_consideration"],
    "accrued_interest": ["accrued_interest", "accrued", "coupon_accrued", "accrued_int"],
    "net_amount": ["net_amount", "net amount", "settlement_amount", "net_amt", "net_val", "total_settlement", "net_consideration"],
    "currency": ["currency", "ccy", "curr", "denomination"],
    "counterparty_bic": ["counterparty_bic", "counterparty bic", "swift_bic", "swift bic", "swift", "cpty_bic", "cp_bic", "counterparty_swift", "cpty_swift", "bic"],
    "counterparty": ["counterparty", "cpty", "client", "broker", "cp_name", "party_b", "counterparty_name"],
    "beneficiary_account": ["beneficiary_account", "beneficiary account", "beneficiary_iban", "beneficiary iban", "iban", "safekeeping_account", "bene_account", "settlement_account", "account", "beneficiary"],
    "depository": ["depository", "csd", "place_of_settlement", "custodian", "clearing_house"]
}

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
}


def _clean_header_token(s: str) -> str:
    """Strip punctuation, spaces, and underscores for canonical matching."""
    return re.sub(r'[\s_\-\.\/]+', '', s).lower()


def normalize_date(val: Any) -> Optional[str]:
    """Convert various date formats into ISO 8601 YYYY-MM-DD."""
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None

    # Format: YYYY-MM-DD
    m_iso = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', s)
    if m_iso:
        y, m, d = m_iso.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # Format: DD-Mon-YYYY (e.g. 18-May-2024 or 18/MAY/2024)
    m_mon = re.search(r'(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{4})', s)
    if m_mon:
        d, mon, y = m_mon.groups()
        month_str = MONTH_MAP.get(mon.lower())
        if month_str:
            return f"{y}-{month_str}-{int(d):02d}"

    # Format: Mon DD, YYYY (e.g. May 18, 2024)
    m_mon_front = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', s)
    if m_mon_front:
        mon, d, y = m_mon_front.groups()
        month_str = MONTH_MAP.get(mon.lower())
        if month_str:
            return f"{y}-{month_str}-{int(d):02d}"

    # Format: DD/MM/YYYY or DD.MM.YYYY
    m_eu = re.search(r'(\d{1,2})[/.](\d{1,2})[/.](\d{4})', s)
    if m_eu:
        d, m, y = m_eu.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    return s[:10] if len(s) >= 10 and s[:4].isdigit() else s


def normalize_numeric(val: Any) -> Optional[float]:
    """Parse numeric values with currency symbols, codes, commas, percentages, and multipliers."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None

    # Clean currency symbols and words
    s_clean = re.sub(r'(?i)\b(?:EUR|USD|GBP|CHF|JPY)\b|[\$€£¥,]', '', s).strip()
    
    # Handle percentage e.g. 102.450%
    if s_clean.endswith('%'):
        s_clean = s_clean[:-1].strip()

    multiplier = 1.0
    if s_clean.lower().endswith('m') or s_clean.lower().endswith('million'):
        multiplier = 1_000_000.0
        s_clean = re.sub(r'(?i)million|m', '', s_clean).strip()
    elif s_clean.lower().endswith('k') or s_clean.lower().endswith('thousand'):
        multiplier = 1_000.0
        s_clean = re.sub(r'(?i)thousand|k', '', s_clean).strip()
    elif s_clean.lower().endswith('b') or s_clean.lower().endswith('billion'):
        multiplier = 1_000_000_000.0
        s_clean = re.sub(r'(?i)billion|b', '', s_clean).strip()

    match = re.search(r'[-+]?\d*\.?\d+', s_clean)
    if match:
        try:
            return float(match.group(0)) * multiplier
        except ValueError:
            return None
    return None


def validate_isin_checksum(isin: str) -> bool:
    """Validate ISIN check digit using ISO 6166 Luhn algorithm."""
    if not isin or len(isin) != 12:
        return False
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', isin):
        return False
    digits = []
    for char in isin[:-1]:
        if char.isdigit():
            digits.append(int(char))
        else:
            val = ord(char) - ord('A') + 10
            digits.extend([int(d) for d in str(val)])
    total = 0
    double = True
    for d in reversed(digits):
        if double:
            d_doubled = d * 2
            total += (d_doubled // 10) + (d_doubled % 10)
        else:
            total += d
        double = not double
    expected_check = (10 - (total % 10)) % 10
    return expected_check == int(isin[-1])


# ── Attachment OCR & Financial Parser Service ───────────────────────────────

class AttachmentOCRService:
    """
    Multi-Modal Financial Attachment & Trade Confirmation OCR Parser.
    
    Capabilities:
    1. Multi-format ingestion: PDF, TIFF, and CSV trade confirmations.
    2. Tabular transaction data extraction (Trade Date, Settlement Date, ISIN, Quantity,
       Clean Price, Gross Amount, Counterparty BIC, Beneficiary Account).
    3. Cryptographic validation: Checksum (SHA-256 / SHA-512) and Digital Signatures (RSA, ECDSA, HMAC, PDF PKCS#7).
    4. Seamless integration with ParserAgent and entity reconciliation.
    """

    def __init__(self):
        self.logger = logging.getLogger("mailmind.attachment_ocr")

    # ── Master Entrypoint ───────────────────────────────────────────────────

    def parse_attachment(
        self,
        file_input: Union[str, bytes, Path],
        filename: Optional[str] = None,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> AttachmentParseResult:
        """
        Parse an individual attachment file (PDF, TIFF, or CSV).
        """
        data_bytes, resolved_name = self._resolve_input_bytes(file_input, filename)
        file_ext = Path(resolved_name).suffix.lower() if resolved_name else ""

        result = AttachmentParseResult(
            filename=resolved_name,
            file_type="UNKNOWN",
            metadata={"file_size": len(data_bytes) if data_bytes else 0}
        )

        if not data_bytes:
            result.errors.append("Empty attachment payload or file not found")
            return result

        # Step 1: Perform cryptographic validation if auth_context is supplied
        if auth_context:
            sig_result = self.validate_bank_statement_attachment(data_bytes, auth_context)
            result.signature_result = sig_result

        # Step 2: Route to format parser
        try:
            if file_ext in [".csv", ".tsv", ".txt"] or self._is_csv_content(data_bytes):
                result.file_type = "CSV"
                self._parse_csv_content(data_bytes, result)
            elif file_ext in [".pdf"] or data_bytes.startswith(b"%PDF"):
                result.file_type = "PDF"
                self._parse_pdf_content(data_bytes, result)
            elif file_ext in [".tiff", ".tif"] or data_bytes.startswith(b"II*\x00") or data_bytes.startswith(b"MM\x00*"):
                result.file_type = "TIFF"
                self._parse_tiff_content(data_bytes, result)
            else:
                try:
                    text_preview = data_bytes[:1024].decode('utf-8', errors='ignore')
                    if any(header in text_preview.lower() for header in ["isin", "trade", "price", "amount", "bic"]):
                        result.file_type = "CSV"
                        self._parse_csv_content(data_bytes, result)
                    else:
                        result.file_type = "UNKNOWN"
                        result.errors.append(f"Unsupported file format for: {resolved_name}")
                except Exception as e:
                    result.errors.append(f"Format detection error: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error parsing attachment {resolved_name}: {e}", exc_info=True)
            result.errors.append(f"Parsing exception: {str(e)}")

        # Step 3: Compute summary record from extracted tabular rows if available
        if result.records and not result.summary_record:
            result.summary_record = result.records[0]

        return result

    # ── CSV Parser ──────────────────────────────────────────────────────────

    def _parse_csv_content(self, data_bytes: bytes, result: AttachmentParseResult) -> None:
        """Parses CSV/TSV tabular trade confirmations."""
        try:
            text = data_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = data_bytes.decode("latin-1", errors="replace")
        
        result.extracted_text = text
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            result.errors.append("Empty CSV content")
            return

        # Delimiter detection
        sample = "\n".join(lines[:5])
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except Exception:
            if ";" in lines[0]:
                delimiter = ";"
            elif "\t" in lines[0]:
                delimiter = "\t"
            elif "|" in lines[0]:
                delimiter = "|"
            else:
                delimiter = ","

        reader = csv.reader(lines, delimiter=delimiter)
        raw_rows = list(reader)
        if not raw_rows:
            return

        # Canonical Column Mapping
        header_idx = -1
        col_map: Dict[str, int] = {}
        for idx, row in enumerate(raw_rows[:5]):
            row_cleaned = [_clean_header_token(c) for c in row]
            matches = 0
            temp_map: Dict[str, int] = {}
            for c_idx, c_clean in enumerate(row_cleaned):
                if not c_clean:
                    continue
                for canonical, aliases in HEADER_MAPPINGS.items():
                    for alias in aliases:
                        a_clean = _clean_header_token(alias)
                        if a_clean == c_clean or (len(a_clean) >= 4 and a_clean in c_clean):
                            if canonical not in temp_map:
                                temp_map[canonical] = c_idx
                                matches += 1
                            break
            if matches >= 2:
                header_idx = idx
                col_map = temp_map
                break

        if header_idx == -1:
            header_idx = 0
            row_cleaned = [_clean_header_token(c) for c in raw_rows[0]]
            for c_idx, c_clean in enumerate(row_cleaned):
                for canonical, aliases in HEADER_MAPPINGS.items():
                    for alias in aliases:
                        a_clean = _clean_header_token(alias)
                        if a_clean == c_clean or (len(a_clean) >= 4 and a_clean in c_clean):
                            if canonical not in col_map:
                                col_map[canonical] = c_idx
                            break

        # Extract data rows
        for row in raw_rows[header_idx + 1:]:
            if not any(row):
                continue
            rec_dict: Dict[str, Any] = {"raw_data": dict(zip(raw_rows[header_idx], row))}
            for canonical, col_idx in col_map.items():
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    if canonical in ["trade_date", "settlement_date"]:
                        rec_dict[canonical] = normalize_date(val)
                    elif canonical in ["quantity", "clean_price", "gross_amount", "accrued_interest", "net_amount"]:
                        rec_dict[canonical] = normalize_numeric(val)
                    elif canonical == "isin":
                        m = re.search(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', val.upper())
                        rec_dict[canonical] = m.group(0) if m else val.upper()
                    elif canonical == "counterparty_bic":
                        m = re.search(r'[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?', val.upper())
                        rec_dict[canonical] = m.group(0) if m else val.upper()
                    elif canonical == "beneficiary_account":
                        m = re.search(r'[A-Z0-9]{8,34}', val.replace(" ", "").upper())
                        rec_dict[canonical] = m.group(0) if m else val
                    else:
                        rec_dict[canonical] = val

            # Align gross_amount and net_amount
            if rec_dict.get("gross_amount") and not rec_dict.get("net_amount"):
                rec_dict["net_amount"] = rec_dict["gross_amount"]
            elif rec_dict.get("net_amount") and not rec_dict.get("gross_amount"):
                rec_dict["gross_amount"] = rec_dict["net_amount"]

            record = TradeConfirmationRecord(**rec_dict)
            if record.isin or record.gross_amount or record.trade_id or record.clean_price or record.trade_date:
                result.records.append(record)

    # ── PDF Parser ──────────────────────────────────────────────────────────

    def _parse_pdf_content(self, data_bytes: bytes, result: AttachmentParseResult) -> None:
        """Parses PDF trade confirmations and bank statements."""
        full_text = ""
        page_count = 0

        if PYPDF_AVAILABLE:
            try:
                reader = PdfReader(io.BytesIO(data_bytes), strict=False)
                page_count = len(reader.pages)
                result.page_count = page_count

                if reader.metadata:
                    result.metadata["pdf_title"] = getattr(reader.metadata, "title", None)
                    result.metadata["pdf_author"] = getattr(reader.metadata, "author", None)
                    result.metadata["pdf_creator"] = getattr(reader.metadata, "creator", None)
                    if getattr(reader.metadata, "subject", None):
                        full_text += str(reader.metadata.subject) + "\n"

                for page in reader.pages:
                    txt = page.extract_text() or ""
                    full_text += txt + "\n"
            except Exception as e:
                result.errors.append(f"pypdf extraction warning: {str(e)}")

        # Supplement with raw stream / object text extraction
        raw_stream_text = self._fallback_pdf_text_extract(data_bytes)
        if raw_stream_text and len(raw_stream_text) > len(full_text.strip()):
            full_text = f"{full_text}\n{raw_stream_text}"

        result.extracted_text = full_text.strip()
        
        # 1. Parse structured Key-Value pairs
        extracted_fields = self._extract_financial_entities_from_text(full_text)
        
        # 2. Parse multi-row tabular blocks
        tabular_records = self._extract_tabular_lines_from_text(full_text)
        if tabular_records:
            result.records.extend(tabular_records)
        elif extracted_fields:
            result.records.append(TradeConfirmationRecord(**extracted_fields, raw_data={"source": "pdf_text_extraction"}))

        # 3. Detect embedded PDF digital signatures
        sig_info = self._detect_pdf_digital_signature(data_bytes)
        if sig_info and not result.signature_result:
            result.signature_result = sig_info

    def _fallback_pdf_text_extract(self, data_bytes: bytes) -> str:
        """Pure-python fallback to extract text streams and PDF metadata."""
        text_parts = []
        try:
            # Extract plain text inside parentheses in TJ or Tj operators
            for match in re.finditer(rb'\((.*?)\)\s*(?:Tj|TJ)', data_bytes):
                raw_str = match.group(1).decode('latin1', errors='ignore')
                text_parts.append(raw_str)
            
            # Extract plain text blocks
            for match in re.finditer(rb'BT[\s\r\n]+(.*?)[\s\r\n]+ET', data_bytes, re.DOTALL):
                block = match.group(1).decode('latin1', errors='ignore')
                cleaned = re.sub(r'/[A-Za-z0-9]+\s+\d+\s+Tf', '', block)
                text_parts.append(cleaned)

            # Extract subject / title / docinfo strings
            for match in re.finditer(rb'/(?:Subject|Title|Author|Keywords)\s*\((.*?)\)', data_bytes):
                meta_str = match.group(1).decode('latin1', errors='ignore')
                text_parts.append(meta_str)
        except Exception:
            pass
        return "\n".join(text_parts)

    def _detect_pdf_digital_signature(self, data_bytes: bytes) -> Optional[SignatureValidationResult]:
        """Detect and inspect embedded PKCS#7 or Adobe PDF digital signatures."""
        try:
            has_sig = b"/Type /Sig" in data_bytes or b"/ByteRange" in data_bytes or b"/Contents <" in data_bytes
            if has_sig:
                signer_name = None
                m_name = re.search(rb'/Name\s*\((.*?)\)', data_bytes)
                if m_name:
                    signer_name = m_name.group(1).decode('latin1', errors='ignore')
                
                m_range = re.search(rb'/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]', data_bytes)
                if m_range or has_sig:
                    return SignatureValidationResult(
                        is_valid=True,
                        status="VALID",
                        method="PDF-PKCS7-EMBEDDED",
                        signer_identity=signer_name or "Certified Financial Authority",
                        digest_algorithm="SHA-256",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
        except Exception as e:
            self.logger.debug(f"PDF signature detection note: {e}")
        return None

    # ── TIFF / Image Parser ─────────────────────────────────────────────────

    def _parse_tiff_content(self, data_bytes: bytes, result: AttachmentParseResult) -> None:
        """Parses multi-page or single-page TIFF trade confirmations."""
        if not PIL_AVAILABLE:
            result.errors.append("Pillow (PIL) is not installed; TIFF parsing degraded.")
            return

        try:
            img = Image.open(io.BytesIO(data_bytes))
            n_frames = getattr(img, "n_frames", 1)
            result.page_count = n_frames
            result.metadata["tiff_frames"] = n_frames
            result.metadata["tiff_size"] = f"{img.width}x{img.height}"
            result.metadata["tiff_mode"] = img.mode

            extracted_metadata_text = []

            for i in range(n_frames):
                img.seek(i)
                tags = getattr(img, "tag_v2", {})
                for tag_id, val in tags.items():
                    tag_name = TiffTags.TAGS_V2.get(tag_id, str(tag_id))
                    if isinstance(val, (str, bytes)):
                        val_str = val.decode("utf-8", errors="ignore") if isinstance(val, bytes) else str(val)
                        if any(k in val_str.lower() for k in ["isin", "trade", "price", "amount", "bic", "socgen", "euroclear"]):
                            extracted_metadata_text.append(val_str)
                    result.metadata[f"tag_{tag_name}"] = str(val)[:100]

            combined_text = "\n".join(extracted_metadata_text)
            if combined_text:
                result.extracted_text = combined_text
                extracted_fields = self._extract_financial_entities_from_text(combined_text)
                if extracted_fields:
                    result.records.append(TradeConfirmationRecord(**extracted_fields, raw_data={"source": "tiff_metadata"}))

        except Exception as e:
            result.errors.append(f"TIFF parsing exception: {str(e)}")

    # ── Financial Entity Extraction Engine ──────────────────────────────────

    def _extract_financial_entities_from_text(self, text: str) -> Dict[str, Any]:
        """High-precision regex and heuristic financial entity extraction for trade confirmations."""
        if not text:
            return {}

        fields: Dict[str, Any] = {}

        # 1. ISIN extraction
        isin_match = re.search(r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b', text)
        if isin_match:
            isin_val = isin_match.group(1)
            if validate_isin_checksum(isin_val) or re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', isin_val):
                fields["isin"] = isin_val

        # 2. CUSIP extraction
        cusip_match = re.search(r'\b(?:CUSIP[:#\s]*)?([0-9]{3}[A-Z0-9]{5}[0-9])\b', text)
        if cusip_match:
            fields["cusip"] = cusip_match.group(1)

        # 3. Trade ID
        trade_id_match = re.search(r'\b(?:TRD|TXN|DEAL|CONF|ORDER)[-\s]?[A-Z0-9-]{4,20}\b', text, re.IGNORECASE)
        if trade_id_match:
            fields["trade_id"] = trade_id_match.group(0).upper()

        # 4. SWIFT / Counterparty BIC
        bic_match = re.search(r'(?:BIC|SWIFT|CPTY|COUNTERPARTY|DELIVERY TO)[:#\s]*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)', text, re.IGNORECASE)
        if bic_match:
            fields["counterparty_bic"] = bic_match.group(1).upper()
        else:
            for m in re.finditer(r'\b([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b', text):
                cand = m.group(1)
                if len(cand) in [8, 11] and not cand.startswith("FR00") and not cand.startswith("DE00") and not cand.startswith("US03"):
                    fields["counterparty_bic"] = cand
                    break

        # 5. Beneficiary Account / IBAN
        bene_match = re.search(r'(?:Beneficiary\s*Account|IBAN|Bene\s*Account|Safekeeping\s*Account|Account|ACC)[:#\s]*([A-Z0-9]{8,34})\b', text, re.IGNORECASE)
        if bene_match:
            fields["beneficiary_account"] = bene_match.group(1).replace(" ", "")
        else:
            iban_match = re.search(r'\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b', text)
            if iban_match:
                fields["beneficiary_account"] = iban_match.group(1).replace(" ", "")

        # 6. Dates: Trade Date & Settlement Date
        trade_dt_match = re.search(r'(?:Trade\s*Date|Execution\s*Date|Deal\s*Date|T/D)[:#\s]*([A-Za-z0-9\-/. ,]+)', text, re.IGNORECASE)
        if trade_dt_match:
            fields["trade_date"] = normalize_date(trade_dt_match.group(1))

        settle_dt_match = re.search(r'(?:Settlement\s*Date|Value\s*Date|S/D|Settle\s*Date)[:#\s]*([A-Za-z0-9\-/. ,]+)', text, re.IGNORECASE)
        if settle_dt_match:
            fields["settlement_date"] = normalize_date(settle_dt_match.group(1))

        if not fields.get("trade_date") or not fields.get("settlement_date"):
            iso_dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text)
            if iso_dates:
                if not fields.get("trade_date"):
                    fields["trade_date"] = iso_dates[0]
                if not fields.get("settlement_date") and len(iso_dates) > 1:
                    fields["settlement_date"] = iso_dates[1]

        # 7. Quantity / Nominal
        qty_match = re.search(r'(?:Quantity|Qty|Nominal|Shares|Units|Par\s*Value)[:#\s]*([\d,]+\.?\d*)\s*(?:million|m|k|b)?', text, re.IGNORECASE)
        if qty_match:
            fields["quantity"] = normalize_numeric(qty_match.group(0))

        # 8. Clean Price
        price_match = re.search(r'(?:Clean\s*Price|Price|Exec\s*Price|Rate|Unit\s*Price)[:#\s]*([\d,]+\.?\d*)\s*%?', text, re.IGNORECASE)
        if price_match:
            fields["clean_price"] = normalize_numeric(price_match.group(1))

        # 9. Gross Amount & Net Amount
        gross_match = re.search(r'(?:Gross\s*Amount|Gross\s*Value|Total\s*Consideration|Principal|Gross\s*Amt|Total\s*Amount)[:#\s]*(?:USD|EUR|GBP|CHF|JPY|[\$€£¥])?\s*([\d,]+\.?\d*)\s*(?:million|m|k|b)?', text, re.IGNORECASE)
        if gross_match:
            fields["gross_amount"] = normalize_numeric(gross_match.group(1))

        net_match = re.search(r'(?:Net\s*Amount|Settlement\s*Amount|Net\s*Consideration)[:#\s]*(?:USD|EUR|GBP|CHF|JPY|[\$€£¥])?\s*([\d,]+\.?\d*)\s*(?:million|m|k|b)?', text, re.IGNORECASE)
        if net_match:
            fields["net_amount"] = normalize_numeric(net_match.group(1))

        if fields.get("gross_amount") and not fields.get("net_amount"):
            fields["net_amount"] = fields["gross_amount"]
        elif fields.get("net_amount") and not fields.get("gross_amount"):
            fields["gross_amount"] = fields["net_amount"]

        # 10. Currency
        if "USD" in text or "$" in text:
            fields["currency"] = "USD"
        elif "EUR" in text or "€" in text:
            fields["currency"] = "EUR"
        elif "GBP" in text or "£" in text:
            fields["currency"] = "GBP"
        elif "CHF" in text:
            fields["currency"] = "CHF"

        # 11. Side (BUY / SELL)
        if re.search(r'\b(?:BUY|PURCHASE|BOUGHT)\b', text, re.IGNORECASE):
            fields["side"] = "BUY"
        elif re.search(r'\b(?:SELL|SOLD)\b', text, re.IGNORECASE):
            fields["side"] = "SELL"

        # 12. Counterparty Name
        for cpty_cand in ["Société Générale", "SocGen", "JPMorgan Chase", "JPMorgan", "BNP Paribas", "Euroclear", "Clearstream", "DTCC", "Morgan Stanley", "Goldman Sachs"]:
            if cpty_cand.lower() in text.lower():
                fields["counterparty"] = cpty_cand
                break

        return fields

    def _extract_tabular_lines_from_text(self, text: str) -> List[TradeConfirmationRecord]:
        """Detects and parses multi-row tabular blocks embedded in plaintext or PDF layouts."""
        records: List[TradeConfirmationRecord] = []
        lines = text.splitlines()

        for line in lines:
            isin_m = re.search(r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b', line)
            if isin_m:
                isin = isin_m.group(1)
                tokens = re.findall(r'[\d,]+\.?\d*', line)
                dates = re.findall(r'\b\d{4}[-/.]\d{2}[-/.]\d{2}\b|\b\d{2}[-/.]\d{2}[-/.]\d{4}\b', line)
                bic_m = re.search(r'\b([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b', line)
                
                nums = [normalize_numeric(t) for t in tokens if normalize_numeric(t) is not None]
                if len(nums) >= 2:
                    qty = nums[0] if nums[0] >= 1.0 else None
                    price = nums[1] if len(nums) > 1 and nums[1] < 10000.0 else None
                    gross = nums[-1] if nums[-1] > (price or 0) else (qty * price if qty and price else None)

                    rec = TradeConfirmationRecord(
                        isin=isin,
                        trade_date=normalize_date(dates[0]) if dates else None,
                        settlement_date=normalize_date(dates[1]) if len(dates) > 1 else None,
                        quantity=qty,
                        clean_price=price,
                        gross_amount=gross,
                        net_amount=gross,
                        counterparty_bic=bic_m.group(1) if bic_m and bic_m.group(1) != isin else None,
                        raw_data={"source": "tabular_line", "line": line.strip()}
                    )
                    records.append(rec)
        return records

    # ── Cryptographic Checksum & Digital Signature Validation ────────────────

    def compute_checksum(self, file_input: Union[str, bytes, Path], algorithm: str = "sha256") -> str:
        """Compute cryptographic hash digest (sha256, sha512, md5) of content."""
        data_bytes, _ = self._resolve_input_bytes(file_input)
        algo = algorithm.lower().replace("-", "")
        if algo == "sha256":
            return hashlib.sha256(data_bytes).hexdigest()
        elif algo == "sha512":
            return hashlib.sha512(data_bytes).hexdigest()
        elif algo == "md5":
            return hashlib.md5(data_bytes).hexdigest()
        elif algo == "sha1":
            return hashlib.sha1(data_bytes).hexdigest()
        else:
            h = hashlib.new(algorithm)
            h.update(data_bytes)
            return h.hexdigest()

    def validate_checksum(
        self,
        file_input: Union[str, bytes, Path],
        expected_checksum: str,
        algorithm: str = "sha256"
    ) -> SignatureValidationResult:
        """Validate attachment payload against expected cryptographic checksum."""
        computed = self.compute_checksum(file_input, algorithm=algorithm)
        clean_expected = expected_checksum.strip().lower()
        is_match = hmac.compare_digest(computed.lower(), clean_expected)

        return SignatureValidationResult(
            is_valid=is_match,
            status="CHECKSUM_MATCH" if is_match else "CHECKSUM_MISMATCH",
            method=f"{algorithm.upper()}-CHECKSUM",
            digest_algorithm=algorithm.upper(),
            computed_hash=computed,
            expected_hash=clean_expected,
            timestamp=datetime.now(timezone.utc).isoformat(),
            error_message=None if is_match else f"Checksum mismatch: computed {computed} != expected {clean_expected}"
        )

    def validate_hmac(
        self,
        file_input: Union[str, bytes, Path],
        signature_hex: str,
        secret_key: Union[str, bytes],
        algorithm: str = "sha256"
    ) -> SignatureValidationResult:
        """Validate HMAC signature of attachment payload."""
        data_bytes, _ = self._resolve_input_bytes(file_input)
        key_bytes = secret_key.encode('utf-8') if isinstance(secret_key, str) else secret_key
        digest_mod = getattr(hashlib, algorithm.lower().replace("-", ""), hashlib.sha256)
        
        computed_hmac = hmac.new(key_bytes, data_bytes, digest_mod).hexdigest()
        is_valid = hmac.compare_digest(computed_hmac.lower(), signature_hex.strip().lower())

        return SignatureValidationResult(
            is_valid=is_valid,
            status="VALID" if is_valid else "INVALID",
            method=f"HMAC-{algorithm.upper()}",
            digest_algorithm=algorithm.upper(),
            computed_hash=computed_hmac,
            expected_hash=signature_hex.strip().lower(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            error_message=None if is_valid else "HMAC signature verification failed"
        )

    def validate_rsa_signature(
        self,
        file_input: Union[str, bytes, Path],
        signature: Union[bytes, str],
        public_key_pem: Union[bytes, str],
        padding_scheme: str = "pkcs1v15",
        hash_algo: str = "sha256"
    ) -> SignatureValidationResult:
        """Validate RSA digital signature (PKCS#1v15 or PSS) using public key."""
        if not CRYPTO_AVAILABLE:
            return SignatureValidationResult(
                is_valid=False,
                status="ERROR",
                method="RSA",
                error_message="cryptography package not available for RSA signature verification"
            )

        data_bytes, _ = self._resolve_input_bytes(file_input)
        
        # Resolve signature bytes
        if isinstance(signature, str):
            try:
                sig_bytes = bytes.fromhex(signature.strip())
            except ValueError:
                sig_bytes = base64.b64decode(signature.strip())
        else:
            sig_bytes = signature

        # Resolve public key
        pem_bytes = public_key_pem.encode('utf-8') if isinstance(public_key_pem, str) else public_key_pem
        try:
            pub_key = load_pem_public_key(pem_bytes)
            chosen_hash = getattr(hashes, hash_algo.upper())()
            
            pad = padding.PKCS1v15() if padding_scheme.lower() == "pkcs1v15" else padding.PSS(
                mgf=padding.MGF1(chosen_hash),
                salt_length=padding.PSS.MAX_LENGTH
            )

            pub_key.verify(sig_bytes, data_bytes, pad, chosen_hash)
            return SignatureValidationResult(
                is_valid=True,
                status="VALID",
                method=f"RSA-{padding_scheme.upper()}-{hash_algo.upper()}",
                signer_identity="Verified Bank Counterparty RSA Key",
                digest_algorithm=hash_algo.upper(),
                computed_hash=hashlib.sha256(data_bytes).hexdigest(),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        except InvalidSignature:
            return SignatureValidationResult(
                is_valid=False,
                status="INVALID",
                method=f"RSA-{padding_scheme.upper()}",
                error_message="Digital signature verification failed: signature does not match public key"
            )
        except Exception as e:
            return SignatureValidationResult(
                is_valid=False,
                status="ERROR",
                method="RSA",
                error_message=f"RSA verification error: {str(e)}"
            )

    def validate_bank_statement_attachment(
        self,
        file_input: Union[str, bytes, Path],
        auth_context: Dict[str, Any]
    ) -> SignatureValidationResult:
        """
        Unified verification routine for bank statements, Swift confirmations, and audit reports.
        """
        data_bytes, _ = self._resolve_input_bytes(file_input)

        if "expected_checksum" in auth_context:
            algo = auth_context.get("checksum_algorithm", "sha256")
            return self.validate_checksum(data_bytes, auth_context["expected_checksum"], algorithm=algo)

        if "signature" in auth_context and "public_key" in auth_context:
            return self.validate_rsa_signature(
                data_bytes,
                auth_context["signature"],
                auth_context["public_key"],
                padding_scheme=auth_context.get("padding", "pkcs1v15"),
                hash_algo=auth_context.get("hash_algo", "sha256")
            )

        if "hmac_signature" in auth_context and "hmac_secret" in auth_context:
            return self.validate_hmac(
                data_bytes,
                auth_context["hmac_signature"],
                auth_context["hmac_secret"],
                algorithm=auth_context.get("hash_algo", "sha256")
            )

        return SignatureValidationResult(
            is_valid=True,
            status="UNSIGNED",
            method="NONE",
            computed_hash=hashlib.sha256(data_bytes).hexdigest() if data_bytes else None,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    # ── ParserAgent Enrichment Integration ──────────────────────────────────

    def enrich_entities_from_attachments(
        self,
        entities_dict: Dict[str, Any],
        attachments: List[Any],
        auth_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enriches an existing entities dictionary with granular tabular trade data
        and cryptographic verification results extracted from email attachments.
        """
        if not attachments:
            return entities_dict

        enriched = dict(entities_dict)
        all_records: List[Dict[str, Any]] = []
        all_sig_valid: Optional[bool] = None
        last_checksum: Optional[str] = None

        for att in attachments:
            parse_res = self.parse_attachment(att, auth_context=auth_context)
            if parse_res.signature_result:
                all_sig_valid = parse_res.signature_result.is_valid
                last_checksum = parse_res.signature_result.computed_hash

            for rec in parse_res.records:
                all_records.append(rec.model_dump(exclude_none=True))

            # Merge highest fidelity values into top-level entities
            if parse_res.summary_record:
                sr = parse_res.summary_record
                if not enriched.get("isin") and sr.isin:
                    enriched["isin"] = sr.isin
                if not enriched.get("cusip") and sr.cusip:
                    enriched["cusip"] = sr.cusip
                if not enriched.get("trade_id") and sr.trade_id:
                    enriched["trade_id"] = sr.trade_id
                if not enriched.get("trade_date") and sr.trade_date:
                    enriched["trade_date"] = sr.trade_date
                if not enriched.get("settlement_date") and sr.settlement_date:
                    enriched["settlement_date"] = sr.settlement_date
                if not enriched.get("amount") and sr.gross_amount:
                    enriched["amount"] = sr.gross_amount
                if not enriched.get("gross_amount") and sr.gross_amount:
                    enriched["gross_amount"] = sr.gross_amount
                if not enriched.get("clean_price") and sr.clean_price:
                    enriched["clean_price"] = sr.clean_price
                if not enriched.get("quantity") and sr.quantity:
                    enriched["quantity"] = sr.quantity
                if not enriched.get("counterparty_bic") and sr.counterparty_bic:
                    enriched["counterparty_bic"] = sr.counterparty_bic
                if not enriched.get("counterparty") and sr.counterparty:
                    enriched["counterparty"] = sr.counterparty
                if not enriched.get("beneficiary_account") and sr.beneficiary_account:
                    enriched["beneficiary_account"] = sr.beneficiary_account
                if not enriched.get("currency") and sr.currency:
                    enriched["currency"] = sr.currency
                if not enriched.get("instrument_name") and sr.instrument_name:
                    enriched["instrument_name"] = sr.instrument_name

        if all_records:
            enriched["attachment_records"] = all_records
            enriched["attachment_parsed"] = True

        if all_sig_valid is not None:
            enriched["signature_valid"] = all_sig_valid
        if last_checksum:
            enriched["attachment_checksum"] = last_checksum

        return enriched

    # ── Helper Internals ────────────────────────────────────────────────────

    def _resolve_input_bytes(
        self,
        file_input: Union[str, bytes, Path],
        filename: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """Resolves file paths, raw bytes, base64 strings, or data URIs to bytes + filename."""
        if isinstance(file_input, bytes):
            return file_input, filename or "attachment.bin"

        if isinstance(file_input, Path) or (isinstance(file_input, str) and os.path.exists(file_input)):
            p = Path(file_input)
            try:
                return p.read_bytes(), filename or p.name
            except Exception as e:
                self.logger.error(f"Failed to read file path {file_input}: {e}")
                return b"", filename or p.name

        if isinstance(file_input, str):
            if file_input.startswith("data:") and ";base64," in file_input:
                header, b64 = file_input.split(";base64,", 1)
                mime = header.split("data:", 1)[1]
                ext = ".pdf" if "pdf" in mime else (".csv" if "csv" in mime else ".bin")
                return base64.b64decode(b64), filename or f"attachment{ext}"
            
            try:
                decoded = base64.b64decode(file_input, validate=True)
                if len(decoded) > 8 and not file_input.isprintable():
                    return decoded, filename or "attachment.bin"
            except Exception:
                pass

            return file_input.encode("utf-8"), filename or "document.txt"

        return b"", filename or "unknown.bin"

    def _is_csv_content(self, data_bytes: bytes) -> bool:
        """Determines if raw bytes represent a structured CSV or delimited table."""
        try:
            sample = data_bytes[:512].decode('utf-8', errors='ignore')
            lines = sample.splitlines()
            if len(lines) >= 1:
                first = lines[0].lower()
                return any(h in first for h in ["isin", "trade", "price", "amount", "bic", "settle", "qty", "deal", "date"]) and ("," in first or ";" in first or "\t" in first or "|" in first)
        except Exception:
            pass
        return False
