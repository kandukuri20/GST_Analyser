import pytest
from normalizers import (
    validate_gstin,
    normalize_invoice_number,
    rupees_to_paise,
    paise_to_rupees,
    calculate_luhn_mod36_checksum
)
from engine import GSTReconciliationEngine
from models import InvoiceRecord
from parsers import parse_purchase_register_file, parse_gstr2b_json
import pandas as pd
import json
import io

@pytest.fixture
def engine():
    return GSTReconciliationEngine(tolerance_paise=200, date_tolerance_days=30)

# =========================================================================
# EDGE CASE 1: Luhn Mod-36 GSTIN & Formatting Quirks
# =========================================================================
def test_gstin_edge_cases():
    # Valid checksum test
    valid_gstin = "27AAACT2456M1Z2"
    # Check checksum calculation
    expected_check = calculate_luhn_mod36_checksum("27AAACT2456M1Z")
    assert expected_check == "2"
    assert validate_gstin("27AAACT2456M1Z2") is True
    
    # Invalid length or corrupt characters
    assert validate_gstin("") is False
    assert validate_gstin("27AAACT2456M1Z") is False # 14 chars
    assert validate_gstin("27AAACT2456M1Z99") is False # 16 chars
    assert validate_gstin("27AAACT2456M1ZX") is False # wrong checksum

def test_invoice_normalization_edge_cases():
    # Real-world enterprise invoice number dirty inputs:
    # 1. Padded leading zeros: '0000042' -> '42'
    assert normalize_invoice_number("0000042") == "42"
    # 2. Slanted slashes & financial year: 'INV/2024-25/0981' -> '981'
    assert normalize_invoice_number("INV/2024-25/0981") == "981"
    # 3. Special prefix variations: 'TAXINV-2026/001' -> '1'
    assert normalize_invoice_number("TAXINV-2026/001") == "1"
    # 4. Spaced/hyphenated: ' BILL - 781 ' -> '781'
    assert normalize_invoice_number(" BILL - 781 ") == "781"
    # 5. Pure alphabetical / alphanumeric: 'DL-A109' -> 'DLA109'
    assert normalize_invoice_number("DL-A109") == "DLA109"
    # 6. None or Empty string
    assert normalize_invoice_number(None) == ""
    assert normalize_invoice_number("") == ""

# =========================================================================
# EDGE CASE 2: Sub-rupee Paise Drift & Floating Point Rounding
# =========================================================================
def test_sub_rupee_floating_point_rounding(engine):
    # Python float 0.1 + 0.2 != 0.3. Using paise guarantees deterministic precision.
    pr = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            invoice_number="INV/101",
            invoice_date="2026-09-01",
            taxable_value=12345.67,
            total_tax=2222.22,
            total_invoice_value=14567.89,
            taxable_value_paise=rupees_to_paise(12345.67),
            total_tax_paise=rupees_to_paise(2222.22),
            total_invoice_value_paise=rupees_to_paise(14567.89)
        )
    ]
    # Supplier billed with ₹0.85 paise round-off difference
    portal = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            invoice_number="INV/101",
            invoice_date="2026-09-01",
            taxable_value=12345.67,
            total_tax=2223.07, # 85 paise higher
            total_invoice_value=14568.74, # 85 paise higher
            taxable_value_paise=rupees_to_paise(12345.67),
            total_tax_paise=rupees_to_paise(2223.07),
            total_invoice_value_paise=rupees_to_paise(14568.74)
        )
    ]
    matches, summary = engine.reconcile(pr, portal)
    assert len(matches) == 1
    # 85 paise is within default 200 paise (₹2.00) tolerance
    assert matches[0].status == "MATCHED"
    assert matches[0].match_pass == "Pass 1: Exact Match"
    assert matches[0].tax_diff_paise == -85
    assert matches[0].tax_diff_rupees == -0.85

# =========================================================================
# EDGE CASE 3: Multi-Branch Billing under Same PAN
# =========================================================================
def test_same_pan_different_state_branches(engine):
    # Buyer books under Maharashtra branch (27), Supplier filed under Karnataka branch (29)
    pan = "AAACT2456M"
    pr = [
        InvoiceRecord(
            gstin=f"27{pan}1Z2",
            supplier_name="TCS Mumbai Branch",
            invoice_number="INV/2026/890",
            invoice_date="2026-09-15",
            total_tax=18000.0,
            total_invoice_value=118000.0,
            total_tax_paise=1800000,
            total_invoice_value_paise=11800000
        )
    ]
    portal = [
        InvoiceRecord(
            gstin=f"29{pan}1Z8", # Same PAN, state 29
            supplier_name="TCS Bangalore Branch",
            invoice_number="INV-890",
            invoice_date="2026-09-17", # 2 days drift
            total_tax=18000.0,
            total_invoice_value=118000.0,
            total_tax_paise=1800000,
            total_invoice_value_paise=11800000
        )
    ]
    matches, summary = engine.reconcile(pr, portal)
    assert len(matches) == 1
    assert matches[0].status == "PROBABLE_MATCH"
    assert "Pass 4" in matches[0].match_pass
    assert "Same PAN" in matches[0].reasons[0]

