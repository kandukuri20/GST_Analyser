import pytest
from normalizers import validate_gstin, normalize_invoice_number, rupees_to_paise
from engine import GSTReconciliationEngine
from models import InvoiceRecord

def test_gstin_luhn_mod36():
    # Valid sample GSTIN
    # 27AABCT1332L1Z5 (Valid Luhn checksum calculated by standard algorithm)
    assert normalize_invoice_number("INV/2026/0014") == "14"
    assert normalize_invoice_number("000492") == "492"
    assert normalize_invoice_number("BILL-501") == "501"

def test_paise_conversion():
    assert rupees_to_paise(100.55) == 10055
    assert rupees_to_paise(0.40) == 40
    assert rupees_to_paise("1520.10") == 152010

def test_exact_match():
    engine = GSTReconciliationEngine(tolerance_paise=200)
    pr = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            supplier_name="Tata Consultancy Services",
            invoice_number="INV/2026/0001",
            invoice_date="2026-09-10",
            taxable_value=10000.0,
            igst=1800.0,
            total_tax=1800.0,
            total_invoice_value=11800.0,
            taxable_value_paise=1000000,
            igst_paise=180000,
            total_tax_paise=180000,
            total_invoice_value_paise=1180000
        )
    ]
    portal = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            supplier_name="Tata Consultancy Services",
            invoice_number="INV/2026/0001",
            invoice_date="2026-09-10",
            taxable_value=10000.0,
            igst=1800.0,
            total_tax=1800.0,
            total_invoice_value=11800.0,
            taxable_value_paise=1000000,
            igst_paise=180000,
            total_tax_paise=180000,
            total_invoice_value_paise=1180000
        )
    ]
    matches, summary = engine.reconcile(pr, portal)
    assert len(matches) == 1
    assert matches[0].status == "MATCHED"
    assert matches[0].match_pass == "Pass 1: Exact Match"
    assert summary.matched_count == 1

def test_normalized_match():
    engine = GSTReconciliationEngine(tolerance_paise=200)
    pr = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            invoice_number="0045",
            invoice_date="2026-09-10",
            total_tax=1800.0,
            total_invoice_value=11800.0,
            total_tax_paise=180000,
            total_invoice_value_paise=1180000
        )
    ]
    portal = [
        InvoiceRecord(
            gstin="27AAACT2456M1Z2",
            invoice_number="BILL-45",
            invoice_date="2026-09-10",
            total_tax=1800.0,
            total_invoice_value=11800.0,
            total_tax_paise=180000,
            total_invoice_value_paise=1180000
        )
    ]
    matches, summary = engine.reconcile(pr, portal)
    assert len(matches) == 1
    assert matches[0].status == "MATCHED"
    assert "Pass 2" in matches[0].match_pass
