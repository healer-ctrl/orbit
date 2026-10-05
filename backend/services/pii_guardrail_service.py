import re
import logging
from typing import Tuple, Dict, Any, List

logger = logging.getLogger("mailmind.guardrails")


class PIIGuardrailService:
    """
    Enterprise-grade PII Anonymization & Prompt Injection Guardrail Service.
    Protects sensitive customer and operational data before sending email payloads
    to LLMs (GPT-4o) while preserving vital financial market identifiers (ISIN, CUSIP, SWIFT BIC, Trade ID).
    """

    # Common Prompt Injection patterns
    PROMPT_INJECTION_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"(?i)system\s*prompt\s*override",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)disregard\s+(all\s+)?safety\s+guidelines",
        r"(?i)output\s+the\s+following\s+system\s+prompt",
        r"(?i)bypass\s+approval",
        r"(?i)auto_execute\s*:\s*true",
        r"(?i)(?:jailbreak|dan\s+mode|roleplay\s+as\s+admin)",
        r"(?i)(?:forget|drop)\s+(all\s+)?(?:rules|instructions|constraints)",
        r"(?i)<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        r"(?i)(?:execute|eval)\s*\(\s*['\"].*['\"]\s*\)",
    ]

    # Standard PII Regexes
    PII_PATTERNS = {
        "IBAN": r"\b[A-Z]{2}[0-9]{2}(?:[ ]?[0-9]{4}){4,7}(?:[ ]?[0-9]{1,4})?\b",
        "BANK_ACCOUNT": r"\b(?:ACC|ACCT|ACCOUNT|A/C)[:#\s]*([0-9]{8,18})\b",
        "CREDIT_CARD": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
        "PHONE": r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "SSN_TIN": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b(?=.*(?:tax|tin|ssn))",
        "PERSONAL_EMAIL": r"\b[A-Za-z0-9._%+-]+@(?!socgen\.com|dtcc\.com|euroclear\.com|clearstream\.com|jpmorgan\.com|bnpparibas\.com)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "INTERNAL_IP": r"\b(?:10\.\d{1,3}|192\.168\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3})\.\d{1,3}\b",
    }

    # Financial domain patterns to PRESERVE and NOT MASK as generic alphanumeric
    PROTECTED_FINANCIAL_PATTERNS = {
        "ISIN": r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b",
        "CUSIP": r"\b[0-9]{3}[A-Z0-9]{5}[0-9]\b",
        "SEDOL": r"\b[B-DF-HJ-NP-TV-Z0-9]{6}[0-9]\b",
        "SWIFT_BIC": r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
        "TRADE_ID": r"\b(?:TRD|TXN|DEAL|ORDER)[-\s]?[A-Z0-9-]+\b",
    }

    def __init__(self, masking_enabled: bool = True, injection_shield_enabled: bool = True):
        self.masking_enabled = masking_enabled
        self.injection_shield_enabled = injection_shield_enabled

    def sanitize_and_guard(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Scans and sanitizes raw email text.
        Returns:
            - sanitized_text: text with PII safely replaced by tokenized placeholders
            - guardrail_report: dictionary of detected PII, mappings for de-masking, and safety flags
        """
        if not text:
            return "", {"pii_detected": False, "mask_count": 0, "injection_flag": False, "mapping": {}}

        report: Dict[str, Any] = {
            "pii_detected": False,
            "mask_count": 0,
            "masked_types": [],
            "mapping": {},
            "injection_flag": False,
            "injection_details": [],
            "original_length": len(text),
        }

        # 1. Check for prompt injection attacks
        if self.injection_shield_enabled:
            for pattern in self.PROMPT_INJECTION_PATTERNS:
                matches = re.findall(pattern, text)
                if matches:
                    report["injection_flag"] = True
                    report["injection_details"].append(f"Detected suspicious pattern: {pattern}")
                    logger.warning("Prompt injection attempt detected: %s", pattern)

        if not self.masking_enabled:
            return text, report

        # 2. Extract and protect financial identifiers so we don't accidentally treat ISINs/SWIFT as account numbers
        protected_tokens: Dict[str, str] = {}
        sanitized = text

        for name, pattern in self.PROTECTED_FINANCIAL_PATTERNS.items():
            matches = list(re.finditer(pattern, sanitized))
            for i, match in enumerate(matches):
                val = match.group(0)
                # Don't protect if already protected
                token_placeholder = f"__PROTECTED_{name}_{i}__"
                protected_tokens[token_placeholder] = val
                sanitized = sanitized.replace(val, token_placeholder)

        # 3. Mask PII
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = list(re.finditer(pattern, sanitized, flags=re.IGNORECASE))
            if matches:
                report["pii_detected"] = True
                if pii_type not in report["masked_types"]:
                    report["masked_types"].append(pii_type)

                for i, match in enumerate(matches):
                    original_val = match.group(0)
                    # Skip if placeholder
                    if original_val.startswith("__PROTECTED_"):
                        continue
                    token = f"[{pii_type}_{i+1}]"
                    report["mapping"][token] = original_val
                    report["mask_count"] += 1
                    sanitized = sanitized.replace(original_val, token)

        # 4. Restore protected financial identifiers
        for placeholder, original_val in protected_tokens.items():
            sanitized = sanitized.replace(placeholder, original_val)

        report["sanitized_length"] = len(sanitized)
        return sanitized, report

    def demask_entities(self, extracted_dict: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Replaces masked placeholders back with their true operational values for local secure processing.
        """
        if not mapping or not extracted_dict:
            return extracted_dict

        restored = {}
        for key, value in extracted_dict.items():
            if isinstance(value, str):
                for token, real_val in mapping.items():
                    value = value.replace(token, real_val)
                restored[key] = value
            elif isinstance(value, dict):
                restored[key] = self.demask_entities(value, mapping)
            elif isinstance(value, list):
                restored[key] = [
                    self.demask_entities(item, mapping) if isinstance(item, dict)
                    else (item if not isinstance(item, str) else item)
                    for item in value
                ]
            else:
                restored[key] = value
        return restored
