# 🏛️ Azure Cloud Infrastructure, Architecture & Cost Specification
### Société Générale Capital Markets · Orbit (MailMind) Enterprise Platform

---

## 📌 1. Global Topology & Cloud Resource Inventory

| Resource Name | Azure Resource Type | SKU / Flavor / Tier | Region | Resource Group | Endpoint / Target | Primary Responsibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ambitious-moss-048f25a0f`** | Azure Static Web Apps | **Standard** (Global CDN Edge) | `East US 2` / Global Edge | `rg-mailmind` | `https://ambitious-moss-048f25a0f.5.azurestaticapps.net` | Real-time Operations & SRE Observability Dashboard |
| **`mailmind-openai-3207`** | Azure OpenAI Service | **S0** (Cognitive Services) <br>Deployment: `gpt-4o` (Standard 50K TPM) | `East US` | `rg-mailmind` | `https://mailmind-openai-3207.openai.azure.com/` | Intent Classification, Financial NER Extraction, Reasoning |
| **`mailmind-search-3207`** | Azure AI Search | **Standard S1** (1 Search Unit, 25 GB) | `East US` | `rg-mailmind` | `https://mailmind-search-3207.search.windows.net` | Semantic Vector & Hybrid RAG across SOPs & Historical Resolutions |
| **`mailmind-cosmos-3209`** | Azure Cosmos DB (NoSQL) | **Serverless / Autoscale** (Multi-region ready) | `East US` | `rg-mailmind` | `https://mailmind-cosmos-3209.documents.azure.com:443/` | Immutable Compliance Audit Trail, Processed Emails, Action Records |
| **`mailmind-functions-3207`** | Azure Functions (Linux) | **Consumption (Y1)** (Dynamic Serverless) | `East US` | `rg-mailmind` | `https://mailmind-functions-3207.azurewebsites.net` | Event-Driven Back-Office Action Execution Microservices |
| **`orbit-vault-3207`** | Azure Key Vault | **Standard** (Hardware/Software protected) | `East US` | `rg-mailmind` | `https://orbit-vault-3207.vault.azure.net/` | Zero-Trust Credential & Secret Dynamic Resolution |
| **`mailmindstore3207`** | Azure Storage Account | **Standard General Purpose v2 (LRS)** (Hot tier) | `East US` | `rg-mailmind` | `https://mailmindstore3207.blob.core.windows.net/` | SWIFT PDF/XML Ingest, Dead Letter Queue storage, Function logs |
| **`orbit-law-3207`** | Azure Log Analytics Workspace | **Per GB Ingestion** (30-day retention) | `East US` | `rg-mailmind` | Workspace ID: `8f72a11b-4190-4c33-b148-e87740f93207` | Centralized Telemetry, SRE Metrics, KQL Querying |
| **`orbit-insights-3207`** | Azure Application Insights | **Standard** (OpenTelemetry Exporter) | `East US` | `rg-mailmind` | App ID: `a789d1f7-e877-4e38-8a95-b7e27ab4d399` | Distributed Tracing, Circuit Breaker Telemetry, SLA Metrics |
| **`orbit-eventgrid-3207`** | Azure Event Grid Topic | **Basic / Standard** (Push delivery) | `East US` | `rg-mailmind` | Event Grid Domain Topic | Ingestion Pub/Sub from Microsoft Graph API Mailbox Webhook |

---

## 💰 2. SKU Specifications & Monthly Cost Breakdown (TCO)

### A. Development & Demo Tier (Current Deployed Footprint)

| Component | Azure SKU / Meter | Spec / Capacity | Unit Cost (USD) | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Azure Static Web Apps** | Standard Tier | Custom domains, SLA 99.95%, Global Edge | \$9.00 / app / month | **\$9.00** |
| **Azure OpenAI Service** | S0 (GPT-4o) | ~1,000,000 Input tokens + 250,000 Output tokens | \$2.50 / 1M in, \$10.00 / 1M out | **\$5.00** |
| **Azure AI Search** | Standard S1 | 1 Search Unit (1 Partition × 1 Replica), 25 GB | \$0.336 / hour (~730 hrs) | **\$245.28** |
| **Azure Cosmos DB** | Serverless | ~1,000,000 Request Units (RU) + 2 GB Storage | \$0.25 / 1M RU + \$0.25 / GB | **\$0.75** |
| **Azure Functions** | Consumption Plan (Y1) | 1,000,000 executions + 400,000 GB-s | First 1M free, \$0.000016 / GB-s | **\$0.00** (Within Free Tier) |
| **Azure Key Vault** | Standard Tier | ~10,000 Secret operations / month | \$0.03 / 10,000 operations | **\$0.03** |
| **Azure Blob Storage** | Standard v2 (LRS, Hot) | 10 GB Data + 50,000 Read/Write Ops | \$0.018 / GB + \$0.05 / 10K writes | **\$0.43** |
| **Azure Log Analytics & App Insights** | Pay-as-you-go | 5 GB Ingestion / month (First 5 GB Free / month) | \$2.30 / GB beyond free allowance | **\$0.00** (Within Free Tier) |
| **Azure Event Grid** | Standard Operations | 100,000 operations / month | First 100K operations free | **\$0.00** (Within Free Tier) |
| **TOTAL ESTIMATED (Dev/Demo)** | | | | **~\$260.49 / month** |

