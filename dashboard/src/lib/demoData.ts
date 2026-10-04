export interface ProcessedEmailRecord {
  id: string;
  sender: string;
  senderName: string;
  senderOrg: string;
  subject: string;
  timeAgo: string;
  receivedAt: string;
  intent: 'CORPORATE_ACTION' | 'SETTLEMENT' | 'TRADE_LINKAGE' | 'INSTRUMENT_CORRECTION' | 'SUPPORT_TICKET';
  urgency: 'HIGH' | 'MEDIUM' | 'LOW';
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  requiresApproval: boolean;
  status: 'AUTO_EXECUTED' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED';
  rawBody: string;
  sanitizedBody: string;
  piiReport: {
    piiDetected: boolean;
    maskCount: number;
    maskedTypes: string[];
    mapping: Record<string, string>;
    injectionShieldPassed: boolean;
  };
  entities: {
    isin?: string;
    cusip?: string;
    sedol?: string;
    counterparty?: string;
    counterpartyBic?: string;
    amount?: number;
    currency?: string;
    tradeId?: string;
    deadline?: string;
    actionType?: string;
  };
  sopApplied: {
    id: string;
    title: string;
    relevance: number;
    rule: string;
  };
  pipelineSteps: {
    agent: string;
    role: string;
    status: 'COMPLETED' | 'IN_PROGRESS' | 'WAITING';
    durationMs: number;
    summary: string;
    details: Record<string, any>;
  }[];
  executionResult: {
    system: string;
    actionId: string;
    message: string;
    timestamp: string;
    payload: Record<string, any>;
  };
}

