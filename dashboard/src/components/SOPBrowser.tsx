'use client';

import React, { useState } from 'react';
import { BookOpen, Search, Filter, CheckCircle2, ShieldCheck, ArrowRight, ExternalLink } from 'lucide-react';

export default function SOPBrowser() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<string>('ALL');

  const sops = [
    {
      id: 'SOP-CA-001',
      title: 'Mandatory Cash Dividend Reconciliation & Entitlement Processing',
      domain: 'CORPORATE_ACTION',
      targetSystem: 'Corporate Actions Master & SWIFT MT566',
      threshold: 'Rate <= €2.00 / Share (Auto-Exec) | > €2.00 (Supervisor HITL)',
      rules: 'Reconcile CSD position (Clearstream/Euroclear) against internal ledger on Record Date. If discrepancy < 100 shares, auto-adjust and book event. If rate > EUR 2.00, flag for supervisor sign-off.',
      keywords: ['dividend', 'cash', 'record date', 'ex-date', 'sap', 'entitlement', 'mt564', 'mt566'],
      sla: '< 2 Hours',
    },
    {
      id: 'SOP-SET-003',
      title: 'T+1 Failed Trade SSI Resolution & Counterparty Resubmission',
      domain: 'SETTLEMENT',
      targetSystem: 'TARGET2 / Euroclear Real-time Gateway',
      threshold: 'Notional <= $5M & Standard BIC (Auto-Exec) | Non-standard BIC (Supervisor HITL)',
      rules: 'Upon receiving failed matching notification with counterparty, query Counterparty SSI Directory. Verify BIC, beneficiary account, and settlement system (TARGET2). Resubmit corrected MT544 instruction prior to 14:00 CET cutoff.',
      keywords: ['failed', 'settlement', 'ssi', 't+1', 'unmatched', 'cutoff', 'target2', 'jpm', 'resubmit'],
      sla: '< 45 Mins',
    },
    {
      id: 'SOP-TL-001',
      title: 'Trade-to-Instrument Allocation & Desk Booking Linkage',
      domain: 'TRADE_LINKAGE',
      targetSystem: 'Front-Office Trade Booking Feeder (Murex/Sophis)',
      threshold: 'Validated CUSIP/ISIN (Auto-Exec) | Unknown Instrument (Desk Review)',
      rules: 'Verify trade ID against front-office trade feeder. Validate CUSIP/ISIN with Bloomberg/Reuters reference feed. Link trade to appropriate trading desk book (e.g. EQ-US-FLOW, FI-EUR-RATES).',
      keywords: ['link', 'trade linkage', 'cusip', 'apple', 'allocation', 'desk', 'book', 'trd-'],
      sla: '< 15 Mins',
    },
    {
      id: 'SOP-REF-002',
      title: 'Instrument Master Data Exception & ISIN/CUSIP Remapping',
      domain: 'INSTRUMENT_CORRECTION',
      targetSystem: 'Reference Data Master & Position Keeper',
      threshold: 'ISO 6166 Checksum Valid (Auto-Exec) | Invalid Checksum (Data Steward)',
      rules: 'When ISIN mismatch alert is raised, validate checksum using ISO 6166 algorithm. Patch Position Keeper and notify Risk Engine with automated rollback snapshot.',
      keywords: ['isin', 'mismatch', 'cusip', 'sedol', 'reference data', 'remap', 'position', 'bond'],
      sla: '< 30 Mins',
    },
    {
      id: 'SOP-SUP-001',
      title: 'Operations Systems Access Provisioning & Role Granting',
      domain: 'SUPPORT_TICKET',
      targetSystem: 'ServiceNow Enterprise ITSM API',
      threshold: 'Director Approval Present (Auto-Exec P3) | Missing Sign-off (Escalate)',
      rules: 'Verify requester identity against HR active directory. Auto-create ServiceNow ticket in "Access Management" queue with P3 SLA (4 hours). Route to Desk Head.',
      keywords: ['access', 'role', 'analyst', 'support', 'provision', 'ticket', 'itsm', 'servicenow'],
      sla: '< 4 Hours',
    },
  ];

  const filtered = sops.filter((s) => {
    const matchSearch = s.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.keywords.some((k) => k.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchDomain = selectedDomain === 'ALL' || s.domain === selectedDomain;
    return matchSearch && matchDomain;
  });

  return (
    <div className="bg-[#131d35] border border-[#1e293b] rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-4 pb-4 border-b border-[#1e293b]">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BookOpen className="text-indigo-400" size={20} />
            Institutional Standard Operating Procedures (SOP Runbooks)
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Azure AI Search Indexed Knowledge Base for Back-Office Autonomous Reasoning</p>
        </div>

        {/* Filter Bar */}
        <div className="flex gap-2 flex-wrap">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search SOPs, rules, ISINs..."
              className="bg-[#0b1120] border border-[#1e293b] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-48 md:w-64 transition-colors"
            />
          </div>

          <select
            value={selectedDomain}
            onChange={(e) => setSelectedDomain(e.target.value)}
            className="bg-[#0b1120] border border-[#1e293b] rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors"
          >
            <option value="ALL">All Domains</option>
            <option value="CORPORATE_ACTION">Corporate Actions</option>
            <option value="SETTLEMENT">Settlement</option>
            <option value="TRADE_LINKAGE">Trade Linkage</option>
            <option value="INSTRUMENT_CORRECTION">Ref Data</option>
            <option value="SUPPORT_TICKET">ITSM / Support</option>
          </select>
        </div>
      </div>

      {/* SOP Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((sop) => (
          <div key={sop.id} className="bg-[#0b1120] border border-[#1e293b] hover:border-indigo-500/50 p-5 rounded-xl transition-all duration-200 flex flex-col justify-between group">
            <div>
              <div className="flex justify-between items-start gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded bg-indigo-500/15 text-indigo-400 font-mono text-xs font-bold border border-indigo-500/30">
                    {sop.id}
                  </span>
                  <span className="text-[10px] font-mono uppercase text-slate-400">{sop.domain.replace('_', ' ')}</span>
                </div>
                <span className="text-xs text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  SLA: {sop.sla}
                </span>
              </div>

              <h3 className="text-sm font-bold text-white group-hover:text-indigo-400 transition-colors">
                {sop.title}
              </h3>

              <p className="text-xs text-slate-300 mt-2 leading-relaxed bg-[#131d35] p-3 rounded-lg border border-[#1e293b]">
                <strong>Rule:</strong> {sop.rules}
              </p>

              <div className="mt-3 text-[11px] text-slate-400 font-mono">
                <span className="text-sky-400 font-semibold">Gating Threshold:</span> {sop.threshold}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#1e293b] flex justify-between items-center text-xs">
              <span className="text-slate-400">Target: <strong className="text-slate-200">{sop.targetSystem}</strong></span>
              <span className="text-indigo-400 flex items-center gap-1 font-medium group-hover:translate-x-1 transition-transform">
                AI Search Indexed ✓
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
