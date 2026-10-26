from typing import Dict, Any, List

def generate_vendor_discrepancy_notice(
    vendor_name: str,
    vendor_gstin: str,
    recipient_company: str = "",
    mismatched_records: List[Dict[str, Any]] = None,
    recipient_gstin: str = ""
) -> Dict[str, Any]:
    """
    Generates formal discrepancy communication (Email template & WhatsApp text)
    under Section 16(2)(aa) of the CGST Act.
    """
    missing_invoices = []
    tax_diff_invoices = []
    
    total_tax_at_stake = 0.0

    for m in mismatched_records:
        pr = m.get("pr_invoice")
        if not pr:
            continue
        tax = pr.get("total_tax", 0.0)
        total_tax_at_stake += tax
        
        status = m.get("status")
        if status == "MISMATCH":
            missing_invoices.append({
                "inv_no": pr.get("invoice_number"),
                "date": pr.get("invoice_date"),
                "value": pr.get("total_invoice_value"),
                "tax": tax,
                "reason": m.get("reasons", ["Invoice missing in GSTR-2B"])[0]
            })
        elif status == "PROBABLE_MATCH":
            tax_diff_invoices.append({
                "pr_inv_no": pr.get("invoice_number"),
                "portal_inv_no": m.get("portal_invoice", {}).get("invoice_number"),
                "tax_diff": m.get("tax_diff_rupees"),
                "reasons": ", ".join(m.get("reasons", []))
            })

    # Compose Email Body
    email_subject = f"URGENT: GST Reconciliation Notice - Missing Invoices in GSTR-2B [{recipient_company} / {vendor_name}]"
    
    rows_html = ""
    for item in missing_invoices:
        rows_html += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #e2e8f0;">{item['inv_no']}</td>
            <td style="padding: 8px; border: 1px solid #e2e8f0;">{item['date']}</td>
            <td style="padding: 8px; border: 1px solid #e2e8f0; text-align: right;">₹{item['value']:,.2f}</td>
            <td style="padding: 8px; border: 1px solid #e2e8f0; text-align: right; color: #dc2626; font-weight: bold;">₹{item['tax']:,.2f}</td>
            <td style="padding: 8px; border: 1px solid #e2e8f0; color: #4b5563;">{item['reason']}</td>
        </tr>
        """

    email_body_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; max-width: 650px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
        <h2 style="color: #0f172a; margin-top: 0;">GST Reconciliation Discrepancy Notice</h2>
        <p>Dear <strong>{vendor_name}</strong> (GSTIN: <code>{vendor_gstin}</code>),</p>
        <p>
            During our monthly Goods and Services Tax (GST) Input Tax Credit (ITC) reconciliation for recipient entity <strong>{recipient_company}</strong> (GSTIN: <code>{recipient_gstin}</code>), our system identified missing or discrepant invoices in our auto-drafted <strong>GSTR-2B</strong> statement.
        </p>
        <p>
            As per <strong>Section 16(2)(aa) of the CGST Act</strong>, Input Tax Credit can only be availed if the details of the invoice or debit note have been furnished by the supplier in GSTR-1 and communicated to the recipient in GSTR-2B.
        </p>

        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
            <p style="margin: 0; color: #991b1b; font-weight: 600;">
                Total Impacted Input Tax Credit: ₹{total_tax_at_stake:,.2f}
            </p>
            <p style="margin: 4px 0 0 0; color: #7f1d1d; font-size: 13px;">
                Pending confirmation, corresponding payment releases may be held in accordance with our vendor compliance terms.
            </p>
        </div>

        <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px;">
            <thead>
                <tr style="background-color: #f8fafc; text-align: left;">
                    <th style="padding: 8px; border: 1px solid #e2e8f0;">Invoice #</th>
                    <th style="padding: 8px; border: 1px solid #e2e8f0;">Invoice Date</th>
                    <th style="padding: 8px; border: 1px solid #e2e8f0; text-align: right;">Total Amount</th>
                    <th style="padding: 8px; border: 1px solid #e2e8f0; text-align: right;">ITC Claim</th>
                    <th style="padding: 8px; border: 1px solid #e2e8f0;">Discrepancy Details</th>
                </tr>
            </thead>
            <tbody>
                {rows_html if rows_html else "<tr><td colspan='5' style='padding: 8px; text-align: center;'>No critical missing invoices</td></tr>"}
            </tbody>
        </table>

        <p><strong>Required Action:</strong></p>
        <ol style="padding-left: 20px; font-size: 14px;">
            <li>Please confirm if these invoices were reported in your filed GSTR-1 / IFF.</li>
            <li>If omitted, kindly include them in your upcoming monthly GSTR-1 filing to avoid statutory ITC lapse under Section 16(4).</li>
            <li>If amended under another invoice number, please reply with the corresponding reference.</li>
        </ol>

        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">
            This is an automated notice generated by the <em>GST Reconciliation Engine</em> on behalf of {recipient_company} Tax & Accounts Team.
        </p>
    </div>
    """

    # Plain text summary for WhatsApp / SMS
    inv_list_txt = ", ".join([i['inv_no'] for i in missing_invoices[:4]])
    whatsapp_text = (
        f"*GST Compliance Notice from {recipient_company}*\n\n"
        f"Dear {vendor_name},\n"
        f"We noticed {len(missing_invoices)} invoice(s) totaling *₹{total_tax_at_stake:,.2f}* ITC missing in our GSTR-2B.\n"
        f"Invoices: {inv_list_txt}{'...' if len(missing_invoices) > 4 else ''}\n\n"
        f"Kindly confirm upload in your GSTR-1 as per CGST Sec 16(2)(aa) to prevent payment hold.\n"
        f"Contact: accounts@{recipient_company.lower().replace(' ', '')}.com"
    )

    return {
        "vendor_name": vendor_name,
        "vendor_gstin": vendor_gstin,
        "email_subject": email_subject,
        "email_html": email_body_html,
        "whatsapp_text": whatsapp_text,
        "impacted_invoices_count": len(missing_invoices),
        "total_tax_at_stake": round(total_tax_at_stake, 2)
    }
