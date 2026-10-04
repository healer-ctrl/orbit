const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface IncomingEmail {
  id: string;
  sender: string;
  subject: string;
  body: string;
  received_at: string;
  attachments: string[];
  raw_headers: Record<string, string>;
}

export interface AgentStep {
  agent_name: string;
  input_data: any;
  output_data: any;
  started_at: string;
  completed_at: string;
  duration_ms: number;
}

export interface PipelineResult {
  email_id: string;
  steps: AgentStep[];
  risk_score: number;
  risk_level: string;
  recommended_actions: any[];
  requires_approval: boolean;
}

export async function processEmail(email: IncomingEmail): Promise<PipelineResult> {
  const res = await fetch(`${API_BASE}/api/process-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(email),
  });
  return res.json();
}

export async function triggerDemo(): Promise<{ status: string; results: PipelineResult[] }> {
  const res = await fetch(`${API_BASE}/api/demo/trigger`, { method: 'POST' });
  return res.json();
}

export async function listEmails(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/emails`);
  return res.json();
}

export async function listActions(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/actions`);
  return res.json();
}

export async function getAudit(traceId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/audit/${traceId}`);
  return res.json();
}

export async function approveAction(traceId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/approve/${traceId}`, { method: 'POST' });
  return res.json();
}

export async function rejectAction(traceId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/reject/${traceId}`, { method: 'POST' });
  return res.json();
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export interface ComplianceCertificate {
  certificate_id: string;
  trace_id: string;
  email_id: string;
  generated_at_utc: string;
  institution: string;
  mifid_ii_rts25: {
    regulation: string;
    gateway_category: string;
    timestamp_utc_microsecond: string;
    time_source: string;
    max_divergence_tolerance: string;
    actual_measured_drift: string;
    clock_synchronization_status: string;
    audit_epoch_nanoseconds: number;
  };
  finra_rule_4511: {
    mandate: string;
    storage_class: string;
    retention_period_years: number;
    retention_creation_utc: string;
    mandatory_retention_until_utc: string;
    custodian_entity: string;
    custody_partition_id: string;
    supervising_principal_id: string;
    compliance_officer_attestation: string;
  };
  pii_anonymization_proof: {
    attestation: string;
    certification_status: string;
    raw_payload_sha256: string;
    sanitized_payload_sha256: string;
    masked_entities_count: number;
    masked_entity_categories: string[];
    protected_market_identifiers: string[];
    prompt_injection_defense: string;
    shield_engine_version: string;
    anonymization_standard: string;
  };
  multi_agent_lineage_dag: {
    nodes: Array<{
      node_id: string;
      step_index: number;
      agent_name: string;
      started_at: string;
      completed_at: string;
      duration_ms: number;
      input_summary: any;
      output_summary: any;
      execution_status: string;
      sha256_checkpoint: string;
    }>;
    edges: Array<{
      from: string;
      to: string;
      dependency_type: string;
    }>;
    total_steps: number;
    total_duration_ms: number;
  };
  pipeline_execution_summary: {
    risk_score: number;
    risk_level: string;
    requires_approval: boolean;
    action_count: number;
    actions: any[];
    email_subject: string;
    email_sender: string;
  };
  supervisor_signature: {
    certificate_id: string;
    trace_id: string;
    signing_algorithm: string;
    signature_hash: string;
    canonical_payload_digest: string;
    signatory_role: string;
    signatory_entity: string;
    verification_status: string;
    certificate_issued_at_utc: string;
  };
}

export async function getComplianceCertificate(emailId: string, format: 'json' | 'html' = 'json'): Promise<any> {
  const res = await fetch(`${API_BASE}/api/compliance/certificate/${emailId}?format=${format}`);
  if (format === 'html') {
    return res.text();
  }
  return res.json();
}

export function getComplianceCertificateUrl(emailId: string, format: 'json' | 'html' = 'html'): string {
  return `${API_BASE}/api/compliance/certificate/${emailId}?format=${format}`;
}

