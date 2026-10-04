'use client';

import React from 'react';
import { ShieldAlert, Scale, CheckCircle2 } from 'lucide-react';

interface Props {
  score?: number;
}

export default function RiskGauge({ score = 0.42 }: Props) {
  const rotation = -90 + (score * 180);

  const getStatusText = () => {
    if (score < 0.4) return { text: 'Low Operational Risk', color: 'text-emerald-400', badge: 'bg-emerald-500/10 border-emerald-500/30' };
    if (score < 0.7) return { text: 'Medium Risk - Monitored', color: 'text-amber-400', badge: 'bg-amber-500/10 border-amber-500/30' };
    return { text: 'High Risk - HITL Required', color: 'text-rose-400', badge: 'bg-rose-500/10 border-rose-500/30' };
  };

  const status = getStatusText();

  return (
    <div className="bg-[#131d35] border border-[#1e293b] rounded-2xl p-5 flex flex-col items-center justify-center h-[225px] shadow-xl">
      <div className="flex justify-between items-center w-full mb-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold">
          <Scale size={15} className="text-sky-400" />
          <span>Risk Gateway Meter</span>
        </div>
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${status.badge} ${status.color}`}>
          {(score * 100).toFixed(0)}% Score
        </span>
      </div>
      
      <div className="relative w-44 h-22 overflow-hidden my-1">
        {/* Arc Background */}
        <div className="absolute top-0 left-0 w-44 h-44 rounded-full border-[14px] border-[#0b1120] border-b-transparent border-l-transparent transform -rotate-45"></div>
        
        {/* Gradient Arc */}
        <div className="absolute top-0 left-0 w-44 h-44 rounded-full border-[14px] border-transparent border-t-emerald-500 border-r-amber-500 border-b-rose-500 border-l-transparent transform -rotate-45 opacity-30"></div>
        
        {/* Needle */}
        <div 
          className="absolute bottom-0 left-1/2 w-1 h-20 bg-white origin-bottom transform transition-transform duration-700 ease-out z-10 shadow-lg shadow-white/50"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        >
          <div className="absolute -top-1 -left-1.5 w-4 h-4 bg-sky-400 rounded-full border-2 border-white"></div>
        </div>
        
        {/* Center Pivot */}
        <div className="absolute bottom-[-6px] left-1/2 transform -translate-x-1/2 w-4 h-4 bg-slate-200 rounded-full z-20 border-2 border-[#131d35]"></div>
        
        {/* 0.70 Threshold Marker */}
        <div className="absolute bottom-0 left-1/2 w-0.5 h-20 bg-rose-500 origin-bottom transform rotate-[36deg] z-0 opacity-80"></div>
      </div>
      
      <div className="text-center mt-1">
        <div className="text-xl font-bold text-white tracking-tight">{(score * 100).toFixed(0)} / 100</div>
        <div className={`text-xs font-semibold ${status.color}`}>{status.text}</div>
      </div>
      
      <div className="w-full flex justify-between text-[10px] font-mono text-slate-400 mt-2 px-2 border-t border-[#1e293b]/60 pt-1.5">
        <span className="text-emerald-400">Auto (≤0.70)</span>
        <span className="text-rose-400 font-bold">Gate: 0.70</span>
        <span className="text-amber-400">Teams HITL</span>
      </div>
    </div>
  );
}
