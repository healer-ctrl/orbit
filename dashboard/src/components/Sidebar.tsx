'use client';

import React, { useState, useEffect } from 'react';
import { 
  Inbox, 
  Cpu, 
  CheckSquare, 
  FileSearch, 
  ShieldCheck, 
  Cloud, 
  Activity,
  BarChart3,
  BookOpen
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  tab: string;
  sectionId?: string;
  icon: React.ReactNode;
  color: string;
}

const NAV_ITEMS = [
  { id: 'overview', label: 'Email Ingestion', tab: 'hub', sectionId: 'overview', icon: <Inbox size={18} />, color: 'text-blue-400' },
  { id: 'pipeline', label: 'Agent Pipeline', tab: 'hub', sectionId: 'pipeline', icon: <Cpu size={18} />, color: 'text-indigo-400' },
  { id: 'hitl', label: 'HITL Approvals', tab: 'hub', sectionId: 'hitl', icon: <CheckSquare size={18} />, color: 'text-amber-400' },
  { id: 'apihub', label: 'OpenAPI / Swagger Hub', tab: 'apihub', sectionId: 'apihub', icon: <FileSearch size={18} />, color: 'text-amber-400' },
  { id: 'guardrails', label: 'PII & Guardrails', tab: 'guardrails', sectionId: 'guardrails', icon: <ShieldCheck size={18} />, color: 'text-emerald-400' },
  { id: 'daily', label: 'Daily Ops Report', tab: 'daily', sectionId: 'daily', icon: <BarChart3 size={18} />, color: 'text-indigo-400' },
  { id: 'sops', label: 'SOP Runbooks', tab: 'sops', sectionId: 'sops', icon: <BookOpen size={18} />, color: 'text-purple-400' },
  { id: 'audit', label: 'Audit Trail', tab: 'audit', sectionId: 'audit', icon: <FileSearch size={18} />, color: 'text-amber-400' },
  { id: 'observability', label: 'SRE Observability', tab: 'observability', sectionId: 'observability', icon: <Activity size={18} />, color: 'text-cyan-400' },
];

export default function Sidebar() {
  const [activeNav, setActiveNav] = useState<string>('overview');

  useEffect(() => {
    const handleTabChange = (e: any) => {
      if (e.detail?.tab) {
        const matching = NAV_ITEMS.find(item => item.tab === e.detail.tab);
        if (matching) {
          setActiveNav(matching.id);
        }
      }
    };
    window.addEventListener('orbit:tab-changed', handleTabChange);
    return () => window.removeEventListener('orbit:tab-changed', handleTabChange);
  }, []);

  const handleNavClick = (item: typeof NAV_ITEMS[0]) => {
    setActiveNav(item.id);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('orbit:navigate', {
          detail: { tab: item.tab, sectionId: item.sectionId }
        })
      );
    }
  };

  return (
    <aside className="w-64 bg-[#111827] border-r border-[#2d3748] flex flex-col h-screen fixed left-0 top-0 z-30">
      {/* Brand Header */}
      <div className="p-6 border-b border-[#2d3748]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/30">
            🧠
          </div>
          <div>
            <h1 className="text-white font-bold text-lg tracking-tight">Orbit</h1>
            <p className="text-[11px] text-[#94a3b8] font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
              Société Générale
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = activeNav === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all text-left ${
                isActive
                  ? 'bg-blue-600/15 border-l-4 border-blue-500 text-white shadow-sm'
                  : 'text-[#94a3b8] hover:text-white hover:bg-[#1a2332]'
              }`}
            >
              <span className={isActive ? item.color : 'text-slate-400'}>
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          );
        })}
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
