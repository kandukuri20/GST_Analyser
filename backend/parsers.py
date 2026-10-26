import json
import io
import re
from datetime import datetime
from typing import List
import pandas as pd
from models import InvoiceRecord
from normalizers import rupees_to_paise, normalize_date

def parse_purchase_register_file(contents: bytes, filename: str) -> List[InvoiceRecord]:
    """
    Parses Purchase Register Excel or CSV into canonical InvoiceRecord list.
    Supports flexible column naming.
    """
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        df = pd.read_csv(io.BytesIO(contents))

    # Normalize column names: lowercase, strip, remove special characters like #, ., /, space
    col_map = {str(c).strip().lower(): c for c in df.columns}
    clean_col_map = {re.sub(r"[^a-z0-9]+", "", str(c).strip().lower()): c for c in df.columns}

    def get_val(row, candidates, default=""):
        for cand in candidates:
            cand_clean = re.sub(r"[^a-z0-9]+", "", cand.lower())
            if cand_clean in clean_col_map:
                v = row[clean_col_map[cand_clean]]
                if pd.notna(v):
                    return v
            if cand.lower() in col_map:
                v = row[col_map[cand.lower()]]
                if pd.notna(v):
                    return v
        return default

    invoices = []
    for _, row in df.iterrows():
        gstin = str(get_val(row, [
            "gstin", "supplier gstin", "supplier_gstin", "ctin", "gstin of supplier",
            "gstinuin", "gstin/uin", "gst identification number (gstin)", "tax number 3", "tax number"
        ])).strip().upper()
        
        inv_no = str(get_val(row, [
            "invoice_number", "invoice no", "inv no", "invoice number", "inum", "doc_no",
            "vch no", "vchno", "voucher no", "invoice#", "invoice #", "bill no", "bill_no", "document no"
        ])).strip()
        
        inv_date = str(get_val(row, [
            "invoice_date", "invoice date", "date", "inv date", "idt", "vch date", "doc. date", "bill date"
        ]))[:10]
        
        sup_name = str(get_val(row, [
            "supplier_name", "supplier name", "vendor", "vendor name", "party name", "cname",
            "particulars", "party", "supplier"
        ]))
        
        inv_type = str(get_val(row, [
            "invoice_type", "type", "inv_type", "document type", "vch type", "voucher type", "doc_type", "doctype"
        ], "INV")).upper()
        if "CR" in inv_type or "CREDIT" in inv_type or "CN" in inv_type:
            inv_type = "CRN"
        elif "DB" in inv_type or "DEBIT" in inv_type or "DN" in inv_type:
            inv_type = "DBN"
        else:
            inv_type = "INV"

        taxable = abs(float(get_val(row, ["taxable_value", "taxable value", "taxable amt", "taxable amount", "txval", "base amount"], 0.0) or 0.0))
        igst = abs(float(get_val(row, ["igst", "iamt", "integrated tax", "igst amount", "integrated tax amount"], 0.0) or 0.0))
        cgst = abs(float(get_val(row, ["cgst", "camt", "central tax", "cgst amount", "central tax amount"], 0.0) or 0.0))
        sgst = abs(float(get_val(row, ["sgst", "samt", "state tax", "sgst amount", "state tax amount"], 0.0) or 0.0))
        cess = abs(float(get_val(row, ["cess", "csamt", "cess amt", "cess amount"], 0.0) or 0.0))
        tot_tax = igst + cgst + sgst + cess
        raw_tot = get_val(row, ["total_invoice_value", "total value", "invoice value", "val", "total", "total amount", "total gross"], taxable + tot_tax)
        tot_val = abs(float(raw_tot or (taxable + tot_tax)))

        raw_date = str(get_val(row, [
            "invoice_date", "invoice date", "date", "inv date", "idt", "vch date", "doc. date", "bill date"
        ]))
        inv_date = normalize_date(raw_date)

        is_risk = str(get_val(row, ["is_at_risk_sec16_4", "sec16_4_risk", "risk"], "false")).lower() in ["true", "1", "yes"]
        # Under Section 16(4) of CGST Act: Invoices from prior FY (e.g. FY 23-24 prior to 2024-04-01) approaching Nov 30 deadline
        if not is_risk and inv_date:
            try:
                # If invoice date is earlier than the beginning of current filing FY (prior to 6+ months ago)
                inv_dt = datetime.strptime(inv_date[:10], "%Y-%m-%d")
                curr_dt = datetime.now()
                # Check if invoice is from a previous financial year (Indian FY ends March 31)
                inv_fy = inv_dt.year if inv_dt.month >= 4 else inv_dt.year - 1
                curr_fy = curr_dt.year if curr_dt.month >= 4 else curr_dt.year - 1
                if inv_fy < curr_fy or (inv_dt.month == 3 and inv_dt.day == 31):
                    is_risk = True
            except Exception:
                pass

        rec = InvoiceRecord(
            gstin=gstin,
            supplier_name=sup_name,
            invoice_number=inv_no,
            invoice_date=inv_date,
            invoice_type=inv_type,
            taxable_value=round(taxable, 2),
            igst=round(igst, 2),
            cgst=round(cgst, 2),
            sgst=round(sgst, 2),
            cess=round(cess, 2),
            total_tax=round(tot_tax, 2),
            total_invoice_value=round(tot_val, 2),
            taxable_value_paise=rupees_to_paise(taxable),
            igst_paise=rupees_to_paise(igst),
            cgst_paise=rupees_to_paise(cgst),
            sgst_paise=rupees_to_paise(sgst),
            cess_paise=rupees_to_paise(cess),
            total_tax_paise=rupees_to_paise(tot_tax),
            total_invoice_value_paise=rupees_to_paise(tot_val),
            itc_available=True,
            is_at_risk_sec16_4=is_risk
        )
        invoices.append(rec)
    
    recipient_name = ""
    recipient_gstin = ""
    for cand in ["recipient_name", "company_name", "buyer_name", "my_company"]:
        if cand in col_map and len(df) > 0 and pd.notna(df[col_map[cand]].iloc[0]):
            recipient_name = str(df[col_map[cand]].iloc[0])
            break
    for cand in ["recipient_gstin", "my_gstin", "buyer_gstin"]:
        if cand in col_map and len(df) > 0 and pd.notna(df[col_map[cand]].iloc[0]):
            recipient_gstin = str(df[col_map[cand]].iloc[0])
            break

    return invoices, recipient_gstin, recipient_name

