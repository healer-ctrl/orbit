'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Sparkles,
  Send,
  Mic,
  MicOff,
  X,
  Maximize2,
  Minimize2,
  ChevronDown,
  CornerDownLeft,
  Volume2,
  VolumeX,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  FileText,
  BookOpen,
  DollarSign,
  Layers,
  Terminal,
  Clock,
  Search,
  ExternalLink,
  MessageSquare,
  HelpCircle
} from 'lucide-react';
import { ProcessedEmailRecord } from '@/lib/demoData';

interface Message {
  id: string;
  sender: 'user' | 'copilot';
  timestamp: string;
  text: string;
  queryType?: 'SETTLEMENT_QUERY' | 'SOP_QUERY' | 'APPROVAL_SUMMARY' | 'RISK_EXPLANATION' | 'GENERAL';
  metrics?: {
    latencyMs?: number;
    tokens?: number;
    confidence?: number;
    sources?: string[];
  };
  cards?: {
    type: 'email' | 'sop' | 'approval' | 'risk_breakdown' | 'action_prompt';
    title: string;
    data: any;
  }[];
}

interface OperationsCopilotProps {
  emails: ProcessedEmailRecord[];
  onSelectEmail?: (email: ProcessedEmailRecord) => void;
  onApproveEmail?: (id: string) => void;
  onRejectEmail?: (id: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

const QUICK_PROMPTS = [
  {
    label: 'Failed Settlements > $1M',
    query: 'Show me all failed settlements with JPM over $1M',
    icon: DollarSign,
    category: 'Settlements',
  },
  {
    label: 'SAP Dividend SOP Rule',
    query: 'What is the SOP rule for SAP dividend?',
    icon: BookOpen,
    category: 'SOPs',
  },
  {
    label: 'Pending Supervisor Approvals',
    query: 'Summarize pending supervisor approvals',
    icon: Clock,
    category: 'Approvals',
  },
  {
    label: 'Explain Email_1 High Risk',
    query: 'Explain why email_1 was flagged as high risk',
    icon: AlertTriangle,
    category: 'Risk',
  },
  {
    label: 'Check JPM SSI Status',
    query: 'Check JPM SSI Status and TARGET2 resubmission',
    icon: Layers,
    category: 'Settlements',
  },
  {
    label: 'Audit PII Redactions',
    query: 'How many PII items were masked today and were there any prompt injections?',
    icon: ShieldCheck,
    category: 'Security',
  },
];

const SOP_DATABASE = [
  {
    id: 'SOP-CA-001',
    title: 'Mandatory Cash Dividend Reconciliation & Entitlement Processing',
    domain: 'CORPORATE_ACTION',
    threshold: 'Rate <= €2.00 / Share (Auto-Exec) | > €2.00 (Supervisor HITL)',
    rules: 'Reconcile CSD position (Clearstream/Euroclear) against internal ledger on Record Date. If discrepancy < 100 shares, auto-adjust and book event. If dividend rate > EUR 2.00, flag for supervisor sign-off before entitlement dispatch.',
    sla: '< 2 Hours',
    appliesTo: ['SAP SE', 'DE0007164600', 'MT564', 'Cash Dividend'],
  },
  {
    id: 'SOP-SET-003',
    title: 'T+1 Failed Trade SSI Resolution & Counterparty Resubmission',
    domain: 'SETTLEMENT',
    threshold: 'Notional <= $5M & Standard BIC (Auto-Exec) | Non-standard BIC (Supervisor HITL)',
    rules: 'Upon receiving failed matching notification with counterparty, query Counterparty SSI Directory. Verify BIC (CHASUS33XXX for JPM), beneficiary account, and settlement gateway (TARGET2). Resubmit corrected MT544 instruction prior to 14:00 CET cutoff.',
    sla: '< 45 Mins',
    appliesTo: ['JPMorgan Chase', 'TARGET2', 'CHASUS33XXX', 'TRD-998822'],
  },
  {
    id: 'SOP-TL-001',
    title: 'Trade-to-Instrument Allocation & Desk Booking Linkage',
    domain: 'TRADE_LINKAGE',
    threshold: 'Validated CUSIP/ISIN (Auto-Exec) | Unknown Instrument (Desk Review)',
    rules: 'Verify trade ID against front-office trade feeder. Validate CUSIP/ISIN with Bloomberg/Reuters reference feed. Link trade to appropriate trading desk book (e.g. EQ-US-FLOW).',
    sla: '< 15 Mins',
    appliesTo: ['Apple Inc', 'US0378331005', 'TRD-2024-88712', 'EQ-US-FLOW'],
  },
  {
    id: 'SOP-REF-002',
    title: 'Instrument Master Data Exception & ISIN/CUSIP Remapping',
    domain: 'INSTRUMENT_CORRECTION',
    threshold: 'ISO 6166 Checksum Valid (Auto-Exec) | Invalid Checksum (Data Steward)',
    rules: 'When ISIN mismatch alert is raised, validate checksum using ISO 6166 algorithm. Patch Position Keeper and notify Risk Engine with automated rollback snapshot.',
    sla: '< 30 Mins',
    appliesTo: ['XS0987654321', 'XS1234567890', 'POS-44332'],
  },
  {
    id: 'SOP-SUP-001',
    title: 'Operations Systems Access Provisioning & Role Granting',
    domain: 'SUPPORT_TICKET',
    threshold: 'Director Approval Present (Auto-Exec P3) | Missing Sign-off (Escalate)',
    rules: 'Verify requester identity against HR active directory. Auto-create ServiceNow ticket in Access Management queue with P3 SLA (4 hours). Route to Desk Head.',
    sla: '< 4 Hours',
    appliesTo: ['ServiceNow', 'John Doe', 'EMP-883921'],
  },
];

export default function OperationsCopilot({
  emails,
  onSelectEmail,
  onApproveEmail,
  onRejectEmail,
  isOpen: initialIsOpen = false,
  onClose,
}: OperationsCopilotProps) {
  const [isOpen, setIsOpen] = useState(initialIsOpen);
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputQuery, setInputQuery] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [speechEnabled, setSpeechEnabled] = useState(false);
  const [activeAudioVisualizer, setActiveAudioVisualizer] = useState(false);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome_1',
      sender: 'copilot',
      timestamp: 'Just now',
      text: `👋 **Hello Trader / Operations Specialist!** I am your **Back-Office AI Copilot** connected to Société Générale's live email ingestion pipeline, Cosmos DB state store, and Azure AI Search SOP knowledge runbooks.\n\nAsk me anything in natural language or click one of the quick queries below!`,
      metrics: {
        latencyMs: 12,
        tokens: 45,
        confidence: 0.99,
        sources: ['CosmosDB:OperationsState', 'AzureAISearch:SOPRunbooks'],
      },
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);

