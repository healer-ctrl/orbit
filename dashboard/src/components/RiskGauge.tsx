'use client';

import React from 'react';
import { Shield } from 'lucide-react';

export default function RiskGauge({ score = 0.42 }) {
  // Calculate rotation (-90deg to 90deg)
  const rotation = -90 + (score * 180);
  
  const getScoreColor = () => {
    if (score < 0.3) return '#10b981'; // green
    if (score < 0.7) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };
  
  const getStatusText = () => {
    if (score < 0.3) return { text: 'Low Risk', color: 'text-green-500' };
    if (score < 0.7) return { text: 'Moderate Risk', color: 'text-amber-500' };
    return { text: 'High Risk - Needs Review', color: 'text-red-500' };
  };

  const status = getStatusText();

  return (
    <div className="bg-[#1a2332] border border-[#2d3748] rounded-xl p-6 flex flex-col items-center justify-center h-64 mb-6">
      <div className="flex items-center gap-2 mb-4 w-full">
        <Shield size={18} className="text-[#94a3b8]" />
        <h3 className="text-sm font-medium text-white">Current Risk Assessment</h3>
      </div>
      
      <div className="relative w-48 h-24 overflow-hidden mb-2">
        {/* Gauge Background */}
        <div className="absolute top-0 left-0 w-48 h-48 rounded-full border-[16px] border-[#2d3748] border-b-transparent border-l-transparent transform -rotate-45"></div>
        
        {/* Gauge Color Gradient - simple implementation using segmented borders */}
        <div className="absolute top-0 left-0 w-48 h-48 rounded-full border-[16px] border-transparent border-t-green-500 border-r-amber-500 border-b-red-500 border-l-transparent transform -rotate-45 opacity-20"></div>
        
        {/* Needle */}
        <div 
          className="absolute bottom-0 left-1/2 w-1 h-24 bg-white origin-bottom transform transition-transform duration-1000 ease-out z-10"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        >
          <div className="absolute -top-1 -left-1.5 w-4 h-4 bg-white rounded-full"></div>
        </div>
        
        {/* Center dot */}
        <div className="absolute bottom-[-8px] left-1/2 transform -translate-x-1/2 w-4 h-4 bg-white rounded-full z-20"></div>
        
        {/* Threshold indicator at 0.7 (approx 36deg from center) */}
        <div className="absolute bottom-0 left-1/2 w-0.5 h-24 bg-red-500/50 origin-bottom transform rotate-[36deg] z-0"></div>
      </div>
      
      <div className="text-center mt-2">
        <div className="text-3xl font-bold text-white">{(score * 100).toFixed(0)}</div>
        <div className={`text-sm font-medium ${status.color}`}>{status.text}</div>
      </div>
      
      <div className="w-full flex justify-between text-xs text-[#94a3b8] mt-4 px-2">
        <span>Auto-Execute</span>
        <span className="text-red-400">Threshold: 70</span>
        <span>Human</span>
      </div>
    </div>
  );
}
