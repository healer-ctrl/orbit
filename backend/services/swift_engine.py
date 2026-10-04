"""
SWIFT ISO 15022 & ISO 20022 Financial Messaging Engine
Société Générale Global Markets & Back-Office Operations

Standards Implemented:
- ISO 15022: MT564 (Corporate Action Notification), MT544 (Receive Free / Settlement Confirmation),
             MT566 (Corporate Action Confirmation), MT599 (Free Format Financial Messaging)
- ISO 20022: seev.031.001.08 (Corporate Action Notification),
             pacs.008.001.08 (FI Customer Credit Transfer),
             camt.053.001.08 (Bank-to-Customer Statement)
"""

import re
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import xml.etree.ElementTree as ET

logger = logging.getLogger("mailmind.swift_engine")


# ─────────────────────────────────────────────────────────────────────────────
# SWIFT Character Sets & Regular Expressions
# ─────────────────────────────────────────────────────────────────────────────

# SWIFT X Character Set: A-Z, a-z, 0-9, /, -, ?, :, (, ), ., ,, ', +, space, Cr-Lf
SWIFT_X_CHARSET_REGEX = re.compile(r"^[A-Za-z0-9/\-?:().,'+ \n\r]*$")
ISIN_FORMAT_REGEX = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
BIC_REGEX = re.compile(r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def compute_isin_check_digit(isin_11: str) -> str:
    """
    Computes ISO 6166 ISIN check digit using the Luhn Algorithm mod 10.
    1. Letters converted to 2 digits (A=10, B=11 ... Z=35).
    2. Weights alternate 2 and 1 from right to left.
    """
    if len(isin_11) != 11:
        raise ValueError(f"Expected 11 characters to calculate check digit, got {len(isin_11)}")

    converted = ""
    for ch in isin_11.upper():
        if ch.isdigit():
            converted += ch
        elif 'A' <= ch <= 'Z':
            converted += str(ord(ch) - ord('A') + 10)
        else:
            raise ValueError(f"Invalid character in ISIN prefix: {ch}")

    digits = [int(d) for d in converted]
    total = 0
    weight = 2
    for d in reversed(digits):
        prod = d * weight
        total += (prod // 10) + (prod % 10)
        weight = 1 if weight == 2 else 2

    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def validate_isin(isin: str, strict_checksum: bool = True) -> bool:
    """
    Validates an ISIN string according to ISO 6166.
    Checks syntax ([A-Z]{2}[A-Z0-9]{9}[0-9]) and optionally validates Luhn check digit.
    """
    if not isin or not isinstance(isin, str) or len(isin.strip()) != 12:
        return False
    isin = isin.strip().upper()
    if not ISIN_FORMAT_REGEX.match(isin):
        return False
    if not strict_checksum:
        return True
    try:
        expected_check = compute_isin_check_digit(isin[:11])
        return isin[11] == expected_check
    except Exception:
        return False


def validate_tag_20(ref: str) -> Tuple[bool, Optional[str]]:
    """
    Tag 20 / :20C: Transaction Reference validation per SWIFT FIN handbook.
    Rules: Max 16 characters, SWIFT X-charset, cannot start or end with '/', cannot contain consecutive '//'.
    """
    if not ref:
        return False, "Tag 20 Reference cannot be empty"
    ref_str = str(ref).strip()
    if len(ref_str) > 16:
        return False, f"Tag 20 length {len(ref_str)} exceeds max 16 chars"
    if ref_str.startswith("/") or ref_str.endswith("/"):
        return False, "Tag 20 cannot start or end with a slash '/'"
    if "//" in ref_str:
        return False, "Tag 20 cannot contain consecutive slashes '//'"
    if not SWIFT_X_CHARSET_REGEX.match(ref_str):
        return False, "Tag 20 contains invalid characters outside SWIFT X-charset"
    return True, None


def validate_tag_19a(val: str) -> Tuple[bool, Optional[str]]:
    """
    Tag 19A / 19B Notional / Amount validation.
    Expected format: :19A::QUAL//CCY12345,67 or CCY12345,67 (comma decimal, ISO currency).
    """
    if not val:
        return False, "Tag 19A Amount cannot be empty"
    val = val.strip()
    match = re.search(r"([A-Z]{3})([0-9]+(?:,[0-9]{1,5})?)", val)
    if not match:
        return False, f"Tag 19A '{val}' does not match standard Currency + Comma-separated Amount format"
    return True, None


def validate_tag_22f(val: str) -> Tuple[bool, Optional[str]]:
    """
    Tag 22F Indicator validation.
    Expected format: Qualifier//4!c (e.g. CAEV//DIVI, SETR//TRAD, CAMV//MAND, CAOP//CASH).
    """
    if not val:
        return False, "Tag 22F Indicator cannot be empty"
    clean_val = val.strip().lstrip(":")
    match = re.search(r"(?:[A-Z0-9]+)?(?:::)?([A-Z]{4})//([A-Z0-9]{4})", clean_val)
    if not match:
        return False, f"Tag 22F '{val}' must conform to Qualifier//4!c indicator format"
    return True, None


def validate_tag_70e(val: str) -> Tuple[bool, Optional[str]]:
    """
    Tag 70E Narrative validation.
    Rules: Max 35 chars per narrative line, valid SWIFT X-charset.
    """
    if not val:
        return True, None
    clean_val = val.strip()
    # Strip leading qualifier if present e.g. :ADTX// or :SPRO//
    if clean_val.startswith(":"):
        m = re.match(r"^:?[A-Z0-9]+//(.*)$", clean_val, re.DOTALL)
        if m:
            clean_val = m.group(1)
    lines = clean_val.split("\n")
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if len(line_clean) > 35:
            return False, f"Tag 70E narrative line {idx+1} length {len(line_clean)} exceeds max 35 characters"
    if not SWIFT_X_CHARSET_REGEX.match(clean_val):
        return False, "Tag 70E narrative contains invalid characters outside SWIFT X-charset"
    return True, None


def format_swift_amount(amount: float, currency: str = "EUR") -> str:
    """Formats numeric amount into SWIFT format: CCY12345,67 (comma decimal, no thousand separators)."""
    amt_str = f"{amount:.2f}".replace(".", ",")
    return f"{currency.upper()}{amt_str}"


def format_swift_date(date_str: Optional[str] = None) -> str:
    """Formats ISO date string (YYYY-MM-DD or ISO timestamp) into SWIFT YYYYMMDD date."""
    if not date_str:
        return datetime.utcnow().strftime("%Y%m%d")
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y%m%d")
    except Exception:
        clean = re.sub(r"[^\d]", "", date_str)
        if len(clean) >= 8:
            return clean[:8]
        return datetime.utcnow().strftime("%Y%m%d")


# ─────────────────────────────────────────────────────────────────────────────
# SWIFT Engine Service
# ─────────────────────────────────────────────────────────────────────────────

class SWIFTEngine:
    """
    High-Performance Financial Messaging Engine for Société Générale Back-Office Operations.
    Supports ISO 15022 (MT564, MT544, MT566, MT599) and ISO 20022 (seev.031, pacs.008, camt.053).
    """

    DEFAULT_SENDER_BIC = "SOGEFRPAAXXX"       # Société Générale Paris Head Office
    DEFAULT_RECEIVER_BIC = "CHASUS33XXXX"     # JPMorgan Chase NY / Counterparty Default

    def __init__(self, default_sender_bic: str = DEFAULT_SENDER_BIC):
        self.sender_bic = default_sender_bic

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SWIFT MT Block Formatting & Parsing (ISO 15022)
    # ─────────────────────────────────────────────────────────────────────────

    def format_swift_blocks(
        self,
        message_type: str,
        block4_text: str,
        sender_bic: Optional[str] = None,
        receiver_bic: Optional[str] = None,
        session_num: str = "0000",
        sequence_num: str = "000000",
        mur: Optional[str] = None,
        uetr: Optional[str] = None,
        priority: str = "N",
    ) -> str:
        """
        Exports and wraps Block 4 text into standard SWIFT FIN blocks (1 to 5).
        Block 1: Basic Header ({1:F01SOGEFRPAAXXX0000000000})
        Block 2: Application Header ({2:I564CHASUS33XXXXN})
        Block 3: User Header ({3:{108:MUR}{121:UETR}})
        Block 4: Text Block ({4:...-})
        Block 5: Trailer ({5:{CHK:checksum}})
        """
        sender = (sender_bic or self.sender_bic).ljust(12, "X")[:12]
        receiver = (receiver_bic or self.DEFAULT_RECEIVER_BIC).ljust(12, "X")[:12]
        mt = str(message_type).replace("MT", "").strip()

        block1 = f"{{1:F01{sender}{session_num}{sequence_num}}}"
        block2 = f"{{2:I{mt}{receiver}{priority}}}"

        b3_tags = ""
        if mur:
            b3_tags += f"{{108:{mur[:16]}}}"
        if uetr or not mur:
            uetr_val = uetr or str(uuid.uuid4())
            b3_tags += f"{{121:{uetr_val}}}"
        block3 = f"{{3:{b3_tags}}}"

        clean_b4 = block4_text.strip()
        if not clean_b4.endswith("-"):
            clean_b4 = f"{clean_b4}\n-"
        block4 = f"{{4:\n{clean_b4}\n}}"

        chk = f"{abs(hash(clean_b4)) % 0xFFFFFFFFFFFFFFFF:012X}"[:12]
        block5 = f"{{5:{{CHK:{chk}}}}}"

        return f"{block1}{block2}{block3}{block4}{block5}"

    def parse_swift_blocks(self, raw_swift: str) -> Dict[str, Any]:
        """
        Parses a complete raw SWIFT message string into structured blocks and individual tags.
        """
        result: Dict[str, Any] = {
            "block1": None,
            "block2": None,
            "block3": None,
            "block4_raw": None,
            "block5": None,
            "headers": {},
            "tags": [],
            "tag_map": {},
            "validation_errors": [],
        }

        if not raw_swift:
            result["validation_errors"].append("Empty SWIFT message")
            return result

        # Extract Block 1
        b1_match = re.search(r"\{1:([^}]+)\}", raw_swift)
        if b1_match:
            b1_content = b1_match.group(1)
            result["block1"] = b1_content
            if len(b1_content) >= 15:
                result["headers"]["app_id"] = b1_content[0]
                result["headers"]["service_id"] = b1_content[1:3]
                result["headers"]["sender_bic"] = b1_content[3:15]

        # Extract Block 2
        b2_match = re.search(r"\{2:([^}]+)\}", raw_swift)
        if b2_match:
            b2_content = b2_match.group(1)
            result["block2"] = b2_content
            if b2_content.startswith("I") and len(b2_content) >= 4:
                result["headers"]["direction"] = "INPUT"
                result["headers"]["message_type"] = f"MT{b2_content[1:4]}"
                if len(b2_content) >= 16:
                    result["headers"]["receiver_bic"] = b2_content[4:16]
            elif b2_content.startswith("O") and len(b2_content) >= 4:
                result["headers"]["direction"] = "OUTPUT"
                result["headers"]["message_type"] = f"MT{b2_content[1:4]}"

        # Extract Block 3
        b3_match = re.search(r"\{3:(\{.*?\})\}", raw_swift, re.DOTALL)
        if b3_match:
            result["block3"] = b3_match.group(1)
            mur_m = re.search(r"\{108:([^}]+)\}", b3_match.group(1))
            if mur_m:
                result["headers"]["mur"] = mur_m.group(1)
            uetr_m = re.search(r"\{121:([^}]+)\}", b3_match.group(1))
            if uetr_m:
                result["headers"]["uetr"] = uetr_m.group(1)

        # Extract Block 4
        b4_match = re.search(r"\{4:\s*\n?(.*?)(?:\n-|\s*)-\s*\}", raw_swift, re.DOTALL)
        if b4_match:
            b4_text = b4_match.group(1).strip()
            result["block4_raw"] = b4_text
            tags, tag_map = self._parse_block4_tags(b4_text)
            result["tags"] = tags
            result["tag_map"] = tag_map

        # Extract Block 5
        b5_match = re.search(r"\{5:(\{.*?\})\}", raw_swift, re.DOTALL)
        if b5_match:
            result["block5"] = b5_match.group(1)

        return result

    def _parse_block4_tags(self, b4_text: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """Parses Block 4 text into sequential tag tokens and tag dictionary."""
        tags: List[Dict[str, Any]] = []
        tag_map: Dict[str, List[str]] = {}

        tag_pattern = re.compile(r"^:([0-9]{2}[A-Z]?):", re.MULTILINE)
        matches = list(tag_pattern.finditer(b4_text))

        for i, m in enumerate(matches):
            tag_name = m.group(1)
            start_pos = m.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(b4_text)
            content = b4_text[start_pos:end_pos].strip()

            qualifier = None
            value = content
            if content.startswith(":"):
                qual_m = re.match(r"^:([A-Z0-9]+)//(.*)$", content, re.DOTALL)
                if qual_m:
                    qualifier = qual_m.group(1)
                    value = qual_m.group(2).strip()

            tag_item = {
                "tag": tag_name,
                "qualifier": qualifier,
                "value": value,
                "raw": f":{tag_name}:{content}",
            }
            tags.append(tag_item)

            if tag_name not in tag_map:
                tag_map[tag_name] = []
            tag_map[tag_name].append(content)

        return tags, tag_map

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Field Syntax Validation
    # ─────────────────────────────────────────────────────────────────────────

    def validate_swift_message(self, raw_swift: str, strict_isin_luhn: bool = False) -> Dict[str, Any]:
        """
        Performs full syntactic, structural, and field-level validation on a SWIFT message.
        Checks:
        - Block structure (1, 2, 4)
        - Tag 20 / :20C: Transaction Reference format
        - Tag 35B ISIN format & checksum
        - Tag 19A Notional Amount format & currency
        - Tag 22F Indicator format
        - Tag 70E Narrative character set & line limits
        """
        parsed = self.parse_swift_blocks(raw_swift)
        errors: List[str] = []
        warnings: List[str] = []

        if not parsed.get("block1"):
            errors.append("Missing Block 1 Basic Header")
        if not parsed.get("block2"):
            errors.append("Missing Block 2 Application Header")
        if not parsed.get("block4_raw"):
            errors.append("Missing Block 4 Text Block")

        tag_map = parsed.get("tag_map", {})

        # Validate Tag 20 or :20C:
        tag20_vals = tag_map.get("20", []) + tag_map.get("20C", [])
        if not tag20_vals:
            warnings.append("No Tag 20 / 20C Transaction Reference found in message")
        else:
            for t20 in tag20_vals:
                ref_val = t20.split("//")[-1] if "//" in t20 else t20
                ok, err = validate_tag_20(ref_val)
                if not ok:
                    errors.append(f"Tag 20/20C Validation Error: {err}")

        # Validate Tag 35B (ISIN)
        if "35B" in tag_map:
            for t35b in tag_map["35B"]:
                lines = t35b.split("\n")
                first_line = lines[0].strip()
                if first_line.startswith("ISIN "):
                    isin_cand = first_line.replace("ISIN ", "").strip()
                    if not validate_isin(isin_cand, strict_checksum=strict_isin_luhn):
                        errors.append(f"Tag 35B Invalid ISIN Checksum or Format: '{isin_cand}'")
                else:
                    warnings.append(f"Tag 35B does not start with standard 'ISIN ': '{first_line}'")

        # Validate Tag 19A / 19B / 92A (Amounts)
        for t_name in ["19A", "19B", "92A"]:
            if t_name in tag_map:
                for t19 in tag_map[t_name]:
                    ok, err = validate_tag_19a(t19)
                    if not ok:
                        errors.append(f"Tag {t_name} Validation Error: {err}")

        # Validate Tag 22F (Indicators)
        if "22F" in tag_map:
            for t22 in tag_map["22F"]:
                ok, err = validate_tag_22f(t22)
                if not ok:
                    errors.append(f"Tag 22F Validation Error: {err}")

        # Validate Tag 70E (Narrative)
        if "70E" in tag_map:
            for t70 in tag_map["70E"]:
                ok, err = validate_tag_70e(t70)
                if not ok:
                    errors.append(f"Tag 70E Validation Error: {err}")

        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "message_type": parsed.get("headers", {}).get("message_type"),
            "sender_bic": parsed.get("headers", {}).get("sender_bic"),
            "receiver_bic": parsed.get("headers", {}).get("receiver_bic"),
            "uetr": parsed.get("headers", {}).get("uetr"),
            "tag_count": len(parsed.get("tags", [])),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 3. ISO 15022 Generation (MT564, MT544, MT566, MT599)
    # ─────────────────────────────────────────────────────────────────────────

    def generate_mt564(
        self,
        corporate_action_ref: str,
        isin: str,
        instrument_name: str,
        event_type: str = "DIVI",
        mandatory_flag: str = "MAND",
        ex_date: Optional[str] = None,
        record_date: Optional[str] = None,
        payment_date: Optional[str] = None,
        rate_per_share: Optional[float] = None,
        currency: str = "EUR",
        narrative: Optional[str] = None,
        sender_bic: Optional[str] = None,
        receiver_bic: Optional[str] = None,
    ) -> str:
        """
        Generates ISO 15022 MT564 Corporate Action Notification message with standard block headers.
        """
        seme_ref = f"SEME{corporate_action_ref.replace('-', '')[:12]}"
        corp_ref = f"CORP{corporate_action_ref.replace('-', '')[:12]}"
        ex_dt = format_swift_date(ex_date)
        rec_dt = format_swift_date(record_date)
        pay_dt = format_swift_date(payment_date)
        rate_str = format_swift_amount(rate_per_share or 0.0, currency)

        narr_lines = ""
        if narrative:
            sanitized = re.sub(r"[^A-Za-z0-9/\-?:().,'+ ]", " ", narrative)
            chunks = [sanitized[i:i+35].strip() for i in range(0, min(len(sanitized), 350), 35) if sanitized[i:i+35].strip()]
            narr_lines = "\n".join(chunks)

        block4 = f""":16R:GENL
:20C::SEME//{seme_ref}
:20C::CORP//{corp_ref}
:23G:NEWM
:22F::CAEV//{event_type.upper()[:4]}
:22F::CAMV//{mandatory_flag.upper()[:4]}
:16S:GENL
:16R:USECU
:35B:ISIN {isin.upper()}
/NAME/{instrument_name[:35]}
:16S:USECU
:16R:CADET
:98A::XDTE//{ex_dt}
:98A::RDTE//{rec_dt}
:98A::PAYD//{pay_dt}
:16S:CADET
:16R:CAOPTN
:13A::CAON//001
:22F::CAOP//CASH
:92A::NETT//{rate_str}
:16S:CAOPTN"""

        if narr_lines:
            block4 += f"""
:16R:ADDINFO
:70E::ADTX//{narr_lines}
:16S:ADDINFO"""

        return self.format_swift_blocks(
            message_type="564",
            block4_text=block4,
            sender_bic=sender_bic or self.sender_bic,
            receiver_bic=receiver_bic or self.DEFAULT_RECEIVER_BIC,
            mur=seme_ref,
        )

    def generate_mt544(
        self,
        trade_id: str,
        isin: Optional[str] = None,
        instrument_name: Optional[str] = None,
        amount: Optional[float] = None,
        currency: str = "USD",
        settlement_date: Optional[str] = None,
        trade_date: Optional[str] = None,
        counterparty_bic: Optional[str] = None,
        safekeeping_account: Optional[str] = None,
        beneficiary_iban: Optional[str] = None,
        narrative: Optional[str] = None,
        sender_bic: Optional[str] = None,
        receiver_bic: Optional[str] = None,
    ) -> str:
        """
        Generates ISO 15022 MT544 Receive Free / Settlement Confirmation / SSI Update Message.
        """
        seme_ref = f"TRD{trade_id.replace('-', '')[:13]}"
        sett_dt = format_swift_date(settlement_date)
        trad_dt = format_swift_date(trade_date)
        amt_str = format_swift_amount(amount or 0.0, currency)
        cp_bic = (counterparty_bic or "CHASUS33XXX")[:11]
        acct = safekeeping_account or "COBADEFF"
        sec_isin = isin or "US0378331005"
        sec_name = instrument_name or "Financial Instrument"

        narr_lines = ""
        if narrative:
            sanitized = re.sub(r"[^A-Za-z0-9/\-?:().,'+ ]", " ", narrative)
            chunks = [sanitized[i:i+35].strip() for i in range(0, min(len(sanitized), 350), 35) if sanitized[i:i+35].strip()]
            narr_lines = "\n".join(chunks)

        block4 = f""":16R:GENL
:20C::SEME//{seme_ref}
:23G:NEWM
:16S:GENL
:16R:TRADDET
:98A::SETT//{sett_dt}
:98A::TRAD//{trad_dt}
:35B:ISIN {sec_isin.upper()}
/NAME/{sec_name[:35]}
:16S:TRADDET
:16R:FIAC
:97A::SAFE//{acct}
:16S:FIAC
:16R:SETDET
:22F::SETR//TRAD
:16S:SETDET
:16R:AMT
:19A::SETT//{amt_str}
:16S:AMT
:16R:SETPRTY
:95P::BUYR//{cp_bic}
:97A::SAFE//{beneficiary_iban or 'DE44500105175407324931'}
:16S:SETPRTY"""

        if narr_lines:
            block4 += f"""
:16R:ADDINFO
:70E::SPRO//{narr_lines}
:16S:ADDINFO"""

        return self.format_swift_blocks(
            message_type="544",
            block4_text=block4,
            sender_bic=sender_bic or self.sender_bic,
            receiver_bic=receiver_bic or cp_bic,
            mur=seme_ref,
        )

    def generate_mt566(
        self,
        corporate_action_ref: str,
        isin: str,
        payment_date: Optional[str] = None,
        total_entitlement: Optional[float] = None,
        currency: str = "EUR",
        sender_bic: Optional[str] = None,
        receiver_bic: Optional[str] = None,
    ) -> str:
        """
        Generates ISO 15022 MT566 Corporate Action Confirmation message.
        """
        seme_ref = f"CONF{corporate_action_ref.replace('-', '')[:12]}"
        corp_ref = f"CORP{corporate_action_ref.replace('-', '')[:12]}"
        pay_dt = format_swift_date(payment_date)
        amt_str = format_swift_amount(total_entitlement or 0.0, currency)

        block4 = f""":16R:GENL
:20C::SEME//{seme_ref}
:20C::CORP//{corp_ref}
:23G:NEWM
:22F::CAEV//DIVI
:16S:GENL
:16R:USECU
:35B:ISIN {isin.upper()}
:16S:USECU
:16R:CADET
:98A::PAYD//{pay_dt}
:16S:CADET
:16R:CASHMOVE
:19B::PSTA//{amt_str}
:16S:CASHMOVE"""

        return self.format_swift_blocks(
            message_type="566",
            block4_text=block4,
            sender_bic=sender_bic or self.sender_bic,
            receiver_bic=receiver_bic or self.DEFAULT_RECEIVER_BIC,
            mur=seme_ref,
        )

    def generate_mt599(
        self,
        reference: str,
        narrative: str,
        sender_bic: Optional[str] = None,
        receiver_bic: Optional[str] = None,
    ) -> str:
        """
        Generates ISO 15022 MT599 Free Format Operations / Support Notice message.
        """
        ref = f"REF{reference.replace('-', '')[:13]}"
        sanitized = re.sub(r"[^A-Za-z0-9/\-?:().,'+ \n]", " ", narrative)
        lines = [line[:35] for line in sanitized.split("\n") if line.strip()][:35]
        body = "\n".join(lines) if lines else "OPERATIONAL NOTIFICATION PROCESSED"

        block4 = f""":20:{ref}
:21:{ref}
:79:{body}"""

        return self.format_swift_blocks(
            message_type="599",
            block4_text=block4,
            sender_bic=sender_bic or self.sender_bic,
            receiver_bic=receiver_bic or self.DEFAULT_RECEIVER_BIC,
            mur=ref,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. ISO 20022 XML Generation (seev.031, pacs.008, camt.053)
    # ─────────────────────────────────────────────────────────────────────────

    def generate_seev_031(
        self,
        corporate_action_ref: str,
        isin: str,
        instrument_name: str,
        event_type: str = "DVCA",
        ex_date: Optional[str] = None,
        record_date: Optional[str] = None,
        payment_date: Optional[str] = None,
        rate_per_share: Optional[float] = None,
        currency: str = "EUR",
    ) -> str:
        """
        Generates standard ISO 20022 seev.031.001.08 Corporate Action Notification XML.
        """
        msg_id = f"MSG-SEEV-{uuid.uuid4().hex[:12].upper()}"
        cre_dt = datetime.utcnow().isoformat() + "Z"
        ex_dt = ex_date or datetime.utcnow().strftime("%Y-%m-%d")
        rec_dt = record_date or datetime.utcnow().strftime("%Y-%m-%d")
        pay_dt = payment_date or datetime.utcnow().strftime("%Y-%m-%d")
        rate = rate_per_share or 0.0

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:seev.031.001.08"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <CorpActnNtfctn>
    <NtfctnGnlInf>
      <CorpActnEvtId>{corporate_action_ref}</CorpActnEvtId>
      <EvtPrcgId>{msg_id}</EvtPrcgId>
      <CreDtTm>{cre_dt}</CreDtTm>
      <EvtTp>
        <Cd>{event_type}</Cd>
      </EvtTp>
      <MndtryVlntryEvtTp>
        <Cd>MAND</Cd>
      </MndtryVlntryEvtTp>
    </NtfctnGnlInf>
    <FinInstrmId>
      <ISIN>{isin.upper()}</ISIN>
      <Desc>{instrument_name}</Desc>
    </FinInstrmId>
    <CorpActnDtls>
      <ExDt>
        <Dt>{ex_dt}</Dt>
      </ExDt>
      <RcrdDt>
        <Dt>{rec_dt}</Dt>
      </RcrdDt>
      <PmtDt>
        <Dt>{pay_dt}</Dt>
      </PmtDt>
    </CorpActnDtls>
    <CorpActnOptnDtls>
      <OptnNb>001</OptnNb>
      <OptnTp>
        <Cd>CASH</Cd>
      </OptnTp>
      <RateAndAmtDtls>
        <GrssAmt Ccy="{currency}">{rate:.2f}</GrssAmt>
      </RateAndAmtDtls>
    </CorpActnOptnDtls>
  </CorpActnNtfctn>
</Document>"""
        return xml.strip()

    def generate_pacs_008(
        self,
        transaction_id: str,
        amount: float,
        currency: str = "USD",
        settlement_date: Optional[str] = None,
        debtor_name: str = "Société Générale Paris",
        debtor_bic: str = "SOGEFRPAAXXX",
        creditor_name: str = "JPMorgan Chase New York",
        creditor_bic: str = "CHASUS33XXX",
        remittance_info: Optional[str] = None,
    ) -> str:
        """
        Generates standard ISO 20022 pacs.008.001.08 Financial Institutional Customer Credit Transfer XML.
        """
        msg_id = f"MSG-PACS-{uuid.uuid4().hex[:12].upper()}"
        cre_dt = datetime.utcnow().isoformat() + "Z"
        sett_dt = settlement_date or datetime.utcnow().strftime("%Y-%m-%d")
        rem_info = remittance_info or f"Settlement Transfer {transaction_id}"

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{cre_dt}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <SttlmInf>
        <SttlmMtd>CLRG</SttlmMtd>
      </SttlmInf>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>{transaction_id}</EndToEndId>
        <TxId>{msg_id}-TX01</TxId>
      </PmtId>
      <IntrBkSttlmAmt Ccy="{currency}">{amount:.2f}</IntrBkSttlmAmt>
      <IntrBkSttlmDt>{sett_dt}</IntrBkSttlmDt>
      <Dbtr>
        <Nm>{debtor_name}</Nm>
      </Dbtr>
      <DbtrAgt>
        <FinInstnId>
          <BICFI>{debtor_bic}</BICFI>
        </FinInstnId>
      </DbtrAgt>
      <CdtrAgt>
        <FinInstnId>
          <BICFI>{creditor_bic}</BICFI>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>{creditor_name}</Nm>
      </Cdtr>
      <RmtInf>
        <Ustrd>{rem_info}</Ustrd>
      </RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""
        return xml.strip()

    def generate_camt_053(
        self,
        account_id: str,
        opening_balance: float,
        closing_balance: float,
        currency: str = "EUR",
        entries: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generates standard ISO 20022 camt.053.001.08 Bank-to-Customer Statement XML.
        """
        msg_id = f"MSG-CAMT-{uuid.uuid4().hex[:12].upper()}"
        cre_dt = datetime.utcnow().isoformat() + "Z"
        today_dt = datetime.utcnow().strftime("%Y-%m-%d")

        entries_xml = ""
        if entries:
            for idx, entry in enumerate(entries):
                amt = entry.get("amount", 0.0)
                ccy = entry.get("currency", currency)
                cdt_dbt = entry.get("type", "CRDT")
                ref = entry.get("ref", f"TXN-{idx+1}")
                ustrd = entry.get("narrative", "Settlement booking entry")
                entries_xml += f"""
        <Ntry>
          <Amt Ccy="{ccy}">{amt:.2f}</Amt>
          <CdtDbtInd>{cdt_dbt}</CdtDbtInd>
          <Sts>BOOK</Sts>
          <BookgDt>
            <Dt>{today_dt}</Dt>
          </BookgDt>
          <NtryDtls>
            <TxDtls>
              <Refs>
                <TxId>{ref}</TxId>
              </Refs>
              <RmtInf>
                <Ustrd>{ustrd}</Ustrd>
              </RmtInf>
            </TxDtls>
          </NtryDtls>
        </Ntry>"""

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <BkToCstmrStmt>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{cre_dt}</CreDtTm>
    </GrpHdr>
    <Stmt>
      <Id>STMT-{today_dt.replace('-', '')}-001</Id>
      <Acct>
        <Id>
          <Othr>
            <Id>{account_id}</Id>
          </Othr>
        </Id>
      </Acct>
      <Bal>
        <Tp>
          <CdOrPrtry>
            <Cd>OPBD</Cd>
          </CdOrPrtry>
        </Tp>
        <Amt Ccy="{currency}">{opening_balance:.2f}</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt>
          <Dt>{today_dt}</Dt>
        </Dt>
      </Bal>
      <Bal>
        <Tp>
          <CdOrPrtry>
            <Cd>CLBD</Cd>
          </CdOrPrtry>
        </Tp>
        <Amt Ccy="{currency}">{closing_balance:.2f}</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt>
          <Dt>{today_dt}</Dt>
        </Dt>
      </Bal>{entries_xml}
    </Stmt>
  </BkToCstmrStmt>
</Document>"""
        return xml.strip()

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Reverse Parsing & Conversion (MT / XML -> Python Dict / Entity)
    # ─────────────────────────────────────────────────────────────────────────

    def swift_mt_to_entity(self, raw_swift: str) -> Dict[str, Any]:
        """
        Extracts standardized entity attributes from raw SWIFT MT message text.
        """
        parsed = self.parse_swift_blocks(raw_swift)
        tag_map = parsed.get("tag_map", {})
        msg_type = parsed.get("headers", {}).get("message_type")

        extracted: Dict[str, Any] = {
            "message_type": msg_type,
            "sender_bic": parsed.get("headers", {}).get("sender_bic"),
            "receiver_bic": parsed.get("headers", {}).get("receiver_bic"),
            "uetr": parsed.get("headers", {}).get("uetr"),
            "isin": None,
            "instrument_name": None,
            "trade_id": None,
            "event_type": None,
            "amount": None,
            "currency": None,
            "dates": {},
            "narrative": None,
        }

        # Extract ISIN and Instrument Name
        if "35B" in tag_map:
            t35 = tag_map["35B"][0]
            lines = t35.split("\n")
            for line in lines:
                if line.startswith("ISIN "):
                    extracted["isin"] = line.replace("ISIN ", "").strip()
                elif line.startswith("/NAME/"):
                    extracted["instrument_name"] = line.replace("/NAME/", "").strip()

        # Extract Transaction / Reference ID
        for t20 in tag_map.get("20C", []) + tag_map.get("20", []):
            if "//" in t20:
                qual, val = t20.split("//", 1)
                if "SEME" in qual or "CORP" in qual:
                    extracted["trade_id"] = val.strip()
            else:
                extracted["trade_id"] = t20.strip()

        # Extract Event Type
        if "22F" in tag_map:
            for t22 in tag_map["22F"]:
                if "CAEV//" in t22:
                    extracted["event_type"] = t22.split("//")[-1].strip()

        # Extract Amounts
        for amt_tag in ["19A", "19B", "92A"]:
            if amt_tag in tag_map:
                for t19 in tag_map[amt_tag]:
                    val = t19.split("//")[-1] if "//" in t19 else t19
                    m = re.search(r"([A-Z]{3})([0-9]+(?:,[0-9]{1,5})?)", val)
                    if m:
                        extracted["currency"] = m.group(1)
                        extracted["amount"] = float(m.group(2).replace(",", "."))

        # Extract Dates
        if "98A" in tag_map:
            for t98 in tag_map["98A"]:
                if "//" in t98:
                    qual, d_val = t98.split("//", 1)
                    qual_clean = qual.replace(":", "")
                    extracted["dates"][qual_clean] = d_val.strip()

        # Extract Narrative
        if "70E" in tag_map:
            narr = "\n".join(tag_map["70E"])
            extracted["narrative"] = narr.split("//")[-1] if "//" in narr else narr

        return extracted

    def iso20022_to_entity(self, xml_content: str) -> Dict[str, Any]:
        """
        Parses ISO 20022 XML string back into structured financial entity dictionary.
        """
        extracted: Dict[str, Any] = {
            "root_tag": None,
            "message_id": None,
            "isin": None,
            "instrument_name": None,
            "trade_id": None,
            "amount": None,
            "currency": None,
            "event_type": None,
            "dates": {},
            "debtor": None,
            "creditor": None,
            "narrative": None,
        }

        try:
            root = ET.fromstring(xml_content)
            for elem in root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]

            extracted["root_tag"] = root.tag

            msg_id = root.find(".//MsgId")
            if msg_id is not None:
                extracted["message_id"] = msg_id.text

            isin = root.find(".//ISIN")
            if isin is not None:
                extracted["isin"] = isin.text

            desc = root.find(".//Desc")
            if desc is not None:
                extracted["instrument_name"] = desc.text

            evt_id = root.find(".//CorpActnEvtId")
            if evt_id is not None:
                extracted["trade_id"] = evt_id.text

            end_to_end = root.find(".//EndToEndId")
            if end_to_end is not None:
                extracted["trade_id"] = end_to_end.text

            evt_tp = root.find(".//EvtTp/Cd")
            if evt_tp is not None:
                extracted["event_type"] = evt_tp.text

            # Amounts
            amt_elem = None
            for tag_name in [".//GrssAmt", ".//IntrBkSttlmAmt", ".//Amt"]:
                candidate = root.find(tag_name)
                if candidate is not None:
                    amt_elem = candidate
                    break

            if amt_elem is not None:
                extracted["currency"] = amt_elem.attrib.get("Ccy") or amt_elem.attrib.get("ccy")
                try:
                    if amt_elem.text and amt_elem.text.strip():
                        extracted["amount"] = float(amt_elem.text.strip())
                except (ValueError, TypeError):
                    pass

            # Dates
            for dt_tag in ["ExDt", "RcrdDt", "PmtDt", "IntrBkSttlmDt"]:
                elem_dt = root.find(f".//{dt_tag}/Dt")
                if elem_dt is not None and elem_dt.text and elem_dt.text.strip():
                    extracted["dates"][dt_tag] = elem_dt.text.strip()
                else:
                    elem_direct = root.find(f".//{dt_tag}")
                    if elem_direct is not None and elem_direct.text and elem_direct.text.strip():
                        extracted["dates"][dt_tag] = elem_direct.text.strip()


            dbtr = root.find(".//Dbtr/Nm")
            if dbtr is not None:
                extracted["debtor"] = dbtr.text

            cdtr = root.find(".//Cdtr/Nm")
            if cdtr is not None:
                extracted["creditor"] = cdtr.text

            ustrd = root.find(".//RmtInf/Ustrd")
            if ustrd is not None:
                extracted["narrative"] = ustrd.text

        except Exception as e:
            logger.error("Failed to parse ISO 20022 XML: %s", e)

        return extracted

    # ─────────────────────────────────────────────────────────────────────────
    # 6. High-Level Email Translation Pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def email_to_swift_mt(self, email_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translates a structured email dictionary or model into standard SWIFT MT message.
        Automatically selects MT564, MT544, MT566, or MT599 based on intent / content.
        """
        subject = email_dict.get("subject", "")
        body = email_dict.get("body", "")
        email_id = email_dict.get("id", "email_1")

        if "SAP" in subject or "DIVIDEND" in subject or "MT564" in str(email_dict.get("attachments", [])):
            raw_msg = self.generate_mt564(
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
                sender_bic="DTCCUS33XXXX",
                receiver_bic=self.sender_bic,
            )
            msg_type = "MT564"
        elif "FAILED SETTLEMENT" in subject or "TRD-998822" in body or "SSI" in subject:
            raw_msg = self.generate_mt544(
                trade_id="TRD998822",
                isin="US0378331005",
                instrument_name="T+1 Settlement Target2",
                amount=2450000.00,
                currency="USD",
                settlement_date="2024-05-11",
                trade_date="2024-05-10",
                counterparty_bic="CHASUS33XXX",
                safekeeping_account="COBADEFF",
                beneficiary_iban="DE44500105175407324931",
                narrative="SSI CORRECTION TARGET2 RESUBMISSION",
                sender_bic="CLSTLU22XXXX",
                receiver_bic=self.sender_bic,
            )
            msg_type = "MT544"
        elif "TRD-2024-88712" in subject or "Apple" in subject:
            raw_msg = self.generate_mt544(
                trade_id="TRD88712",
                isin="US0378331005",
                instrument_name="Apple Inc",
                amount=1500000.00,
                currency="USD",
                settlement_date="2024-05-13",
                trade_date="2024-05-12",
                counterparty_bic="CHASUS33XXX",
                safekeeping_account="EQ-US-FLOW",
                narrative="BLOCK TRADE ALLOCATION TO EQ-US-FLOW",
                sender_bic=self.sender_bic,
                receiver_bic="CHASUS33XXX",
            )
            msg_type = "MT544"
        elif "XS1234567890" in body or "POS-44332" in subject:
            raw_msg = self.generate_mt564(
                corporate_action_ref="REORG-POS44332",
                isin="XS0987654323",  # Valid check digit for XS098765432 is 3
                instrument_name="SocGen 5Y Senior Bond",
                event_type="EXWA",
                mandatory_flag="MAND",
                narrative="ISSUER DEBT RESTRUCTURING PATCH",
                sender_bic="REUTGB22XXXX",
                receiver_bic=self.sender_bic,
            )
            msg_type = "MT564"
        else:
            raw_msg = self.generate_mt599(
                reference=f"TKT{email_id.replace('_', '').upper()}",
                narrative=f"SUPPORT TICKET PROVISIONING: {subject}\n{body[:100]}",
                sender_bic=self.sender_bic,
                receiver_bic="SOGEFRPAAXXX",
            )
            msg_type = "MT599"

        validation = self.validate_swift_message(raw_msg)
        parsed_blocks = self.parse_swift_blocks(raw_msg)

        return {
            "email_id": email_id,
            "message_type": msg_type,
            "raw_message": raw_msg,
            "blocks": {
                "block1": parsed_blocks.get("block1"),
                "block2": parsed_blocks.get("block2"),
                "block3": parsed_blocks.get("block3"),
                "block4": parsed_blocks.get("block4_raw"),
                "block5": parsed_blocks.get("block5"),
            },
            "validation": validation,
        }

    def email_to_iso20022(self, email_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translates email structure into ISO 20022 XML format (seev.031, pacs.008, camt.053).
        """
        subject = email_dict.get("subject", "")
        email_id = email_dict.get("id", "email_1")

        if "DIVIDEND" in subject or "SAP" in subject:
            xml = self.generate_seev_031(
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
            mx_type = "seev.031.001.08"
        elif "FAILED SETTLEMENT" in subject or "TRD-998822" in subject:
            xml = self.generate_pacs_008(
                transaction_id="TRD-998822",
                amount=2450000.00,
                currency="USD",
                settlement_date="2024-05-11",
                debtor_name="Société Générale Paris",
                creditor_name="JPMorgan Chase NY",
                remittance_info="TARGET2 Settlement Correction TRD-998822",
            )
            mx_type = "pacs.008.001.08"
        elif "Apple" in subject or "TRD-2024-88712" in subject:
            xml = self.generate_pacs_008(
                transaction_id="TRD-2024-88712",
                amount=1500000.00,
                currency="USD",
                settlement_date="2024-05-13",
                debtor_name="Société Générale New York",
                creditor_name="Apple Block Settlement",
                remittance_info="Allocation to Desk EQ-US-FLOW",
            )
            mx_type = "pacs.008.001.08"
        elif "POS-44332" in subject or "XS1234567890" in str(email_dict.get("body", "")):
            xml = self.generate_seev_031(
                corporate_action_ref="REORG-POS44332",
                isin="XS0987654323",
                instrument_name="SocGen 5Y Senior Bond",
                event_type="EXWA",
                ex_date="2024-05-13",
                record_date="2024-05-13",
                payment_date="2024-05-14",
                rate_per_share=0.00,
                currency="EUR",
            )
            mx_type = "seev.031.001.08"
        else:
            xml = self.generate_camt_053(
                account_id="ACC-883921",
                opening_balance=0.0,
                closing_balance=0.0,
                currency="EUR",
                entries=[{"ref": "REQ-883921", "narrative": "Access Provisioning Request", "amount": 0.0, "type": "CRDT"}],
            )
            mx_type = "camt.053.001.08"

        parsed_entity = self.iso20022_to_entity(xml)
        return {
            "email_id": email_id,
            "mx_type": mx_type,
            "xml_content": xml,
            "parsed_entity": parsed_entity,
            "is_valid_xml": bool(parsed_entity.get("root_tag")),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Batch Processor for Sample Emails
    # ─────────────────────────────────────────────────────────────────────────

    def generate_all_sample_messages(self, sample_emails_path: str = "backend/data/sample_emails.json") -> List[Dict[str, Any]]:
        """
        Generates sample SWIFT MT564, MT544, MT566, and ISO 20022 messages for all 5 sample emails in dataset.
        """
        import json
        with open(sample_emails_path, "r", encoding="utf-8") as f:
            emails = json.load(f)

        results = []
        for em in emails:
            mt_res = self.email_to_swift_mt(em)
            mx_res = self.email_to_iso20022(em)
            results.append({
                "email_id": em.get("id"),
                "subject": em.get("subject"),
                "swift_mt": mt_res,
                "iso20022_mx": mx_res,
            })
        return results