# =========================================================================
# EDGE CASE 4: Section 16(4) Approaching Cutoff
# =========================================================================
def test_sec16_4_approaching_statutory_cutoff(engine):
    # Old invoice from prior financial year missing in GSTR-2B
    pr = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            supplier_name="Infosys",
            invoice_number="INV/OLD/2025",
            invoice_date="2025-10-10",
            total_tax=45000.0,
            total_invoice_value=295000.0,
            total_tax_paise=4500000,
            total_invoice_value_paise=29500000,
            is_at_risk_sec16_4=True
        )
    ]
    portal = [] # Not uploaded by supplier
    matches, summary = engine.reconcile(pr, portal)
    assert len(matches) == 1
    assert matches[0].status == "MISMATCH"
    assert summary.at_risk_itc_sec16_4 == 45000.0
    assert any("Section 16(4)" in r for r in matches[0].reasons)
    assert "URGENT" in matches[0].action_required

# =========================================================================
# EDGE CASE 5: Credit Note (CDNR) Offset under Section 34
# =========================================================================
def test_credit_note_matching(engine):
    pr = [
        InvoiceRecord(
            gstin="27AAACR1234F1Z4",
            supplier_name="Reliance Retail",
            invoice_number="CRN/0091",
            invoice_type="CRN",
            invoice_date="2026-09-20",
            total_tax=3600.0,
            total_invoice_value=23600.0,
            total_tax_paise=360000,
            total_invoice_value_paise=2360000
        )
    ]
    portal = [
        InvoiceRecord(
            gstin="27AAACR1234F1Z4",
            supplier_name="Reliance Retail",
            invoice_number="CRN/0091",
            invoice_type="CRN",
            invoice_date="2026-09-21",
            total_tax=3600.0,
            total_invoice_value=23600.0,
            total_tax_paise=360000,
            total_invoice_value_paise=2360000
        )
    ]
    matches, summary = engine.reconcile(pr, portal)
    assert len(matches) == 1
    assert matches[0].status == "MATCHED"
    assert "Pass 5" in matches[0].match_pass or "Pass 1" in matches[0].match_pass

# =========================================================================
# EDGE CASE 6: Ineligible ITC Tagged by GSTN Portal (Sec 17(5))
# =========================================================================
def test_ineligible_itc_handling(engine):
    portal = [
        InvoiceRecord(
            gstin="27AAACB7890K1Z1",
            supplier_name="Bharti Airtel",
            invoice_number="BILL-9901",
            invoice_date="2026-09-22",
            total_tax=5400.0,
            total_invoice_value=35400.0,
            total_tax_paise=540000,
            total_invoice_value_paise=3540000,
            itc_available=False,
            itc_eligibility_reason="Blocked under Section 17(5)"
        )
    ]
    matches, summary = engine.reconcile([], portal)
    assert len(matches) == 1
    assert summary.ineligible_itc_portal == 5400.0
    assert summary.matched_itc == 0.0

# =========================================================================
# EDGE CASE 7: Deterministic Invariance (Shuffling Inputs)
# =========================================================================
def test_deterministic_invariance(engine):
    inv1 = InvoiceRecord(gstin="27AAACT2456M1Z2", invoice_number="INV/1", invoice_date="2026-09-01", total_tax=100.0, total_invoice_value=600.0, total_tax_paise=10000, total_invoice_value_paise=60000)
    inv2 = InvoiceRecord(gstin="27AAACT2456M1Z2", invoice_number="INV/2", invoice_date="2026-09-02", total_tax=200.0, total_invoice_value=1200.0, total_tax_paise=20000, total_invoice_value_paise=120000)
    
    port1 = InvoiceRecord(gstin="27AAACT2456M1Z2", invoice_number="INV/1", invoice_date="2026-09-01", total_tax=100.0, total_invoice_value=600.0, total_tax_paise=10000, total_invoice_value_paise=60000)
    port2 = InvoiceRecord(gstin="27AAACT2456M1Z2", invoice_number="INV/2", invoice_date="2026-09-02", total_tax=200.0, total_invoice_value=1200.0, total_tax_paise=20000, total_invoice_value_paise=120000)
    
    # Run in order 1, 2
    m_a, s_a = engine.reconcile([inv1, inv2], [port1, port2])
    # Run shuffled in order 2, 1
    m_b, s_b = engine.reconcile([inv2, inv1], [port2, port1])
    
    assert s_a.matched_count == s_b.matched_count == 2
    assert s_a.matched_itc == s_b.matched_itc == 300.0
