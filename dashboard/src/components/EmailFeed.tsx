'use client';

import React, { useState } from 'react';
import { Mail, Clock, AlertCircle } from 'lucide-react';

export default function EmailFeed() {
  const mockEmails = [
    {
      id: '1',
      sender: 'alex.williams@morganstanley.com',
      subject: 'URGENT: Settlement failure on AAPL block trade',
      timeAgo: '2 mins ago',
      intent: 'SETTLEMENT',
      urgency: 'HIGH',
      riskScore: 0.85,
    },
    {
      id: '2',
      sender: 'corp-actions@dtcc.com',
      subject: 'Dividend Announcement: MSFT Q3',
      timeAgo: '15 mins ago',
      intent: 'CORPORATE_ACTION',
      urgency: 'MEDIUM',
      riskScore: 0.35,
    },
    {
      id: '3',
      sender: 'j.smith@goldmansachs.com',
      subject: 'Correction to CUSIP on yesterday\'s bond trade',
      timeAgo: '42 mins ago',
      intent: 'INSTRUMENT_CORRECTION',
      urgency: 'HIGH',
      riskScore: 0.72,
    },
    {
      id: '4',
      sender: 'support@tradeweb.com',
      subject: 'API Connectivity Issue - Resolve by EOD',
      timeAgo: '1 hour ago',
      intent: 'SUPPORT_TICKET',
      urgency: 'LOW',
      riskScore: 0.15,
    },
    {
      id: '5',
      sender: 'matching-system@internal.bank.com',
      subject: 'Unmatched trade linkage requested',
      timeAgo: '2 hours ago',
      intent: 'TRADE_LINKAGE',
      urgency: 'MEDIUM',
      riskScore: 0.45,
    }
  ];

  const getIntentColor = (intent: string) => {
    switch (intent) {
      case 'CORPORATE_ACTION': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'SETTLEMENT': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'TRADE_LINKAGE': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'INSTRUMENT_CORRECTION': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'SUPPORT_TICKET': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getUrgencyDot = (urgency: string) => {
    switch (urgency) {
      case 'HIGH': return 'bg-red-500';
      case 'MEDIUM': return 'bg-amber-500';
      case 'LOW': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getRiskColor = (score: number) => {
    if (score < 0.3) return 'bg-green-500';
    if (score < 0.7) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-[#1a2332] border border-[#2d3748] rounded-xl flex flex-col h-[500px]">
      <div className="p-4 border-b border-[#2d3748] flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Mail className="text-blue-500" size={20} />
          Live Email Feed
        </h2>
        <div className="flex items-center gap-2 text-sm text-[#94a3b8]">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
          </span>
          Monitoring Inbox
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {mockEmails.map((email) => (
          <div key={email.id} className="bg-[#0a0f1c] border border-[#2d3748] p-4 rounded-lg hover:border-blue-500/50 transition-colors cursor-pointer group">
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                  {email.sender.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="text-white text-sm font-medium truncate max-w-[200px]" title={email.sender}>
                    {email.sender}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-[#94a3b8]">
                    <Clock size={12} />
                    {email.timeAgo}
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className={`text-xs px-2 py-1 rounded-md border ${getIntentColor(email.intent)}`}>
                  {email.intent.replace('_', ' ')}
                </span>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${getUrgencyDot(email.urgency)}`}></div>
                  <span className="text-[10px] text-[#94a3b8]">{email.urgency}</span>
                </div>
              </div>
            </div>
            
            <div className="text-white font-medium mb-3 truncate group-hover:text-blue-400 transition-colors">
              {email.subject}
            </div>
            
            <div className="mt-2">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#94a3b8]">Risk Score</span>
                <span className={email.riskScore >= 0.7 ? 'text-red-400' : 'text-white'}>
                  {(email.riskScore * 100).toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-[#1a2332] rounded-full h-1.5">
                <div 
                  className={`h-1.5 rounded-full ${getRiskColor(email.riskScore)}`} 
                  style={{ width: `${email.riskScore * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