export const INITIAL_EMAILS: ProcessedEmailRecord[] = [
  {
    id: 'email_1',
    sender: 'notifications@dtcc.com',
    senderName: 'Michael Braun',
    senderOrg: 'DTCC Clearing Europe',
    subject: 'CORPORATE ACTION ANNOUNCEMENT: SAP SE DIVIDEND (ISIN DE0007164600)',
    timeAgo: '2 mins ago',
    receivedAt: '2024-05-10T10:00:00Z',
    intent: 'CORPORATE_ACTION',
    urgency: 'HIGH',
    riskScore: 0.88,
    riskLevel: 'HIGH',
    requiresApproval: true,
    status: 'PENDING_APPROVAL',
    rawBody: `CONFIDENTIAL - DTCC Corporate Actions Announcement\n\nPlease be advised that SAP SE (ISIN: DE0007164600) has confirmed a mandatory cash dividend of EUR 2.20 per share.\nEx-Date: 2024-05-18\nRecord Date: 2024-05-19\nPayment Date: 2024-05-22\n\nDirect contact officer: Michael Braun (+49 69 1234 5678, m.braun@external-advisory.de).\nInternal clearing account reference: ACC: 884729104829.\n\nPlease reconcile your entitlements against Euroclear/Clearstream positions before record date.`,
    sanitizedBody: `CONFIDENTIAL - DTCC Corporate Actions Announcement\n\nPlease be advised that SAP SE (ISIN: DE0007164600) has confirmed a mandatory cash dividend of EUR 2.20 per share.\nEx-Date: 2024-05-18\nRecord Date: 2024-05-19\nPayment Date: 2024-05-22\n\nDirect contact officer: Michael Braun ([PHONE_1], [PERSONAL_EMAIL_1]).\nInternal clearing account reference: [BANK_ACCOUNT_1].\n\nPlease reconcile your entitlements against Euroclear/Clearstream positions before record date.`,
    piiReport: {
      piiDetected: true,
      maskCount: 3,
      maskedTypes: ['PHONE', 'PERSONAL_EMAIL', 'BANK_ACCOUNT'],
      mapping: {
        '[PHONE_1]': '+49 69 1234 5678',
        '[PERSONAL_EMAIL_1]': 'm.braun@external-advisory.de',
        '[BANK_ACCOUNT_1]': 'ACC: 884729104829',
      },
      injectionShieldPassed: true,
    },
    entities: {
      isin: 'DE0007164600',
      counterparty: 'SAP SE / DTCC',
      amount: 2.20,
      currency: 'EUR',
      actionType: 'MANDATORY_CASH_DIVIDEND',
      deadline: '2024-05-19T18:00:00Z',
    },
    sopApplied: {
      id: 'SOP-CA-001',
      title: 'Mandatory Cash Dividend Reconciliation & Entitlement Processing',
      relevance: 0.98,
      rule: 'Reconcile CSD position on Record Date. If rate > EUR 2.00 or discrepancy detected, escalate to Supervisor.',
    },
    pipelineSteps: [
      {
        agent: 'PIIGuardrailShield',
        role: 'Data Anonymization & Prompt Injection Defense',
        status: 'COMPLETED',
        durationMs: 18,
        summary: '3 PII tokens anonymized (Phone, Email, Bank Account). ISIN preserved.',
        details: { masked_count: 3, isin_preserved: 'DE0007164600', injection_detected: false },
      },
      {
        agent: 'ClassifierAgent',
        role: 'GPT-4o Capital Markets Intent Categorization',
        status: 'COMPLETED',
        durationMs: 145,
        summary: 'Classified as CORPORATE_ACTION (Confidence: 98.4%)',
        details: { intent: 'CORPORATE_ACTION', confidence: 0.984, reasoning: 'Standard MT564 cash dividend notification.' },
      },
      {
        agent: 'ParserAgent',
        role: 'Financial Entity & Master Data Extraction',
        status: 'COMPLETED',
        durationMs: 98,
        summary: 'Extracted ISIN DE0007164600, Rate EUR 2.20, Ex-Date 2024-05-18',
        details: { isin: 'DE0007164600', security: 'SAP SE (XETRA)', rate: 'EUR 2.20' },
      },
      {
        agent: 'DecisionAgent',
        role: 'Azure AI Search Institutional SOP RAG',
        status: 'COMPLETED',
        durationMs: 112,
        summary: 'Matched SOP-CA-001. Rate exceeds EUR 2.00 threshold -> Flag for approval.',
        details: { sop_id: 'SOP-CA-001', action: 'CREATE_CORPORATE_ACTION_EVENT' },
      },
      {
        agent: 'RiskScorerAgent',
        role: 'Operational Risk Evaluation & Gating',
        status: 'COMPLETED',
        durationMs: 64,
        summary: 'Score 0.88 / 1.00 (HIGH). Generated Teams Adaptive Card v1.5 for Supervisor.',
        details: { risk_score: 0.88, threshold: 0.70, alert_channel: 'MS_TEAMS_WEBHOOK' },
      },
    ],
    executionResult: {
      system: 'Corporate Actions Processing Master',
      actionId: 'CA-EVT-99281',
      message: 'Event generated. Pending supervisor sign-off before entitlement dispatch.',
      timestamp: '2024-05-10T10:00:01Z',
      payload: { event_id: 'CA-EVT-99281', isin: 'DE0007164600', affected_accounts: 14, total_shares: 14000 },
    },
  },
  {
    id: 'email_2',
    sender: 'settlements@clearstream.com',
    senderName: 'Clearstream Operations',
    senderOrg: 'Clearstream Banking Frankfurt',
    subject: 'URGENT: FAILED SETTLEMENT - T+1 SSI CORRECTION REQUIRED (TRD-998822)',
    timeAgo: '12 mins ago',
    receivedAt: '2024-05-11T09:30:00Z',
    intent: 'SETTLEMENT',
    urgency: 'HIGH',
    riskScore: 0.62,
    riskLevel: 'MEDIUM',
    requiresApproval: false,
    status: 'AUTO_EXECUTED',
    rawBody: `CRITICAL / URGENT ACTION REQUIRED - SETTLEMENT FAILURE\n\nTrade reference TRD-998822 with counterparty JPMorgan Chase (CHASUS33XXX) for value USD 2,450,000.00 failed matching in TARGET2 due to incorrect SSI instruction on your side.\n\nCustodian notes: Incorrect Beneficiary IBAN DE89370400440532013000 provided. Correct account must be COBADEFF account.\nTrade Settlement Cutoff: 14:00 CET today.\nTrader in charge: Sarah Jenkins (cell: +1-212-555-0199, SSN: 992-12-8821).\n\nPlease update SSI immediately to prevent buy-in penalty.`,
    sanitizedBody: `CRITICAL / URGENT ACTION REQUIRED - SETTLEMENT FAILURE\n\nTrade reference TRD-998822 with counterparty JPMorgan Chase (CHASUS33XXX) for value USD 2,450,000.00 failed matching in TARGET2 due to incorrect SSI instruction on your side.\n\nCustodian notes: Incorrect Beneficiary [IBAN_1] provided. Correct account must be COBADEFF account.\nTrade Settlement Cutoff: 14:00 CET today.\nTrader in charge: Sarah Jenkins (cell: [PHONE_1], SSN: [SSN_TIN_1]).\n\nPlease update SSI immediately to prevent buy-in penalty.`,
    piiReport: {
      piiDetected: true,
      maskCount: 3,
      maskedTypes: ['IBAN', 'PHONE', 'SSN_TIN'],
      mapping: {
        '[IBAN_1]': 'DE89370400440532013000',
        '[PHONE_1]': '+1-212-555-0199',
        '[SSN_TIN_1]': '992-12-8821',
      },
      injectionShieldPassed: true,
    },
    entities: {
      tradeId: 'TRD-998822',
      counterparty: 'JPMorgan Chase Bank N.A.',
      counterpartyBic: 'CHASUS33XXX',
      amount: 2450000,
      currency: 'USD',
      actionType: 'SSI_UPDATE_AND_RESUBMIT',
      deadline: '14:00 CET Today',
    },
    sopApplied: {
      id: 'SOP-SET-003',
      title: 'T+1 Failed Trade SSI Resolution & Counterparty Resubmission',
      relevance: 0.99,
      rule: 'Verify counterparty directory. Update beneficiary BIC to COBADEFF and resubmit MT544 instruction before cutoff.',
    },
    pipelineSteps: [
      {
        agent: 'PIIGuardrailShield',
        role: 'Data Anonymization',
        status: 'COMPLETED',
        durationMs: 22,
        summary: 'Sanitized IBAN, phone, and SSN. SWIFT BIC CHASUS33XXX preserved.',
        details: { masked_count: 3, bic: 'CHASUS33XXX' },
      },
      {
        agent: 'ClassifierAgent',
        role: 'Intent Classification',
        status: 'COMPLETED',
        durationMs: 130,
        summary: 'Classified as SETTLEMENT (Confidence: 99.1%, High Urgency)',
        details: { intent: 'SETTLEMENT', urgency: 'HIGH' },
      },
      {
        agent: 'ParserAgent',
        role: 'Entity Resolution',
        status: 'COMPLETED',
        durationMs: 88,
        summary: 'Extracted TRD-998822, $2.45M, Counterparty JPM (CHASUS33XXX)',
        details: { tradeId: 'TRD-998822', amount: 2450000 },
      },
      {
        agent: 'DecisionAgent',
        role: 'SOP RAG Resolution',
        status: 'COMPLETED',
        durationMs: 104,
        summary: 'SOP-SET-003 matched. Verified COBADEFF mapping in Counterparty Registry.',
        details: { action: 'CORRECT_SSI_AND_RESUBMIT', system: 'TARGET2' },
      },
      {
        agent: 'RiskScorerAgent',
        role: 'Risk Evaluation',
        status: 'COMPLETED',
        durationMs: 58,
        summary: 'Risk Score 0.62 / 1.00 (Standard SSI fix, reversible action). Auto-Executed.',
        details: { risk_score: 0.62, auto_execute: true },
      },
    ],
    executionResult: {
      system: 'TARGET2 / Euroclear Gateway',
      actionId: 'SET-INST-88192',
      message: 'SSI patched to COBADEFF account. SWIFT MT544 resubmitted and matched.',
      timestamp: '2024-05-11T09:30:02Z',
      payload: { instruction_id: 'SET-INST-88192', delivery_type: 'DVP', status: 'MATCHED' },
    },
  },
  {
    id: 'email_3',
    sender: 'middleoffice@socgen.com',
    senderName: 'David Miller',
    senderOrg: 'Global Equities Desk NY',
    subject: 'Request to Link Block Trade TRD-2024-88712 to US0378331005 (Apple Inc)',
    timeAgo: '35 mins ago',
    receivedAt: '2024-05-12T11:15:00Z',
    intent: 'TRADE_LINKAGE',
    urgency: 'LOW',
    riskScore: 0.22,
    riskLevel: 'LOW',
    requiresApproval: false,
    status: 'AUTO_EXECUTED',
    rawBody: `Hi Ops Team,\n\nPlease allocate and link block trade ID TRD-2024-88712 to Apple Inc (CUSIP: 037833100, ISIN: US0378331005).\nTrade size: USD 1,500,000.00.\nTarget Desk Book: EQ-US-FLOW.\nBroker Contact: David Miller (phone: 212-555-7821, internal IP: 10.240.12.88).\n\nThanks,\nNew York Trading Desk`,
    sanitizedBody: `Hi Ops Team,\n\nPlease allocate and link block trade ID TRD-2024-88712 to Apple Inc (CUSIP: 037833100, ISIN: US0378331005).\nTrade size: USD 1,500,000.00.\nTarget Desk Book: EQ-US-FLOW.\nBroker Contact: David Miller (phone: [PHONE_1], internal IP: [INTERNAL_IP_1]).\n\nThanks,\nNew York Trading Desk`,
    piiReport: {
      piiDetected: true,
      maskCount: 2,
      maskedTypes: ['PHONE', 'INTERNAL_IP'],
      mapping: {
        '[PHONE_1]': '212-555-7821',
        '[INTERNAL_IP_1]': '10.240.12.88',
      },
      injectionShieldPassed: true,
    },
    entities: {
      tradeId: 'TRD-2024-88712',
      isin: 'US0378331005',
      cusip: '037833100',
      counterparty: 'Apple Inc.',
      amount: 1500000,
      currency: 'USD',
      actionType: 'TRADE_LINK_ALLOCATION',
    },
    sopApplied: {
      id: 'SOP-TL-001',
      title: 'Trade-to-Instrument Allocation & Desk Booking Linkage',
      relevance: 0.97,
      rule: 'Verify trade ID against booking system. Allocate to EQ-US-FLOW desk and dispatch confirmation.',
    },
    pipelineSteps: [
      {
        agent: 'PIIGuardrailShield',
        role: 'Data Anonymization',
        status: 'COMPLETED',
        durationMs: 14,
        summary: 'Sanitized internal IP & phone. CUSIP 037833100 preserved.',
        details: { masked_count: 2 },
      },
      {
        agent: 'ClassifierAgent',
        role: 'Intent Classification',
        status: 'COMPLETED',
        durationMs: 110,
        summary: 'Classified as TRADE_LINKAGE (Confidence: 96.5%)',
        details: { intent: 'TRADE_LINKAGE' },
      },
      {
        agent: 'ParserAgent',
        role: 'Entity Resolution',
        status: 'COMPLETED',
        durationMs: 76,
        summary: 'Resolved Apple Inc (NASDAQ), CUSIP 037833100, Desk EQ-US-FLOW',
        details: { instrument: 'Apple Inc', cusip: '037833100' },
      },
      {
        agent: 'DecisionAgent',
        role: 'SOP RAG Resolution',
        status: 'COMPLETED',
        durationMs: 82,
        summary: 'SOP-TL-001 applied. Trade validated in booking queue.',
        details: { action: 'UPDATE_TRADE_INSTRUMENT_MAPPING' },
      },
      {
        agent: 'RiskScorerAgent',
        role: 'Risk Evaluation',
        status: 'COMPLETED',
        durationMs: 42,
        summary: 'Risk Score 0.22 / 1.00 (Routine allocation). Auto-Executed.',
        details: { risk_score: 0.22, auto_execute: true },
      },
    ],
    executionResult: {
      system: 'Front-Office Trade Booking Feeder',
      actionId: 'TL-LNK-44910',
      message: 'Trade TRD-2024-88712 mapped to Apple Inc in EQ-US-FLOW book.',
      timestamp: '2024-05-12T11:15:01Z',
      payload: { book: 'EQ-US-FLOW', linkage_status: 'LINKED', desk_trader: 'desk_head_us_eq' },
    },
  },
  {
    id: 'email_4',
    sender: 'referencedata-alerts@reuters.com',
    senderName: 'Elena Rostova',
    senderOrg: 'LSEG Reference Data Feed',
    subject: 'ALERT: Security Identifier Mismatch Detected for Position POS-44332',
    timeAgo: '1 hour ago',
    receivedAt: '2024-05-13T08:45:00Z',
    intent: 'INSTRUMENT_CORRECTION',
    urgency: 'MEDIUM',
    riskScore: 0.25,
    riskLevel: 'LOW',
    requiresApproval: false,
    status: 'AUTO_EXECUTED',
    rawBody: `Automated Reference Data Exception:\n\nPosition POS-44332 currently mapped to obsolete ISIN XS1234567890. Following issuer debt restructuring, the active bond ISIN has been updated to XS0987654321 (SocGen 5Y Senior Bond).\nAccount Ref: ACCT# 992817263541\nData Steward: Elena Rostova (+33 1 42 14 20 00).\n\nPlease patch instrument master reference mapping.`,
    sanitizedBody: `Automated Reference Data Exception:\n\nPosition POS-44332 currently mapped to obsolete ISIN XS1234567890. Following issuer debt restructuring, the active bond ISIN has been updated to XS0987654321 (SocGen 5Y Senior Bond).\nAccount Ref: [BANK_ACCOUNT_1]\nData Steward: Elena Rostova ([PHONE_1]).\n\nPlease patch instrument master reference mapping.`,
    piiReport: {
      piiDetected: true,
      maskCount: 2,
      maskedTypes: ['BANK_ACCOUNT', 'PHONE'],
      mapping: {
        '[BANK_ACCOUNT_1]': 'ACCT# 992817263541',
        '[PHONE_1]': '+33 1 42 14 20 00',
      },
      injectionShieldPassed: true,
    },
    entities: {
      isin: 'XS0987654321',
      counterparty: 'Société Générale Fixed Income',
      actionType: 'ISIN_MASTER_PATCH',
    },
    sopApplied: {
      id: 'SOP-REF-002',
      title: 'Instrument Master Data Exception & ISIN/CUSIP Remapping',
      relevance: 0.98,
      rule: 'Validate ISO 6166 checksum. Remap Position Keeper and notify Risk Engine with rollback snapshot.',
    },
    pipelineSteps: [
      {
        agent: 'PIIGuardrailShield',
        role: 'Data Anonymization',
        status: 'COMPLETED',
        durationMs: 16,
        summary: 'Account and phone redacted. ISIN XS0987654321 preserved.',
        details: { masked_count: 2 },
      },
      {
        agent: 'ClassifierAgent',
        role: 'Intent Classification',
        status: 'COMPLETED',
        durationMs: 122,
        summary: 'Classified as INSTRUMENT_CORRECTION (Confidence: 97.2%)',
        details: { intent: 'INSTRUMENT_CORRECTION' },
      },
      {
        agent: 'ParserAgent',
        role: 'Entity Resolution',
        status: 'COMPLETED',
        durationMs: 65,
        summary: 'Validated ISIN XS0987654321 checksum (ISO 6166 VALID)',
        details: { new_isin: 'XS0987654321', old_isin: 'XS1234567890' },
      },
      {
        agent: 'DecisionAgent',
        role: 'SOP RAG Resolution',
        status: 'COMPLETED',
        durationMs: 78,
        summary: 'SOP-REF-002 applied. Patched reference data master.',
        details: { action: 'PATCH_REFERENCE_DATA' },
      },
      {
        agent: 'RiskScorerAgent',
        role: 'Risk Evaluation',
        status: 'COMPLETED',
        durationMs: 38,
        summary: 'Risk Score 0.25 / 1.00 (Checksum valid, automated rollback ready). Auto-Executed.',
        details: { risk_score: 0.25, auto_execute: true },
      },
    ],
    executionResult: {
      system: 'Reference Data Master & Position Keeper',
      actionId: 'IC-COR-33819',
      message: 'Position POS-44332 re-mapped from XS1234567890 to XS0987654321.',
      timestamp: '2024-05-13T08:45:01Z',
      payload: { validation: 'ISO_6166_PASSED', downstream_systems_notified: 3 },
    },
  },
  {
    id: 'email_5',
    sender: 'hr-onboarding@socgen.com',
    senderName: 'HR Global Markets',
    senderOrg: 'Société Générale HR Paris',
    subject: 'Access Provisioning Request: Trade Booking System for New Analyst',
    timeAgo: '2 hours ago',
    receivedAt: '2024-05-14T14:20:00Z',
    intent: 'SUPPORT_TICKET',
    urgency: 'LOW',
    riskScore: 0.35,
    riskLevel: 'LOW',
    requiresApproval: false,
    status: 'AUTO_EXECUTED',
    rawBody: `Hello Support Team,\n\nPlease provision Trade Booking & Settlement Portal access for John Doe (Employee ID: EMP-883921, email: john.doe.contractor@personalmail.org, phone: +33 6 12 34 56 78).\nDepartment: Global Markets Operations - Paris.\nRequired Roles: Trade Entry, Settlement Read-Only.\n\nManager Sign-off: Approved by Operations Director.`,
    sanitizedBody: `Hello Support Team,\n\nPlease provision Trade Booking & Settlement Portal access for John Doe (Employee ID: EMP-883921, email: [PERSONAL_EMAIL_1], phone: [PHONE_1]).\nDepartment: Global Markets Operations - Paris.\nRequired Roles: Trade Entry, Settlement Read-Only.\n\nManager Sign-off: Approved by Operations Director.`,
    piiReport: {
      piiDetected: true,
      maskCount: 2,
      maskedTypes: ['PERSONAL_EMAIL', 'PHONE'],
      mapping: {
        '[PERSONAL_EMAIL_1]': 'john.doe.contractor@personalmail.org',
        '[PHONE_1]': '+33 6 12 34 56 78',
      },
      injectionShieldPassed: true,
    },
    entities: {
      counterparty: 'John Doe',
      actionType: 'ITSM_INCIDENT_CREATE',
    },
    sopApplied: {
      id: 'SOP-SUP-001',
      title: 'Operations Systems Access Provisioning & Role Granting',
      relevance: 0.96,
      rule: 'Verify HR approval. Auto-create ServiceNow incident in Access Management queue with P3 SLA.',
    },
    pipelineSteps: [
      {
        agent: 'PIIGuardrailShield',
        role: 'Data Anonymization',
        status: 'COMPLETED',
        durationMs: 12,
        summary: 'Sanitized contractor email and mobile number.',
        details: { masked_count: 2 },
      },
      {
        agent: 'ClassifierAgent',
        role: 'Intent Classification',
        status: 'COMPLETED',
        durationMs: 95,
        summary: 'Classified as SUPPORT_TICKET (Confidence: 96.0%)',
        details: { intent: 'SUPPORT_TICKET' },
      },
      {
        agent: 'ParserAgent',
        role: 'Entity Resolution',
        status: 'COMPLETED',
        durationMs: 54,
        summary: 'Identified Employee ID EMP-883921, Roles: Trade Entry, Settlement Read-Only',
        details: { employee_id: 'EMP-883921' },
      },
      {
        agent: 'DecisionAgent',
        role: 'SOP RAG Resolution',
        status: 'COMPLETED',
        durationMs: 70,
        summary: 'SOP-SUP-001 matched. Created ServiceNow Ticket INC-77821.',
        details: { action: 'CREATE_ITSM_TICKET' },
      },
      {
        agent: 'RiskScorerAgent',
        role: 'Risk Evaluation',
        status: 'COMPLETED',
        durationMs: 34,
        summary: 'Risk Score 0.35 / 1.00 (Standard P3 request with Director approval). Auto-Executed.',
        details: { risk_score: 0.35, auto_execute: true },
      },
    ],
    executionResult: {
      system: 'ServiceNow ITSM Enterprise',
      actionId: 'INC-882910',
      message: 'ServiceNow ticket created in Access Management queue with P3 (4-hour) SLA target.',
      timestamp: '2024-05-14T14:20:01Z',
      payload: { ticket_id: 'INC-882910', category: 'Access Management', priority: 'P3 - Medium', sla: '4 hours' },
    },
  },
];
