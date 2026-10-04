import React, { useState } from 'react';
import { Search, Filter, CheckCircle, Clock, AlertTriangle, FileDown, ArrowUpRight, ShieldCheck, Award, Printer } from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';
import ComplianceCertificateModal from './ComplianceCertificateModal';

interface Props {
  emails: ProcessedEmailRecord[];
  onSelectEmail: (email: ProcessedEmailRecord) => void;
}

export default function AuditTrail({ emails, onSelectEmail }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedCertEmail, setSelectedCertEmail] = useState<ProcessedEmailRecord | null>(null);

  const filtered = emails.filter((item) => {
    const matchStatus = statusFilter === 'ALL' || item.status === statusFilter;
    const matchSearch = item.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sender.toLowerCase().includes(searchTerm.toLowerCase());
    return matchStatus && matchSearch;
  });

  const exportAuditReport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(emails, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `orbit_audit_compliance_report_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const printFullAuditLedger = () => {
    if (emails.length > 0) {
      setSelectedCertEmail(emails[0]);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'AUTO_EXECUTED':
        return (
          <span className="px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[11px] font-mono font-medium flex items-center gap-1">
            <CheckCircle size={12} /> Auto Executed
          </span>
        );
      case 'APPROVED':
        return (
          <span className="px-2.5 py-1 rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/30 text-[11px] font-mono font-medium flex items-center gap-1">
            <CheckCircle size={12} /> Supervisor Approved
          </span>
        );
      case 'PENDING_APPROVAL':
        return (
          <span className="px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 text-[11px] font-mono font-medium flex items-center gap-1 animate-pulse">
            <Clock size={12} /> Pending Approval
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 text-[11px] font-mono font-medium flex items-center gap-1">
            <AlertTriangle size={12} /> Rejected / Ticketed
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-[#131d35] border border-[#1e293b] rounded-2xl flex flex-col shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-[#1e293b] flex justify-between items-center bg-[#0f172a] flex-wrap gap-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldCheck className="text-emerald-400" size={18} />
            Regulatory Compliance Audit Ledger (Azure Cosmos DB WORM)
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Immutable trace records for FINRA Rule 4511 &amp; MiFID II RTS 25 back-office execution audit</p>
        </div>

        <div className="flex gap-2 flex-wrap items-center">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter by Trace ID, subject..." 
              className="bg-[#0b1120] border border-[#1e293b] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 w-44 md:w-56 transition-colors"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#0b1120] border border-[#1e293b] rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-sky-500 transition-colors"
          >
            <option value="ALL">All Statuses</option>
            <option value="AUTO_EXECUTED">Auto Executed</option>
            <option value="PENDING_APPROVAL">Pending Approval</option>
            <option value="APPROVED">Supervisor Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>

          {/* Certificate View Button */}
          <button 
            onClick={printFullAuditLedger}
            className="flex items-center gap-1.5 bg-red-600 hover:bg-red-500 text-white rounded-xl px-3 py-1.5 text-xs font-medium transition-colors shadow-sm"
          >
            <Award size={14} />
            MiFID II Audit Certificate
          </button>

          {/* Export Button */}
          <button 
            onClick={exportAuditReport}
            className="flex items-center gap-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl px-3 py-1.5 text-xs font-medium transition-colors shadow-sm"
          >
            <FileDown size={14} />
            Export Audit JSON
          </button>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-[#0b1120] text-slate-400 font-mono uppercase text-[11px] border-b border-[#1e293b]">
            <tr>
              <th className="px-4 py-3 font-semibold">Trace ID</th>
              <th className="px-4 py-3 font-semibold">Email & Transaction Context</th>
              <th className="px-4 py-3 font-semibold">Intent & SOP</th>
              <th className="px-4 py-3 font-semibold">PII Shield</th>
              <th className="px-4 py-3 font-semibold">Risk Rating</th>
              <th className="px-4 py-3 font-semibold">Execution Status</th>
              <th className="px-4 py-3 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e293b]">
            {filtered.map((item) => (
              <tr 
                key={item.id}
                className="hover:bg-[#1e293b]/50 transition-colors group"
              >
                <td 
                  onClick={() => onSelectEmail(item)}
                  className="px-4 py-3.5 font-mono text-sky-400 font-semibold whitespace-nowrap cursor-pointer hover:underline"
                >
                  {item.id}
                </td>
                <td 
                  onClick={() => onSelectEmail(item)}
                  className="px-4 py-3.5 max-w-[260px] cursor-pointer"
                >
                  <div className="font-semibold text-white truncate group-hover:text-sky-400 transition-colors">
                    {item.subject}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate mt-0.5">
                    {item.senderName} ({item.senderOrg})
                  </div>
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap">
                  <span className="font-mono px-2 py-0.5 rounded bg-[#0b1120] text-slate-300 border border-[#1e293b]">
                    {item.intent.replace('_', ' ')}
                  </span>
                  <div className="text-[10px] text-indigo-400 font-mono mt-1">
                    {item.sopApplied.id} ({(item.sopApplied.relevance * 100).toFixed(0)}%)
                  </div>
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap font-mono text-emerald-400">
                  {item.piiReport.maskCount} Redacted
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap font-mono font-bold">
                  <span className={item.riskScore >= 0.7 ? 'text-rose-400' : item.riskScore >= 0.4 ? 'text-amber-400' : 'text-emerald-400'}>
                    {(item.riskScore * 100).toFixed(0)}% ({item.riskLevel})
                  </span>
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap">
                  {getStatusBadge(item.status)}
                </td>
                <td className="px-4 py-3.5 text-right whitespace-nowrap">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCertEmail(item);
                      }}
                      className="px-2.5 py-1 rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 text-[11px] font-semibold flex items-center gap-1 transition-colors"
                      title="View MiFID II / FINRA Compliance Audit Certificate"
                    >
                      <Award size={12} /> Certificate
                    </button>
                    <button
                      onClick={() => onSelectEmail(item)}
                      className="px-2.5 py-1 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 text-sky-400 border border-sky-500/30 text-[11px] font-semibold flex items-center gap-1 transition-colors"
                    >
                      Diff <ArrowUpRight size={12} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Compliance Certificate Modal */}
      {selectedCertEmail && (
        <ComplianceCertificateModal
          email={selectedCertEmail}
          onClose={() => setSelectedCertEmail(null)}
        />
      )}
    </div>
  );
}