  // Sync external isOpen prop if provided
  useEffect(() => {
    if (initialIsOpen !== undefined) {
      setIsOpen(initialIsOpen);
    }
  }, [initialIsOpen]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isThinking]);

  // Initialize Web Speech API if supported
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setVoiceSupported(true);
        const recog = new SpeechRecognition();
        recog.continuous = false;
        recog.interimResults = true;
        recog.lang = 'en-US';

        recog.onresult = (event: any) => {
          let transcript = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
          }
          setInputQuery(transcript);
        };

        recog.onstart = () => {
          setIsListening(true);
          setActiveAudioVisualizer(true);
        };

        recog.onend = () => {
          setIsListening(false);
          setActiveAudioVisualizer(false);
        };

        recog.onerror = () => {
          setIsListening(false);
          setActiveAudioVisualizer(false);
        };

        recognitionRef.current = recog;
      }
    }
  }, []);

  const handleVoiceToggle = () => {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      setActiveAudioVisualizer(false);
    } else {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
          setIsListening(true);
          setActiveAudioVisualizer(true);
        } catch (e) {
          simulateVoiceInput();
        }
      } else {
        simulateVoiceInput();
      }
    }
  };

  // Fallback realistic voice simulation
  const simulateVoiceInput = () => {
    setIsListening(true);
    setActiveAudioVisualizer(true);
    setInputQuery('');

    const sampleQueries = [
      'Show me all failed settlements with JPM over $1M',
      'What is the SOP rule for SAP dividend?',
      'Summarize pending supervisor approvals',
      'Explain why email_1 was flagged as high risk',
    ];
    const picked = sampleQueries[Math.floor(Math.random() * sampleQueries.length)];

    let currIdx = 0;
    const interval = setInterval(() => {
      if (currIdx <= picked.length) {
        setInputQuery(picked.slice(0, currIdx));
        currIdx++;
      } else {
        clearInterval(interval);
        setIsListening(false);
        setActiveAudioVisualizer(false);
      }
    }, 40);
  };

  // Text to speech playback
  const speakText = (text: string) => {
    if (!speechEnabled || typeof window === 'undefined' || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    // Clean markdown syntax for speech
    const cleanText = text
      .replace(/[*_#`[\]()]/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .slice(0, 300);
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // Query Resolution Engine
  const processQuery = (rawQuery: string) => {
    const q = rawQuery.trim().toLowerCase();
    const queryTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let responseText = '';
    let queryType: Message['queryType'] = 'GENERAL';
    let cards: Message['cards'] = [];
    let sources: string[] = ['CosmosDB:OperationsState'];

    // 1. "Show me all failed settlements with JPM over $1M" or Settlement queries
    if (
      (q.includes('failed') || q.includes('settlement') || q.includes('ssi')) &&
      (q.includes('jpm') || q.includes('jpmorgan') || q.includes('1m') || q.includes('million') || q.includes('target2'))
    ) {
      queryType = 'SETTLEMENT_QUERY';
      sources.push('SOP-SET-003', 'TARGET2:GatewayLedger');
      
      const jpmSettlements = emails.filter(
        (e) =>
          e.intent === 'SETTLEMENT' ||
          e.entities.counterparty?.toLowerCase().includes('jpmorgan') ||
          e.entities.counterparty?.toLowerCase().includes('jpm') ||
          e.rawBody.toLowerCase().includes('jpmorgan')
      );

      if (jpmSettlements.length > 0) {
        const item = jpmSettlements[0];
        responseText = `🔎 Found **${jpmSettlements.length} failed settlement exception** involving **JPMorgan Chase (CHASUS33XXX)** exceeding **$1,000,000**:\n\n` +
          `• **Trade Ref**: \`${item.entities.tradeId || 'TRD-998822'}\`\n` +
          `• **Notional Amount**: **$${(item.entities.amount || 2450000).toLocaleString()} ${item.entities.currency || 'USD'}**\n` +
          `• **Failure Reason**: Unmatched Beneficiary IBAN in TARGET2 matching engine\n` +
          `• **SOP Resolution**: Applied **SOP-SET-003** (Counterparty SSI Directory lookup -> patched to COBADEFF account)\n` +
          `• **Status**: **${item.status}** (SWIFT MT544 instruction resubmitted before 14:00 CET cutoff)\n` +
          `• **Risk Score**: ${item.riskScore} (Medium Risk - Standard reversible SSI fix)`;

        cards.push({
          type: 'email',
          title: `Trade ${item.entities.tradeId || 'TRD-998822'} - Settlement Exception`,
          data: item,
        });
      } else {
        responseText = `No active failed settlements with JPM over $1M found in the current settlement window. All TARGET2 queues are synchronized.`;
      }
    }
    // 2. "What is the SOP rule for SAP dividend?" or SOP queries
    else if (
      (q.includes('sop') || q.includes('rule') || q.includes('runbook') || q.includes('policy')) &&
      (q.includes('sap') || q.includes('dividend') || q.includes('cash') || q.includes('corporate action') || q.includes('ca-001'))
    ) {
      queryType = 'SOP_QUERY';
      sources.push('AzureAISearch:SOP-CA-001', 'CSD:ClearstreamEuroclear');
      const sop = SOP_DATABASE.find((s) => s.id === 'SOP-CA-001')!;

      responseText = `📖 **Runbook Retrieved: ${sop.id} — ${sop.title}**\n\n` +
        `• **Target Domain**: \`${sop.domain}\`\n` +
        `• **Operational Threshold**: ${sop.threshold}\n` +
        `• **Standard Operating Rule**:\n> "${sop.rules}"\n\n` +
        `• **Target SLA**: ${sop.sla}\n` +
        `• **Current Trigger**: SAP SE (ISIN: \`DE0007164600\`) announced a cash dividend of **€2.20/share**. Since this exceeds the **€2.00 autonomous threshold**, human-in-the-loop (HITL) supervisor approval is mandatory before entitlement booking.`;

      cards.push({
        type: 'sop',
        title: `${sop.id} - Institutional SOP Runbook`,
        data: sop,
      });
    }
    // 3. "Summarize pending supervisor approvals"
    else if (
      q.includes('pending') ||
      (q.includes('supervisor') && q.includes('approval')) ||
      q.includes('queue') ||
      q.includes('hitl') ||
      q.includes('awaiting')
    ) {
      queryType = 'APPROVAL_SUMMARY';
      const pending = emails.filter((e) => e.status === 'PENDING_APPROVAL' || e.requiresApproval);
      sources.push('CosmosDB:ApprovalQueue', 'MSTeams:AdaptiveCardGateway');

      if (pending.length > 0) {
        responseText = `⚠️ **Supervisor Approval Queue Summary:** There is currently **${pending.length} item** awaiting supervisor authorization:\n\n`;
        pending.forEach((p, idx) => {
          responseText += `${idx + 1}. **[${p.id}]** **${p.subject}**\n` +
            `   • **Sender**: ${p.senderName} (${p.senderOrg})\n` +
            `   • **Intent**: \`${p.intent}\` | **Risk Score**: \`${p.riskScore}\` (HIGH)\n` +
            `   • **Gating Reason**: Dividend rate €2.20 exceeds €2.00 autonomous ceiling (SOP-CA-001).\n` +
            `   • **Teams Alert**: Notification dispatched via Adaptive Card v1.5 with JWT 1-click token.\n`;

          cards.push({
            type: 'approval',
            title: `Pending Authorization: ${p.id}`,
            data: p,
          });
        });
      } else {
        responseText = `✅ **No pending supervisor approvals!** All processed messages have either been auto-executed via STP rules or previously signed off by operations supervisors.`;
      }
    }
    // 4. "Explain why email_1 was flagged as high risk"
    else if (
      (q.includes('why') || q.includes('explain') || q.includes('flagged') || q.includes('reason')) &&
      (q.includes('email_1') || q.includes('high risk') || q.includes('sap') || q.includes('risk score'))
    ) {
      queryType = 'RISK_EXPLANATION';
      const targetEmail = emails.find((e) => e.id === 'email_1') || emails[0];
      sources.push('RiskScorerAgent:ModelV3', 'GuardrailShield:PII', 'SOP-CA-001');

      responseText = `🛡️ **Risk Diagnostic Breakdown for \`${targetEmail.id}\` (Overall Risk: 0.88 / HIGH)**:\n\n` +
        `1. **Financial Exposure Weight (40%)**: Cash dividend rate of **€2.20/share** impacts 14 customer accounts with 14,000 shares (total gross liability **€30,800.00**).\n` +
        `2. **SOP Threshold Breach (35%)**: SOP-CA-001 strictly sets €2.00 as the maximum threshold for straight-through-processing (STP). Rates > €2.00 require manual four-eyes review.\n` +
        `3. **External Entity Communication (15%)**: Originated from DTCC Clearing with sensitive broker contact details and clearing account references.\n` +
        `4. **PII Sanitization (10%)**: 3 PII entities masked ([PHONE_1], [PERSONAL_EMAIL_1], [BANK_ACCOUNT_1]) prior to GPT-4o submission.\n\n` +
        `🎯 **Action Taken**: Automatically held in Pending Approval queue & broadcast to Operations Supervisor via Teams.`;

      cards.push({
        type: 'risk_breakdown',
        title: `Risk Breakdown - ${targetEmail.id}`,
        data: targetEmail,
      });
    }
    // 5. PII / Security queries
    else if (
      q.includes('pii') ||
      q.includes('mask') ||
      q.includes('injection') ||
      q.includes('security') ||
      q.includes('shield') ||
      q.includes('redact')
    ) {
      sources.push('PIIGuardrailShield:Telemetry', 'PromptShieldEngine');
      const totalMasks = emails.reduce((acc, e) => acc + e.piiReport.maskCount, 0);
      const passedInjections = emails.filter((e) => e.piiReport.injectionShieldPassed).length;

      responseText = `🛡️ **PII & Guardrail Security Telemetry Report**:\n\n` +
        `• **Total PII Entities Redacted**: **${totalMasks} tokens** across IBANs, Phone numbers, SSNs/TINs, and Personal Emails.\n` +
        `• **Prompt Injection Shield**: **100% Passed (${passedInjections}/${emails.length} safe)**. Zero jailbreak or prompt override attempts detected.\n` +
        `• **Financial Entity Preservation**: Strict allowlist preserved all ISO 6166 ISINs (e.g. \`DE0007164600\`, \`XS0987654321\`), CUSIPs (\`037833100\`), and SWIFT BICs (\`CHASUS33XXX\`).\n` +
        `• **Compliance Standard**: GDPR Article 9 & SOC-2 Type II compliant ephemeral token vault.`;
    }
    // 6. Generic SOP search
    else if (q.includes('sop') || q.includes('runbook') || q.includes('procedure')) {
      queryType = 'SOP_QUERY';
      sources.push('AzureAISearch:Index');
      responseText = `📚 **Société Générale Back-Office SOP Knowledge Base**:\n\n` +
        `I have active indexing across **5 production runbooks**:\n\n` +
        SOP_DATABASE.map(
          (s) => `• **\`${s.id}\`**: ${s.title} *(SLA: ${s.sla})*`
        ).join('\n') +
        `\n\nYou can ask me specific details on any SOP ID or financial operation!`;
    }
    // 7. Fallback intelligent response
    else {
      queryType = 'GENERAL';
      sources.push('GPT-4o:BackOfficeReasoning');
      responseText = `🤖 **Copilot Analysis for:** "${rawQuery}"\n\n` +
        `I analyzed the current pipeline state containing **${emails.length} operational emails** across Corporate Actions, Settlements, Trade Linkages, Reference Data Corrections, and Support Tickets.\n\n` +
        `• **Straight-Through-Processing (STP) Rate**: ${((emails.filter(e => e.status === 'AUTO_EXECUTED').length / emails.length) * 100).toFixed(0)}%\n` +
        `• **Average System Latency**: ~340ms per email\n` +
        `• **Average Risk Score**: ${(emails.reduce((a, b) => a + b.riskScore, 0) / emails.length).toFixed(2)}\n\n` +
        `Try asking:\n` +
        `• *"Show me all failed settlements with JPM over $1M"*\n` +
        `• *"What is the SOP rule for SAP dividend?"*\n` +
        `• *"Summarize pending supervisor approvals"*\n` +
        `• *"Explain why email_1 was flagged as high risk"*`;
    }

    return {
      responseText,
      queryType,
      cards,
      sources,
    };
  };

  const handleSend = (textToSend?: string) => {
    const query = textToSend || inputQuery;
    if (!query.trim()) return;

    const userMessage: Message = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: query,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setIsThinking(true);

    // Simulate realistic AI generation latency (300ms to 650ms)
    setTimeout(() => {
      const result = processQuery(query);
      const copilotMessage: Message = {
        id: `cop_${Date.now()}`,
        sender: 'copilot',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: result.responseText,
        queryType: result.queryType,
        cards: result.cards,
        metrics: {
          latencyMs: Math.floor(Math.random() * 150) + 120,
          tokens: Math.floor(Math.random() * 90) + 60,
          confidence: 0.98,
          sources: result.sources,
        },
      };

      setMessages((prev) => [...prev, copilotMessage]);
      setIsThinking(false);

      if (speechEnabled) {
        speakText(result.responseText);
      }
    }, 450);
  };

  const handleQuickPrompt = (prompt: string) => {
    handleSend(prompt);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        sender: 'copilot',
        timestamp: 'Just now',
        text: `Conversation reset. Ready for back-office and operations queries!`,
        metrics: {
          latencyMs: 8,
          tokens: 20,
          confidence: 1.0,
          sources: ['CosmosDB:OperationsState'],
        },
      },
    ]);
  };

  // Render markdown bold and quotes cleanly
  const renderFormattedText = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      // Blockquotes
      if (line.startsWith('> ')) {
        return (
          <div key={idx} className="border-l-2 border-indigo-400 pl-3 py-1 my-1.5 text-xs italic text-indigo-200 bg-indigo-950/30 rounded-r">
            {line.substring(2)}
          </div>
        );
      }
      // Bullet points
      if (line.startsWith('• ') || line.startsWith('- ')) {
        const bulletContent = line.substring(2);
        return (
          <div key={idx} className="flex items-start gap-1.5 my-1 text-xs text-slate-200 leading-relaxed">
            <span className="text-sky-400 mt-0.5">•</span>
            <span>{parseInlineBoldAndCode(bulletContent)}</span>
          </div>
        );
      }
      // Numbered lists
      if (/^\d+\.\s/.test(line)) {
        return (
          <div key={idx} className="my-1.5 text-xs text-slate-200 leading-relaxed">
            {parseInlineBoldAndCode(line)}
          </div>
        );
      }
      // Empty line
      if (line.trim() === '') {
        return <div key={idx} className="h-1.5" />;
      }
      // Regular text
      return (
        <p key={idx} className="text-xs text-slate-200 leading-relaxed">
          {parseInlineBoldAndCode(line)}
        </p>
      );
    });
  };

  const parseInlineBoldAndCode = (text: string) => {
    // Splits text into chunks of bold (**...**), code (`...`), and regular text
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*.*?\*\*|`.*?`)/g;
    let lastIdx = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push(text.substring(lastIdx, match.index));
      }
      const matchText = match[0];
      if (matchText.startsWith('**') && matchText.endsWith('**')) {
        parts.push(
          <strong key={match.index} className="font-bold text-white">
            {matchText.slice(2, -2)}
          </strong>
        );
      } else if (matchText.startsWith('`') && matchText.endsWith('`')) {
        parts.push(
          <code
            key={match.index}
            className="px-1.5 py-0.5 rounded bg-[#1e293b] border border-sky-500/30 text-sky-300 font-mono text-[11px]"
          >
            {matchText.slice(1, -1)}
          </code>
        );
      }
      lastIdx = regex.lastIndex;
    }

    if (lastIdx < text.length) {
      parts.push(text.substring(lastIdx));
    }

    return parts.length > 0 ? parts : text;
  };

  return (
    <>
      {/* 1. FLOATING ACTION TRIGGER BUTTON (When closed) */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-40 animate-bounce-subtle">
          <button
            onClick={() => setIsOpen(true)}
            className="group relative flex items-center gap-3 bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-600 hover:from-sky-500 hover:to-purple-500 text-white px-5 py-3.5 rounded-2xl shadow-2xl border border-sky-400/30 transition-all transform hover:scale-105 active:scale-95"
            title="Open Operations AI Copilot"
          >
            <div className="relative">
              <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center backdrop-blur-sm">
                <Bot className="text-sky-200 animate-pulse" size={20} />
              </div>
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            </div>

            <div className="text-left">
              <div className="flex items-center gap-1.5 text-xs font-bold text-white tracking-wide">
                <span>AI Copilot</span>
                <span className="px-1.5 py-0.2 bg-white/20 rounded-md text-[9px] font-semibold text-sky-200">
                  GPT-4o
                </span>
              </div>
              <div className="text-[10px] text-sky-200/80 font-medium">Ask operations & SOP queries</div>
            </div>

            <Sparkles size={16} className="text-amber-300 ml-1 group-hover:rotate-12 transition-transform" />
          </button>
        </div>
      )}

      {/* 2. COPILOT DRAWER / MODAL PANEL (When open) */}
      {isOpen && (
        <div
          className={`fixed bottom-0 right-0 z-50 flex flex-col bg-[#0b1120] border-t md:border-l border-[#1e293b] shadow-2xl transition-all duration-300 ease-out ${
            isExpanded
              ? 'w-full md:w-[780px] h-[92vh] md:rounded-tl-3xl'
              : 'w-full md:w-[460px] h-[680px] max-h-[92vh] md:rounded-tl-2xl'
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1e293b] bg-[#131d35] md:rounded-tl-2xl">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-lg border border-sky-400/30">
                  <Bot size={20} />
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[#131d35]"></span>
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">Operations AI Copilot</h3>
                  <span className="text-[10px] bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded-full font-mono font-semibold border border-sky-500/30">
                    Back-Office v2.4
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  RAG Connected: Cosmos DB & Azure AI Search
                </p>
              </div>
            </div>

            {/* Header Action Controls */}
            <div className="flex items-center gap-1">
              {/* Text to Speech Toggle */}
              <button
                onClick={() => setSpeechEnabled(!speechEnabled)}
                className={`p-1.5 rounded-lg transition-colors ${
                  speechEnabled
                    ? 'text-sky-400 bg-sky-500/20 border border-sky-500/40'
                    : 'text-slate-400 hover:text-white hover:bg-[#1e293b]'
                }`}
                title={speechEnabled ? 'Mute AI voice readback' : 'Enable AI voice readback'}
              >
                {speechEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>

              {/* Clear Chat */}
              <button
                onClick={clearChat}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1e293b] transition-colors"
                title="Reset conversation"
              >
                <RefreshCw size={15} />
              </button>

              {/* Expand / Minimize */}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="hidden md:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1e293b] transition-colors"
                title={isExpanded ? 'Collapse panel' : 'Expand panel'}
              >
                {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>

              {/* Close Drawer */}
              <button
                onClick={() => {
                  setIsOpen(false);
                  if (onClose) onClose();
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-rose-500/20 hover:text-rose-400 transition-colors"
                title="Close assistant"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Quick Prompt Chips Ribbon */}
          <div className="bg-[#0e1628] px-4 py-2 border-b border-[#1e293b] flex items-center gap-1.5 overflow-x-auto scrollbar-thin">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1 mr-1 shrink-0">
              <Sparkles size={11} className="text-amber-400" /> Prompts:
            </span>
            {QUICK_PROMPTS.map((qp, idx) => {
              const IconComp = qp.icon;
              return (
                <button
                  key={idx}
                  onClick={() => handleQuickPrompt(qp.query)}
                  className="shrink-0 flex items-center gap-1 px-2.5 py-1 bg-[#131d35] hover:bg-sky-950/60 border border-[#1e293b] hover:border-sky-500/40 rounded-lg text-[11px] font-medium text-slate-300 hover:text-sky-200 transition-all active:scale-95"
                >
                  <IconComp size={11} className="text-sky-400" />
                  <span>{qp.label}</span>
                </button>
              );
            })}
          </div>

          {/* Chat Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-[#0b1120] to-[#070b14]">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} space-y-1.5`}
              >
                {/* Sender Tag & Timestamp */}
                <div className="flex items-center gap-1.5 px-1 text-[10px] text-slate-500">
                  {msg.sender === 'copilot' ? (
                    <>
                      <Bot size={11} className="text-sky-400" />
                      <span className="font-semibold text-sky-400">Operations Copilot</span>
                      <span>•</span>
                      <span>{msg.timestamp}</span>
                    </>
                  ) : (
                    <>
                      <span className="font-semibold text-slate-400">You (Operations Desk)</span>
                      <span>•</span>
                      <span>{msg.timestamp}</span>
                    </>
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  className={`p-3.5 rounded-2xl max-w-[92%] text-xs shadow-lg transition-all ${
                    msg.sender === 'user'
                      ? 'bg-gradient-to-br from-sky-600 to-indigo-600 text-white rounded-tr-none'
                      : 'bg-[#131d35] border border-[#1e293b] text-slate-200 rounded-tl-none space-y-2.5'
                  }`}
                >
                  {/* Bubble Content */}
                  <div>{renderFormattedText(msg.text)}</div>

                  {/* Interactive Cards (If any attached) */}
                  {msg.cards && msg.cards.length > 0 && (
                    <div className="mt-3 space-y-2 pt-2 border-t border-[#1e293b]">
                      {msg.cards.map((card, cIdx) => (
                        <div
                          key={cIdx}
                          className="bg-[#0b1120] border border-[#1e293b] hover:border-sky-500/40 rounded-xl p-3 space-y-2 transition-all"
                        >
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                              {card.type === 'email' && <Layers size={13} className="text-sky-400" />}
                              {card.type === 'sop' && <BookOpen size={13} className="text-purple-400" />}
                              {card.type === 'approval' && <Clock size={13} className="text-amber-400" />}
                              {card.type === 'risk_breakdown' && <AlertTriangle size={13} className="text-rose-400" />}
                              <span className="text-[11px] font-bold text-white">{card.title}</span>
                            </div>

                            {card.type === 'email' && card.data && onSelectEmail && (
                              <button
                                onClick={() => onSelectEmail(card.data)}
                                className="flex items-center gap-1 text-[10px] font-semibold text-sky-400 hover:text-sky-300 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/30 transition-colors"
                              >
                                <span>Inspect</span>
                                <ArrowRight size={10} />
                              </button>
                            )}

                            {card.type === 'approval' && card.data && onApproveEmail && (
                              <div className="flex items-center gap-1.5">
                                <button
                                  onClick={() => onApproveEmail(card.data.id)}
                                  className="flex items-center gap-1 text-[10px] font-bold text-emerald-300 bg-emerald-500/20 hover:bg-emerald-500/30 px-2.5 py-1 rounded border border-emerald-500/40 transition-colors"
                                >
                                  <CheckCircle2 size={10} />
                                  <span>Authorize</span>
                                </button>
                                {onRejectEmail && (
                                  <button
                                    onClick={() => onRejectEmail(card.data.id)}
                                    className="flex items-center gap-1 text-[10px] font-bold text-rose-300 bg-rose-500/20 hover:bg-rose-500/30 px-2 py-1 rounded border border-rose-500/40 transition-colors"
                                  >
                                    <X size={10} />
                                  </button>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Quick Mini Metadata */}
                          {card.type === 'email' && card.data && (
                            <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 bg-[#131d35] p-2 rounded-lg font-mono">
                              <div>
                                <span className="text-slate-500">Counterparty:</span>{' '}
                                <span className="text-slate-200">{card.data.entities?.counterparty || 'JPMorgan'}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Amount:</span>{' '}
                                <span className="text-emerald-400">${(card.data.entities?.amount || 0).toLocaleString()}</span>
                              </div>
                            </div>
                          )}

                          {card.type === 'sop' && card.data && (
                            <div className="text-[10px] text-slate-300 bg-[#131d35] p-2 rounded-lg">
                              <span className="text-purple-300 font-semibold">Rule Threshold:</span>{' '}
                              {card.data.threshold}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Metadata & Audit Footnotes */}
                  {msg.metrics && (
                    <div className="flex items-center justify-between gap-2 pt-2 border-t border-[#1e293b]/60 text-[10px] text-slate-400 font-mono">
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-sky-400/80">
                          <Terminal size={10} /> {msg.metrics.latencyMs}ms
                        </span>
                        <span>•</span>
                        <span>{msg.metrics.tokens} tokens</span>
                      </div>
                      {msg.metrics.sources && msg.metrics.sources.length > 0 && (
                        <div className="text-[9px] text-indigo-300 truncate max-w-[200px]" title={msg.metrics.sources.join(', ')}>
                          Sources: {msg.metrics.sources[0]}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Thinking / Streaming Indicator */}
            {isThinking && (
              <div className="flex flex-col items-start space-y-1.5 animate-fadeIn">
                <div className="flex items-center gap-1.5 px-1 text-[10px] text-slate-500">
                  <Bot size={11} className="text-sky-400" />
                  <span className="font-semibold text-sky-400">Operations Copilot</span>
                  <span>•</span>
                  <span>Reasoning...</span>
                </div>
                <div className="bg-[#131d35] border border-sky-500/30 rounded-2xl rounded-tl-none p-3.5 shadow-lg flex items-center gap-3">
                  <div className="flex space-x-1.5">
                    <div className="w-2 h-2 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-xs text-slate-300 font-mono">Scanning SOP runbooks & pipeline state...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Voice Visualizer Banner (When listening) */}
          {activeAudioVisualizer && (
            <div className="bg-gradient-to-r from-sky-950/80 via-indigo-950/80 to-purple-950/80 px-4 py-2 border-t border-sky-500/30 flex items-center justify-between text-xs text-sky-200 animate-pulse">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
                <span className="font-semibold text-white">Listening to voice query...</span>
              </div>
              <div className="flex items-center gap-1">
                {[...Array(8)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-sky-400 rounded-full animate-pulse"
                    style={{
                      height: `${Math.floor(Math.random() * 18) + 6}px`,
                      animationDuration: `${300 + i * 100}ms`,
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Input Bar & Controls */}
          <div className="p-3.5 bg-[#131d35] border-t border-[#1e293b]">
            <div className="relative flex items-center bg-[#0b1120] border border-[#1e293b] focus-within:border-sky-500/60 rounded-xl transition-all shadow-inner">
              <input
                ref={inputRef}
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about failed trades, SAP SOP rules, supervisor approvals..."
                className="flex-1 bg-transparent py-2.5 pl-3.5 pr-20 text-xs text-white placeholder-slate-500 focus:outline-none"
              />

              <div className="absolute right-2 flex items-center gap-1">
                {/* Voice / Mic Button */}
                <button
                  onClick={handleVoiceToggle}
                  className={`p-1.5 rounded-lg transition-all ${
                    isListening
                      ? 'bg-rose-500 text-white animate-bounce'
                      : 'text-slate-400 hover:text-white hover:bg-[#1e293b]'
                  }`}
                  title={isListening ? 'Stop listening' : 'Voice Query / Speech-to-Text'}
                >
                  {isListening ? <MicOff size={15} /> : <Mic size={15} />}
                </button>

                {/* Send Button */}
                <button
                  onClick={() => handleSend()}
                  disabled={!inputQuery.trim() || isThinking}
                  className="p-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:hover:bg-sky-600 text-white transition-all shadow-md active:scale-95"
                  title="Send Query (Enter)"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>

            {/* Bottom Status bar */}
            <div className="flex justify-between items-center px-1 pt-2 text-[10px] text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                SocGen Sovereign Model: <strong className="text-slate-400">Azure OpenAI GPT-4o</strong>
              </span>
              <span className="hidden sm:inline">Press Enter ↵ to query</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
