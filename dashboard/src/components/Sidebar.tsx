'use client';

import React from 'react';
import { 
  Inbox, 
  Cpu, 
  CheckSquare, 
  FileSearch, 
  Settings, 
  ShieldCheck, 
  Layers, 
  Send,
  Cloud 
} from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="w-64 bg-[#111827] border-r border-[#2d3748] flex flex-col h-screen fixed left-0 top-0 z-30">
      {/* Brand Header */}
      <div className="p-6 border-b border-[#2d3748]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/30">
            🧠
          </div>
          <div>
            <h1 className="text-white font-bold text-lg tracking-tight">MailMind</h1>
            <p className="text-[11px] text-[#94a3b8] font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
              Société Générale
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
        <a href="#overview" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg bg-blue-600/15 border-l-4 border-blue-500 text-white font-medium text-sm transition-colors">
          <Inbox size={18} className="text-blue-400" />
          <span>Email Ingestion</span>
        </a>
        <a href="#pipeline" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[#94a3b8] hover:text-white hover:bg-[#1a2332] font-medium text-sm transition-colors">
          <Cpu size={18} />
          <span>Agent Pipeline</span>
        </a>
        <a href="#hitl" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[#94a3b8] hover:text-white hover:bg-[#1a2332] font-medium text-sm transition-colors">
          <CheckSquare size={18} />
          <span>HITL Approvals</span>
        </a>
        <a href="#copilot" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sky-300 hover:text-white hover:bg-sky-500/10 font-medium text-sm transition-colors border border-sky-500/20">
          <span className="text-base">🤖</span>
          <div className="flex-1 flex items-center justify-between">
            <span>AI Copilot</span>
            <span className="text-[10px] bg-sky-500/20 text-sky-300 px-1.5 py-0.5 rounded font-mono font-bold">GPT-4o</span>
          </div>
        </a>
        <a href="#guardrails" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[#94a3b8] hover:text-white hover:bg-[#1a2332] font-medium text-sm transition-colors">
          <ShieldCheck size={18} className="text-emerald-400" />
          <span>PII & Guardrails</span>
        </a>
        <a href="#audit" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[#94a3b8] hover:text-white hover:bg-[#1a2332] font-medium text-sm transition-colors">
          <FileSearch size={18} />
          <span>Audit Trail</span>
        </a>
        <a href="#azure" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[#94a3b8] hover:text-white hover:bg-[#1a2332] font-medium text-sm transition-colors">
          <Cloud size={18} className="text-cyan-400" />
          <span>Azure Services</span>
        </a>
      </nav>

      {/* Outlook & Cloud Status Indicators */}
      <div className="p-4 border-t border-[#2d3748] space-y-3 bg-[#0a0f1c]/50">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#94a3b8] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Outlook Graph API
          </span>
          <span className="text-emerald-400 font-mono">Connected</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#94a3b8] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            Azure Cosmos DB
          </span>
          <span className="text-blue-400 font-mono">Active</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#94a3b8] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-500"></span>
            Teams Webhook
          </span>
          <span className="text-purple-400 font-mono">Ready</span>
        </div>
      </div>
    </aside>
  );
}
