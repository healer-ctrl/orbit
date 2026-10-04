'use client';

import React, { useState } from 'react';
import { Check, X, AlertTriangle, Clock } from 'lucide-react';

export default function ApprovalQueue() {
  const [approvals, setApprovals] = useState([
    {
      id: 'req-1',
      subject: 'URGENT: Settlement failure on AAPL block trade',
      intent: 'SETTLEMENT',
      riskScore: 0.85,
      factors: ['High Value (>$10M)', 'Unrecognized counterparty email'],
      timeWaiting: '4m 12s'
    },
    {
      id: 'req-2',
      subject: 'Correction to CUSIP on yesterday\'s bond trade',
      intent: 'INSTRUMENT_CORRECTION',
      riskScore: 0.72,
      factors: ['Post-T+1 modification', 'Conflicts with matched ticket'],
      timeWaiting: '12m 45s'
    }
  ]);

  const handleAction = (id: string, action: 'approve' | 'reject') => {
    // In a real app, call API here
    setApprovals(approvals.filter(a => a.id !== id));
  };

  if (approvals.length === 0) {
    return (
      <div className="bg-[#1a2332] border border-[#2d3748] rounded-xl p-6 flex flex-col items-center justify-center h-[212px]">
        <div className="w-12 h-12 bg-green-500/10 rounded-full flex items-center justify-center mb-3">
          <Check className="text-green-500" size={24} />
        </div>
        <h3 className="text-white font-medium">All caught up!</h3>
        <p className="text-[#94a3b8] text-sm mt-1">No pending approvals required.</p>
      </div>
    );
  }

  return (
    <div className="bg-[#1a2332] border border-[#2d3748] rounded-xl flex flex-col h-[212px]">
      <div className="p-4 border-b border-[#2d3748] flex justify-between items-center">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <AlertTriangle className="text-amber-500" size={18} />
          Action Required ({approvals.length})
        </h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {approvals.map((item) => (
          <div key={item.id} className="bg-[#0a0f1c] border border-amber-500/30 rounded-lg p-3 mb-2 last:mb-0">
            <div className="flex justify-between items-start mb-2">
              <div className="text-white text-sm font-medium truncate pr-2" title={item.subject}>
                {item.subject}
              </div>
              <div className="flex items-center gap-1 text-xs text-amber-500 whitespace-nowrap bg-amber-500/10 px-2 py-0.5 rounded">
                <Clock size={10} />
                {item.timeWaiting}
              </div>
            </div>
            
            <div className="flex gap-2 mb-3 text-xs">
              <span className="text-[#94a3b8] bg-[#1a2332] px-1.5 py-0.5 rounded border border-[#2d3748]">
                {item.intent}
              </span>
              <span className="text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                Risk: {(item.riskScore * 100).toFixed(0)}%
              </span>
            </div>
            
            <div className="flex gap-2">
              <button 
                onClick={() => handleAction(item.id, 'approve')}
                className="flex-1 bg-green-600 hover:bg-green-500 text-white text-xs font-medium py-1.5 rounded flex items-center justify-center gap-1 transition-colors"
              >
                <Check size={14} /> Approve
              </button>
              <button 
                onClick={() => handleAction(item.id, 'reject')}
                className="flex-1 bg-[#2d3748] hover:bg-red-600 text-white text-xs font-medium py-1.5 rounded flex items-center justify-center gap-1 transition-colors"
              >
                <X size={14} /> Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
