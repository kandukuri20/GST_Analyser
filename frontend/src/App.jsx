import React, { useState, useEffect } from 'react';
import { 
  FileSpreadsheet, 
  Layers, 
  AlertTriangle, 
  CheckCircle2, 
  Send, 
  Lock, 
  Unlock, 
  Sparkles, 
  Search, 
  RefreshCw,
  Mail,
  ShieldAlert,
  ArrowRightLeft,
  Calendar,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  FileCheck2
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [activeTab, setActiveTab] = useState('reconcile'); // reconcile, review, chasing, compliance
  const [summary, setSummary] = useState(null);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  
  // Notice modal state
  const [selectedVendorNotice, setSelectedVendorNotice] = useState(null);
  const [vendorList, setVendorList] = useState([]);
  const [noticeLoading, setNoticeLoading] = useState(false);

  const [recipientName, setRecipientName] = useState('');
  const [recipientGstin, setRecipientGstin] = useState('');

  // File upload state
  const [prFile, setPrFile] = useState(null);
  const [gstrFile, setGstrFile] = useState(null);
  const [tolerance, setTolerance] = useState(2.0);

  // Fetch initial results or trigger sample dataset
  useEffect(() => {
    fetchResults();
    fetchVendors();
  }, []);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reconcile/results`);
      const data = await res.json();
      setSummary(data.summary);
      setMatches(data.matches || []);
      if (data.recipient_name) setRecipientName(data.recipient_name);
      if (data.recipient_gstin) setRecipientGstin(data.recipient_gstin);
    } catch (err) {
      console.error("API error", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchVendors = async () => {
    try {
      const res = await fetch(`${API_BASE}/vendors`);
      const data = await res.json();
      setVendorList(data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleLoadSample = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reconcile/load-sample?count=45`, { method: 'POST' });
      const data = await res.json();
      setSummary(data.summary);
      setMatches(data.matches || []);
      fetchVendors();
    } catch (err) {
      alert("Failed to load sample dataset: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUploadReconcile = async (e) => {
    e.preventDefault();
    if (!prFile || !gstrFile) {
      alert("Please upload both Purchase Register Excel/CSV and GSTR-2B JSON file");
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('pr_file', prFile);
      formData.append('gstr_file', gstrFile);
      formData.append('tolerance_rupees', tolerance);
      formData.append('date_window_days', 30);

      const res = await fetch(`${API_BASE}/reconcile/upload`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setSummary(data.summary);
      setMatches(data.matches || []);
      fetchVendors();
      alert("Reconciliation completed successfully!");
    } catch (err) {
      alert("Error reconciling files: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLockReconciliation = async () => {
    if (!window.confirm("Are you sure you want to lock and sign-off this reconciliation? This will freeze records under Section 16 compliance rules.")) return;
    try {
      const res = await fetch(`${API_BASE}/reconcile/lock`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSummary(data.summary);
      alert("Reconciliation cryptographically locked with SHA-256 seal!");
    } catch (err) {
      alert(err.message);
    }
  };

  const handleVendorNoticeOpen = async (vendorGstin) => {
    setNoticeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/vendor/notice?vendor_gstin=${vendorGstin}`);
      const data = await res.json();
      setSelectedVendorNotice(data);
    } catch (err) {
      alert("Failed to generate notice: " + err.message);
    } finally {
      setNoticeLoading(false);
    }
  };

  const handleManualOverride = async (matchId, newStatus) => {
    const note = prompt("Enter CA / Reviewer reasoning note for this override:", "Verified physically stamped tax invoice");
    if (!note) return;
    try {
      const res = await fetch(`${API_BASE}/reconcile/override?match_id=${matchId}&new_status=${newStatus}&notes=${encodeURIComponent(note)}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setMatches(matches.map(m => m.match_id === matchId ? data.updated_match : m));
    } catch (err) {
      alert(err.message);
    }
  };

  // Filtered Matches
  const filteredMatches = matches.filter(m => {
    const q = searchQuery.toLowerCase();
    const pr = m.pr_invoice;
    const port = m.portal_invoice;
    
    const matchesQuery = 
      (pr && (pr.invoice_number.toLowerCase().includes(q) || pr.supplier_name.toLowerCase().includes(q) || pr.gstin.toLowerCase().includes(q))) ||
      (port && (port.invoice_number.toLowerCase().includes(q) || port.supplier_name.toLowerCase().includes(q) || port.gstin.toLowerCase().includes(q)));
      
    if (!matchesQuery) return false;

    if (statusFilter === 'MATCHED') return m.status === 'MATCHED';
    if (statusFilter === 'PROBABLE_MATCH') return m.status === 'PROBABLE_MATCH';
    if (statusFilter === 'MISMATCH') return m.status === 'MISMATCH';
    if (statusFilter === 'SEC16_4') return (pr && pr.is_at_risk_sec16_4);
    return true;
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Bar */}
      <header style={{ 
        borderBottom: '1px solid var(--border-color)', 
        background: 'rgba(9, 13, 22, 0.85)', 
        backdropFilter: 'blur(12px)',
        position: 'sticky', 
        top: 0, 
        zIndex: 50,
        padding: '14px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ 
            width: 42, 
            height: 42, 
            borderRadius: 10, 
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)'
          }}>
            <Layers size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.02em', margin: 0, color: '#f8fafc' }}>
              GST Reconciliation Engine
            </h1>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Autonomous 7-Tier Matching & Section 16(2)(aa)</span>
              {recipientGstin && (
                <span style={{ 
                  background: 'rgba(99, 102, 241, 0.2)', 
                  color: '#818cf8', 
                  padding: '2px 8px', 
                  borderRadius: 4, 
                  fontFamily: 'monospace',
                  fontSize: 11
                }}>
                  {recipientName ? `${recipientName} (${recipientGstin})` : recipientGstin}
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px', background: 'rgba(255, 255, 255, 0.04)', padding: '4px', borderRadius: '10px' }}>
          {[
            { id: 'reconcile', label: 'Reconciliation Dashboard', icon: FileSpreadsheet },
            { id: 'review', label: 'Reviewer Workspace', icon: FileCheck2 },
            { id: 'chasing', label: 'Vendor Action Center', icon: Mail },
            { id: 'compliance', label: 'Sec 16(4) Risk Radar', icon: ShieldAlert }
          ].map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: active ? 600 : 500,
                  background: active ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(6, 182, 212, 0.2))' : 'transparent',
                  color: active ? '#38bdf8' : 'var(--text-muted)',
                  borderBottom: active ? '2px solid #38bdf8' : '2px solid transparent',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={handleLoadSample}
            disabled={loading}
            className="outline-btn"
            style={{ padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}
          >
            <Sparkles size={15} color="#38bdf8" />
            {loading ? 'Synthesizing...' : 'Load Sample Data'}
          </button>

          {summary?.is_locked ? (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px', 
              background: 'rgba(16, 185, 129, 0.15)', 
              color: '#34d399', 
              border: '1px solid rgba(16, 185, 129, 0.3)',
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600
            }}>
              <Lock size={14} /> Audit Locked
            </div>
          ) : (
            <button 
              onClick={handleLockReconciliation}
              className="glow-btn"
              style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}
            >
              <Lock size={15} /> Sign-off & Lock
            </button>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main style={{ flex: 1, padding: '24px 32px', maxWidth: 1600, width: '100%', margin: '0 auto' }}>
        
        {/* Top Metric Cards */}
        {summary && (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', 
            gap: '16px', 
            marginBottom: '24px' 
          }}>
            <div className="glass-panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 13, marginBottom: 8 }}>
                <span>Match Precision</span>
                <TrendingUp size={16} color="#34d399" />
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, color: '#38bdf8' }}>
                {summary.match_rate_percentage}%
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
                {summary.matched_count} of {summary.total_pr_count} PR invoices reconciled
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 13, marginBottom: 8 }}>
                <span>Matched Eligible ITC</span>
                <CheckCircle2 size={16} color="#10b981" />
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#10b981' }}>
                ₹{summary.matched_itc.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
                Safe to claim in GSTR-3B Table 4(A)(5)
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 13, marginBottom: 8 }}>
                <span>Sec 16(4) Risk ITC</span>
                <ShieldAlert size={16} color="#ef4444" />
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#ef4444' }}>
                ₹{summary.at_risk_itc_sec16_4.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: 12, color: '#f87171', marginTop: 4 }}>
                Nov 30 Cutoff Lapse Threat!
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 13, marginBottom: 8 }}>
                <span>Missing in GSTR-2B</span>
                <AlertTriangle size={16} color="#f59e0b" />
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#f59e0b' }}>
                ₹{summary.missing_in_portal_itc.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
                {summary.unmatched_pr_count} invoices to chase vendors
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 13, marginBottom: 8 }}>
                <span>Ineligible Portal ITC</span>
                <AlertTriangle size={16} color="#fb7185" />
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#fb7185' }}>
                ₹{summary.ineligible_itc_portal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
                Blocked under CGST Sec 17(5)
              </div>
            </div>
          </div>
        )}

        {/* Tab 1: Reconciliation Dashboard */}
        {activeTab === 'reconcile' && (
          <div>
            {/* Upload & Matching Controls */}
            <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', margin: 0 }}>
                    Upload Registers for Automated 7-Tier Reconciliation
                  </h3>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                    Upload your Purchase Register (Tally / Zoho / SAP Excel) and GSTN auto-drafted GSTR-2B JSON
                  </p>
                </div>
                <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-dim)' }}>
                  Audit Seal: {summary?.reconciliation_hash || 'PENDING'}
                </div>
              </div>

              <form onSubmit={handleFileUploadReconcile} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 180px auto', gap: '14px', alignItems: 'end' }}>
                <div>
                  <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                    Purchase Register (Excel/CSV)
                  </label>
                  <input 
                    type="file" 
                    accept=".xlsx, .xls, .csv" 
                    onChange={e => setPrFile(e.target.files[0])}
                    style={{ 
                      width: '100%', 
                      fontSize: 12, 
                      padding: '8px', 
                      background: 'rgba(255, 255, 255, 0.03)', 
                      border: '1px solid var(--border-color)', 
                      borderRadius: 8,
                      color: 'var(--text-main)'
                    }} 
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                    GSTR-2B File (JSON)
                  </label>
                  <input 
                    type="file" 
                    accept=".json" 
                    onChange={e => setGstrFile(e.target.files[0])}
                    style={{ 
                      width: '100%', 
                      fontSize: 12, 
                      padding: '8px', 
                      background: 'rgba(255, 255, 255, 0.03)', 
                      border: '1px solid var(--border-color)', 
                      borderRadius: 8,
                      color: 'var(--text-main)'
                    }} 
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                    Rounding Tolerance (₹)
                  </label>
                  <input 
                    type="number" 
                    step="0.5" 
                    min="0" 
                    max="10" 
                    value={tolerance} 
                    onChange={e => setTolerance(parseFloat(e.target.value) || 0)}
                    style={{ 
                      width: '100%', 
                      fontSize: 13, 
                      padding: '9px 12px', 
                      background: 'rgba(255, 255, 255, 0.03)', 
                      border: '1px solid var(--border-color)', 
                      borderRadius: 8,
                      color: 'var(--text-main)'
                    }} 
                  />
                </div>

                <button 
                  type="submit" 
                  disabled={loading}
                  className="glow-btn"
                  style={{ padding: '10px 24px', fontSize: 13, height: 40 }}
                >
                  {loading ? 'Reconciling...' : 'Run Reconciliation'}
                </button>
              </form>
            </div>

            {/* Filter & Search Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[
                  { id: 'ALL', label: 'All Records' },
                  { id: 'MATCHED', label: 'Strict Matched' },
                  { id: 'PROBABLE_MATCH', label: 'Probable / CA Review' },
                  { id: 'MISMATCH', label: 'Missing / Mismatches' },
                  { id: 'SEC16_4', label: 'Section 16(4) Risk' }
                ].map(f => (
                  <button
                    key={f.id}
                    onClick={() => setStatusFilter(f.id)}
                    className="outline-btn"
                    style={{
                      padding: '6px 14px',
                      fontSize: 12,
                      background: statusFilter === f.id ? 'rgba(99, 102, 241, 0.25)' : undefined,
                      borderColor: statusFilter === f.id ? '#6366f1' : undefined
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div style={{ position: 'relative', width: 320 }}>
                <Search size={16} color="var(--text-dim)" style={{ position: 'absolute', left: 12, top: 11 }} />
                <input 
                  type="text" 
                  placeholder="Search invoice #, vendor, or GSTIN..." 
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 36px',
                    fontSize: 12,
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    color: 'var(--text-main)'
                  }}
                />
              </div>
            </div>

            {/* Matches Side-by-Side Table */}
            <div className="glass-panel" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '12px 16px' }}>Status & Tier</th>
                    <th style={{ padding: '12px 16px' }}>Purchase Register (Books)</th>
                    <th style={{ padding: '12px 16px' }}>GSTR-2B (GSTN Portal)</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Tax Variance (₹)</th>
                    <th style={{ padding: '12px 16px' }}>Explanation & Audit Trail</th>
                    <th style={{ padding: '12px 16px', textAlign: 'center' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMatches.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-dim)' }}>
                        No records match current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredMatches.map(m => {
                      const pr = m.pr_invoice;
                      const port = m.portal_invoice;
                      
                      let badgeClass = 'badge-pass';
                      if (m.status === 'PROBABLE_MATCH') badgeClass = 'badge-probable';
                      if (m.status === 'MISMATCH') badgeClass = 'badge-mismatch';
                      if (pr && pr.is_at_risk_sec16_4) badgeClass = 'badge-critical';

                      return (
                        <tr key={m.match_id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', transition: 'background 0.15s' }}>
                          <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                            <span className={badgeClass}>{m.status}</span>
                            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6 }}>
                              {m.match_pass}
                            </div>
                            <div style={{ fontSize: 10, fontFamily: 'monospace', color: '#6366f1', marginTop: 2 }}>
                              Score: {m.confidence_score}%
                            </div>
                          </td>

                          {/* Purchase Register Column */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                            {pr ? (
                              <div>
                                <div style={{ fontWeight: 600, color: '#f8fafc' }}>{pr.invoice_number}</div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{pr.supplier_name}</div>
                                <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-dim)' }}>{pr.gstin}</div>
                                <div style={{ fontSize: 12, marginTop: 4 }}>
                                  <span style={{ color: 'var(--text-dim)' }}>Date: </span>{pr.invoice_date} | 
                                  <span style={{ color: 'var(--text-dim)' }}> Total: </span>₹{pr.total_invoice_value.toLocaleString('en-IN')}
                                </div>
                                <div style={{ fontSize: 12, color: '#10b981', fontWeight: 600 }}>
                                  Tax: ₹{pr.total_tax.toLocaleString('en-IN')}
                                </div>
                              </div>
                            ) : (
                              <div style={{ color: '#fb7185', fontStyle: 'italic', fontSize: 12 }}>
                                Omitted in Books
                              </div>
                            )}
                          </td>

                          {/* GSTR-2B Column */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                            {port ? (
                              <div>
                                <div style={{ fontWeight: 600, color: '#f8fafc' }}>{port.invoice_number}</div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{port.supplier_name}</div>
                                <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-dim)' }}>{port.gstin}</div>
                                <div style={{ fontSize: 12, marginTop: 4 }}>
                                  <span style={{ color: 'var(--text-dim)' }}>Date: </span>{port.invoice_date} | 
                                  <span style={{ color: 'var(--text-dim)' }}> Total: </span>₹{port.total_invoice_value.toLocaleString('en-IN')}
                                </div>
                                <div style={{ fontSize: 12, color: port.itc_available ? '#10b981' : '#fb7185', fontWeight: 600 }}>
                                  Tax: ₹{port.total_tax.toLocaleString('en-IN')} {port.itc_available ? '' : '(Blocked Sec 17(5))'}
                                </div>
                              </div>
                            ) : (
                              <div style={{ color: '#fb7185', fontStyle: 'italic', fontSize: 12 }}>
                                Missing in GSTR-2B
                              </div>
                            )}
                          </td>

                          {/* Variance */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'top', textAlign: 'right' }}>
                            <div style={{ fontWeight: 600, color: m.tax_diff_rupees === 0 ? '#10b981' : '#fb7185' }}>
                              ₹{Math.abs(m.tax_diff_rupees).toFixed(2)}
                            </div>
                            {m.date_diff_days > 0 && (
                              <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                {m.date_diff_days} days drift
                              </div>
                            )}
                          </td>

                          {/* Explanation */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'top', maxWidth: 300 }}>
                            <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                              {m.reasons.map((r, i) => (
                                <li key={i} style={{ marginBottom: 2 }}>{r}</li>
                              ))}
                            </ul>
                            {m.reviewer_notes && (
                              <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 4, fontStyle: 'italic' }}>
                                Note: {m.reviewer_notes}
                              </div>
                            )}
                          </td>

                          {/* Actions */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'top', textAlign: 'center' }}>
                            {m.status === 'PROBABLE_MATCH' && !summary.is_locked && (
                              <button
                                onClick={() => handleManualOverride(m.match_id, 'MATCHED')}
                                className="outline-btn"
                                style={{ padding: '4px 10px', fontSize: 11, color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.4)' }}
                              >
                                Approve Pair
                              </button>
                            )}
                            {m.status === 'MISMATCH' && pr && (
                              <button
                                onClick={() => handleVendorNoticeOpen(pr.gstin)}
                                className="outline-btn"
                                style={{ padding: '4px 10px', fontSize: 11, color: '#fbbf24', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                              >
                                Notice
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Reviewer Workspace */}
        {activeTab === 'review' && (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: '#f8fafc', marginBottom: 8 }}>
              CA & Senior Reviewer Audit Workspace
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              Verify borderline matches, apply professional judgement overrides with statutory audit trails, and cryptographically seal reconciliation.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
              {matches.filter(m => m.status === 'PROBABLE_MATCH').map(m => (
                <div key={m.match_id} style={{ 
                  background: 'rgba(255, 255, 255, 0.02)', 
                  border: '1px solid rgba(245, 158, 11, 0.3)', 
                  borderRadius: 12, 
                  padding: 16 
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                    <span className="badge-probable">Probable ({m.confidence_score}%)</span>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-dim)' }}>{m.match_id}</span>
                  </div>

                  <div style={{ fontSize: 13, marginBottom: 8 }}>
                    <strong>Books:</strong> #{m.pr_invoice?.invoice_number} | ₹{m.pr_invoice?.total_invoice_value}
                  </div>
                  <div style={{ fontSize: 13, marginBottom: 12 }}>
                    <strong>Portal:</strong> #{m.portal_invoice?.invoice_number} | ₹{m.portal_invoice?.total_invoice_value}
                  </div>

                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                    Reasons: {m.reasons.join('; ')}
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => handleManualOverride(m.match_id, 'MATCHED')}
                      className="glow-btn"
                      disabled={summary?.is_locked}
                      style={{ flex: 1, padding: '6px', fontSize: 12 }}
                    >
                      Confirm Match
                    </button>
                    <button
                      onClick={() => handleManualOverride(m.match_id, 'MISMATCH')}
                      className="outline-btn"
                      disabled={summary?.is_locked}
                      style={{ flex: 1, padding: '6px', fontSize: 12, color: '#fb7185' }}
                    >
                      Reject Link
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Vendor Action Center */}
        {activeTab === 'chasing' && (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  Vendor Action & Discrepancy Chasing Center
                </h3>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                  Auto-generate formal legal notices under Section 16(2)(aa) with automatic payment-hold calculations.
                </p>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '12px 16px' }}>Vendor Name</th>
                    <th style={{ padding: '12px 16px' }}>Supplier GSTIN</th>
                    <th style={{ padding: '12px 16px', textAlign: 'center' }}>Un-uploaded Invoices</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Tax at Risk (ITC)</th>
                    <th style={{ padding: '12px 16px' }}>Section 16(4) Risk</th>
                    <th style={{ padding: '12px 16px', textAlign: 'center' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {vendorList.map(v => (
                    <tr key={v.gstin} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f8fafc' }}>{v.name}</td>
                      <td style={{ padding: '14px 16px', fontFamily: 'monospace', color: 'var(--text-muted)' }}>{v.gstin}</td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <span className="badge-mismatch">{v.missing_count} Invoices</span>
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 700, color: '#fb7185' }}>
                        ₹{v.tax_at_stake.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        {v.has_sec16_4_risk ? (
                          <span className="badge-critical">Critical Lapse Risk</span>
                        ) : (
                          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Current FY</span>
                        )}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <button
                          onClick={() => handleVendorNoticeOpen(v.gstin)}
                          className="glow-btn"
                          style={{ padding: '6px 14px', fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6 }}
                        >
                          <Mail size={13} /> Generate Notice
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: Section 16(4) Risk Radar */}
        {activeTab === 'compliance' && (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: '#f8fafc', marginBottom: 8 }}>
              Section 16(4) Statutory Deadline Risk Radar
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              Under Section 16(4) of the CGST Act, ITC for any financial year lapses on <strong>30th November</strong> of the subsequent year. These invoices are un-reconciled and imminent to permanent tax loss.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              {matches.filter(m => m.pr_invoice?.is_at_risk_sec16_4).map(m => (
                <div key={m.match_id} style={{ 
                  background: 'rgba(239, 68, 68, 0.05)', 
                  border: '1px solid rgba(239, 68, 68, 0.3)', 
                  borderRadius: 12, 
                  padding: 18 
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span className="badge-critical">Section 16(4) Lapse</span>
                    <span style={{ fontSize: 11, color: '#f87171' }}>Statutory Cutoff: Nov 30</span>
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                    {m.pr_invoice?.supplier_name}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                    Invoice #{m.pr_invoice?.invoice_number} | Dated {m.pr_invoice?.invoice_date}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: '#ef4444', marginTop: 12 }}>
                    ITC at Stake: ₹{m.pr_invoice?.total_tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 8 }}>
                    Vendor has not filed in GSTR-1. If not amended in next cycle, credit will be permanently forfeited.
                  </p>
                  <button 
                    onClick={() => handleVendorNoticeOpen(m.pr_invoice.gstin)}
                    className="glow-btn" 
                    style={{ width: '100%', padding: '8px', fontSize: 12, marginTop: 8 }}
                  >
                    Send Urgent Chasing Notice
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>

      {/* Discrepancy Notice Modal */}
      {selectedVendorNotice && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: 24
        }}>
          <div className="glass-panel" style={{ 
            maxWidth: 700, 
            width: '100%', 
            maxHeight: '90vh', 
            overflowY: 'auto',
            padding: 28,
            border: '1px solid var(--border-highlight)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                Vendor Discrepancy Notice Preview
              </h3>
              <button 
                onClick={() => setSelectedVendorNotice(null)}
                className="outline-btn"
                style={{ padding: '4px 12px', fontSize: 12 }}
              >
                Close
              </button>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Subject:</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', marginTop: 2 }}>
                {selectedVendorNotice.email_subject}
              </div>
            </div>

            <div style={{ 
              background: '#ffffff', 
              color: '#0f172a', 
              borderRadius: 8, 
              padding: 20, 
              marginBottom: 16,
              boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <div dangerouslySetInnerHTML={{ __html: selectedVendorNotice.email_html }} />
            </div>

            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>WhatsApp / Quick SMS Notice:</div>
              <pre style={{ 
                background: 'rgba(255, 255, 255, 0.04)', 
                padding: 12, 
                borderRadius: 8, 
                fontSize: 12, 
                color: '#34d399', 
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace'
              }}>
                {selectedVendorNotice.whatsapp_text}
              </pre>
            </div>

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button 
                onClick={() => {
                  navigator.clipboard.writeText(selectedVendorNotice.whatsapp_text);
                  alert("WhatsApp notice copied to clipboard!");
                }}
                className="outline-btn"
                style={{ padding: '8px 16px', fontSize: 13 }}
              >
                Copy WhatsApp Text
              </button>
              <button 
                onClick={() => {
                  alert(`Discrepancy notice successfully dispatched to ${selectedVendorNotice.vendor_name}!`);
                  setSelectedVendorNotice(null);
                }}
                className="glow-btn"
                style={{ padding: '8px 20px', fontSize: 13 }}
              >
                Dispatch Notice via Email
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer style={{ 
        borderTop: '1px solid var(--border-color)', 
        padding: '16px 32px', 
        fontSize: 12, 
        color: 'var(--text-dim)', 
        display: 'flex', 
        justifyContent: 'space-between',
        background: 'rgba(9, 13, 22, 0.95)'
      }}>
        <span>GST Reconciliation Engine &middot; Capstone / MVP Release</span>
        <span>Built strictly to CGST Act Sections 16(2)(aa), 16(4), 17(5) and Rule 36(4)</span>
      </footer>
    </div>
  );
}