def parse_gstr2b_json(json_content: str | dict) -> List[InvoiceRecord]:
    """
    Parses GSTN GSTR-2B official JSON format (b2b, cdnr arrays).
    Supports itemized schema (items array) or flat invoice tax fields (txval, cgst, sgst, igst, cess).
    """
    if isinstance(json_content, str):
        data = json.loads(json_content)
    else:
        data = json_content

    invoices = []
    docdata = data.get("docdata", data) # Some APIs wrap in docdata, some direct

    # 1. B2B Invoices
    b2b_list = docdata.get("b2b", [])
    for supplier in b2b_list:
        ctin = supplier.get("ctin", "").strip().upper()
        cname = supplier.get("cname", "") or supplier.get("trdnm", "")
        for inv in supplier.get("inv", []):
            inum = str(inv.get("inum", "") or inv.get("inv_no", "")).strip()
            raw_date = str(inv.get("idt", "") or inv.get("dt", "") or inv.get("inv_dt", ""))
            idt = normalize_date(raw_date)
            val = float(inv.get("val", 0.0) or 0.0)
            itcavl = str(inv.get("itcavl", "Y")).upper() == "Y"
            rsn = inv.get("rsn", "Eligible ITC" if itcavl else "Ineligible under Sec 17(5)")

            # Aggregate tax items: check items array first; if absent, read directly from inv
            txval = 0.0
            iamt = 0.0
            camt = 0.0
            samt = 0.0
            csamt = 0.0

            items = inv.get("items", [])
            if items:
                for item in items:
                    txval += float(item.get("txval", 0.0) or 0.0)
                    iamt += float(item.get("iamt", 0.0) or item.get("igst", 0.0) or 0.0)
                    camt += float(item.get("camt", 0.0) or item.get("cgst", 0.0) or 0.0)
                    samt += float(item.get("samt", 0.0) or item.get("sgst", 0.0) or 0.0)
                    csamt += float(item.get("csamt", 0.0) or item.get("cess", 0.0) or 0.0)
            else:
                txval = float(inv.get("txval", 0.0) or 0.0)
                iamt = float(inv.get("iamt", 0.0) or inv.get("igst", 0.0) or 0.0)
                camt = float(inv.get("camt", 0.0) or inv.get("cgst", 0.0) or 0.0)
                samt = float(inv.get("samt", 0.0) or inv.get("sgst", 0.0) or 0.0)
                csamt = float(inv.get("csamt", 0.0) or inv.get("cess", 0.0) or 0.0)

            tot_tax = iamt + camt + samt + csamt
            if val == 0.0:
                val = txval + tot_tax

            rec = InvoiceRecord(
                gstin=ctin,
                supplier_name=cname,
                invoice_number=inum,
                invoice_date=idt,
                invoice_type="INV",
                taxable_value=round(txval, 2),
                igst=round(iamt, 2),
                cgst=round(camt, 2),
                sgst=round(samt, 2),
                cess=round(csamt, 2),
                total_tax=round(tot_tax, 2),
                total_invoice_value=round(val, 2),
                taxable_value_paise=rupees_to_paise(txval),
                igst_paise=rupees_to_paise(iamt),
                cgst_paise=rupees_to_paise(camt),
                sgst_paise=rupees_to_paise(samt),
                cess_paise=rupees_to_paise(csamt),
                total_tax_paise=rupees_to_paise(tot_tax),
                total_invoice_value_paise=rupees_to_paise(val),
                itc_available=itcavl,
                itc_eligibility_reason=rsn
            )
            invoices.append(rec)

    # 2. CDNR (Credit / Debit Notes)
    cdnr_list = docdata.get("cdnr", [])
    for supplier in cdnr_list:
        ctin = supplier.get("ctin", "").strip().upper()
        cname = supplier.get("cname", "") or supplier.get("trdnm", "")
        for note in supplier.get("nt", []):
            inum = str(note.get("ntnum", "") or note.get("nt_num", "") or note.get("inum", "")).strip()
            raw_date = str(note.get("ntdt", "") or note.get("dt", "") or note.get("nt_dt", ""))
            idt = normalize_date(raw_date)
            val = float(note.get("val", 0.0) or 0.0)
            typ = str(note.get("typ", "") or note.get("ntty", "C")).upper()
            inv_type = "CRN" if "C" in typ else "DBN"
            itcavl = str(note.get("itcavl", "Y")).upper() == "Y"

            txval = 0.0
            iamt = 0.0
            camt = 0.0
            samt = 0.0
            csamt = 0.0

            items = note.get("items", [])
            if items:
                for item in items:
                    txval += float(item.get("txval", 0.0) or 0.0)
                    iamt += float(item.get("iamt", 0.0) or item.get("igst", 0.0) or 0.0)
                    camt += float(item.get("camt", 0.0) or item.get("cgst", 0.0) or 0.0)
                    samt += float(item.get("samt", 0.0) or item.get("sgst", 0.0) or 0.0)
                    csamt += float(item.get("csamt", 0.0) or item.get("cess", 0.0) or 0.0)
            else:
                txval = float(note.get("txval", 0.0) or 0.0)
                iamt = float(note.get("iamt", 0.0) or note.get("igst", 0.0) or 0.0)
                camt = float(note.get("camt", 0.0) or note.get("cgst", 0.0) or 0.0)
                samt = float(note.get("samt", 0.0) or note.get("sgst", 0.0) or 0.0)
                csamt = float(note.get("csamt", 0.0) or note.get("cess", 0.0) or 0.0)

            tot_tax = iamt + camt + samt + csamt
            if val == 0.0:
                val = txval + tot_tax

            rec = InvoiceRecord(
                gstin=ctin,
                supplier_name=cname,
                invoice_number=inum,
                invoice_date=idt,
                invoice_type=inv_type,
                taxable_value=round(txval, 2),
                igst=round(iamt, 2),
                cgst=round(camt, 2),
                sgst=round(samt, 2),
                cess=round(csamt, 2),
                total_tax=round(tot_tax, 2),
                total_invoice_value=round(val, 2),
                taxable_value_paise=rupees_to_paise(txval),
                igst_paise=rupees_to_paise(iamt),
                cgst_paise=rupees_to_paise(camt),
                sgst_paise=rupees_to_paise(samt),
                cess_paise=rupees_to_paise(csamt),
                total_tax_paise=rupees_to_paise(tot_tax),
                total_invoice_value_paise=rupees_to_paise(val),
                itc_available=itcavl
            )
            invoices.append(rec)

    recipient_gstin = data.get("gstin", "")
    recipient_name = data.get("legal_name", "") or data.get("trade_name", "") or data.get("trdnm", "")
    return invoices, recipient_gstin, recipient_name
