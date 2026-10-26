"""
GSTIN Luhn Mod-36 Checksum Validator and Format Normalizer
"""
import re
from datetime import datetime

GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

def is_valid_gstin_syntax(gstin: str) -> bool:
    if not gstin or len(gstin) != 15:
        return False
    return bool(GSTIN_REGEX.match(gstin.upper()))

def calculate_luhn_mod36_checksum(gstin_14: str) -> str:
    """
    Computes the 15th character checksum of a 14-char GSTIN prefix using ISO/IEC 7064 Mod 37, 36 / Luhn mod 36 algorithm.
    """
    gstin_14 = gstin_14.upper()
    factor = 2
    total = 0
    mod = len(GSTIN_CHARSET)

    for char in reversed(gstin_14):
        code_point = GSTIN_CHARSET.index(char)
        digit = factor * code_point
        factor = 1 if factor == 2 else 2
        digit = (digit // mod) + (digit % mod)
        total += digit

    remainder = total % mod
    check_code_point = (mod - remainder) % mod
    return GSTIN_CHARSET[check_code_point]

def validate_gstin(gstin: str) -> bool:
    """
    Performs full syntax & Luhn mod-36 checksum verification.
    """
    if not is_valid_gstin_syntax(gstin):
        return False
    gstin = gstin.upper()
    expected_check = calculate_luhn_mod36_checksum(gstin[:14])
    return gstin[14] == expected_check

def normalize_date(d: str) -> str:
    """
    Normalizes any standard date format (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD) to ISO YYYY-MM-DD.
    """
    if not d:
        return ""
    d_clean = str(d).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(d_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return d_clean

def normalize_invoice_number(inv_no: str) -> str:
    """
    Normalizes invoice number by:
    - Stripping punctuation, whitespace, and leading zeros
    - Removing standard prefixes like INV, IN, BILL, TAXINV, CN, CRN, DN
    - Removing compound financial year patterns (e.g. 2023-24, 2024-25, 23-24) and standalone years
    """
    if not inv_no:
        return ""
    cleaned = str(inv_no).strip().upper()
    # Strip prefix labels followed by delimiter
    cleaned = re.sub(r"^(INV(OICE)?|BILL|TAXINV|TI|DOC|CN|CRN|DN|DBN)[\/\-_\s\\#]+", "", cleaned)
    
    # Remove compound FY patterns like 2023-24, 2024-25, 23-24, 24-25
    cleaned = re.sub(r"(^|[\/\-_\s\\#])(20\d{2}|\d{2})[\-_](20\d{2}|\d{2})($|[\/\-_\s\\#])", r"\1\4", cleaned)
    
    # Split by major segment separators: / \ # space _
    parts = [p for p in re.split(r"[\/\\#\s_]+", cleaned) if p]
    if not parts:
        return ""
    
    filtered = []
    for idx, p in enumerate(parts):
        # Skip label prefix at start if still present
        if idx == 0 and re.match(r"^(INV(OICE)?|BILL|TAXINV|TI|DOC|CN|CRN|DN|DBN)$", p):
            continue
        # Skip standalone 4-digit or 2-digit years if there are other parts
        if re.match(r"^(FY)?(20\d{2}|\d{2})$", p) and (idx < len(parts) - 1 or len(parts) > 1):
            continue
        filtered.append(p)

    res = "".join(filtered) if filtered else "".join(parts)
    res = re.sub(r"[^A-Z0-9]+", "", res)
    res = res.lstrip("0")
    return res or "0"

def rupees_to_paise(val: float | int | str | None) -> int:
    """
    Converts currency to integer paise safely, avoiding floating-point drift.
    """
    if val is None or val == "":
        return 0
    try:
        f = float(val)
        return int(round(f * 100))
    except (ValueError, TypeError):
        return 0

def paise_to_rupees(paise: int) -> float:
    return round(paise / 100.0, 2)
