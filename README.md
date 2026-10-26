# GST Reconciliation Engine — MVP / Capstone Project

## 1. Executive Summary
This project implements the complete **GST Reconciliation Engine (MVP / Capstone Design)** outlined in `GST Reconciliation Engine.docx`.

It provides an end-to-end automated platform to reconcile a business's **Purchase Register (Books)** against the government GSTN portal's auto-drafted **GSTR-2B Statement**, strictly adhering to:
- **CGST Act Section 16(2)(aa)**: Verification of vendor upload condition for claiming Input Tax Credit (ITC).
- **CGST Act Section 16(4)**: Statutory 30th November deadline monitoring for lapsed credits.
- **CGST Act Section 17(5)**: Segregation of Ineligible/Blocked ITC credits.
- **CGST Act Section 34**: Credit and Debit Note (CDNR) netting against invoices.

---

## 2. Architecture & Tech Stack

```
+--------------------------------------------------------------------------------+
|                           FRONTEND: REACT + VITE + CSS                         |
|   - Glassmorphic Dashboard & Real-Time Match Analytics                         |
|   - Side-by-Side Purchase Register vs GSTR-2B Difference Viewer                |
|   - CA / Reviewer Manual Override Workspace & Cryptographic Audit Seal         |
|   - Vendor Action Center (Automated Discrepancy Emailer & WhatsApp Notice)     |
|   - Section 16(4) Risk Radar                                                   |
+---------------------------------------+----------------------------------------+
                                        |  REST API (JSON / Multipart Upload)
                                        v
+--------------------------------------------------------------------------------+
|                         BACKEND: FASTAPI + PYTHON 3.10                         |
|   - Robust Luhn Mod-36 GSTIN Checksum Validation                               |
|   - Sub-Rupee Integer Paise Precision (0 floating-point drift)                 |
|   - 5-Tier Hierarchical Matching Engine (RapidFuzz, Normalizers, CDN Netting)  |
|   - GSTR-2B JSON & Excel/CSV Ingestion Parsers                                 |
|   - Synthetic Dataset Generator (Injects realistic Indian supplier errors)     |
+--------------------------------------------------------------------------------+
```

---

## 3. Core Engine Match Passes

1. **Pass 1: Exact Match (100% Confidence)**: Exact GSTIN, exact Invoice Number, and exact values within configurable sub-rupee rounding tolerance (default ₹2.00).
2. **Pass 2: Normalized Number Match (95% Confidence)**: Strips punctuation, `/`, `-`, leading zeros, year patterns (`2026/`, `FY25`), and labels (`INV`, `BILL`, `TAXINV`).
3. **Pass 3: Amount + Date Proximity & Fuzzy String Match (70–90% Confidence)**: Evaluates date proximity window (±30 days) and Levenshtein token ratio via RapidFuzz.
4. **Pass 4: Multi-Branch PAN Match (78% Confidence)**: Matches invoices between distinct state branches of the same corporate PAN (chars 2:12 of GSTIN).
5. **Pass 5: Credit/Debit Note (CDNR) Netting**: Matches credit notes against invoices under Section 34 of the CGST Act.
6. **Unmatched Exceptions**:
   - *Missing in GSTR-2B*: Flags ITC at risk of notice DRC-01C; routes to **Vendor Action Center**.
   - *Section 16(4) Risk*: Invoices from preceding FY approaching statutory November 30 cutoff.
   - *Missing in Books*: Invoices present on portal but missing in enterprise accounting.

---

## 4. How to Run the Application

### Prerequisites
- Python 3.10+
- Node.js 18+

### Step 1: Start Backend API
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project"
.\venv\Scripts\uvicorn backend.main:app --port 8000 --reload
```
API runs at: `http://localhost:8000`  
Interactive Swagger docs: `http://localhost:8000/docs`

### Step 2: Start Frontend UI
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project\frontend"
npm run dev
```
Frontend runs at: `http://localhost:5173`

---

## 5. Sample Data & Test Files
Pre-generated synthetic files are available in `sample_data/`:
- `sample_data/purchase_register_sample.xlsx`: Realistic Purchase Register with Indian suppliers (TCS, Infosys, Reliance, L&T, Airtel, Wipro, etc.).
- `sample_data/gstr2b_sample.json`: GSTN official JSON schema payload.

To re-generate or modify synthetic datasets:
```powershell
.\venv\Scripts\python backend/data_generator.py
```

### Running Automated Test Suite
```powershell
.\venv\Scripts\pytest backend/test_engine.py
```
