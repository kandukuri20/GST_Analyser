import json
import os
import random
from datetime import datetime, timedelta
import pandas as pd
from normalizers import calculate_luhn_mod36_checksum, rupees_to_paise

# List of realistic Indian suppliers
SUPPLIERS = [
    {"name": "Tata Consultancy Services Ltd", "pan": "AAACT2456M", "state": "27"}, # Maharashtra
    {"name": "Infosys Technologies Ltd", "pan": "AABCI9087E", "state": "29"},     # Karnataka
    {"name": "Reliance Retail Ventures", "pan": "AAACR1234F", "state": "27"},      # Maharashtra
    {"name": "Larsen & Toubro Ltd", "pan": "AAACL4567H", "state": "24"},            # Gujarat
    {"name": "Bharti Airtel Ltd", "pan": "AAACB7890K", "state": "07"},              # Delhi
    {"name": "Wipro Enterprises Pvt Ltd", "pan": "AAACW3452B", "state": "29"},     # Karnataka
    {"name": "HCL Technologies Ltd", "pan": "AAACH6781D", "state": "09"},          # Uttar Pradesh
    {"name": "Mahindra & Mahindra Logistics", "pan": "AAACM1122P", "state": "27"}, # Maharashtra
    {"name": "Adani Ports & SEZ Ltd", "pan": "AAACA8899J", "state": "24"},         # Gujarat
    {"name": "Sun Pharma Industries", "pan": "AAACS4455Q", "state": "24"},         # Gujarat
]

def make_gstin(state_code: str, pan: str, entity_num: str = "1") -> str:
    partial = f"{state_code}{pan}{entity_num}Z"
    chk = calculate_luhn_mod36_checksum(partial)
    return f"{partial}{chk}"

