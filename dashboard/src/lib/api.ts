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
