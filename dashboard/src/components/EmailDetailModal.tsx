'use client';

import React, { useState } from 'react';
import { 
  X, 
  ShieldCheck, 
  FileText, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Copy, 
  Check, 
  Lock, 
  Send,
  BookOpen,
  ArrowRight
} from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';

interface Props {
  email: ProcessedEmailRecord | null;
  onClose: () => void;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
}

export default function EmailDetailModal({ email, onClose, onApprove, onReject }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'pii' | 'agents' | 'payload'>('overview');
  const [copied, setCopied] = useState(false);

  if (!email) return null;

  const copyJson = (data: any) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getIntentBadge = (intent: string) => {
    switch (intent) {
      case 'CORPORATE_ACTION': return 'bg-blue-500/20 text-blue-400 border-blue-500/40';
      case 'SETTLEMENT': return 'bg-red-500/20 text-red-400 border-red-500/40';
      case 'TRADE_LINKAGE': return 'bg-purple-500/20 text-purple-400 border-purple-500/40';
      case 'INSTRUMENT_CORRECTION': return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'SUPPORT_TICKET': return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
      default: return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-[#1e293b] bg-[#131d35] flex justify-between items-start">
          <div className="flex-1 pr-6">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${getIntentBadge(email.intent)}`}>
                {email.intent.replace('_', ' ')}
              </span>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
                email.riskScore >= 0.70 
                  ? 'bg-rose-500/20 text-rose-400 border-rose-500/40' 
                  : email.riskScore >= 0.40 
                    ? 'bg-amber-500/20 text-amber-400 border-amber-500/40' 
                    : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
              }`}>
                Risk Score: {(email.riskScore * 100).toFixed(0)}% ({email.riskLevel})
              </span>
              {email.status === 'PENDING_APPROVAL' && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 animate-pulse font-medium">
                  <Clock size={12} /> Pending Supervisor Approval
                </span>
              )}
              {email.status === 'APPROVED' && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5 font-medium">
                  <CheckCircle2 size={12} /> Supervisor Approved & Executed
                </span>
              )}
              {email.status === 'AUTO_EXECUTED' && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5 font-medium">
                  <CheckCircle2 size={12} /> Auto-Executed
                </span>
              )}
            </div>
            <h2 className="text-lg md:text-xl font-bold text-white tracking-tight leading-snug">
              {email.subject}
            </h2>
            <div className="flex items-center gap-4 text-xs text-slate-400 mt-2 flex-wrap">
              <span><strong className="text-slate-300">From:</strong> {email.senderName} ({email.sender})</span>
              <span><strong className="text-slate-300">Org:</strong> {email.senderOrg}</span>
              <span><strong className="text-slate-300">Time:</strong> {email.timeAgo}</span>
            </div>
          </div>
          
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X size={22} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#1e293b] bg-[#0b1120] px-6 gap-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 px-4 font-medium text-xs md:text-sm border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'overview' ? 'border-sky-400 text-sky-400 bg-sky-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText size={16} />
            Raw Email & Entities
          </button>
          <button
            onClick={() => setActiveTab('pii')}
            className={`py-3 px-4 font-medium text-xs md:text-sm border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'pii' ? 'border-emerald-400 text-emerald-400 bg-emerald-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck size={16} />
            🛡️ PII Guardrail Inspection ({email.piiReport.maskCount} Redacted)
          </button>
          <button
            onClick={() => setActiveTab('agents')}
            className={`py-3 px-4 font-medium text-xs md:text-sm border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'agents' ? 'border-indigo-400 text-indigo-400 bg-indigo-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu size={16} />
            AI Foundry Agent Reasoning ({email.pipelineSteps.length} Steps)
          </button>
          <button
            onClick={() => setActiveTab('payload')}
            className={`py-3 px-4 font-medium text-xs md:text-sm border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'payload' ? 'border-purple-400 text-purple-400 bg-purple-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Send size={16} />
            Azure Functions Execution Payload
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#0a0f1c]">
          
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-fadeIn">
              {/* Entity Cards */}
              <div>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Extracted Financial Entities & Resolution</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {Object.entries(email.entities).map(([key, val]) => (
                    <div key={key} className="bg-[#131d35] border border-[#1e293b] p-3 rounded-xl">
                      <div className="text-[10px] uppercase font-mono text-sky-400 mb-1">{key}</div>
                      <div className="text-sm font-semibold text-white truncate" title={String(val)}>{String(val)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Standard Operating Procedure Matched */}
              <div className="bg-[#131d35] border border-[#1e293b] p-4 rounded-xl flex items-start gap-4">
                <div className="p-2.5 rounded-lg bg-indigo-500/20 text-indigo-400 mt-1">
                  <BookOpen size={20} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/30">
                      {email.sopApplied.id}
                    </span>
                    <span className="text-xs text-slate-400">Match Confidence: {(email.sopApplied.relevance * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-sm font-semibold text-white mt-1">{email.sopApplied.title}</div>
                  <div className="text-xs text-slate-300 mt-1 bg-[#0b1120] p-2.5 rounded-lg border border-[#1e293b]">
                    <strong>SOP Rule:</strong> {email.sopApplied.rule}
                  </div>
                </div>
              </div>

              {/* Raw Email Body */}
              <div>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Original Email Content (From Outlook M365)</h3>
                <pre className="bg-[#070b14] border border-[#1e293b] p-4 rounded-xl text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                  {email.rawBody}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 2: PII GUARDRAIL INSPECTION */}
          {activeTab === 'pii' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <ShieldCheck size={28} className="text-emerald-400" />
                  <div>
                    <h4 className="text-sm font-bold text-white">Enterprise PII Protection & Data Anonymization Active</h4>
                    <p className="text-xs text-emerald-300">
                      Sensitive client numbers and personal data were tokenized BEFORE sending payload to GPT-4o.
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 rounded-full text-xs font-mono border border-emerald-500/40">
                    {email.piiReport.maskCount} Redacted Items
                  </span>
                  <span className="px-3 py-1 bg-sky-500/20 text-sky-300 rounded-full text-xs font-mono border border-sky-500/40">
                    Prompt Injection: PASSED
                  </span>
                </div>
              </div>

              {/* Token Mapping Table */}
              <div>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Reversible Anonymization Token Map</h3>
                <div className="overflow-x-auto border border-[#1e293b] rounded-xl bg-[#0f172a]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#131d35] text-slate-400 uppercase font-mono">
                      <tr>
                        <th className="p-3">Sanitized Placeholder (Sent to GPT)</th>
                        <th className="p-3">Protected Actual Value (Restored Internally)</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e293b]">
                      {Object.entries(email.piiReport.mapping).map(([token, actual]) => (
                        <tr key={token} className="hover:bg-[#1e293b]/40 transition-colors">
                          <td className="p-3 font-mono text-amber-400 font-semibold">{token}</td>
                          <td className="p-3 font-mono text-emerald-400">{actual}</td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-mono border border-emerald-500/20">
                              PROTECTED
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Before vs After Diff */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-xs font-semibold text-rose-400 mb-2 flex items-center gap-1.5">
                    <Lock size={14} /> 1. Raw Sensitive Email (Internal Only)
                  </h4>
                  <pre className="bg-[#070b14] border border-rose-500/20 p-3 rounded-xl text-[11px] font-mono text-slate-300 whitespace-pre-wrap leading-relaxed h-56 overflow-y-auto">
                    {email.rawBody}
                  </pre>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-emerald-400 mb-2 flex items-center gap-1.5">
                    <ShieldCheck size={14} /> 2. Sanitized Payload (Sent to Azure OpenAI GPT-4o)
                  </h4>
                  <pre className="bg-[#070b14] border border-emerald-500/30 p-3 rounded-xl text-[11px] font-mono text-emerald-300/90 whitespace-pre-wrap leading-relaxed h-56 overflow-y-auto">
                    {email.sanitizedBody}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AGENTS REASONING */}
          {activeTab === 'agents' && (
            <div className="space-y-4 animate-fadeIn">
              {email.pipelineSteps.map((step, idx) => (
                <div key={idx} className="bg-[#131d35] border border-[#1e293b] p-4 rounded-xl flex gap-4 items-start">
                  <div className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-indigo-400 font-bold text-xs shrink-0">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-center flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">{step.agent}</span>
                        <span className="text-xs text-slate-400">({step.role})</span>
                      </div>
                      <span className="text-xs font-mono text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
                        {step.durationMs}ms
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 font-medium">{step.summary}</p>
                    <pre className="mt-2 bg-[#070b14] p-2.5 rounded-lg border border-[#1e293b] text-[10px] font-mono text-slate-400 overflow-x-auto">
                      {JSON.stringify(step.details, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: PAYLOAD */}
          {activeTab === 'payload' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="text-sm font-bold text-white">Target Subsystem: {email.executionResult.system}</h4>
                  <p className="text-xs text-slate-400">Action Execution ID: {email.executionResult.actionId}</p>
                </div>
                <button
                  onClick={() => copyJson(email.executionResult)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 text-xs font-mono border border-sky-500/30 transition-colors"
                >
                  {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                  {copied ? 'Copied JSON!' : 'Copy Payload JSON'}
                </button>
              </div>

              <pre className="bg-[#070b14] border border-[#1e293b] p-4 rounded-xl text-xs font-mono text-sky-300 overflow-x-auto leading-relaxed">
                {JSON.stringify(email.executionResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer with Interactive Action Buttons */}
        <div className="p-4 border-t border-[#1e293b] bg-[#131d35] flex justify-between items-center flex-wrap gap-3">
          <div className="text-xs text-slate-400 font-mono">
            Trace ID: <span className="text-slate-200">{email.id}</span> | Cosmos DB: <span className="text-emerald-400">Synced</span>
          </div>

          <div className="flex gap-3">
            {email.status === 'PENDING_APPROVAL' && onApprove && onReject ? (
              <>
                <button
                  onClick={() => {
                    onApprove(email.id);
                    onClose();
                  }}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 shadow-lg shadow-emerald-600/30 transition-all transform hover:scale-105"
                >
                  <Check size={16} /> Approve & Auto-Execute (HITL)
                </button>
                <button
                  onClick={() => {
                    onReject(email.id);
                    onClose();
                  }}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 shadow-lg shadow-rose-600/30 transition-all transform hover:scale-105"
                >
                  <X size={16} /> Reject & Create ServiceNow Ticket
                </button>
              </>
            ) : (
              <button
                onClick={onClose}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs rounded-xl transition-colors"
              >
                Close View
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