---

### B. Enterprise Production Scale (5,000,000 Operational Emails / Month)

For a Tier-1 Investment Bank (Société Générale Global Markets) with high availability and multi-region failover:

| Enterprise Component | Production SKU | Capacity & Redundancy | Monthly Cost (Est.) |
| :--- | :--- | :--- | :--- |
| **Azure Static Web Apps** | Enterprise Dedicated | Enterprise SLA, High Concurrency, Custom WAF | **\$50.00** |
| **Azure OpenAI (PTU / Provisioned)** | Provisioned Throughput (PTU) | 100 PTUs (Guaranteed latency < 800ms, Zero Rate-Limits) | **\$3,200.00** |
| **Azure AI Search** | Standard S2 (3 Replicas × 2 Partitions) | 6 Search Units (High Availability 99.99%, 200 QPS) | **\$2,940.00** |
| **Azure Cosmos DB** | Provisioned 10,000 RU/s Autoscale | Multi-Region Active-Active (East US + West Europe) | **\$1,168.00** |
| **Azure Functions** | Elastic Premium Plan (EP2) | 3 Dedicated Pre-Warmed Linux Workers (Zero Cold Starts) | **\$540.00** |
| **Azure Key Vault** | Premium HSM Tier | Hardware Security Module (FIPS 140-2 Level 3) | **\$60.00** |
| **Azure Storage (GRS Archive)** | 5 TB Geo-Redundant + Cold Tier | 7-Year Regulatory Retention (MiFID II / FINRA) | **\$115.00** |
| **Azure Monitor & Log Analytics** | 100 GB/day Commitment Tier | Dedicated SRE Alerting & Application Performance Monitoring | **\$590.00** |
| **Azure Front Door Premium + WAF** | Global Anycast + DDoS | Bot Protection, Geo-Filtering, SSL Offload | **\$330.00** |
| **TOTAL ENTERPRISE PRODUCTION TCO** | | | **~\$8,993.00 / month** |

---

## 🗄️ 3. Database Architecture & Schema Specifications

### A. Azure Cosmos DB (`mailminddb`)
Cosmos DB is configured with **NoSQL API** using strict partitioning for sub-10ms point reads and compliance query performance.

```
mailminddb
├── 📂 emails        (Partition Key: /id)
├── 📂 audittrail    (Partition Key: /trace_id)
└── 📂 actions       (Partition Key: /action_id)
```

#### 1. Container: `emails` (`/id`)
Stores ingested, sanitized, and enriched email documents.
```json
{
  "id": "email_1",
  "emailId": "email_1",
  "sender": "notifications@dtcc.com",
  "sender_name": "Michael Braun",
  "sender_org": "DTCC Clearing Europe",
  "subject": "CORPORATE ACTION ANNOUNCEMENT: SAP SE DIVIDEND (ISIN DE0007164600)",
  "intent": "CORPORATE_ACTION",
  "urgency": "HIGH",
  "risk_score": 0.88,
  "requires_approval": true,
  "status": "PENDING_APPROVAL",
  "received_at": "2024-05-10T10:00:00Z",
  "saved_at": "2026-10-05T11:45:00Z",
  "sanitized_body": "CONFIDENTIAL - DTCC Corporate Actions Announcement...\nDirect contact officer: Michael Braun ([PHONE_1], [PERSONAL_EMAIL_1]).\nInternal clearing account reference: [BANK_ACCOUNT_1].",
  "pii_report": {
    "pii_detected": true,
    "mask_count": 3,
    "masked_types": ["PHONE", "PERSONAL_EMAIL", "BANK_ACCOUNT"],
    "injection_shield_passed": true
  },
  "entities": {
    "isin": "DE0007164600",
    "counterparty": "SAP SE / DTCC",
    "amount": 2.20,
    "currency": "EUR",
    "action_type": "MANDATORY_CASH_DIVIDEND"
  },
  "sop_applied": {
    "id": "SOP-CA-001",
    "title": "Mandatory Cash Dividend Reconciliation & Entitlement Processing",
    "relevance": 0.98
  },
  "_ts": 1728128700
}
```

