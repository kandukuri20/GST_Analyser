import math
import uuid
import hashlib
from datetime import datetime
from typing import List, Tuple, Dict, Any
from rapidfuzz import fuzz

from models import InvoiceRecord, MatchGroup, ReconciliationSummary
from normalizers import (
    validate_gstin,
    normalize_invoice_number,
    rupees_to_paise,
    paise_to_rupees
)

class GSTReconciliationEngine:
    def __init__(self, tolerance_paise: int = 200, date_tolerance_days: int = 30):
        """
        tolerance_paise: Max allowable rounding discrepancy (200 paise = Rs 2.00)
        date_tolerance_days: allowable date window for matching invoice variations
        """
        self.tolerance_paise = tolerance_paise
        self.date_tolerance_days = date_tolerance_days

    def _days_between(self, d1: str, d2: str) -> int:
        try:
            dt1 = datetime.strptime(d1[:10], "%Y-%m-%d")
            dt2 = datetime.strptime(d2[:10], "%Y-%m-%d")
            return abs((dt1 - dt2).days)
        except Exception:
            return 9999

    def reconcile(
        self,
        pr_invoices: List[InvoiceRecord],
        portal_invoices: List[InvoiceRecord],
        supplier_aliases: Dict[str, str] = None
    ) -> Tuple[List[MatchGroup], ReconciliationSummary]:
        if supplier_aliases is None:
            supplier_aliases = {}

        # Prepare normalized working copies
        pr_pool: Dict[str, InvoiceRecord] = {}
        for idx, inv in enumerate(pr_invoices):
            if not inv.id:
                inv.id = f"pr_{idx}_{uuid.uuid4().hex[:6]}"
            inv.norm_invoice_number = normalize_invoice_number(inv.invoice_number)
            pr_pool[inv.id] = inv

        portal_pool: Dict[str, InvoiceRecord] = {}
        for idx, inv in enumerate(portal_invoices):
            if not inv.id:
                inv.id = f"gstr_{idx}_{uuid.uuid4().hex[:6]}"
            inv.norm_invoice_number = normalize_invoice_number(inv.invoice_number)
            portal_pool[inv.id] = inv

        matches: List[MatchGroup] = []

        # -------------------------------------------------------------
        # PASS 1: EXACT MATCH (Exact GSTIN + Exact Inv No + Exact Value/Tax within tolerance)
        # -------------------------------------------------------------
        pr_matched_ids = set()
        portal_matched_ids = set()

        for pr_id, pr in list(pr_pool.items()):
            for port_id, port in list(portal_pool.items()):
                if port_id in portal_matched_ids:
                    continue

                if pr.gstin.upper() == port.gstin.upper() and pr.invoice_number.strip().upper() == port.invoice_number.strip().upper():
                    val_diff = abs(pr.total_invoice_value_paise - port.total_invoice_value_paise)
                    tax_diff = abs(pr.total_tax_paise - port.total_tax_paise)
                    
                    if val_diff <= self.tolerance_paise and tax_diff <= self.tolerance_paise:
                        days = self._days_between(pr.invoice_date, port.invoice_date)
                        mg = MatchGroup(
                            match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                            match_pass="Pass 1: Exact Match",
                            confidence_score=100.0,
                            status="MATCHED",
                            pr_invoice=pr,
                            portal_invoice=port,
                            value_diff_paise=pr.total_invoice_value_paise - port.total_invoice_value_paise,
                            tax_diff_paise=pr.total_tax_paise - port.total_tax_paise,
                            value_diff_rupees=paise_to_rupees(pr.total_invoice_value_paise - port.total_invoice_value_paise),
                            tax_diff_rupees=paise_to_rupees(pr.total_tax_paise - port.total_tax_paise),
                            date_diff_days=days,
                            reasons=["Exact GSTIN", "Exact Invoice Number", "Exact Amount within sub-rupee tolerance"]
                        )
                        matches.append(mg)
                        pr_matched_ids.add(pr_id)
                        portal_matched_ids.add(port_id)
                        break

        # Remove matched from active pool
        for pid in pr_matched_ids:
            pr_pool.pop(pid, None)
        for pid in portal_matched_ids:
            portal_pool.pop(pid, None)

        # -------------------------------------------------------------
        # PASS 2: NORMALIZED INVOICE NUMBER MATCH
        # Strip prefixes (INV/, 2024/), leading zeros, punctuation
        # -------------------------------------------------------------
        pass2_pr = set()
        pass2_port = set()

        for pr_id, pr in list(pr_pool.items()):
            for port_id, port in list(portal_pool.items()):
                if port_id in pass2_port:
                    continue

                if pr.gstin.upper() == port.gstin.upper() and pr.norm_invoice_number == port.norm_invoice_number and pr.norm_invoice_number:
                    val_diff = abs(pr.total_invoice_value_paise - port.total_invoice_value_paise)
                    tax_diff = abs(pr.total_tax_paise - port.total_tax_paise)
                    
                    if val_diff <= self.tolerance_paise and tax_diff <= self.tolerance_paise:
                        days = self._days_between(pr.invoice_date, port.invoice_date)
                        mg = MatchGroup(
                            match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                            match_pass="Pass 2: Normalized Number",
                            confidence_score=95.0,
                            status="MATCHED",
                            pr_invoice=pr,
                            portal_invoice=port,
                            value_diff_paise=pr.total_invoice_value_paise - port.total_invoice_value_paise,
                            tax_diff_paise=pr.total_tax_paise - port.total_tax_paise,
                            value_diff_rupees=paise_to_rupees(pr.total_invoice_value_paise - port.total_invoice_value_paise),
                            tax_diff_rupees=paise_to_rupees(pr.total_tax_paise - port.total_tax_paise),
                            date_diff_days=days,
                            reasons=[
                                f"Normalized Number Match ('{pr.invoice_number}' vs '{port.invoice_number}')",
                                "Exact GSTIN & Verified Amount"
                            ]
                        )
                        matches.append(mg)
                        pass2_pr.add(pr_id)
                        pass2_port.add(port_id)
                        break

        for pid in pass2_pr:
            pr_pool.pop(pid, None)
        for pid in pass2_port:
            portal_pool.pop(pid, None)

        # -------------------------------------------------------------
        # PASS 3: AMOUNT + DATE PROXIMITY & STRING DISTANCE
        # (Same GSTIN, RapidFuzz string match > 75%, or Date proximity within 30 days)
        # -------------------------------------------------------------
        pass3_pr = set()
        pass3_port = set()

        for pr_id, pr in list(pr_pool.items()):
            best_candidate = None
            best_score = -1.0

            for port_id, port in list(portal_pool.items()):
                if port_id in pass3_port:
                    continue

                if pr.gstin.upper() == port.gstin.upper():
                    # Check amount proximity (allowing small variance up to Rs 10 or 1%)
                    val_diff = abs(pr.total_invoice_value_paise - port.total_invoice_value_paise)
                    tax_diff = abs(pr.total_tax_paise - port.total_tax_paise)
                    days = self._days_between(pr.invoice_date, port.invoice_date)

                    ratio = fuzz.ratio(pr.invoice_number.upper(), port.invoice_number.upper())
                    partial_ratio = fuzz.partial_ratio(pr.invoice_number.upper(), port.invoice_number.upper())
                    token_ratio = fuzz.token_set_ratio(pr.invoice_number.upper(), port.invoice_number.upper())
                    best_str_ratio = max(ratio, partial_ratio, token_ratio)
                    
                    if days <= self.date_tolerance_days:
                        # Score weighting: 50% amount, 30% fuzzy string, 20% date
                        amt_score = 100 if val_diff <= self.tolerance_paise else max(0, 100 - (val_diff / 100.0) * 5)
                        date_score = max(0, 100 - (days * 3))
                        composite_score = (amt_score * 0.5) + (best_str_ratio * 0.3) + (date_score * 0.2)
                        
                        if composite_score > 70.0 and composite_score > best_score:
                            best_score = composite_score
                            best_candidate = (port_id, port, val_diff, tax_diff, days, best_str_ratio)

            if best_candidate and best_score >= 70.0:
                port_id, port, val_diff, tax_diff, days, best_str_ratio = best_candidate
                status = "MATCHED" if best_score >= 88.0 and val_diff <= self.tolerance_paise else "PROBABLE_MATCH"
                
                reasons = [
                    f"Fuzzy Invoice Similarity: {best_str_ratio:.1f}%",
                    f"Date Proximity: {days} days apart"
                ]
                if val_diff > self.tolerance_paise:
                    reasons.append(f"Value difference of ₹{paise_to_rupees(val_diff):,.2f}")
                
                mg = MatchGroup(
                    match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                    match_pass="Pass 3: Amount + Date Proximity",
                    confidence_score=round(best_score, 1),
                    status=status,
                    pr_invoice=pr,
                    portal_invoice=port,
                    value_diff_paise=pr.total_invoice_value_paise - port.total_invoice_value_paise,
                    tax_diff_paise=pr.total_tax_paise - port.total_tax_paise,
                    value_diff_rupees=paise_to_rupees(pr.total_invoice_value_paise - port.total_invoice_value_paise),
                    tax_diff_rupees=paise_to_rupees(pr.total_tax_paise - port.total_tax_paise),
                    date_diff_days=days,
                    reasons=reasons,
                    action_required="CA Review Recommended" if status == "PROBABLE_MATCH" else None
                )
                matches.append(mg)
                pass3_pr.add(pr_id)
                pass3_port.add(port_id)

        for pid in pass3_pr:
            pr_pool.pop(pid, None)
        for pid in pass3_port:
            portal_pool.pop(pid, None)

        # -------------------------------------------------------------
        # PASS 4: PAN-LEVEL MATCH (Different GSTIN state branch of same PAN entity)
        # PAN is chars 2:12 of 15-char GSTIN
        # -------------------------------------------------------------
        pass4_pr = set()
        pass4_port = set()

        for pr_id, pr in list(pr_pool.items()):
            pr_pan = pr.gstin[2:12] if len(pr.gstin) >= 12 else ""
            if not pr_pan:
                continue

            for port_id, port in list(portal_pool.items()):
                if port_id in pass4_port:
                    continue

                port_pan = port.gstin[2:12] if len(port.gstin) >= 12 else ""
                # Pass 4 is strictly for cross-branch / different state GSTIN of same PAN entity
                if pr_pan == port_pan and pr.gstin.upper() != port.gstin.upper():
                    if (pr.norm_invoice_number == port.norm_invoice_number and pr.norm_invoice_number) or \
                       (fuzz.ratio(pr.invoice_number.upper(), port.invoice_number.upper()) > 80):
                        val_diff = abs(pr.total_invoice_value_paise - port.total_invoice_value_paise)
                        days = self._days_between(pr.invoice_date, port.invoice_date)
                        
                        mg = MatchGroup(
                            match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                            match_pass="Pass 4: Multi-Branch PAN Match",
                            confidence_score=78.0,
                            status="PROBABLE_MATCH",
                            pr_invoice=pr,
                            portal_invoice=port,
                            value_diff_paise=pr.total_invoice_value_paise - port.total_invoice_value_paise,
                            tax_diff_paise=pr.total_tax_paise - port.total_tax_paise,
                            value_diff_rupees=paise_to_rupees(pr.total_invoice_value_paise - port.total_invoice_value_paise),
                            tax_diff_rupees=paise_to_rupees(pr.total_tax_paise - port.total_tax_paise),
                            date_diff_days=days,
                            reasons=[
                                f"Same PAN ({pr_pan}) across different state branches: {pr.gstin[:2]} vs {port.gstin[:2]}",
                                f"Invoice #{pr.invoice_number}"
                            ],
                            action_required="Confirm Interstate/Branch billing alignment"
                        )
                        matches.append(mg)
                        pass4_pr.add(pr_id)
                        pass4_port.add(port_id)
                        break

        for pid in pass4_pr:
            pr_pool.pop(pid, None)
        for pid in pass4_port:
            portal_pool.pop(pid, None)

        # -------------------------------------------------------------
        # PASS 5: CREDIT / DEBIT NOTE NETTING (CDNR vs INV)
        # Identify Credit Notes in Portal or Books that offset invoices
        # -------------------------------------------------------------
        # Gather remaining unlinked CDN records
        pass5_pr = set()
        pass5_port = set()

        for pr_id, pr in list(pr_pool.items()):
            if pr.invoice_type in ["CRN", "DBN"]:
                for port_id, port in list(portal_pool.items()):
                    if port_id in pass5_port:
                        continue
                    if pr.gstin.upper() == port.gstin.upper() and pr.invoice_type == port.invoice_type:
                        val_diff = abs(pr.total_invoice_value_paise - port.total_invoice_value_paise)
                        if val_diff <= self.tolerance_paise:
                            mg = MatchGroup(
                                match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                                match_pass="Pass 5: Credit/Debit Note Match",
                                confidence_score=92.0,
                                status="MATCHED",
                                pr_invoice=pr,
                                portal_invoice=port,
                                value_diff_paise=pr.total_invoice_value_paise - port.total_invoice_value_paise,
                                tax_diff_paise=pr.total_tax_paise - port.total_tax_paise,
                                value_diff_rupees=paise_to_rupees(pr.total_invoice_value_paise - port.total_invoice_value_paise),
                                tax_diff_rupees=paise_to_rupees(pr.total_tax_paise - port.total_tax_paise),
                                date_diff_days=self._days_between(pr.invoice_date, port.invoice_date),
                                reasons=[f"Matched {pr.invoice_type} Note under Section 34 of CGST Act"]
                            )
                            matches.append(mg)
                            pass5_pr.add(pr_id)
                            pass5_port.add(port_id)
                            break

        for pid in pass5_pr:
            pr_pool.pop(pid, None)
        for pid in pass5_port:
            portal_pool.pop(pid, None)

        # -------------------------------------------------------------
        # REMAINING UNMATCHED RECORDS
        # Missing in Portal (Risk of Ineligible ITC under Sec 16(2)(aa))
        # Missing in Books (Supplier filed, but accountant hasn't booked)
        # -------------------------------------------------------------
        for pr_id, pr in pr_pool.items():
            reasons = ["Not found in GSTR-2B for current tax period"]
            action = "Chasing Email to Vendor via Vendor Action Center"
            if pr.is_at_risk_sec16_4:
                reasons.append("CRITICAL: Approaching Section 16(4) statutory cutoff (Nov 30)!")
                action = "URGENT: Expedite vendor filing or reverse provisional ITC"

            mg = MatchGroup(
                match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                match_pass="Unmatched: Missing in GSTR-2B",
                confidence_score=0.0,
                status="MISMATCH",
                pr_invoice=pr,
                portal_invoice=None,
                value_diff_paise=pr.total_invoice_value_paise,
                tax_diff_paise=pr.total_tax_paise,
                value_diff_rupees=paise_to_rupees(pr.total_invoice_value_paise),
                tax_diff_rupees=paise_to_rupees(pr.total_tax_paise),
                date_diff_days=0,
                reasons=reasons,
                action_required=action
            )
            matches.append(mg)

        for port_id, port in portal_pool.items():
            reasons = ["Appears in GSTR-2B but omitted in Purchase Register"]
            action = "Book in Purchase Register to claim eligible ITC"
            if not port.itc_available:
                reasons.append("Marked 'Ineligible ITC' by GSTN portal (Sec 17(5))")
                action = "Do not claim ITC in GSTR-3B Table 4(B)"

            mg = MatchGroup(
                match_id=f"MG-{uuid.uuid4().hex[:8].upper()}",
                match_pass="Unmatched: Missing in Books",
                confidence_score=0.0,
                status="MISMATCH",
                pr_invoice=None,
                portal_invoice=port,
                value_diff_paise=-port.total_invoice_value_paise,
                tax_diff_paise=-port.total_tax_paise,
                value_diff_rupees=-paise_to_rupees(port.total_invoice_value_paise),
                tax_diff_rupees=-paise_to_rupees(port.total_tax_paise),
                date_diff_days=0,
                reasons=reasons,
                action_required=action
            )
            matches.append(mg)

        # -------------------------------------------------------------
        # COMPUTE RECONCILIATION SUMMARY & COMPLIANCE TOTALS
        # -------------------------------------------------------------
        matched_groups = [m for m in matches if m.status == "MATCHED"]
        probable_groups = [m for m in matches if m.status == "PROBABLE_MATCH"]
        unmatched_pr = [m for m in matches if m.pr_invoice and not m.portal_invoice]
        unmatched_portal = [m for m in matches if m.portal_invoice and not m.pr_invoice]

        pr_tax_total = sum(i.total_tax for i in pr_invoices)
        portal_tax_total = sum(i.total_tax for i in portal_invoices)
        
        matched_itc = sum(m.portal_invoice.total_tax for m in matched_groups if m.portal_invoice and m.portal_invoice.itc_available)
        at_risk_itc = sum(m.pr_invoice.total_tax for m in unmatched_pr if m.pr_invoice and m.pr_invoice.is_at_risk_sec16_4)
        ineligible_itc = sum(i.total_tax for i in portal_invoices if not i.itc_available)
        missing_in_portal_tax = sum(m.pr_invoice.total_tax for m in unmatched_pr if m.pr_invoice)
        missing_in_pr_tax = sum(m.portal_invoice.total_tax for m in unmatched_portal if m.portal_invoice)

        total_records = len(pr_invoices)
        match_rate = (len(matched_groups) / total_records * 100.0) if total_records > 0 else 0.0

        # Cryptographic Hash for audit lock
        hash_seed = f"{len(matches)}_{len(matched_groups)}_{matched_itc}_{datetime.now().isoformat()}"
        audit_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:16].upper()

        summary = ReconciliationSummary(
            total_pr_count=len(pr_invoices),
            total_portal_count=len(portal_invoices),
            matched_count=len(matched_groups),
            probable_match_count=len(probable_groups),
            unmatched_pr_count=len(unmatched_pr),
            unmatched_portal_count=len(unmatched_portal),
            pr_total_tax=round(pr_tax_total, 2),
            portal_total_tax=round(portal_tax_total, 2),
            matched_itc=round(matched_itc, 2),
            at_risk_itc_sec16_4=round(at_risk_itc, 2),
            ineligible_itc_portal=round(ineligible_itc, 2),
            missing_in_portal_itc=round(missing_in_portal_tax, 2),
            missing_in_pr_itc=round(missing_in_pr_tax, 2),
            match_rate_percentage=round(match_rate, 2),
            reconciliation_hash=f"REC-SHA256-{audit_hash}",
            is_locked=False,
            locked_at=None
        )

        return matches, summary
