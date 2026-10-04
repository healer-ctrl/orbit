'use client';

import React, { useState } from 'react';
import StatsCards from '@/components/StatsCards';
import EmailFeed from '@/components/EmailFeed';
import RiskGauge from '@/components/RiskGauge';
import ApprovalQueue from '@/components/ApprovalQueue';
import AgentPipeline from '@/components/AgentPipeline';
import DemoButton from '@/components/DemoButton';
import AuditTrail from '@/components/AuditTrail';
import EmailDetailModal from '@/components/EmailDetailModal';
import DailyOpsReport from '@/components/DailyOpsReport';
import SOPBrowser from '@/components/SOPBrowser';
import GuardrailPlayground from '@/components/GuardrailPlayground';
import { INITIAL_EMAILS, ProcessedEmailRecord } from '@/lib/demoData';
import { Layers, ShieldCheck, BarChart3, BookOpen, FileSearch, Inbox, CheckCircle2 } from 'lucide-react';

export default function Home() {
  const [emails, setEmails] = useState<ProcessedEmailRecord[]>(INITIAL_EMAILS);
  const [selectedEmail, setSelectedEmail] = useState<ProcessedEmailRecord | null>(null);
  const [activeTab, setActiveTab] = useState<'hub' | 'guardrails' | 'daily' | 'sops' | 'audit'>('hub');
  const [isSimulating, setIsSimulating] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleApprove = (id: string) => {
    setEmails((prev) =>
      prev.map((e) =>
        e.id === id
          ? {
              ...e,
              status: 'APPROVED',
              requiresApproval: false,
              executionResult: {
                ...e.executionResult,
                message: 'Approved by Supervisor (HITL). Auto-dispatched to execution gateway.',
                timestamp: new Date().toISOString(),
              },
            }
          : e
      )
    );
    showToast(`✅ Email ${id} Approved by Supervisor! Action dispatched to Azure Functions.`);
  };

  const handleReject = (id: string) => {
    setEmails((prev) =>
      prev.map((e) =>
        e.id === id
          ? {
              ...e,
              status: 'REJECTED',
              requiresApproval: false,
              executionResult: {
                ...e.executionResult,
                message: 'Rejected by Supervisor. Escalation ticket logged in ServiceNow ITSM.',
                timestamp: new Date().toISOString(),
              },
            }
          : e
      )
    );
    showToast(`❌ Email ${id} Rejected. Escalation incident created in ServiceNow.`);
  };

  const handleTriggerDemo = () => {
    setIsSimulating(true);
    showToast('🚀 Running Live Multi-Agent Pipeline simulation across 5 test scenarios...');
    
    // Simulate real-time streaming updates
    setTimeout(() => {
      setEmails(INITIAL_EMAILS);
      setIsSimulating(false);
      showToast('✨ Simulation completed! 5 emails classified, PII sanitized, and Cosmos DB synced.');
    }, 2000);
  };

  const pendingEmails = emails.filter((e) => e.status === 'PENDING_APPROVAL');
  const avgRisk = emails.reduce((acc, curr) => acc + curr.riskScore, 0) / emails.length;

  return (
    <div className="space-y-8 pb-16 animate-fadeIn">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 bg-[#131d35] border border-sky-500/50 text-sky-200 px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 animate-slideDown backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span>
          <span className="text-xs font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* Top Level KPIs */}
      <StatsCards emails={emails} />

      {/* Section Navigation Tabs */}
      <div className="flex border-b border-[#1e293b] gap-2 overflow-x-auto pb-1">
        <button
          onClick={() => setActiveTab('hub')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all ${
            activeTab === 'hub'
              ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-[#131d35]'
          }`}
        >
          <Inbox size={16} /> Operations Hub & Pipeline
        </button>

        <button
          onClick={() => setActiveTab('guardrails')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all ${
            activeTab === 'guardrails'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-[#131d35]'
          }`}
        >
          <ShieldCheck size={16} /> 🛡️ PII & Security Playground
        </button>

        <button
          onClick={() => setActiveTab('daily')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all ${
            activeTab === 'daily'
              ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-[#131d35]'
          }`}
        >
          <BarChart3 size={16} /> 📊 Executive Daily STP Report
        </button>

        <button
          onClick={() => setActiveTab('sops')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all ${
            activeTab === 'sops'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-[#131d35]'
          }`}
        >
          <BookOpen size={16} /> 📖 SOP Knowledge Runbooks
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all ${
            activeTab === 'audit'
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-[#131d35]'
          }`}
        >
          <FileSearch size={16} /> 📑 Compliance Audit Ledger
        </button>
      </div>

      {/* TAB 1: OPERATIONS HUB */}
      {activeTab === 'hub' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Main 2-Column Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Email Feed (2 Cols) */}
            <div className="lg:col-span-2">
              <EmailFeed 
                emails={emails} 
                onSelectEmail={(e) => setSelectedEmail(e)} 
              />
            </div>

            {/* Right: Risk Meter & Approval Queue (1 Col) */}
            <div className="lg:col-span-1 flex flex-col gap-6">
              <RiskGauge score={avgRisk} />
              <ApprovalQueue 
                pendingEmails={pendingEmails} 
                onSelectEmail={(e) => setSelectedEmail(e)}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            </div>
          </div>

          {/* Multi-Agent Animated Pipeline */}
          <AgentPipeline />

          {/* Inline Compliance Table */}
          <AuditTrail 
            emails={emails} 
            onSelectEmail={(e) => setSelectedEmail(e)} 
          />
        </div>
      )}

      {/* TAB 2: PII GUARDRAIL PLAYGROUND */}
      {activeTab === 'guardrails' && (
        <div className="animate-fadeIn">
          <GuardrailPlayground />
        </div>
      )}

      {/* TAB 3: DAILY OPS REPORT */}
      {activeTab === 'daily' && (
        <div className="animate-fadeIn">
          <DailyOpsReport />
        </div>
      )}

      {/* TAB 4: SOP RUNBOOKS */}
      {activeTab === 'sops' && (
        <div className="animate-fadeIn">
          <SOPBrowser />
        </div>
      )}

      {/* TAB 5: AUDIT LEDGER */}
      {activeTab === 'audit' && (
        <div className="animate-fadeIn">
          <AuditTrail 
            emails={emails} 
            onSelectEmail={(e) => setSelectedEmail(e)} 
          />
        </div>
      )}

      {/* Floating Simulation Trigger Button */}
      <DemoButton 
        isRunning={isSimulating} 
        onTriggerDemo={handleTriggerDemo} 
      />

      {/* Interactive Detail & Diff Modal */}
      <EmailDetailModal 
        email={selectedEmail} 
        onClose={() => setSelectedEmail(null)}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </div>
  );
}
