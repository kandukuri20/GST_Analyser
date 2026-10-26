import pytest
import io
import json
import pandas as pd
from parsers import parse_purchase_register_file, parse_gstr2b_json
from engine import GSTReconciliationEngine

@pytest.fixture
def engine():
    return GSTReconciliationEngine(tolerance_paise=200, date_tolerance_days=30)

# =========================================================================
# DATA SOURCE 1: Tally Prime CSV Export Format
# Real-world Tally has columns: Date, Particulars, Vch Type, Vch No, GSTIN/UIN, Taxable Value, Integrated Tax, Central Tax, State Tax, Total Amount
# =========================================================================
def test_tally_prime_csv_source(engine):
    tally_csv = """Date,Particulars,Vch Type,Vch No,GSTIN/UIN,Taxable Value,Integrated Tax,Central Tax,State Tax,Total Amount,Recipient_Name,Recipient_GSTIN
2026-09-05,Infosys Technologies,Purchase,INV-9021,29AABCI9087E1ZN,50000,9000,0,0,59000,Godrej Consumer Products,27AABCG4567P1ZV
2026-09-12,Wipro Cloud Solutions,Purchase,INV-3312,29AAACW3452B1ZX,20000,3600,0,0,23600,Godrej Consumer Products,27AABCG4567P1ZV
"""
    records, recipient_gstin, recipient_name = parse_purchase_register_file(tally_csv.encode("utf-8"), "tally_purchase_register.csv")
    assert len(records) == 2
    assert recipient_gstin == "27AABCG4567P1ZV"
    assert recipient_name == "Godrej Consumer Products"
    assert records[0].invoice_number == "INV-9021"
    assert records[0].gstin == "29AABCI9087E1ZN"
    assert records[0].total_tax == 9000.0

# =========================================================================
# DATA SOURCE 2: Zoho Books Excel/CSV Export Format
# Real-world Zoho columns: Invoice Date, Vendor Name, Invoice#, GST Identification Number (GSTIN), Taxable Amount, IGST, CGST, SGST, Total
# =========================================================================
def test_zoho_books_csv_source(engine):
    zoho_csv = """Invoice Date,Vendor Name,Invoice#,GST Identification Number (GSTIN),Taxable Amount,IGST,CGST,SGST,Total
2026-09-08,Tata Consultancy Services,TI/2026/0045,27AAACT2456M1Z2,100000,0,9000,9000,118000
2026-09-18,Larsen & Toubro Ltd,BILL/889,24AAACL4567H1ZR,75000,13500,0,0,88500
"""
    records, recipient_gstin, recipient_name = parse_purchase_register_file(zoho_csv.encode("utf-8"), "zoho_bills_export.csv")
    assert len(records) == 2
    assert records[0].supplier_name == "Tata Consultancy Services"
    assert records[0].invoice_number == "TI/2026/0045"
    assert records[0].cgst == 9000.0
    assert records[0].sgst == 9000.0

# =========================================================================
# DATA SOURCE 3: SAP ECC / S4HANA Standard MM-FI Export
# Real-world SAP columns: Doc. Date, Vendor, Document No, Tax Number 3 (GSTIN), Base Amount, Output/Input Tax, Total Gross
# =========================================================================
def test_sap_s4hana_excel_source(engine):
    sap_data = {
        "Doc_No": ["INV/SAP/001", "CRN/SAP/002"],
        "Supplier_GSTIN": ["27AAACR1234F1Z4", "27AAACR1234F1Z4"],
        "Party Name": ["Reliance Retail", "Reliance Retail"],
        "Date": ["2026-09-15", "2026-09-20"],
        "Document Type": ["INV", "Credit Note"],
        "Taxable Value": [40000.0, 10000.0],
        "IGST": [7200.0, 1800.0],
        "CGST": [0.0, 0.0],
        "SGST": [0.0, 0.0],
        "Total Value": [47200.0, 11800.0]
    }
    df = pd.DataFrame(sap_data)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)

    records, recipient_gstin, recipient_name = parse_purchase_register_file(buf.getvalue(), "sap_purchase_register.xlsx")
    assert len(records) == 2
    assert records[0].invoice_type == "INV"
    assert records[1].invoice_type == "CRN"
    assert records[0].total_tax == 7200.0
    assert records[1].total_tax == 1800.0

# =========================================================================
# DATA SOURCE 4: GSTN Official GSTR-2B JSON Payload (Direct from GST Portal)
# Zero hardcoded values: taxpayer recipient GSTIN, suppliers, and items all fetched from json payload
# =========================================================================
def test_gstn_gstr2b_portal_json_source(engine):
    portal_json = {
        "gstin": "06AABCM9988K1ZQ", # Dynamic Recipient (Haryana entity)
        "legal_name": "Maruti Suzuki Supply Chain Ltd",
        "fp": "092026",
        "docdata": {
            "b2b": [
                {
                    "ctin": "29AABCI9087E1ZN",
                    "cname": "Infosys Technologies",
                    "inv": [
                        {
                            "inum": "INV-9021",
                            "idt": "2026-09-05",
                            "val": 59000.0,
                            "pos": "06",
                            "itcavl": "Y",
                            "items": [
                                {
                                    "txval": 50000.0,
                                    "iamt": 9000.0,
                                    "camt": 0.0,
                                    "samt": 0.0,
                                    "csamt": 0.0
                                }
                            ]
                        }
                    ]
                }
            ],
            "cdnr": []
        }
    }
    records, recipient_gstin, recipient_name = parse_gstr2b_json(portal_json)
    assert len(records) == 1
    assert recipient_gstin == "06AABCM9988K1ZQ"
    assert recipient_name == "Maruti Suzuki Supply Chain Ltd"
    assert records[0].gstin == "29AABCI9087E1ZN"
    assert records[0].total_tax == 9000.0

# =========================================================================
# CROSS-SOURCE RECONCILIATION TEST: Tally CSV vs GSTN JSON
# Reconciles records completely without hardcoding any entities
# =========================================================================
def test_cross_source_reconciliation(engine):
    tally_csv = """Date,Particulars,Vch Type,Vch No,GSTIN/UIN,Taxable Value,Integrated Tax,Central Tax,State Tax,Total Amount
2026-09-05,Infosys Technologies,Purchase,INV-9021,29AABCI9087E1ZN,50000,9000,0,0,59000
"""
    portal_json = {
        "gstin": "06AABCM9988K1ZQ",
        "legal_name": "Maruti Suzuki Supply Chain Ltd",
        "docdata": {
            "b2b": [
                {
                    "ctin": "29AABCI9087E1ZN",
                    "cname": "Infosys Technologies",
                    "inv": [
                        {
                            "inum": "INV-9021",
                            "idt": "2026-09-05",
                            "val": 59000.0,
                            "itcavl": "Y",
                            "items": [{"txval": 50000.0, "iamt": 9000.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0}]
                        }
                    ]
                }
            ]
        }
    }
    pr_records, _, _ = parse_purchase_register_file(tally_csv.encode("utf-8"), "tally.csv")
    portal_records, _, _ = parse_gstr2b_json(portal_json)

    matches, summary = engine.reconcile(pr_records, portal_records)
    assert len(matches) == 1
    assert matches[0].status == "MATCHED"
    assert summary.match_rate_percentage == 100.0
    assert summary.matched_itc == 9000.0