#### 2. Container: `audittrail` (`/trace_id`)
Immutable regulatory compliance log preserving full cryptographic model trace, token usage, guardrail outputs, and execution timeline.
```json
{
  "id": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
  "trace_id": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
  "email_id": "email_1",
  "timestamp": "2026-10-05T11:45:01Z",
  "agents_executed": [
    {"agent": "PIIGuardrailShield", "status": "PASSED", "duration_ms": 18},
    {"agent": "ClassifierAgent", "intent": "CORPORATE_ACTION", "confidence": 0.984, "duration_ms": 145},
    {"agent": "ParserAgent", "isin": "DE0007164600", "duration_ms": 98},
    {"agent": "DecisionAgent", "sop_matched": "SOP-CA-001", "duration_ms": 112},
    {"agent": "RiskScorerAgent", "risk_score": 0.88, "gate": "SUPERVISOR_APPROVAL", "duration_ms": 64}
  ],
  "hitl_approval": {
    "requested_channel": "MS_TEAMS_WEBHOOK",
    "approver": "supervisor@socgen.com",
    "decision": "APPROVED",
    "decision_time": "2026-10-05T11:46:12Z"
  },
  "compliance_cert": "FINRA_2210_MIFID_II_VERIFIED"
}
```

#### 3. Container: `actions` (`/action_id`)
Tracks all downstream serverless execution dispatches and Target Core Banking response statuses.
```json
{
  "id": "CA-EVT-99281",
  "action_id": "CA-EVT-99281",
  "email_id": "email_1",
  "target_system": "Corporate Actions Processing Master",
  "status": "EXECUTED",
  "execution_timestamp": "2026-10-05T11:46:13Z",
  "payload": {
    "isin": "DE0007164600",
    "dividend_rate": 2.20,
    "currency": "EUR",
    "affected_accounts": 14,
    "total_shares": 14000
  },
  "acknowledgement_id": "ACK-XETRA-9901824"
}
```

---

### B. Azure AI Search Indexes (`mailmind-search-3207`)

#### 1. Index: `sops-index`
- **Fields**:
  - `id` (String, Key)
  - `domain` (String, Filterable, Facetable)
  - `title` (String, Searchable)
  - `rules` (String, Searchable, Vectorized)
  - `keywords` (Collection(String), Filterable, Searchable)
  - `vector` (Collection(Single), 1536 dims, `text-embedding-3-small`)
- **Search Mode**: Semantic Hybrid Search (BM25 + Cosine Vector Similarity + Semantic Re-ranker).

#### 2. Index: `historical-resolutions-index`
- **Fields**:
  - `id` (String, Key)
  - `subject` (String, Searchable)
  - `intent` (String, Filterable)
  - `resolution` (String, Searchable)
  - `risk_score` (Double, Filterable, Sortable)

---

### C. Azure Storage Account Containers (`mailmindstore3207`)

| Container / Table | Access Level | Purpose |
| :--- | :--- | :--- |
| `email-attachments` | Private | Stores raw MT564/MT544 PDF, XML, and CSV attachments ingested from Graph API. |
| `dlq-payloads` | Private | Stores failed message payloads exceeding maximum circuit breaker retries for SRE inspection. |
| `functions-runtime` | Private | Azure Functions serverless package zip files & execution logs. |

---

### D. Azure Log Analytics & Application Insights Tables (`orbit-law-3207`)

- **`AppTraces`**: Log messages emitted across all Python backend services, agent transitions, and circuit breaker trip events.
- **`AppDependencies`**: Outbound telemetry to Azure OpenAI, Azure AI Search, Azure Cosmos DB, and Microsoft Teams webhooks with duration and status code.
- **`AppRequests`**: Inbound HTTP/WebSocket requests to FastAPI orchestrator and Next.js frontend.
- **`OrbitSystemAlerts_CL`**: Custom SRE alerts (SLA breaches, P99 latency spikes, DLQ threshold crossings, Prompt Injection anomalies).

---

