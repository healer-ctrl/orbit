'use client';

import React from 'react';
import { Search, Filter, ChevronDown, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export default function AuditTrail() {
  const mockAudit = [
    {
      id: 'tx-19283',
      time: '2023-10-24 14:32:41',
      subject: 'Dividend Announcement: MSFT Q3',
      intent: 'CORPORATE_ACTION',
      riskScore: 0.12,
      decision: 'AUTO_EXECUTE',
      action: 'Updated Corporate Action DB',
      status: 'SUCCESS'
    },
    {
      id: 'tx-19282',
      time: '2023-10-24 14:15:22',
      subject: 'API Connectivity Issue - Resolve by EOD',
      intent: 'SUPPORT_TICKET',
      riskScore: 0.05,
      decision: 'AUTO_EXECUTE',
      action: 'Created JIRA Ticket IT-4921',
      status: 'SUCCESS'
    },
    {
      id: 'tx-19281',
      time: '2023-10-24 13:45:10',
      subject: 'URGENT: Settlement failure on AAPL block trade',
      intent: 'SETTLEMENT',
      riskScore: 0.85,
      decision: 'APPROVAL_REQUIRED',
      action: 'Escalated to Settlement Ops Team',
      status: 'PENDING'
    },
    {
      id: 'tx-19280',
      time: '2023-10-24 12:30:05',
      subject: 'Unmatched trade linkage requested',
      intent: 'TRADE_LINKAGE',
      riskScore: 0.45,
      decision: 'AUTO_EXECUTE',
      action: 'Linked trades in Matching Engine',
      status: 'FAILED'
    }
  ];

  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'SUCCESS': return <CheckCircle size={16} className="text-green-500" />;
      case 'FAILED': return <XCircle size={16} className="text-red-500" />;
      case 'PENDING': return <AlertCircle size={16} className="text-amber-500" />;
      default: return null;
    }
  };

  return (
    <div className="bg-[#1a2332] border border-[#2d3748] rounded-xl flex flex-col h-[400px]">
      <div className="p-4 border-b border-[#2d3748] flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white">Audit Trail</h2>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#94a3b8]" size={16} />
            <input 
              type="text" 
              placeholder="Search traces..." 
              className="bg-[#0a0f1c] border border-[#2d3748] rounded-lg pl-9 pr-4 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500 w-64"
            />
          </div>
          <button className="flex items-center gap-2 bg-[#0a0f1c] border border-[#2d3748] rounded-lg px-3 py-1.5 text-sm text-[#94a3b8] hover:text-white transition-colors">
            <Filter size={16} />
            Filter
          </button>
        </div>
      </div>
      
      <div className="overflow-auto flex-1">
        <table className="w-full text-left text-sm text-[#94a3b8]">
          <thead className="text-xs uppercase bg-[#0a0f1c] text-[#94a3b8] sticky top-0">
            <tr>
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Email Subject</th>
              <th className="px-4 py-3 font-medium">Intent</th>
              <th className="px-4 py-3 font-medium">Decision</th>
              <th className="px-4 py-3 font-medium">Action Taken</th>
              <th className="px-4 py-3 font-medium text-center">Status</th>
              <th className="px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {mockAudit.map((row) => (
              <tr key={row.id} className="border-b border-[#2d3748] hover:bg-[#2d3748]/30 transition-colors cursor-pointer">
                <td className="px-4 py-3 whitespace-nowrap">{row.time}</td>
                <td className="px-4 py-3 text-white truncate max-w-[200px]" title={row.subject}>{row.subject}</td>
                <td className="px-4 py-3">
                  <span className="bg-[#0a0f1c] px-2 py-1 rounded border border-[#2d3748] text-xs">
                    {row.intent}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`${row.decision === 'AUTO_EXECUTE' ? 'text-green-400' : 'text-amber-400'}`}>
                    {row.decision.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-4 py-3 truncate max-w-[200px]">{row.action}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-center">
                    {getStatusIcon(row.status)}
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <ChevronDown size={16} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
