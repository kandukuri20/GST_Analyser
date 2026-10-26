from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field

class InvoiceRecord(BaseModel):
    id: Optional[str] = None
    gstin: str
    supplier_name: Optional[str] = ""
    invoice_number: str
    norm_invoice_number: Optional[str] = ""
    invoice_date: str # YYYY-MM-DD
    invoice_type: str = "INV" # INV, CRN (Credit Note), DBN (Debit Note)
    taxable_value: float = 0.0
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    cess: float = 0.0
    total_tax: float = 0.0
    total_invoice_value: float = 0.0
    
    # Integer Paise representations
    taxable_value_paise: int = 0
    igst_paise: int = 0
    cgst_paise: int = 0
    sgst_paise: int = 0
    cess_paise: int = 0
    total_tax_paise: int = 0
    total_invoice_value_paise: int = 0
    
    # Compliance & GSTR metadata
    itc_available: bool = True
    itc_eligibility_reason: Optional[str] = "Eligible ITC"
    filing_date: Optional[str] = None
    gstr1_filed: bool = True
    sec16_4_deadline: Optional[str] = None
    is_at_risk_sec16_4: bool = False

class MatchGroup(BaseModel):
    match_id: str
    match_pass: str  # Pass 1: Exact, Pass 2: Normalized, Pass 3: Approx, Pass 4: Fuzzy Supplier, Pass 5: CDN Netting, Manual Override
    confidence_score: float # 0 - 100
    status: str # MATCHED, PROBABLE_MATCH, MISMATCH, MANUAL_APPROVED
    pr_invoice: Optional[InvoiceRecord] = None
    portal_invoice: Optional[InvoiceRecord] = None
    
    # Variance in Paise
    value_diff_paise: int = 0
    tax_diff_paise: int = 0
    value_diff_rupees: float = 0.0
    tax_diff_rupees: float = 0.0
    date_diff_days: int = 0
    
    reasons: List[str] = []
    action_required: Optional[str] = None
    locked: bool = False
    reviewer_notes: Optional[str] = None

class ReconciliationSummary(BaseModel):
    total_pr_count: int = 0
    total_portal_count: int = 0
    
    matched_count: int = 0
    probable_match_count: int = 0
    unmatched_pr_count: int = 0
    unmatched_portal_count: int = 0
    
    # Financial Aggregates in Rupees
    pr_total_tax: float = 0.0
    portal_total_tax: float = 0.0
    matched_itc: float = 0.0
    at_risk_itc_sec16_4: float = 0.0
    ineligible_itc_portal: float = 0.0
    missing_in_portal_itc: float = 0.0
    missing_in_pr_itc: float = 0.0
    
    match_rate_percentage: float = 0.0
    reconciliation_hash: str = ""
    is_locked: bool = False
    locked_at: Optional[str] = None
