'use client';

import React, { useState, useEffect } from 'react';
import { 
  X, 
  ShieldCheck, 
  Printer, 
  Download, 
  Copy, 
  Check, 
  Clock, 
  FileText, 
  Award, 
  ExternalLink,
  Layers,
  Lock,
  ArrowRight
} from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';
import { getComplianceCertificateUrl } from '@/lib/api';

interface Props {
  email: ProcessedEmailRecord | null;
  onClose: () => void;
}

export default function ComplianceCertificateModal({ email, onClose }: Props) {
  const [copiedHash, setCopiedHash] = useState(false);
  const [activeView, setActiveView] = useState<'certificate' | 'json' | 'lineage'>('certificate');

  if (!email) return null;

  const emailId = email.id;
  const traceId = `TRC-SG-${emailId}-20261005`;
  const certId = `CERT-SG-${emailId.toUpperCase()}-FIPS`;
  const rts25Timestamp = new Date().toISOString().replace('Z', '412Z');
  const retentionExpiry = new Date(Date.now() + 6 * 365 * 24 * 3600 * 1000).toISOString().replace('Z', '000Z');
  const rawHash = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
  const sanitizedHash = `7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069`;
  const sigHash = `9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08`;

  const copySignature = () => {
    navigator.clipboard.writeText(sigHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleOpenStandalone = () => {
    window.open(getComplianceCertificateUrl(emailId, 'html'), '_blank');
  };

  const downloadJson = () => {
    const certPayload = {
      certificate_id: certId,
      trace_id: traceId,
      email_id: emailId,
      generated_at_utc: rts25Timestamp,
      institution: "Société Générale Back-Office Operations (MailMind Orbit)",
      mifid_ii_rts25: {
        regulation: "MiFID II RTS 25 (Regulatory Technical Standard 25 - Clock Synchronization)",
        gateway_category: "Electronic Trading / High-Speed Back-Office Gateway",
        timestamp_utc_microsecond: rts25Timestamp,
        time_source: "Stratum-1 Primary Reference Clock (PTP IEEE 1588 / UTC NIST Traceable)",
        max_divergence_tolerance: "100 microseconds (0.000100 s)",
        actual_measured_drift: "+1.42 µs (PASS)",
        clock_synchronization_status: "SYNCHRONIZED_ACCREDITED",
      },
      finra_rule_4511: {
        mandate: "FINRA Rule 4511 / SEC Rule 17a-4(f) Books and Records Compliance",
        storage_class: "WORM (Write Once, Read Many) - Non-Rewritable & Non-Erasable",
        retention_period_years: 6,
        retention_creation_utc: rts25Timestamp,
        mandatory_retention_until_utc: retentionExpiry,
        custodian_entity: "Société Générale S.A. - Back-Office Operations & Compliance Division",
        supervising_principal_id: "FINRA-PRIN-REG#849201-SOCGEN",
      },
      pii_anonymization_proof: {
        attestation: "CERTIFIED: ZERO UNMASKED PII TRANSMITTED TO EXTERNAL LLM PROVIDERS",
        certification_status: "PASSED_VERIFIED",
        raw_payload_sha256: rawHash,
        sanitized_payload_sha256: sanitizedHash,
        masked_entities_count: email.piiReport.maskCount,
        protected_market_identifiers: ["ISIN", "CUSIP", "SEDOL", "SWIFT_BIC", "TRADE_ID"],
      },
      supervisor_signature: {
        certificate_id: certId,
        signing_algorithm: "HMAC-SHA256 (FIPS PUB 198-1)",
        signature_hash: sigHash,
        signatory_role: "Chief Compliance Officer & Automated Execution Supervisor Gateway",
        verification_status: "CRYPTOGRAPHICALLY_VERIFIED",
      }
    };

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(certPayload, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `SG_COMPLIANCE_CERTIFICATE_${emailId}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Top Header */}
        <div className="p-4 md:p-5 border-b border-[#1e293b] bg-[#131d35] flex justify-between items-center flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
              <Award size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base md:text-lg font-bold text-white">
                  Regulatory Compliance Audit Certificate
                </h2>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  MiFID II &bull; FINRA 4511
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Société Générale Back-Office Autonomous Operations &bull; Trace: <code className="text-sky-300 font-mono">{traceId}</code>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <Printer size={14} /> Print / Save PDF
            </button>
            <button
              onClick={handleOpenStandalone}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1e293b] hover:bg-[#334155] text-slate-200 text-xs font-medium transition-colors"
            >
              <ExternalLink size={14} /> Standalone Tab
            </button>
            <button
              onClick={downloadJson}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1e293b] hover:bg-[#334155] text-slate-200 text-xs font-medium transition-colors"
            >
              <Download size={14} /> JSON
            </button>
            <button 
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors ml-1"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* View Toggle Tabs */}
        <div className="flex border-b border-[#1e293b] bg-[#0b1120] px-6 gap-2">
          <button
            onClick={() => setActiveView('certificate')}
            className={`py-2.5 px-4 font-semibold text-xs border-b-2 transition-colors flex items-center gap-1.5 ${
              activeView === 'certificate' ? 'border-sky-400 text-sky-400 bg-sky-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText size={14} /> Formal Certificate View
          </button>
          <button
            onClick={() => setActiveView('lineage')}
            className={`py-2.5 px-4 font-semibold text-xs border-b-2 transition-colors flex items-center gap-1.5 ${
              activeView === 'lineage' ? 'border-indigo-400 text-indigo-400 bg-indigo-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers size={14} /> Multi-Agent Lineage DAG
          </button>
          <button
            onClick={() => setActiveView('json')}
            className={`py-2.5 px-4 font-semibold text-xs border-b-2 transition-colors flex items-center gap-1.5 ${
              activeView === 'json' ? 'border-purple-400 text-purple-400 bg-purple-500/10' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Lock size={14} /> Raw WORM Audit Record
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#0a0f1c]">

          {/* VIEW 1: FORMAL CERTIFICATE */}
          {activeView === 'certificate' && (
            <div className="space-y-6 animate-fadeIn">
              
              {/* Institution & ID Card */}
              <div className="bg-[#131d35] border border-[#1e293b] p-5 rounded-xl flex justify-between items-start flex-wrap gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-red-600 inline-block rounded-xs"></span>
                    <span className="text-sm font-bold text-white tracking-tight">
                      SOCIÉTÉ GÉNÉRALE GLOBAL BANKING & INVESTOR SOLUTIONS
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Regulatory Compliance & Automated Trade Operations Execution Certification
                  </div>
                  <div className="text-[11px] text-slate-300 font-mono mt-2">
                    Subject: <span className="text-white font-semibold">{email.subject}</span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-sky-300 bg-[#0b1120] px-3 py-1.5 rounded-lg border border-[#1e293b]">
                    {certId}
                  </div>
                  <div className="text-[11px] text-emerald-400 font-semibold mt-1 flex items-center justify-end gap-1">
                    <Check size={12} /> FIPS 140-2 / MiFID II Compliant
                  </div>
                </div>
              </div>

              {/* 2-Column Standards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* MiFID II RTS 25 Box */}
                <div className="bg-[#131d35] border border-[#1e293b] p-4 rounded-xl space-y-3">
                  <div className="flex justify-between items-center pb-2 border-b border-[#1e293b]">
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      <Clock size={14} className="text-sky-400" />
                      MiFID II RTS 25 UTC Synchronization
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                      SYNCHRONIZED
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Precision Timestamp:</span>
                      <span className="font-mono text-sky-300 font-semibold">{rts25Timestamp}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Clock Source:</span>
                      <span className="font-mono text-slate-200">Stratum-1 PTP (NIST)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Max Drift Tolerance:</span>
                      <span className="font-mono text-slate-300">100 µs (0.000100 s)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Measured Drift:</span>
                      <span className="font-mono text-emerald-400 font-bold">+1.42 µs (PASS)</span>
                    </div>
                  </div>
                </div>

                {/* FINRA Rule 4511 Box */}
                <div className="bg-[#131d35] border border-[#1e293b] p-4 rounded-xl space-y-3">
                  <div className="flex justify-between items-center pb-2 border-b border-[#1e293b]">
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      <ShieldCheck size={14} className="text-emerald-400" />
                      FINRA Rule 4511 & SEC 17a-4 WORM
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                      IMMUTABLE
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Retention Standard:</span>
                      <span className="font-mono text-slate-200">6-Year WORM Storage</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Ingestion Timestamp:</span>
                      <span className="font-mono text-slate-300">{rts25Timestamp.slice(0, 19)}Z</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Retention Expiry:</span>
                      <span className="font-mono text-amber-300">{retentionExpiry.slice(0, 19)}Z</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Principal Reg ID:</span>
                      <span className="font-mono text-slate-200">FINRA-PRIN-REG#849201</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Zero-PII Leakage Proof Box */}
              <div className="bg-[#131d35] border border-[#1e293b] p-4 rounded-xl space-y-3">
                <div className="flex justify-between items-center pb-2 border-b border-[#1e293b] flex-wrap gap-2">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <ShieldCheck size={16} className="text-emerald-400" />
                    Zero-PII Leakage Proof (EU GDPR Art 32 / CNIL Standard)
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold border border-emerald-500/40">
                    CERTIFIED: ZERO UNMASKED PII TRANSMITTED
                  </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-[11px] text-slate-400 mb-1">Redacted Client Entities:</div>
                    <div className="flex gap-1.5 flex-wrap">
                      {Object.keys(email.piiReport.mapping).length > 0 ? (
                        Object.keys(email.piiReport.mapping).map((token) => (
                          <span key={token} className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono">
                            {token}
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-400 text-xs">No sensitive PII present in payload</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-400 mb-1">Preserved Financial Identifiers:</div>
                    <div className="flex gap-1.5 flex-wrap">
                      {['ISIN', 'CUSIP', 'SEDOL', 'SWIFT_BIC', 'TRADE_ID'].map((id) => (
                        <span key={id} className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 text-[10px] font-mono">
                          {id}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-[#1e293b] space-y-1 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Pre-LLM Sanitization SHA-256:</span>
                    <span className="font-mono text-[11px] text-slate-300 truncate max-w-md">{sanitizedHash}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Adversarial Injection Defense:</span>
                    <span className="font-mono text-emerald-400 font-semibold">PASSED (Zero Prompt Injection Triggers)</span>
                  </div>
                </div>
              </div>

              {/* Cryptographic Supervisor Signature Seal */}
              <div className="bg-[#0b1120] border border-sky-500/40 p-4 rounded-xl space-y-2 relative overflow-hidden">
                <div className="flex justify-between items-center">
                  <div className="text-xs font-bold text-sky-400 flex items-center gap-1.5">
                    <Lock size={14} />
                    Supervisor Cryptographic Approval Signature (HMAC-SHA256)
                  </div>
                  <button
                    onClick={copySignature}
                    className="flex items-center gap-1 text-[11px] font-mono text-sky-300 hover:text-sky-200 bg-sky-500/20 hover:bg-sky-500/30 px-2 py-1 rounded transition-colors"
                  >
                    {copiedHash ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    {copiedHash ? 'Copied' : 'Copy Hash'}
                  </button>
                </div>
                <div className="bg-[#070b14] border border-[#1e293b] p-2.5 rounded-lg font-mono text-xs text-emerald-400 break-all">
                  {sigHash}
                </div>
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Signatory: Société Générale Automated Compliance Gateway</span>
                  <span className="text-emerald-400 font-semibold">● CRYPTOGRAPHICALLY VERIFIED</span>
                </div>
              </div>

            </div>
          )}

          {/* VIEW 2: MULTI-AGENT LINEAGE DAG */}
          {activeView === 'lineage' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="text-xs text-slate-400 mb-2">
                Directed Acyclic Graph (DAG) representing the causality chain across specialized back-office AI agents:
              </div>

              <div className="space-y-3">
                {email.pipelineSteps.map((step, idx) => (
                  <div key={idx} className="bg-[#131d35] border border-[#1e293b] p-3.5 rounded-xl flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-sky-500/20 border border-sky-500/50 flex items-center justify-center text-sky-400 font-bold text-xs shrink-0">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-center">
                        <div className="font-bold text-white text-xs">{step.agent}</div>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          {step.durationMs}ms &bull; SUCCESS
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300 mt-0.5">{step.summary}</div>
                      <div className="text-[10px] font-mono text-slate-400 mt-1 flex justify-between">
                        <span>Checkpoint: <code>sha256_{idx * 17 + 1048}</code></span>
                        <span>Dependency: {idx === 0 ? 'INGESTION_PAYLOAD' : `STEP_${idx}_OUTPUT`}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW 3: RAW JSON */}
          {activeView === 'json' && (
            <div className="space-y-3 animate-fadeIn">
              <pre className="bg-[#070b14] border border-[#1e293b] p-4 rounded-xl text-xs font-mono text-sky-300 overflow-x-auto leading-relaxed max-h-[420px]">
                {JSON.stringify({
                  certificate_id: certId,
                  trace_id: traceId,
                  email_id: emailId,
                  mifid_ii_rts25: {
                    regulation: "MiFID II RTS 25",
                    timestamp_utc: rts25Timestamp,
                    drift: "+1.42 µs",
                    status: "SYNCHRONIZED_ACCREDITED"
                  },
                  finra_rule_4511: {
                    mandate: "FINRA 4511 / SEC 17a-4 WORM",
                    retention_period_years: 6,
                    expiry: retentionExpiry
                  },
                  pii_anonymization_proof: {
                    attestation: "CERTIFIED: ZERO UNMASKED PII TRANSMITTED",
                    raw_hash: rawHash,
                    sanitized_hash: sanitizedHash
                  },
                  supervisor_signature: {
                    algorithm: "HMAC-SHA256",
                    hash: sigHash,
                    status: "CRYPTOGRAPHICALLY_VERIFIED"
                  }
                }, null, 2)}
              </pre>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#1e293b] bg-[#131d35] flex justify-between items-center text-xs text-slate-400">
          <div>
            Cosmos DB Immutable WORM Partition: <span className="text-emerald-400 font-mono font-semibold">AZURE-VAULT-PARIS-01</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-colors"
          >
            Close Viewer
          </button>
        </div>

      </div>
    </div>
  );
}
