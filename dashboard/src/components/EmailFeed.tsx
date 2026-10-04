'use client';

import React, { useState } from 'react';
import { Mail, Clock, Search, ShieldCheck, AlertCircle, ArrowUpRight } from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';

interface Props {
  emails: ProcessedEmailRecord[];
  onSelectEmail: (email: ProcessedEmailRecord) => void;
}

export default function EmailFeed({ emails, onSelectEmail }: Props) {
  const [filterIntent, setFilterIntent] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const getIntentColor = (intent: string) => {
    switch (intent) {
      case 'CORPORATE_ACTION': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'SETTLEMENT': return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'TRADE_LINKAGE': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'INSTRUMENT_CORRECTION': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'SUPPORT_TICKET': return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
      default: return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
    }
  };

  const getUrgencyDot = (urgency: string) => {
    switch (urgency) {
      case 'HIGH': return 'bg-rose-500';
      case 'MEDIUM': return 'bg-amber-500';
      case 'LOW': return 'bg-emerald-500';
      default: return 'bg-slate-500';
    }
  };

  const filtered = emails.filter((email) => {
    const matchIntent = filterIntent === 'ALL' || email.intent === filterIntent;
    const matchSearch = email.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      email.sender.toLowerCase().includes(searchTerm.toLowerCase());
    return matchIntent && matchSearch;
  });

  return (
    <div className="bg-[#131d35] border border-[#1e293b] rounded-2xl flex flex-col h-[520px] shadow-xl overflow-hidden">
      {/* Feed Header */}
      <div className="p-4 border-b border-[#1e293b] flex justify-between items-center bg-[#0f172a] flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Mail className="text-sky-400" size={18} />
          <h2 className="text-sm md:text-base font-bold text-white">Live Operations Mailbox Feed</h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/30">
            {filtered.length} Messages
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>Outlook Graph API Active</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-3 border-b border-[#1e293b] bg-[#0b1120] flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[160px]">
          <Search size={13} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search sender, subject..."
            className="w-full bg-[#131d35] border border-[#1e293b] rounded-lg pl-8 pr-3 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>

        <select
          value={filterIntent}
          onChange={(e) => setFilterIntent(e.target.value)}
          className="bg-[#131d35] border border-[#1e293b] rounded-lg px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-sky-500 transition-colors"
        >
          <option value="ALL">All Intents</option>
          <option value="CORPORATE_ACTION">Corporate Action</option>
          <option value="SETTLEMENT">Settlement</option>
          <option value="TRADE_LINKAGE">Trade Linkage</option>
          <option value="INSTRUMENT_CORRECTION">Ref Data</option>
          <option value="SUPPORT_TICKET">Support</option>
        </select>
      </div>
      
      {/* Scrollable Feed List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {filtered.map((email) => (
          <div 
            key={email.id} 
            onClick={() => onSelectEmail(email)}
            className="bg-[#0b1120] border border-[#1e293b] hover:border-sky-500/60 p-3.5 rounded-xl transition-all duration-200 cursor-pointer group hover:bg-[#0f172a] shadow-sm hover:shadow-md"
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-sky-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow">
                  {email.senderName.charAt(0)}
                </div>
                <div>
                  <div className="text-white text-xs font-semibold truncate max-w-[180px] group-hover:text-sky-400 transition-colors">
                    {email.senderName}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate max-w-[160px]">
                    {email.senderOrg}
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className={`text-[10px] px-2 py-0.5 rounded-md border font-mono font-medium ${getIntentColor(email.intent)}`}>
                  {email.intent.replace('_', ' ')}
                </span>
                <div className="flex items-center gap-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${getUrgencyDot(email.urgency)}`}></div>
                  <span className="text-[10px] text-slate-400">{email.timeAgo}</span>
                </div>
              </div>
            </div>
            
            <div className="text-slate-200 text-xs font-medium line-clamp-1 mb-2">
              {email.subject}
            </div>

            <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1.5 border-t border-[#1e293b]">
              <div className="flex items-center gap-1.5">
                <ShieldCheck size={12} className="text-emerald-400" />
                <span>{email.piiReport.maskCount} PII Redacted</span>
              </div>
              <div className="flex items-center gap-1 group-hover:text-sky-400 transition-colors font-mono">
                <span>Inspect Trace</span>
                <ArrowUpRight size={12} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
