'use client';

import React, { useState } from 'react';
import { 
  Activity, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Terminal, 
  Server, 
  Zap, 
  Cloud, 
  Cpu, 
  RefreshCw, 
  Bell, 
  Check, 
  ExternalLink 
} from 'lucide-react';

interface LogItem {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  service: string;
  logger: string;
  message: string;
  trace_id: string;
}

interface AlertItem {
  id: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  category: string;
  title: string;
  description: string;
  component: string;
  metric: string;
  threshold: string;
  trace_id: string;
  created_at: string;
  resolved: boolean;
}

export default function ObservabilityDashboard() {
  const [selectedLogLevel, setSelectedLogLevel] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'metrics' | 'logs' | 'alerts'>('metrics');
  const [isTriggeringAlert, setIsTriggeringAlert] = useState(false);
  const [alertSuccessMessage, setAlertSuccessMessage] = useState<string | null>(null);

  // Live Simulated Structured Logs (OpenTelemetry W3C Traced)
  const [logs, setLogs] = useState<LogItem[]>([
    {
      id: 'log-001',
      timestamp: '07:44:12.891 UTC',
      level: 'INFO',
      service: 'mailmind-backend',
      logger: 'orbit.agents.orchestrator',
      message: 'Incoming M365 email received. W3C traceparent propagated: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736'
    },
    {
      id: 'log-002',
      timestamp: '07:44:12.894 UTC',
      level: 'INFO',
      service: 'mailmind-backend',
      logger: 'orbit.guardrails',
      message: 'PII Shield: 3 client tokens anonymized in 2.1ms (IBAN, SSN, Account). ISIN US0378331005 preserved.',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736'
    },
    {
      id: 'log-003',
      timestamp: '07:44:13.412 UTC',
      level: 'INFO',
      service: 'mailmind-backend',
      logger: 'orbit.agents.classifier',
      message: 'Classifier Agent completed intent determination (SETTLEMENT, confidence 0.98, latency 518ms).',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736'
    },
    {
      id: 'log-004',
      timestamp: '07:44:14.205 UTC',
      level: 'INFO',
      service: 'mailmind-backend',
      logger: 'orbit.resilience',
      message: 'Azure AI Search RAG SOP query verified (SOP-SET-003, latency 48ms, status: HEALTHY).',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736'
    },
    {
      id: 'log-005',
      timestamp: '07:44:14.980 UTC',
      level: 'WARNING',
      service: 'mailmind-backend',
      logger: 'orbit.agents.risk_scorer',
      message: 'High financial exposure detected (€2.4M > €1M threshold). Escalating to HITL Teams channel.',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736'
    },
    {
      id: 'log-006',
      timestamp: '07:44:15.012 UTC',
      level: 'INFO',
      service: 'mailmind-backend',
      logger: 'orbit.services.cosmos',
      message: 'Cosmos DB audit record committed to container "audittrail" (Trace: 4bf92f3577b34da6a3ce929d0e0e4736).',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736'
    }
  ]);

  // System SRE Alerts
  const [alerts, setAlerts] = useState<AlertItem[]>([
    {
      id: 'ALT-2026-1001',
      severity: 'WARNING',
      category: 'SLA_BREACH',
      title: 'P99 Latency Spike Warning (> 4000ms)',
      description: 'Cold start LLM fallback exceeded 3500ms budget during burst ingestion.',
      component: 'AzureOpenAI (Cognitive Services)',
      metric: '4340 ms',
      threshold: '2500 ms',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
      created_at: '10 mins ago',
      resolved: true,
    },
    {
      id: 'ALT-2026-1002',
      severity: 'INFO',
      category: 'CIRCUIT_BREAKER',
      title: 'Circuit Breaker Auto-Reset to CLOSED',
      description: 'Azure AI Search circuit breaker completed probe in HALF-OPEN state and recovered to CLOSED.',
      component: 'AzureAISearch (mailmind-search-3207)',
      metric: 'Probe OK',
      threshold: 'Fast-Fail',
      trace_id: '8a3c2e1f4b5d6a7e8f9a0b1c2d3e4f5a',
      created_at: '25 mins ago',
      resolved: true,
    },
    {
      id: 'ALT-2026-1003',
      severity: 'CRITICAL',
      category: 'SECURITY_ANOMALY',
      title: 'Prompt Injection Attack Quarantined',
      description: 'Instruction override attack isolated into Dead Letter Queue (DLQ). Zero trade corruption.',
      component: 'PIIGuardrailShield',
      metric: 'Threat: 1.0',
      threshold: '0.70',
      trace_id: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c',
      created_at: '42 mins ago',
      resolved: true,
    }
  ]);

  const handleSimulateAlert = () => {
    setIsTriggeringAlert(true);
    setTimeout(() => {
      const newAlert: AlertItem = {
        id: `ALT-2026-${Math.floor(1000 + Math.random() * 9000)}`,
        severity: 'WARNING',
        category: 'SLA_BREACH',
        title: 'Burst Ingestion Latency Probe Triggered',
        description: 'Simulated high-frequency traffic probe tested against SRE alerting webhook.',
        component: 'AzureOpenAI / IngestionGateway',
        metric: '3820 ms',
        threshold: '2500 ms',
        trace_id: '7b2a9c1e4f6d8a0b3c5e7f9a1b3d5e7f',
        created_at: 'Just now',
        resolved: false,
      };
      setAlerts([newAlert, ...alerts]);
      setIsTriggeringAlert(false);
      setAlertSuccessMessage(`Alert ${newAlert.id} dispatched to MS Teams & Azure Monitor!`);
      setTimeout(() => setAlertSuccessMessage(null), 4000);
    }, 600);
  };

  const filteredLogs = logs.filter(log => {
    const matchesLevel = selectedLogLevel === 'ALL' || log.level === selectedLogLevel;
    const matchesQuery = !searchQuery || 
      log.message.toLowerCase().includes(searchQuery.toLowerCase()) || 
      log.trace_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.logger.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesQuery;
  });

  return (
    <div id="observability" className="bg-[#1a2332] rounded-xl border border-[#2d3748] p-6 shadow-xl mb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#2d3748]">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="text-blue-400" size={22} />
            <h2 className="text-xl font-bold text-white tracking-tight">System Health & SRE Observability</h2>
            <span className="bg-emerald-500/20 text-emerald-400 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Telemetry
            </span>
          </div>
          <p className="text-sm text-[#94a3b8] mt-1">
            OpenTelemetry W3C distributed tracing, Azure Application Insights streaming & SRE alerting engine
          </p>
        </div>

        {/* Azure Monitor Live Link */}
        <div className="flex items-center gap-3">
          <div className="bg-[#111827] px-3.5 py-2 rounded-lg border border-[#2d3748] text-xs">
            <div className="flex items-center gap-2 text-slate-300">
              <Cloud size={14} className="text-blue-400" />
              <span>Azure App Insights:</span>
              <span className="font-mono text-cyan-400 font-semibold">orbit-insights-3207</span>
            </div>
          </div>

          <button
            onClick={handleSimulateAlert}
            disabled={isTriggeringAlert}
            className="flex items-center gap-2 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition-all shadow-md active:scale-95 disabled:opacity-50"
          >
            <Bell size={14} />
            {isTriggeringAlert ? 'Dispatching...' : 'Test SRE Alert'}
          </button>
        </div>
      </div>

      {alertSuccessMessage && (
        <div className="mt-4 p-3 bg-emerald-950/60 border border-emerald-500/40 rounded-lg flex items-center gap-2 text-xs text-emerald-300 animate-fadeIn">
          <Check size={14} className="text-emerald-400" />
          <span>{alertSuccessMessage}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 mt-6 border-b border-[#2d3748] pb-3">
        <button
          onClick={() => setActiveTab('metrics')}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'metrics'
              ? 'bg-blue-600 text-white shadow'
              : 'text-[#94a3b8] hover:text-white hover:bg-[#111827]'
          }`}
        >
          SRE Health KPIs & Circuit Breakers
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
            activeTab === 'logs'
              ? 'bg-blue-600 text-white shadow'
              : 'text-[#94a3b8] hover:text-white hover:bg-[#111827]'
          }`}
        >
          <Terminal size={13} />
          Structured Log Stream
          <span className="bg-[#111827] text-slate-400 text-[10px] px-1.5 py-0.2 rounded-full">
            {logs.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
            activeTab === 'alerts'
              ? 'bg-blue-600 text-white shadow'
              : 'text-[#94a3b8] hover:text-white hover:bg-[#111827]'
          }`}
        >
          <ShieldAlert size={13} />
          Alerting Center
          <span className="bg-amber-500/20 text-amber-300 text-[10px] px-1.5 py-0.2 rounded-full border border-amber-500/30">
            {alerts.length}
          </span>
        </button>
      </div>

      {/* TAB 1: SRE Health KPIs & Circuit Breakers */}
      {activeTab === 'metrics' && (
        <div className="mt-6 space-y-6">
          {/* Top KPI Metrics Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#111827] p-4 rounded-xl border border-[#2d3748]">
              <div className="flex items-center justify-between text-[#94a3b8] text-xs">
                <span>System Uptime</span>
                <Server size={14} className="text-emerald-400" />
              </div>
              <div className="text-xl font-bold text-white mt-1">99.99%</div>
              <div className="text-[11px] text-emerald-400 mt-0.5">86,400s continuous session</div>
            </div>

            <div className="bg-[#111827] p-4 rounded-xl border border-[#2d3748]">
              <div className="flex items-center justify-between text-[#94a3b8] text-xs">
                <span>STP Autonomous Rate</span>
                <Zap size={14} className="text-blue-400" />
              </div>
              <div className="text-xl font-bold text-white mt-1">65.0%</div>
              <div className="text-[11px] text-blue-400 mt-0.5">13/20 auto-settled</div>
            </div>

            <div className="bg-[#111827] p-4 rounded-xl border border-[#2d3748]">
              <div className="flex items-center justify-between text-[#94a3b8] text-xs">
                <span>P90 End-to-End Latency</span>
                <Activity size={14} className="text-cyan-400" />
              </div>
              <div className="text-xl font-bold text-white mt-1">1,150 ms</div>
              <div className="text-[11px] text-cyan-400 mt-0.5">P50: 420ms | P99: 2.34s</div>
            </div>

            <div className="bg-[#111827] p-4 rounded-xl border border-[#2d3748]">
              <div className="flex items-center justify-between text-[#94a3b8] text-xs">
                <span>PII Guardrail Overhead</span>
                <CheckCircle2 size={14} className="text-emerald-400" />
              </div>
              <div className="text-xl font-bold text-white mt-1">&lt; 2.5 ms</div>
              <div className="text-[11px] text-emerald-400 mt-0.5">Zero LLM latency impact</div>
            </div>
          </div>

          {/* Circuit Breakers & Health Probes Matrix */}
          <div>
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Cloud Service Circuit Breakers & Dependency Probes
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* OpenAI */}
              <div className="bg-[#111827] p-4 rounded-xl border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">Azure OpenAI (GPT-4o)</span>
                  <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">
                    CLOSED
                  </span>
                </div>
                <div className="mt-3 space-y-1 text-[11px] text-[#94a3b8]">
                  <div className="flex justify-between"><span>Failures:</span><span className="text-white font-mono">0 / 3</span></div>
                  <div className="flex justify-between"><span>Fallback:</span><span className="text-emerald-400 font-semibold">Domain Engine</span></div>
                  <div className="flex justify-between"><span>Timeout Budget:</span><span className="text-white font-mono">3,500 ms</span></div>
                </div>
              </div>

              {/* AI Search */}
              <div className="bg-[#111827] p-4 rounded-xl border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">Azure AI Search</span>
                  <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">
                    CLOSED
                  </span>
                </div>
                <div className="mt-3 space-y-1 text-[11px] text-[#94a3b8]">
                  <div className="flex justify-between"><span>Probe Latency:</span><span className="text-white font-mono">48 ms</span></div>
                  <div className="flex justify-between"><span>SOP Runbooks:</span><span className="text-white font-mono">5 Active</span></div>
                  <div className="flex justify-between"><span>Health:</span><span className="text-emerald-400 font-semibold">Healthy</span></div>
                </div>
              </div>

              {/* Cosmos DB */}
              <div className="bg-[#111827] p-4 rounded-xl border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">Azure Cosmos DB</span>
                  <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">
                    CLOSED
                  </span>
                </div>
                <div className="mt-3 space-y-1 text-[11px] text-[#94a3b8]">
                  <div className="flex justify-between"><span>Consistency:</span><span className="text-white font-mono">Session</span></div>
                  <div className="flex justify-between"><span>Containers:</span><span className="text-white font-mono">emails, audit</span></div>
                  <div className="flex justify-between"><span>Failover:</span><span className="text-emerald-400 font-semibold">Local Resilience</span></div>
                </div>
              </div>

              {/* Key Vault */}
              <div className="bg-[#111827] p-4 rounded-xl border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">Azure Key Vault</span>
                  <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">
                    CLOSED
                  </span>
                </div>
                <div className="mt-3 space-y-1 text-[11px] text-[#94a3b8]">
                  <div className="flex justify-between"><span>Auth Mode:</span><span className="text-white font-mono">RBAC Officer</span></div>
                  <div className="flex justify-between"><span>Cached Secrets:</span><span className="text-white font-mono">9 Synced</span></div>
                  <div className="flex justify-between"><span>Zero-Trust:</span><span className="text-emerald-400 font-semibold">Verified</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Structured Log Stream */}
      {activeTab === 'logs' && (
        <div className="mt-6 space-y-4">
          <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Level Filter:</span>
              {['ALL', 'INFO', 'WARNING', 'ERROR'].map(lvl => (
                <button
                  key={lvl}
                  onClick={() => setSelectedLogLevel(lvl)}
                  className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
                    selectedLogLevel === lvl
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'bg-[#111827] text-slate-400 hover:text-white border border-[#2d3748]'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>

            <input
              type="text"
              placeholder="Search logs by message, logger, or trace ID..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full md:w-80 bg-[#111827] border border-[#2d3748] rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>

          <div className="bg-[#0b0f19] border border-[#2d3748] rounded-xl p-4 font-mono text-xs overflow-x-auto space-y-2 max-h-[380px] overflow-y-auto">
            {filteredLogs.map(log => (
              <div key={log.id} className="p-2 rounded hover:bg-[#1e293b]/50 transition-colors border-l-2 border-slate-700">
                <div className="flex items-center gap-2 text-[11px] text-slate-400 mb-0.5">
                  <span className="text-slate-500">{log.timestamp}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                    log.level === 'INFO' ? 'bg-blue-500/20 text-blue-400' :
                    log.level === 'WARNING' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {log.level}
                  </span>
                  <span className="text-purple-400 font-semibold">[{log.logger}]</span>
                  <span className="text-cyan-400/80 text-[10px]">Trace: {log.trace_id.substring(0, 8)}...</span>
                </div>
                <div className="text-slate-200 text-xs pl-2">{log.message}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: Alerting Center */}
      {activeTab === 'alerts' && (
        <div className="mt-6 space-y-4">
          <div className="grid grid-cols-1 gap-3">
            {alerts.map(alt => (
              <div 
                key={alt.id}
                className="bg-[#111827] p-4 rounded-xl border border-[#2d3748] flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg mt-0.5 ${
                    alt.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                    alt.severity === 'WARNING' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                    'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  }`}>
                    <AlertTriangle size={18} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-white">{alt.title}</h4>
                      <span className="text-[10px] font-mono bg-[#1e293b] text-slate-400 px-2 py-0.5 rounded">
                        {alt.id}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{alt.description}</p>
                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 mt-2 font-mono">
                      <span>Component: <strong className="text-slate-300">{alt.component}</strong></span>
                      <span>Metric: <strong className="text-amber-400">{alt.metric}</strong></span>
                      <span>Threshold: <strong className="text-slate-400">{alt.threshold}</strong></span>
                    </div>
                  </div>
                </div>

                <div className="flex md:flex-col items-center md:items-end justify-between gap-2 border-t md:border-t-0 pt-2 md:pt-0 border-[#2d3748]">
                  <span className="text-[11px] text-slate-400">{alt.created_at}</span>
                  <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full ${
                    alt.resolved ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}>
                    {alt.resolved ? 'RESOLVED' : 'ACTIVE'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
