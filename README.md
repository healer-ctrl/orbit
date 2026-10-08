# 🚀 Orbit — Intelligent Financial Email Automation Platform
### Société Générale Capital Markets Hackathon 2024 · Built by **Team Orbit**

[![Azure Cloud Native](https://img.shields.io/badge/Azure-Cloud%20Native-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Azure%20Static%20Web%20App-success?logo=microsoftazure)](https://ambitious-moss-048f25a0f.5.azurestaticapps.net)
[![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-0078D4?logo=openai&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![Azure AI Search](https://img.shields.io/badge/Azure-AI%20Search%20(RAG)-0078D4)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Azure Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-Serverless%20Audit-4A154B)](https://azure.microsoft.com/en-us/products/cosmos-db)
[![Next.js 14](https://img.shields.io/badge/Next.js-14%20App%20Router-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PII Guardrail Shield](https://img.shields.io/badge/Security-PII%20%26%20Prompt%20Shield-emerald)](https://github.com/ummadi/orbit)

---

## 🌐 Public Live Dashboard URL

> 🚀 **Live Production Cloud URL**: [https://ambitious-moss-048f25a0f.5.azurestaticapps.net](https://ambitious-moss-048f25a0f.5.azurestaticapps.net)
>
> Open this link on any device/laptop directly — zero local installation required! Includes Microsoft Entra ID SSO integration and enterprise security headers.

---

## 📌 Executive Summary

**Orbit** is a 100% cloud-native, multi-agent AI system designed for **Société Générale Capital Markets Back-Office Operations**. It ingests high-volume operational emails from **Outlook M365**, understands domain-specific transaction intent, sanitizes sensitive client PII before LLM reasoning, retrieves institutional SOP knowledge via **Azure AI Search**, scores operational risk, and executes back-office actions via **Azure Functions** with **Human-in-the-Loop (HITL) Microsoft Teams** escalation for high-value transactions.

---

## 🏛️ Architecture Overview

```
                        [ Outlook M365 Mailbox ]
                                   │
                                   ▼ (Microsoft Graph API Webhook)
                        [ Azure Event Grid Ingestion ]
                                   │
                                   ▼
         ┌────────────────────────────────────────────────────────┐
         │         🛡️ PII Guardrail & Prompt Shield              │
         │  • Anonymizes IBANs, Bank Accs, SSNs, Phone, Contacts  │
         │  • Preserves ISINs, CUSIPs, SEDOLs, SWIFT BICs, TRDs   │
         │  • Blocks Prompt Injections & Context Hijacking        │
         └─────────────────────────┬──────────────────────────────┘
                                   │ (Sanitized Payload)
                                   ▼
         ┌────────────────────────────────────────────────────────┐
         │     🎯 Azure AI Foundry Multi-Agent Orchestrator       │
         │                                                        │
         │  1. Classifier Agent (GPT-4o Intent Mapping)           │
         │     └─ CA | Settlement | Trade Link | Ref Data | ITSM  │
         │                                                        │
         │  2. Parser Agent (Entity & Reference Enrichment)       │
         │     └─ CSD Entitlements, Counterparty BIC Resolution   │
         │                                                        │
         │  3. Decision Agent (Azure AI Search RAG)               │
         │     └─ SOPs (SOP-CA-001, SOP-SET-003) & History        │
         │                                                        │
         │  4. Risk Scorer Agent (0.00 – 1.00 Scoring)            │
         │     └─ Exposure (> €1M), Cutoff (< 2h), Injection Flags│
         └─────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────┐
              │   ⚖️ Decision Gateway (Threshold: 0.70)│
              └───────────────┬────────────────┬───────┘
                              │                │
            [Risk < 0.70]     │                │     [Risk ≥ 0.70]
            🟢 LOW RISK       │                │     🟠 HIGH RISK
                              ▼                ▼
     ┌───────────────────────────────┐  ┌───────────────────────────────┐
     │  ⚡ Azure Functions (Serverless│  │  👥 Microsoft Teams HITL Card │
     │  • fn-corporate-action        │  │  • Adaptive Card v1.5 Alert   │
     │  • fn-settlement-instruction  │  │  • Interactive Approve/Reject │
     │  • fn-trade-linkage           │  │  • SLA Escalation Countdown   │
     │  • fn-instrument-correction   │  └──────────────┬────────────────┘
     │  • fn-ticket-creator (ITSM)   │                 │ (Supervisor Approved)
     └───────────────┬───────────────┘                 ▼
                     │                 [ Azure Functions Execution ]
                     └─────────────────────────┬────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │  📊 Azure Cosmos DB & AI Search  │
                              │  • Immutable Audit Trail         │
                              │  • Regulatory Compliance Ledger  │
                              │  • Searchable Resolution Archive │
                              └──────────────────────────────────┘
```

---

## 🌟 Key Features

1. **🛡️ PII Guardrail & Prompt Shield**:
   - Automatically sanitizes client IBANs, bank accounts, SSNs, personal contact numbers, and personal emails before sending any data to LLMs.
   - **Domain Integrity**: Protects capital market identifiers (`ISIN`, `CUSIP`, `SEDOL`, `SWIFT BIC`, `Trade ID`) from accidental redaction.
   - Defends against prompt injection attempts, immediately flagging attempts with Risk `1.0 (CRITICAL_INJECTION)`.

2. **🤖 Multi-Agent AI Pipeline**:
   - **Classifier Agent**: 5 domain intents (`CORPORATE_ACTION`, `SETTLEMENT`, `TRADE_LINKAGE`, `INSTRUMENT_CORRECTION`, `SUPPORT_TICKET`).
   - **Parser Agent**: Extracts and normalizes trade numbers, amounts, currencies, and counterparties.
   - **Decision Agent**: Ingests Standard Operating Procedures (SOPs) from **Azure AI Search** for grounded resolutions.
   - **Risk Scorer Agent**: Evaluates financial exposure, T+1 cutoffs, and data confidence.

3. **👥 Risk-Based Human-in-the-Loop (HITL)**:
   - Low-risk transactions execute autonomously in milliseconds.
   - High-value transactions (> €1M / urgent cutoffs) generate **Microsoft Teams Adaptive Cards** for supervisor sign-off.

4. **📊 Enterprise Compliance & Audit**:
   - **Azure Cosmos DB** stores full audit records (trace ID, raw vs sanitized payload, model telemetry, and approval records) satisfying regulatory requirements (FINRA / MiFID II).

6. **🔐 Azure Key Vault Zero-Trust Secret Management**:
   - Zero hardcoded or plain-text secrets in repository or environment files.
   - All connection strings, OpenAI keys, Search keys, and Webhook URLs dynamically resolved via `Azure Key Vault` (`orbit-vault-3207`) using Azure Managed Identity / RBAC `DefaultAzureCredential`.

---

## 🌐 Live Azure Cloud Resources, Cost Breakdown & Developer Handbook

> 📑 **Architecture & Cost Specs**: See [**`AZURE_INFRASTRUCTURE_ARCHITECTURE_COSTS.md`**](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/AZURE_INFRASTRUCTURE_ARCHITECTURE_COSTS.md) for full SKU specs, machine flavors, database container schemas, Mermaid topology diagrams, and multi-tier TCO cost breakdowns.
>
> 🛠️ **Developer Customization & Deployment Handbook**: See [**`DEVELOPER_CUSTOMIZATION_AND_DEPLOYMENT_GUIDE.md`**](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/DEVELOPER_CUSTOMIZATION_AND_DEPLOYMENT_GUIDE.md) for how to write custom conditions in Azure Functions, customize UI components, restart apps, and deploy to Azure.

All cloud infrastructure is provisioned and running on Azure:

```ini
AZURE_KEY_VAULT_URI     = https://orbit-vault-3207.vault.azure.net/
AZURE_OPENAI_ENDPOINT   = https://mailmind-openai-3207.openai.azure.com/
AZURE_SEARCH_ENDPOINT   = https://mailmind-search-3207.search.windows.net
AZURE_COSMOS_ENDPOINT   = https://mailmind-cosmos-3209.documents.azure.com:443/
AZURE_FUNCTIONS_APP_URL = https://mailmind-functions-3207.azurewebsites.net
AZURE_STORAGE_ACCOUNT   = mailmindstore3207
AZURE_STATIC_WEB_APP    = https://ambitious-moss-048f25a0f.5.azurestaticapps.net
```

---

## ⚡ Quickstart Guide for Teammates (Plug & Play)

No complex installations needed. Follow these simple steps:

### 1. Clone the Repository
```bash
git clone https://github.com/healer-ctrl/orbit.git
cd orbit
```

### 2. Configure Environment
Copy the pre-configured `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run Backend API (FastAPI)
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start the Multi-Agent API server
uvicorn backend.main:app --reload --port 8000
```
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 4. Run Operations Dashboard (Next.js)
```bash
cd dashboard
npm install
npm run dev
```
- **Live Dashboard**: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing & Demo Scenarios

You can trigger the entire multi-agent pipeline with our 5 pre-built Capital Markets scenarios:

```bash
# Trigger automated test run across all 5 financial emails
curl -X POST http://localhost:8000/api/demo/trigger
```

### Test Email Matrix:
| ID | Type | Scenario | Expected Path |
|---|---|---|---|
| `email_1` | **Corporate Action** | SAP SE Mandatory Dividend (EUR 2.20) with client contact PII | 🟠 **HITL Teams Card** |
| `email_2` | **Settlement** | Urgent T+1 Settlement Failure on JPM Trade ($2.45M) | 🟢 **Auto-Execute SSI Resubmit** |
| `email_3` | **Trade Linkage** | Block Trade TRD-2024-88712 to Apple CUSIP | 🟢 **Auto-Execute Desk Link** |
| `email_4` | **Instrument Correction**| Bond POS-44332 ISIN Remap Exception | 🟢 **Auto-Execute Master Patch** |
| `email_5` | **Support Ticket** | Operations Analyst System Access Request | 🟢 **Auto-Execute ServiceNow P3** |

---

## 📁 Repository Structure

```
orbit/
├── README.md                      # Complete project & deployment documentation
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules for secrets & build files
├── backend/
│   ├── requirements.txt           # Python dependencies
│   ├── config.py                  # Environment config loader
│   ├── main.py                    # FastAPI server & WebSocket manager
│   ├── agents/
│   │   ├── classifier.py          # Intent classification agent
│   │   ├── parser_agent.py        # Financial entity extraction agent
│   │   ├── decision_agent.py      # SOP & Knowledge retrieval agent
│   │   ├── risk_scorer.py         # Risk evaluation agent
│   │   ├── action_executor.py     # Serverless action dispatcher
│   │   └── orchestrator.py        # Multi-agent workflow orchestrator
│   ├── services/
│   │   ├── pii_guardrail_service.py # PII sanitization & prompt injection shield
│   │   ├── openai_service.py      # Azure OpenAI wrapper & domain fallback
│   │   ├── search_service.py      # Azure AI Search RAG service
│   │   ├── cosmos_service.py      # Azure Cosmos DB compliance storage
│   │   ├── graph_service.py       # Microsoft Graph API / Outlook M365
│   │   └── teams_service.py       # Microsoft Teams Adaptive Card alerting
│   ├── actions/                   # Serverless action handlers (Corporate Actions, SSI, etc.)
│   ├── models/                    # Pydantic data schemas
│   └── data/                      # Sample financial emails with embedded PII
├── dashboard/                     # Next.js 14 Real-time Operations Dashboard
│   ├── src/app/                   # App Router pages & layout
│   └── src/components/            # UI components (Agent Pipeline, Feed, Gauge, HITL)
└── functions/                     # Azure Functions serverless app code
```

---

## ⚡ Live Production Cloud Deployments

| Component | Live Cloud URL | Details |
| :--- | :--- | :--- |
| **🚀 Production Dashboard & UI** | **[ambitious-moss-048f25a0f.5.azurestaticapps.net](https://ambitious-moss-048f25a0f.5.azurestaticapps.net)** | Live Next.js Web App with full Operations Hub, PII Guardrails, SOP Runbooks, Audit Ledger, and **OpenAPI Swagger Action Hub**. |
| **⚡ Azure Functions Action Layer** | **[mailmind-functions-3207.azurewebsites.net](https://mailmind-functions-3207.azurewebsites.net)** | Live Serverless Action Gateway executing all 8 domain endpoints, Graph API mail daemon, and Cosmos DB audit logging. |
| **📘 Interactive Swagger UI (`/docs`)** | **[mailmind-functions-3207.azurewebsites.net/docs](https://mailmind-functions-3207.azurewebsites.net/docs)** | Interactive Swagger UI definition to manually test endpoints with schema validation. |
| **📕 ReDoc OpenAPI Docs (`/redoc`)** | **[mailmind-functions-3207.azurewebsites.net/redoc](https://mailmind-functions-3207.azurewebsites.net/redoc)** | Clean, human-readable API reference documentation for all 8 capital markets topics. |
| **📜 OpenAPI JSON Schema** | **[mailmind-functions-3207.azurewebsites.net/openapi.json](https://mailmind-functions-3207.azurewebsites.net/openapi.json)** | Machine-readable OpenAPI 3.1.0 schema specification. |

---

## 🏛️ Capital Markets OpenAPI Action Layer (8 Core Topics)

Orbit features an enterprise REST Action Layer covering 8 core Société Générale operational domains (16 endpoints):
1. **Trade Linkage**: `POST /api/v1/linkage/create`, `POST /api/v1/linkage/verify`, `GET /api/v1/linkage/{galaxy_id}`
2. **ELIOT Failure Resolution**: `POST /api/v1/eliot/retry`, `GET /api/v1/eliot/status/{ticket_id}`
3. **Cash Flow (CF) Issues**: `POST /api/v1/cf-issue/create`, `GET /api/v1/cf-issue/{issue_id}`
4. **Instrument Creation**: `POST /api/v1/instruments/create`, `GET /api/v1/instruments/{isin}`
5. **Warrants Creation**: `POST /api/v1/warrants/issue`, `GET /api/v1/warrants/{warrant_id}`
6. **Price Queries**: `POST /api/v1/prices/query`, `GET /api/v1/prices/history/{isin}`
7. **Refinancing Rates**: `POST /api/v1/rates/update`, `GET /api/v1/rates/benchmark/{currency}`
8. **KPIs & STP Tracking**: `POST /api/v1/kpi/record`, `GET /api/v1/kpi/summary`

---

## 🏆 Hackathon Pitch Points for Judges

1. **Domain Depth**: Tailored specifically for tier-1 investment bank capital markets operations (ISIN, CUSIP, SWIFT MT564/MT544, SSI).
2. **Security-First**: Enterprise PII anonymization ensures sensitive customer data never leaves the security perimeter unprotected.
3. **Institutional Memory**: Azure AI Search ensures decisions follow official Société Générale Standard Operating Procedures.
4. **Governed Autonomy**: Risk-gated execution combines speed for routine operations with supervisor oversight for high-exposure trades.
5. **Full Cloud Native**: Deployed across Azure AI Foundry, OpenAI, AI Search, Cosmos DB, Azure Static Web Apps, and Azure Functions.

---

**Built with ❤️ by Team Orbit for Société Générale Hackathon**
