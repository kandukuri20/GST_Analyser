# Setup & Installation Guide — GST Reconciliation Engine

A step-by-step guide for setting up the development environment, installing dependencies, and running both the FastAPI backend and React frontend.

---

## 1. System Requirements

Before beginning, ensure you have the following installed on your system:
- **Python**: Version `3.10` or higher (`python --version`)
- **Node.js**: Version `18.0.0` or higher (`node --version`)
- **npm**: Version `9.0.0` or higher (`npm --version`)
- **Git**: (`git --version`)

---

## 2. Project Directory Structure

```text
GST Project/
├── backend/                  # FastAPI Application & Reconciliation Engine
│   ├── main.py               # REST API endpoints
│   ├── engine.py             # 5-Tier Reconciliation Engine
│   ├── normalizers.py        # Luhn Mod-36 checksum, invoice normalization
│   ├── data_generator.py     # Generates realistic synthetic Indian test data
│   └── ...
├── frontend/                 # React 19 + Vite Web Application
│   ├── src/                  # Components, styles, state logic
│   ├── package.json          # Frontend npm scripts & dependencies
│   └── vite.config.js
├── sample_data/              # Sample test datasets (Purchase Registers, GSTR-2B JSON/Excel)
├── requirements.txt          # Python backend dependencies
├── INSTALLATION.md           # This comprehensive guide
└── README.md                 # Project architecture & statutory context
```

---

## 3. Backend Setup & Installation

### Step 3.1: Open Terminal in Project Root
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project"
```

### Step 3.2: Create & Activate Python Virtual Environment

- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(If PowerShell displays execution policy error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

- **On Windows (Command Prompt / cmd):**
  ```cmd
  python -m venv venv
  venv\Scripts\activate.bat
  ```

- **On macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 3.3: Install Backend Dependencies
Upgrade `pip` and install all required packages from `requirements.txt`:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.4: Verify Backend Installation (Run Tests)
Ensure all matching rules, edge cases, and parsing modules pass:
```powershell
pytest
```
*Expected result: 17 passed tests.*

---

## 4. Frontend Setup & Installation

### Step 4.1: Navigate to the `frontend/` Folder
Open a **new** terminal window or navigate into `frontend`:
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project\frontend"
```

### Step 4.2: Install Node Dependencies
```powershell
npm install
```

---

## 5. Running the Application

To run the complete system, keep two terminal sessions running simultaneously (one for backend, one for frontend).

### Terminal 1: Start Backend (FastAPI)
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project"
.\venv\Scripts\uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Backend API URL**: `http://localhost:8000`
- **Swagger Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

### Terminal 2: Start Frontend (Vite + React)
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project\frontend"
npm run dev
```
- **Frontend Web UI**: `http://localhost:5173`

Open `http://localhost:5173` in your browser to view the application.

---

## 6. Using the Application (Quick Walkthrough)

1. **Dashboard Overview**: View live statutory KPIs including total invoice volumes, matched percentages, ITC claimable, blocked ITC, and Section 16(4) risk exposure.
2. **Reconciliation**:
   - Upload a Purchase Register (`.xlsx` or `.csv`) from `sample_data/purchase_register_sample.xlsx` or `sample_data/purchase_register_comprehensive.xlsx`.
   - Upload a GSTR-2B file (`.json` or `.xlsx`) from `sample_data/gstr2b_sample.json` or `sample_data/gstr2b_comprehensive.json`.
   - Click **Run Reconciliation** to trigger the 5-Tier Engine.
3. **Difference Viewer**: Inspect side-by-side comparisons of Purchase Register vs. GSTR-2B invoices with color-coded mismatch fields (e.g. tax value differences, invoice number variations).
4. **Manual CA Review & Cryptographic Audit Seal**: Review borderline fuzzy matches, accept/reject overrides, and generate an immutable audit log.
5. **Vendor Action Center**: Generate automated discrepancy communication templates (email & WhatsApp draft notices) for missing invoices.
6. **Export Report**: Download an audit-ready reconciliation report in Excel/PDF format.

---

## 7. Generating Fresh Sample Datasets

If you want to generate fresh synthetic datasets with realistic Indian supplier names, valid Luhn Mod-36 GSTIN checksums, and intentional edge cases:
```powershell
cd "c:\Users\mnikhil\Desktop\GST Project"
.\venv\Scripts\python backend/data_generator.py
```
This updates files in `sample_data/`.

---

## 8. Troubleshooting & FAQs

- **Port 8000 or 5173 is already in use**:
  - Run backend on a different port: `uvicorn backend.main:app --port 8005 --reload`
  - Run frontend on a different port: `npm run dev -- --port 3000`
- **CORS Issues**:
  - The backend is configured with permissive CORS for `http://localhost:5173` and local dev environments in `backend/main.py`.
- **PowerShell Script Execution Restriction**:
  - Run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before activating `venv`.
