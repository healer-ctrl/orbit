'use client';

import React from 'react';
import { BarChart3, TrendingUp, ShieldCheck, CheckCircle2, AlertOctagon, Layers, ArrowUpRight } from 'lucide-react';

export default function DailyOpsReport() {
  const counterparties = [
    { name: 'JPMorgan Chase (CHASUS33XXX)', volume: 142, autoExecRate: '92.4%', riskLevel: 'MEDIUM', amount: '$42.8M' },
    { name: 'Clearstream Banking (Frankfurt)', volume: 389, autoExecRate: '98.1%', riskLevel: 'LOW', amount: '€112.5M' },
    { name: 'Euroclear Bank (Brussels)', volume: 294, autoExecRate: '96.5%', riskLevel: 'LOW', amount: '€88.2M' },
    { name: 'BNP Paribas (BNPAFR22XXX)', volume: 88, autoExecRate: '89.0%', riskLevel: 'HIGH', amount: '€34.1M' },
    { name: 'DTCC Clearing Corp (NY)', volume: 512, autoExecRate: '99.2%', riskLevel: 'LOW', amount: '$210.0M' },
  ];

  return (
    <div className="bg-[#131d35] border border-[#1e293b] rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-3 pb-4 border-b border-[#1e293b]">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart3 className="text-sky-400" size={20} />
            Executive Daily Operations & STP Summary
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Société Générale Back-Office Autonomous Processing Metrics (24h Window)</p>
        </div>
        <div className="flex gap-2">
          <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-mono">
            STP Rate: 94.8%
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/30 font-mono">
            Avg Turnaround: 1.4s
          </span>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0b1120] border border-[#1e293b] p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium">Daily Transaction Volume</div>
          <div className="text-2xl font-bold text-white mt-1">€487.6M</div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
            <TrendingUp size={12} /> +18.4% vs 30d baseline
          </div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium">Auto-Executed Clean Trades</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">1,385</div>
          <div className="text-[11px] text-slate-400 mt-1">Zero manual touch required</div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium">Supervisory HITL Escalations</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">28</div>
          <div className="text-[11px] text-amber-300 mt-1">100% resolved before cutoff</div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium">PII Items Anonymized</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">4,192</div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
            <ShieldCheck size={12} /> Zero data leakage incidents
          </div>
        </div>
      </div>

      {/* Counterparty Risk Breakdown Table */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Counterparty Routing & Autonomy Breakdown</h3>
        <div className="overflow-x-auto border border-[#1e293b] rounded-xl bg-[#0b1120]">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#131d35] text-slate-400 font-mono uppercase">
              <tr>
                <th className="p-3">Counterparty / CSD</th>
                <th className="p-3">24h Volume</th>
                <th className="p-3">Total Notional</th>
                <th className="p-3">Auto-Execution STP Rate</th>
                <th className="p-3">Risk Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b]">
              {counterparties.map((cp) => (
                <tr key={cp.name} className="hover:bg-[#1e293b]/40 transition-colors">
                  <td className="p-3 font-semibold text-white">{cp.name}</td>
                  <td className="p-3 font-mono text-slate-300">{cp.volume} msgs</td>
                  <td className="p-3 font-mono text-sky-400">{cp.amount}</td>
                  <td className="p-3 font-mono text-emerald-400">{cp.autoExecRate}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded-full font-mono text-[10px] border ${
                      cp.riskLevel === 'HIGH' ? 'bg-rose-500/20 text-rose-400 border-rose-500/40' :
                      cp.riskLevel === 'MEDIUM' ? 'bg-amber-500/20 text-amber-400 border-amber-500/40' :
                      'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                    }`}>
                      {cp.riskLevel}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