def generate_synthetic_dataset(num_records: int = 40):
    """
    Generates paired Purchase Register (Excel-ready) and GSTR-2B (JSON-ready) data,
    deliberately injecting:
    - Exact matches
    - Normalized number variances (INV/001 vs 1 vs 001)
    - Sub-rupee rounding differences (Rs 0.40 - 0.90)
    - Missing in GSTR-2B (vendor failed to file)
    - Missing in Purchase Register (accountant missed entering invoice)
    - Credit Notes (CDNR)
    - Section 16(4) at-risk old invoices
    - Ineligible ITC tags
    """
    pr_records = []
    gstr_records = []
    
    base_date = datetime(2026, 9, 1)

    for i in range(1, num_records + 1):
        sup = random.choice(SUPPLIERS)
        gstin = make_gstin(sup["state"], sup["pan"], "1")
        inv_no_raw = f"{i:04d}"
        inv_date = (base_date + timedelta(days=random.randint(0, 28))).strftime("%Y-%m-%d")
        
        taxable = round(random.uniform(5000, 250000), 2)
        # Tax rate: 18%
        is_interstate = (sup["state"] != "27") # Assuming our recipient company is in Maharashtra (27)
        
        if is_interstate:
            igst = round(taxable * 0.18, 2)
            cgst = 0.0
            sgst = 0.0
        else:
            igst = 0.0
            cgst = round(taxable * 0.09, 2)
            sgst = round(taxable * 0.09, 2)
            
        total_tax = round(igst + cgst + sgst, 2)
        total_val = round(taxable + total_tax, 2)
        
        category = i % 8

        if category in [0, 1, 2]:
            # CATEGORY A: Exact Match
            inv_str = f"INV/2026/{inv_no_raw}"
            pr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": True,
                "is_at_risk_sec16_4": False
            })
            gstr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": True,
                "filing_date": "2026-10-11"
            })

        elif category == 3:
            # CATEGORY B: Normalized Number Difference (e.g., '0015' in books vs 'INV-15' on portal)
            pr_inv_str = f"00{inv_no_raw}"
            portal_inv_str = f"BILL-{inv_no_raw.lstrip('0')}"
            pr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": pr_inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": True,
                "is_at_risk_sec16_4": False
            })
            gstr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": portal_inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": True,
                "filing_date": "2026-10-10"
            })

        elif category == 4:
            # CATEGORY C: Sub-Rupee Rounding Discrepancy (e.g. ₹0.65 rounding drift)
            inv_str = f"INV/{inv_no_raw}"
            drift = 0.65
            pr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": True,
                "is_at_risk_sec16_4": False
            })
            gstr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": round(igst + (drift if is_interstate else 0.0), 2),
                "cgst": round(cgst + (0.0 if is_interstate else drift / 2), 2),
                "sgst": round(sgst + (0.0 if is_interstate else drift / 2), 2),
                "cess": 0.0,
                "total_tax": round(total_tax + drift, 2),
                "total_invoice_value": round(total_val + drift, 2),
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(round(igst + (drift if is_interstate else 0.0), 2)),
                "cgst_paise": rupees_to_paise(round(cgst + (0.0 if is_interstate else drift / 2), 2)),
                "sgst_paise": rupees_to_paise(round(sgst + (0.0 if is_interstate else drift / 2), 2)),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(round(total_tax + drift, 2)),
                "total_invoice_value_paise": rupees_to_paise(round(total_val + drift, 2)),
                "itc_available": True,
                "filing_date": "2026-10-12"
            })

        elif category == 5:
            # CATEGORY D: Missing in GSTR-2B (Vendor failed to upload GSTR-1, or Section 16(4) Risk)
            inv_str = f"INV/DEF/{inv_no_raw}"
            is_sec16_4 = (i % 2 == 0)
            old_date = "2025-11-15" if is_sec16_4 else inv_date
            pr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": old_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": True,
                "sec16_4_deadline": "2026-11-30",
                "is_at_risk_sec16_4": is_sec16_4
            })
            # Deliberately NOT added to gstr_records

        elif category == 6:
            # CATEGORY E: Ineligible ITC on GSTR-2B or Missing in Books
            inv_str = f"GSTR-ONLY/{inv_no_raw}"
            gstr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "INV",
                "taxable_value": taxable,
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "cess": 0.0,
                "total_tax": total_tax,
                "total_invoice_value": total_val,
                "taxable_value_paise": rupees_to_paise(taxable),
                "igst_paise": rupees_to_paise(igst),
                "cgst_paise": rupees_to_paise(cgst),
                "sgst_paise": rupees_to_paise(sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(total_tax),
                "total_invoice_value_paise": rupees_to_paise(total_val),
                "itc_available": False,
                "itc_eligibility_reason": "Ineligible under Section 17(5) - Blocked Credit",
                "filing_date": "2026-10-08"
            })
            # Not in pr_records

        elif category == 7:
            # CATEGORY F: Credit Note Netting (CRN)
            inv_str = f"CRN/{inv_no_raw}"
            crn_taxable = round(taxable * 0.25, 2)
            crn_igst = round(igst * 0.25, 2)
            crn_cgst = round(cgst * 0.25, 2)
            crn_sgst = round(sgst * 0.25, 2)
            crn_tax = round(crn_igst + crn_cgst + crn_sgst, 2)
            crn_val = round(crn_taxable + crn_tax, 2)
            
            pr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "CRN",
                "taxable_value": crn_taxable,
                "igst": crn_igst,
                "cgst": crn_cgst,
                "sgst": crn_sgst,
                "cess": 0.0,
                "total_tax": crn_tax,
                "total_invoice_value": crn_val,
                "taxable_value_paise": rupees_to_paise(crn_taxable),
                "igst_paise": rupees_to_paise(crn_igst),
                "cgst_paise": rupees_to_paise(crn_cgst),
                "sgst_paise": rupees_to_paise(crn_sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(crn_tax),
                "total_invoice_value_paise": rupees_to_paise(crn_val),
                "itc_available": True,
                "is_at_risk_sec16_4": False
            })
            gstr_records.append({
                "gstin": gstin,
                "supplier_name": sup["name"],
                "invoice_number": inv_str,
                "invoice_date": inv_date,
                "invoice_type": "CRN",
                "taxable_value": crn_taxable,
                "igst": crn_igst,
                "cgst": crn_cgst,
                "sgst": crn_sgst,
                "cess": 0.0,
                "total_tax": crn_tax,
                "total_invoice_value": crn_val,
                "taxable_value_paise": rupees_to_paise(crn_taxable),
                "igst_paise": rupees_to_paise(crn_igst),
                "cgst_paise": rupees_to_paise(crn_cgst),
                "sgst_paise": rupees_to_paise(crn_sgst),
                "cess_paise": 0,
                "total_tax_paise": rupees_to_paise(crn_tax),
                "total_invoice_value_paise": rupees_to_paise(crn_val),
                "itc_available": True,
                "filing_date": "2026-10-10"
            })

    # Save to disk as files for immediate testing
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_dir = os.path.join(base_dir, "sample_data")
    os.makedirs(sample_dir, exist_ok=True)

    # 1. Purchase Register Excel
    df_pr = pd.DataFrame(pr_records)
    pr_excel_path = os.path.join(sample_dir, "purchase_register_sample.xlsx")
    df_pr.to_excel(pr_excel_path, index=False)

    # 2. GSTR-2B JSON (simulates GSTN portal payload format)
    gstr2b_payload = {
        "gstin": "27AABCT1332L1Z5", # Taxpayer Recipient GSTIN
        "fp": "092026",
        "docdata": {
            "b2b": [
                {
                    "ctin": r["gstin"],
                    "cname": r["supplier_name"],
                    "inv": [
                        {
                            "inum": r["invoice_number"],
                            "idt": r["invoice_date"],
                            "val": r["total_invoice_value"],
                            "pos": "27",
                            "inv_typ": "R",
                            "itcavl": "Y" if r.get("itc_available", True) else "N",
                            "rsn": r.get("itc_eligibility_reason", ""),
                            "items": [
                                {
                                    "num": 1,
                                    "txval": r["taxable_value"],
                                    "iamt": r["igst"],
                                    "camt": r["cgst"],
                                    "samt": r["sgst"],
                                    "csamt": r["cess"]
                                }
                            ]
                        }
                    ]
                }
                for r in gstr_records if r.get("invoice_type") == "INV"
            ],
            "cdnr": [
                {
                    "ctin": r["gstin"],
                    "cname": r["supplier_name"],
                    "nt": [
                        {
                            "ntnum": r["invoice_number"],
                            "ntdt": r["invoice_date"],
                            "val": r["total_invoice_value"],
                            "typ": "C",
                            "itcavl": "Y",
                            "items": [
                                {
                                    "txval": r["taxable_value"],
                                    "iamt": r["igst"],
                                    "camt": r["cgst"],
                                    "samt": r["sgst"],
                                    "csamt": 0.0
                                }
                            ]
                        }
                    ]
                }
                for r in gstr_records if r.get("invoice_type") == "CRN"
            ]
        }
    }
    
    gstr_json_path = os.path.join(sample_dir, "gstr2b_sample.json")
    with open(gstr_json_path, "w") as f:
        json.dump(gstr2b_payload, f, indent=2)

    return pr_records, gstr_records, pr_excel_path, gstr_json_path

if __name__ == "__main__":
    pr, gstr, exc_path, json_path = generate_synthetic_dataset(50)
    print(f"Generated {len(pr)} PR records and {len(gstr)} GSTR records.")
    print(f"Saved: {exc_path} and {json_path}")
