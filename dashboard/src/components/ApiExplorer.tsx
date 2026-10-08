'use client';

import React, { useState } from 'react';
import { 
  Code2, 
  Play, 
  Copy, 
  Check, 
  ExternalLink, 
  Layers, 
  Search, 
  TrendingUp, 
  DollarSign, 
  ShieldAlert, 
  BarChart3, 
  Cpu, 
  FileCode2 
} from 'lucide-react';

interface EndpointDef {
  id: string;
  category: string;
  method: 'GET' | 'POST' | 'PATCH';
  path: string;
  title: string;
  description: string;
  samplePayload?: any;
  defaultResponse: any;
}

const API_ENDPOINTS: EndpointDef[] = [
  {
    id: 'linkage-create',
    category: '1. Trade Linkage',
    method: 'POST',
    path: '/api/v1/linkage/create',
    title: 'Create Trade-to-Galaxy Linkage',
    description: 'Allocates front-office block trades to a Société Générale Galaxy ID and trading desk book.',
    samplePayload: {
      trade_id: 'TRD-2026-88712',
      isin: 'US0378331005',
      cusip: '037833100',
      desk_book: 'EQ-US-FLOW',
      amount: 1500000.0,
      currency: 'USD',
      counterparty: 'Apple Inc / Morgan Stanley'
    },
    defaultResponse: {
      status: 'success',
      message: 'Linkage successfully created and verified in Front-Office Booking Feeder',
      galaxy_id: 'SG828282',
      timestamp: new Date().toISOString(),
      details: {
        trade_id: 'TRD-2026-88712',
        isin: 'US0378331005',
        allocated_book: 'EQ-US-FLOW',
        amount: 1500000.0,
        currency: 'USD',
        settlement_status: 'MATCHED',
        allocation_state: 'LINKED_CONFIRMED'
      }
    }
  },
  {
    id: 'linkage-verify',
    category: '1. Trade Linkage',
    method: 'POST',
    path: '/api/v1/linkage/verify',
    title: 'Verify Settlement Status',
    description: 'Validates TARGET2 / Euroclear settlement status for a linked Galaxy ID.',
    samplePayload: {
      galaxy_id: 'SG828282',
      settlement_system: 'TARGET2'
    },
    defaultResponse: {
      status: 'success',
      message: 'Galaxy linkage SG828282 successfully verified against TARGET2',
      galaxy_id: 'SG828282',
      timestamp: new Date().toISOString(),
      details: {
        matching_status: 'AFFIRMED',
        settlement_system: 'TARGET2',
        clearing_account: 'COBADEFF-7729104',
        swift_message_type: 'MT544'
      }
    }
  },
  {
    id: 'eliot-resolve',
    category: '2. ELIOT System Failures',
    method: 'POST',
    path: '/api/v1/eliot/resolve-failure',
    title: 'Resolve ELIOT Matching Break',
    description: 'Auto-remediates front-to-back ELIOT trade exceptions, overrides SSI mappings, and resubmits to matching engine.',
    samplePayload: {
      trade_id: 'TRD-ELIOT-99214',
      exception_code: 'ELIOT_MATCH_BREAK_404',
      corrected_ssi_bic: 'CHASUS33XXX',
      resubmit_now: true
    },
    defaultResponse: {
      status: 'success',
      message: 'ELIOT trade booking failure remediated and resubmitted',
      trade_id: 'TRD-ELIOT-99214',
      eliot_ticket_id: 'ELIOT-TKT-881920',
      timestamp: new Date().toISOString(),
      details: {
        exception_code: 'ELIOT_MATCH_BREAK_404',
        resolution_action: 'SSI_OVERRIDE_AND_FORCE_MATCH',
        patched_bic: 'CHASUS33XXX',
        resubmitted: true,
        eliot_engine_state: 'PROCESSING_ACK'
      }
    }
  },
  {
    id: 'eliot-unmatched',
    category: '2. ELIOT System Failures',
    method: 'GET',
    path: '/api/v1/eliot/unmatched-trades',
    title: 'List Unmatched ELIOT Trades',
    description: 'Queries unbooked trades in the ELIOT trading queue with SLA countdowns.',
    defaultResponse: {
      status: 'success',
      queue_name: 'ELIOT_GLOBAL_UNMATCHED_EXCEPTIONS',
      total_unmatched: 3,
      unmatched_trades: [
        { trade_id: 'TRD-ELIOT-99214', counterparty: 'JPMorgan Chase', amount: 2450000, currency: 'USD', severity: 'HIGH', cutoff_mins: 45 },
        { trade_id: 'TRD-ELIOT-88120', counterparty: 'BNP Paribas', amount: 1200000, currency: 'EUR', severity: 'MEDIUM', cutoff_mins: 120 }
      ]
    }
  },
  {
    id: 'cf-reconcile',
    category: '3. Cash Flow (CF) Issues',
    method: 'POST',
    path: '/api/v1/cf-issue/reconcile',
    title: 'Reconcile Cash Flow Entitlements',
    description: 'Reconciles internal dividend entitlements vs external Nostro settled amounts.',
    samplePayload: {
      clearing_account: 'ACC: 884729104829',
      expected_amount: 30800.0,
      settled_amount: 30800.0,
      currency: 'EUR',
      isin: 'DE0007164600'
    },
    defaultResponse: {
      status: 'success',
      message: 'Cash flow reconciliation completed with ZERO variance',
      cash_flow_id: 'CF-REC-881924',
      timestamp: new Date().toISOString(),
      details: {
        variance: 0.0,
        currency: 'EUR',
        reconciliation_status: 'BALANCED'
      }
    }
  },
  {
    id: 'instruments-create',
    category: '4. Instrument Creation',
    method: 'POST',
    path: '/api/v1/instruments/create',
    title: 'Register Master Instrument',
    description: 'Registers new security with ISO 6166 checksum validation and Position Keeper broadcast.',
    samplePayload: {
      isin: 'FR0000120271',
      security_name: 'TotalEnergies SE',
      asset_class: 'EQUITY',
      currency: 'EUR',
      exchange: 'EURONEXT_PARIS',
      sedol: 'B09H070'
    },
    defaultResponse: {
      status: 'success',
      message: 'Instrument successfully registered in Position Keeper & Master Reference Data',
      isin: 'FR0000120271',
      timestamp: new Date().toISOString(),
      details: {
        iso_6166_checksum_valid: true,
        active_status: 'ACTIVE',
        downstream_systems_synced: ['PositionKeeper', 'RiskEngine', 'ELIOT_Feeder']
      }
    }
  },
  {
    id: 'warrants-issue',
    category: '5. Warrants Creation',
    method: 'POST',
    path: '/api/v1/warrants/issue',
    title: 'Issue Structured Warrant',
    description: 'Issues warrant product with strike, knock-out barrier, multiplier, and live Greeks.',
    samplePayload: {
      underlying_isin: 'US0378331005',
      warrant_type: 'CALL',
      strike_price: 220.0,
      barrier_price: 190.0,
      expiry_date: '2026-12-18',
      ratio_multiplier: 0.1,
      currency: 'USD',
      issuer: 'Société Générale Effekten GmbH'
    },
    defaultResponse: {
      status: 'success',
      message: 'Structured warrant successfully created and issued into trading system',
      warrant_id: 'SG-WRNT-99812',
      warrant_isin: 'DE000SG99812',
      timestamp: new Date().toISOString(),
      details: {
        delta: 0.54,
        gamma: 0.012,
        vega: 0.18,
        theta: -0.045,
        termsheet_status: 'ISSUED_CONFIRMED'
      }
    }
  },
  {
    id: 'pricing-quote',
    category: '6. Price Queries',
    method: 'GET',
    path: '/api/v1/pricing/quote/US0378331005',
    title: 'Real-Time Market Quote',
    description: 'Fetches real-time composite bid/ask quote and spread for an instrument.',
    defaultResponse: {
      status: 'success',
      isin: 'US0378331005',
      security_name: 'Apple Inc.',
      bid: 224.50,
      ask: 224.55,
      mid: 224.525,
      currency: 'USD',
      market_source: 'NASDAQ Consolidated Realtime',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'refinancing-rates',
    category: '7. Refinancing Rates',
    method: 'POST',
    path: '/api/v1/refinancing/rates/update',
    title: 'Publish Benchmark Rate Update',
    description: 'Updates central bank benchmark curves (€STR, SOFR, EURIBOR) and internal treasury funding spread.',
    samplePayload: {
      benchmark_code: 'SOFR',
      rate_percent: 5.33,
      effective_date: '2026-10-08',
      spread_bps: 12.5
    },
    defaultResponse: {
      status: 'success',
      message: 'Refinancing rate curve successfully updated and published to trading desks',
      rate_update_id: 'RATE-UPD-99182',
      timestamp: new Date().toISOString(),
      details: {
        benchmark_code: 'SOFR',
        total_all_in_rate: 5.455,
        desks_notified: ['Global_Markets_Treasury', 'Repo_Desk', 'Fixed_Income_Flow']
      }
    }
  },
  {
    id: 'kpi-summary',
    category: '8. KPIs & Metrics',
    method: 'GET',
    path: '/api/v1/kpi/operations-summary',
    title: 'Daily Operations & SRE KPIs',
    description: 'Aggregates STP rate, daily transaction volume, and P99 latency SLA compliance.',
    defaultResponse: {
      status: 'success',
      operational_date: '2026-10-08',
      summary: {
        total_emails_ingested: 12480,
        straight_through_processing_rate: '94.2%',
        high_risk_flagged: 724,
        pii_tokens_sanitized: 36192,
        dead_letter_queue_pending: 0,
        p99_orchestrator_latency_ms: 480.0,
        sla_compliance_rate: '99.98%'
      }
    }
  }
];

export default function ApiExplorer() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointDef>(API_ENDPOINTS[0]);
  const [requestBody, setRequestBody] = useState<string>(
    JSON.stringify(API_ENDPOINTS[0].samplePayload || {}, null, 2)
  );
  const [responseOutput, setResponseOutput] = useState<any>(API_ENDPOINTS[0].defaultResponse);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const handleSelectEndpoint = (ep: EndpointDef) => {
    setSelectedEndpoint(ep);
    setRequestBody(JSON.stringify(ep.samplePayload || {}, null, 2));
    setResponseOutput(ep.defaultResponse);
  };

  const handleExecuteRequest = () => {
    setIsLoading(true);
    setTimeout(() => {
      try {
        const parsed = selectedEndpoint.samplePayload ? JSON.parse(requestBody) : {};
        const simulated = {
          ...selectedEndpoint.defaultResponse,
          timestamp: new Date().toISOString(),
          details: {
            ...(selectedEndpoint.defaultResponse.details || {}),
            ...parsed
          }
        };
        setResponseOutput(simulated);
      } catch {
        setResponseOutput(selectedEndpoint.defaultResponse);
      }
      setIsLoading(false);
    }, 300);
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(responseOutput, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-[#0f172a] via-[#1e1b4b] to-[#0f172a] border border-[#3b82f6]/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-full text-xs font-mono font-semibold">
                OpenAPI 3.1 Standard
              </span>
              <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-mono font-semibold">
                Azure Cloud Native
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <FileCode2 className="text-blue-400" />
              Capital Markets OpenAPI & Action Layer Hub
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Test and execute back-office operations across all 8 Société Générale domain suites directly in the browser.
            </p>
          </div>
          <div className="flex gap-3">
            <a
              href="https://mailmind-functions-3207.azurewebsites.net/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-blue-600/20"
            >
              <ExternalLink size={16} />
              Open Live Swagger UI
            </a>
            <a
              href="https://mailmind-functions-3207.azurewebsites.net/redoc"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-sm font-medium transition-all"
            >
              <ExternalLink size={16} />
              Open ReDoc Spec
            </a>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Endpoints Directory */}
        <div className="lg:col-span-4 space-y-3">
          <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <Layers size={14} className="text-blue-400" />
              Available Domain Actions (8 Suites)
            </h3>
            <div className="space-y-1.5 max-h-[620px] overflow-y-auto pr-1">
              {API_ENDPOINTS.map((ep) => {
                const isSelected = selectedEndpoint.id === ep.id;
                return (
                  <button
                    key={ep.id}
                    onClick={() => handleSelectEndpoint(ep)}
                    className={`w-full text-left p-3 rounded-xl transition-all border ${
                      isSelected
                        ? 'bg-blue-600/15 border-blue-500/50 shadow-md'
                        : 'bg-slate-900/50 border-slate-800 hover:bg-slate-800/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-[11px] font-mono text-slate-400 truncate">{ep.category}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                          ep.method === 'GET'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : ep.method === 'POST'
                            ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {ep.method}
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-white truncate">{ep.title}</div>
                    <div className="text-[11px] font-mono text-slate-400 truncate mt-0.5">{ep.path}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Request & Response Panel */}
        <div className="lg:col-span-8 space-y-6">
          {/* Endpoint Details & Path Card */}
          <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <span className="text-xs font-mono text-blue-400 font-medium">{selectedEndpoint.category}</span>
                <h3 className="text-lg font-bold text-white mt-0.5">{selectedEndpoint.title}</h3>
                <p className="text-slate-400 text-xs mt-1">{selectedEndpoint.description}</p>
              </div>
              <button
                onClick={handleExecuteRequest}
                disabled={isLoading}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold transition-all shadow-lg shadow-blue-600/25 disabled:opacity-50 self-end sm:self-auto"
              >
                <Play size={14} className={isLoading ? 'animate-spin' : ''} />
                {isLoading ? 'Executing...' : 'Execute Request'}
              </button>
            </div>

            {/* Path Banner */}
            <div className="flex items-center gap-3 bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs">
              <span
                className={`px-2.5 py-1 rounded text-xs font-bold ${
                  selectedEndpoint.method === 'GET'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : selectedEndpoint.method === 'POST'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-amber-500/20 text-amber-400'
                }`}
              >
                {selectedEndpoint.method}
              </span>
              <span className="text-slate-300 flex-1 truncate">{selectedEndpoint.path}</span>
            </div>

            {/* Request Body Editor (if POST/PATCH) */}
            {selectedEndpoint.method !== 'GET' && (
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs font-semibold text-slate-400">
                  <span>JSON Request Body</span>
                  <span className="text-[11px] text-slate-500 font-mono">application/json</span>
                </div>
                <textarea
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  rows={6}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-blue-500/50"
                />
              </div>
            )}
          </div>

          {/* Response Inspector */}
          <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-5 space-y-3">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-300">HTTP Response</span>
                <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-[11px] font-mono font-bold">
                  200 OK
                </span>
              </div>
              <button
                onClick={handleCopyJson}
                className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition-all border border-slate-700"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                {copied ? 'Copied!' : 'Copy JSON'}
              </button>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs text-emerald-400 overflow-x-auto max-h-[340px]">
              <pre>{JSON.stringify(responseOutput, null, 2)}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
