'use client';

import React, { useEffect, useState } from 'react';
import { ShieldCheck, SplitSquareHorizontal, FileText, BookOpen, Scale, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';

export default function AgentPipeline() {
  const [animState, setAnimState] = useState(0);

  // Animation cycle through all pipeline stages
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimState((prev) => (prev + 1) % 7);
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  const getStatusStyle = (step: number) => {
    if (animState > step) return "border-emerald-500/60 bg-emerald-500/10 text-emerald-400";
    if (animState === step) return "border-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.35)] bg-blue-500/15 text-blue-400 pulse-dot";
    return "border-[#2d3748] bg-[#0a0f1c] opacity-50 text-[#94a3b8]";
  };

  const getLineStyle = (step: number) => {
    if (animState > step) return "bg-emerald-500";
    if (animState === step) return "bg-blue-500 pipeline-flow";
    return "bg-[#2d3748]";
  };

  const agents = [
    { icon: <ShieldCheck size={20} />, name: "PII Guardrail", detail: "Anonymizes sensitive data" },
    { icon: <SplitSquareHorizontal size={20} />, name: "Classifier", detail: "GPT-4o Intent mapping" },
    { icon: <FileText size={20} />, name: "Parser Agent", detail: "ISIN / CUSIP / BICs" },
    { icon: <BookOpen size={20} />, name: "Decision & SOP", detail: "Azure AI Search RAG" },
    { icon: <Scale size={20} />, name: "Risk Scorer", detail: "Threshold gating (0.7)" },
  ];

  return (
    <div className="bg-[#1a2332] border border-[#2d3748] rounded-xl p-6 mt-8 shadow-xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Activity size={20} className="text-blue-500 animate-pulse" />
          Live Multi-Agent Pipeline & Guardrails Flow
        </h2>
        <span className="text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-full font-mono">
          Azure AI Foundry Orchestrator
        </span>
      </div>
      
      <div className="flex items-center justify-between relative pb-4 overflow-x-auto">
        {/* Pipeline Agent Nodes */}
        {agents.map((agent, idx) => (
          <React.Fragment key={idx}>
            <div className={`relative z-10 flex flex-col items-center justify-center p-3 w-28 h-28 md:w-32 md:h-32 rounded-xl border-2 transition-all duration-500 ${getStatusStyle(idx)}`}>
              <div className="mb-2">
                {agent.icon}
              </div>
              <div className="text-white font-medium text-xs md:text-sm text-center">{agent.name}</div>
              <div className="text-[#94a3b8] text-[9px] md:text-[10px] text-center mt-1 leading-tight">{agent.detail}</div>
              
              {animState === idx && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-ping"></div>
              )}
            </div>
            
            {/* Connector Line */}
            {idx < agents.length - 1 && (
              <div className="flex-1 h-1 bg-[#2d3748] relative overflow-hidden min-w-[20px]">
                <div className={`absolute top-0 left-0 h-full ${getLineStyle(idx)} w-full`}></div>
              </div>
            )}
          </React.Fragment>
        ))}

        {/* Final Connector to Decision Gateway */}
        <div className="flex-1 h-1 bg-[#2d3748] relative overflow-hidden min-w-[20px]">
          <div className={`absolute top-0 left-0 h-full ${getLineStyle(4)} w-full`}></div>
        </div>

        {/* Final Decision Gateway Output Node */}
        <div className={`relative z-10 flex flex-col items-center justify-center p-3 w-36 h-28 md:w-40 md:h-32 rounded-xl border-2 transition-all duration-500 ${
          animState >= 5 ? (animState === 6 ? 'border-amber-500/70 bg-amber-500/15' : 'border-emerald-500/70 bg-emerald-500/15') : 'border-[#2d3748] bg-[#0a0f1c] opacity-50'
        }`}>
          {animState >= 5 ? (
            animState === 6 ? (
              <>
                <AlertTriangle className="text-amber-400 mb-1" size={24} />
                <div className="text-white font-medium text-xs md:text-sm text-center">HITL Approval</div>
                <div className="text-amber-300 text-[10px] mt-0.5 font-mono">Teams Alert (Risk 0.85)</div>
              </>
            ) : (
              <>
                <CheckCircle2 className="text-emerald-400 mb-1" size={24} />
                <div className="text-white font-medium text-xs md:text-sm text-center">Auto-Executed</div>
                <div className="text-emerald-300 text-[10px] mt-0.5 font-mono">Functions API (Risk 0.25)</div>
              </>
            )
          ) : (
            <>
              <div className="w-6 h-6 rounded-full border-2 border-dashed border-[#475569] animate-spin mb-1.5"></div>
              <div className="text-[#94a3b8] font-medium text-xs">Awaiting Output...</div>
            </>
          )}
        </div>
      </div>
      
      <div className="mt-4 p-3 bg-[#0a0f1c] border border-[#2d3748] rounded-lg text-xs font-mono text-[#94a3b8] flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>PII SHIELD: <span className="text-emerald-400">Active</span> (IBAN, SSN, Contact Data Tokenized)</span>
        </div>
        <div className="text-blue-400">Avg Latency: 420ms | Security Score: 100%</div>
      </div>
    </div>
  );
}
