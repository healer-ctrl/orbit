'use client';

import React from 'react';
import { Check, X, AlertTriangle, Clock, ShieldCheck, ArrowRight } from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';

interface Props {
  pendingEmails: ProcessedEmailRecord[];
  onSelectEmail: (email: ProcessedEmailRecord) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export default function ApprovalQueue({ pendingEmails, onSelectEmail, onApprove, onReject }: Props) {
  return (
    <div className="bg-[#131d35] border border-[#1e293b] rounded-2xl flex flex-col h-[280px] shadow-xl overflow-hidden">
      <div className="p-3.5 border-b border-[#1e293b] flex justify-between items-center bg-[#0f172a]">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-amber-400" size={16} />
          <h2 className="text-xs md:text-sm font-bold text-white">Supervisory HITL Approval Queue</h2>
        </div>
        <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold animate-pulse">
          {pendingEmails.length} Action Required
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {pendingEmails.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-4 text-slate-400">
            <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-2">
              <Check size={20} />
            </div>
            <p className="text-xs font-semibold text-white">Approval Queue Clear</p>
            <p className="text-[10px] text-slate-400 mt-0.5">All high-risk operations trades approved or auto-executed.</p>
          </div>
        ) : (
          pendingEmails.map((item) => (
            <div 
              key={item.id} 
              className="bg-[#0b1120] border border-amber-500/30 hover:border-amber-500/60 rounded-xl p-3 transition-colors shadow-sm"
            >
              <div 
                onClick={() => onSelectEmail(item)}
                className="cursor-pointer group"
              >
                <div className="flex justify-between items-start mb-1.5">
                  <div className="text-white text-xs font-semibold truncate max-w-[220px] group-hover:text-amber-300 transition-colors" title={item.subject}>
                    {item.subject}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded font-mono">
                    <Clock size={10} /> {item.timeAgo}
                  </div>
                </div>

                <div className="flex gap-2 mb-2.5 text-[10px] flex-wrap">
                  <span className="text-slate-300 bg-[#131d35] px-2 py-0.5 rounded border border-[#1e293b] font-mono">
                    {item.intent.replace('_', ' ')}
                  </span>
                  <span className="text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20 font-mono font-bold">
                    Risk: {(item.riskScore * 100).toFixed(0)}%
                  </span>
                  <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-mono">
                    {item.piiReport.maskCount} PII Masked
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-1 border-t border-[#1e293b]">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    onApprove(item.id);
                  }}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-1.5 rounded-lg flex items-center justify-center gap-1 transition-all shadow-sm transform hover:scale-[1.02]"
                >
                  <Check size={14} /> Approve & Execute
                </button>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    onReject(item.id);
                  }}
                  className="flex-1 bg-[#1e293b] hover:bg-rose-600 text-white text-xs font-semibold py-1.5 rounded-lg flex items-center justify-center gap-1 transition-all shadow-sm"
                >
                  <X size={14} /> Reject / Ticket
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