## 🏗️ 4. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph INGESTION["1. Ingestion & Communication Layer"]
        M365["📧 Microsoft 365 Exchange<br/>(Mailbox Webhook)"]
        GRAPH["⚡ Microsoft Graph API"]
        EGRID["📬 Azure Event Grid<br/>(orbit-eventgrid-3207)"]
        M365 --> GRAPH --> EGRID
    end

    subgraph SECURITY["2. Security & Guardrail Perimeter"]
        KV["🔐 Azure Key Vault<br/>(orbit-vault-3207)<br/>Zero-Trust Secrets"]
        PII["🛡️ PII Guardrail & Prompt Shield<br/>• Regex & Checksum Masking<br/>• Capital Market Identifier Preserver<br/>• Prompt Injection Classifier"]
        EGRID --> PII
        KV -.-> |RBAC Credentials| PII
    end

    subgraph ORCHESTRATOR["3. Multi-Agent AI Pipeline (Azure AI Foundry / OpenAI)"]
        direction TB
        ORCH["🎯 Multi-Agent Orchestrator"]
        CL["1. Classifier Agent<br/>(GPT-4o Intent Analysis)"]
        PA["2. Parser Agent<br/>(Financial NER Extraction)"]
        DA["3. Decision Agent<br/>(Azure AI Search RAG)"]
        RS["4. Risk Scorer Agent<br/>(0.00 – 1.00 Scoring Engine)"]

        PII --> ORCH
        ORCH --> CL --> PA --> DA --> RS
    end

    subgraph KNOWLEDGE["4. Knowledge & RAG Store"]
        SEARCH["🔍 Azure AI Search (S1)<br/>• SOP Knowledge Base<br/>• Historical Resolutions"]
        DA <--> |Hybrid Vector RAG| SEARCH
    end

    subgraph GOVERNANCE["5. Decision & Execution Gateway"]
        GATE{"⚖️ Risk Gate<br/>Score ≥ 0.70?"}
        RS --> GATE
        
        AUTO["⚡ Azure Functions (Y1)<br/>Serverless Auto-Execution<br/>• Corporate Actions<br/>• SSI Resubmission<br/>• Trade Linkage<br/>• ISIN Remap<br/>• ServiceNow ITSM"]
        
        HITL["👥 Microsoft Teams HITL<br/>Adaptive Card v1.5<br/>Supervisor Approval"]
        
        GATE -->|No (Score < 0.70)| AUTO
        GATE -->|Yes (Score ≥ 0.70)| HITL
        HITL -->|Approved| AUTO
        HITL -->|Rejected| REJ["🚫 Action Cancelled & Logged"]
    end

    subgraph STORAGE["6. Compliance & Persistence"]
        COSMOS[("📊 Azure Cosmos DB (mailminddb)<br/>• /emails<br/>• /audittrail<br/>• /actions")]
        BLOB["🗄️ Azure Storage (mailmindstore3207)<br/>• SWIFT MT564/MT544 Attachments"]
        AUTO --> COSMOS
        AUTO --> BLOB
    end

    subgraph OBSERVABILITY["7. SRE Observability & Alerting"]
        LAW["📉 Azure Log Analytics (orbit-law-3207)"]
        APPINS["📡 Azure Application Insights"]
        SWA["🌐 Azure Static Web Apps<br/>Operations Dashboard<br/>(ambitious-moss-048f25a0f)"]
        
        ORCH -.-> APPINS --> LAW
        COSMOS -.-> LAW
        LAW --> SWA
    end
```

---

## 🛡️ 5. Security, Resilience & Compliance Topology

1. **Zero-Trust Key Management**:
   - Zero hardcoded plaintext keys. All services use Azure Managed Identity (`DefaultAzureCredential`) or dynamic Key Vault retrieval (`orbit-vault-3207`).
2. **Circuit Breakers (`resilience.py`)**:
   - Built-in circuit breakers for `azure_openai`, `azure_search`, `cosmos_db`, and `graph_api`.
   - **Failure threshold**: 3 errors -> Trips to `OPEN` state.
   - **Recovery timeout**: 30 seconds -> Transitions to `HALF-OPEN` probe.
   - **Fallback mechanism**: Automatic in-memory cache and rule-based deterministic models if Azure services experience outages.
3. **Dead Letter Queue (DLQ)**:
   - Poison messages and malformed payloads are quarantined in `dlq_service` with one-click re-injection and debugging.
4. **Regulatory Audit Trail (FINRA / MiFID II)**:
   - Full non-repudiation audit trail recorded in Azure Cosmos DB capturing trace ID, raw payload, sanitized tokens, agent chain reasoning, and supervisor sign-offs.

---

*Document generated and synchronized with GitHub repository [`healer-ctrl/orbit`](https://github.com/healer-ctrl/orbit) for Société Générale Hackathon 2024.*
