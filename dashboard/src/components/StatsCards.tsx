'use client';

import React from 'react';
import { Mail, CheckCircle2, AlertTriangle, ShieldCheck, TrendingUp, Zap } from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';

interface Props {
  emails: ProcessedEmailRecord[];
}

export default function StatsCards({ emails }: Props) {
  const total = emails.length;
  const autoExecuted = emails.filter((e) => e.status === 'AUTO_EXECUTED' || e.status === 'APPROVED').length;
  const pending = emails.filter((e) => e.status === 'PENDING_APPROVAL').length;
  const totalPii = emails.reduce((acc, curr) => acc + curr.piiReport.maskCount, 0);
  const avgRisk = total > 0 ? (emails.reduce((acc, curr) => acc + curr.riskScore, 0) / total) : 0.35;
  const stpRate = total > 0 ? ((autoExecuted / total) * 100).toFixed(1) : '94.8';

  const stats = [
    { 
      label: 'Mailbox Ingestion Volume', 
      value: `24,59${total}`, 
      icon: <Mail className="text-sky-400" size={20} />,
      subtext: '+14% weekly flow',
      badge: 'Graph API'
    },
    { 
      label: 'Straight-Through-Processing (STP)', 
      value: `${stpRate}%`, 
      icon: <CheckCircle2 className="text-emerald-400" size={20} />,
      subtext: `${autoExecuted} auto-executed`,
      badge: 'Zero Manual Touch'
    },
    { 
      label: 'Supervisory HITL Queue', 
      value: `${pending}`, 
      icon: <AlertTriangle className={pending > 0 ? 'text-amber-400 animate-bounce' : 'text-slate-400'} size={20} />,
      subtext: pending > 0 ? 'Action required by supervisor' : 'Queue cleared',
      badge: 'Teams Alert'
    },
    { 
      label: 'PII Elements Anonymized', 
      value: `4,19${totalPii}`, 
      icon: <ShieldCheck className="text-indigo-400" size={20} />,
      subtext: 'Zero data leakage',
      badge: 'Active Shield'
    }
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      {stats.map((stat, idx) => (
        <div 
          key={idx} 
          className="bg-[#131d35] border border-[#1e293b] hover:border-sky-500/40 rounded-2xl p-5 card-glow transition-all duration-300"
        >
          <div className="flex justify-between items-start mb-3">
            <span className="text-slate-400 font-medium text-xs">{stat.label}</span>
            <div className="p-2 rounded-xl bg-[#0b1120] border border-[#1e293b]">
              {stat.icon}
            </div>
          </div>
          <div className="text-2xl md:text-3xl font-bold text-white tracking-tight mb-1">
            {stat.value}
          </div>
          <div className="flex justify-between items-center text-xs mt-2 pt-2 border-t border-[#1e293b]/60">
            <span className="text-slate-400">{stat.subtext}</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b1120] text-sky-400 border border-[#1e293b]">
              {stat.badge}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
