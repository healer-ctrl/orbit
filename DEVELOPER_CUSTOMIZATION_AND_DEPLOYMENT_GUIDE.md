# 🛠️ Orbit Developer Customization & Deployment Handbook
### Société Générale Capital Markets · Complete Customization & Operations Guide

---

## 📑 Table of Contents
1. [📊 Complete Database, Container & Table Reference](#-1-complete-database-container--table-reference)
2. [⚡ Azure Functions Triggers & Custom Condition Guide](#-2-azure-functions-triggers--custom-condition-guide)
   - [Triggers Catalog](#a-triggers-catalog)
   - [Where Code Lives](#b-where-the-code-lives)
   - [How to Write Custom Conditions (Step-by-Step)](#c-how-to-write-custom-conditions-step-by-step)
   - [How to Add a Brand New Action Handler](#d-how-to-add-a-brand-new-action-handler)
3. [🎨 UI / Dashboard Architecture & Customization](#-3-ui--dashboard-architecture--customization)
   - [UI File Map](#a-ui-file-map)
   - [How to Modify Components & Add New Tabs](#b-how-to-modify-components--add-new-tabs)
   - [Where to Edit Live/Demo Data](#c-where-to-edit-livedemo-data)
4. [💻 Local Development & Restarting Applications](#-4-local-development--restarting-applications)
5. [🚀 Hosting & Cloud Deployment Guide (Azure)](#-5-hosting--cloud-deployment-guide-azure)

---

## 📊 1. Complete Database, Container & Table Reference

### A. Azure Cosmos DB (`mailminddb`)
| Container / Table Name | Partition Key | Purpose | Key Data Fields |
| :--- | :--- | :--- | :--- |
| **`emails`** | `/id` | Primary store for all ingested emails | `id`, `sender`, `subject`, `intent`, `urgency`, `risk_score`, `sanitized_body`, `pii_report`, `entities`, `sop_applied`, `status` |
| **`audittrail`** | `/trace_id` | Immutable regulatory compliance ledger (FINRA / MiFID II) | `trace_id`, `email_id`, `timestamp`, `agents_executed`, `pii_sanitization_metrics`, `hitl_approval`, `compliance_cert` |
| **`actions`** | `/action_id` | Tracks executed back-office actions and downstream core banking confirmations | `action_id`, `email_id`, `action_type`, `status` (`EXECUTED`/`REJECTED`), `payload`, `acknowledgement_id`, `execution_timestamp` |
| **`dlq`** | `/dlq_id` | Dead Letter Queue for poison messages & failed API calls | `dlq_id`, `email_id`, `error_type`, `stack_trace`, `retry_count`, `quarantined_at`, `status` (`PENDING_REPLAY`/`DISCARDED`) |

---

### B. Azure AI Search Indexes (`mailmind-search-3207`)
| Index Name | Search Type | Primary Fields |
| :--- | :--- | :--- |
| **`sops-index`** | Semantic Hybrid (BM25 + Vector 1536d) | `id`, `domain`, `title`, `rules`, `keywords`, `vector` |
| **`historical-resolutions-index`** | Semantic & Keyword | `id`, `subject`, `intent`, `resolution`, `risk_score` |

---

### C. Azure Storage Account Containers (`mailmindstore3207`)
| Container Name | Access | Purpose |
| :--- | :--- | :--- |
| **`email-attachments`** | Private Blob | Stores ingested SWIFT MT564/MT544 PDF and XML attachments |
| **`dlq-payloads`** | Private Blob | Stores raw unparsable payload dumps for SRE investigation |
| **`functions-runtime`** | Private Blob | Azure Functions deployment packages and execution state |

---

### D. Azure Log Analytics & Application Insights Tables (`orbit-law-3207`)
| Table Name | Description / Query Purpose |
| :--- | :--- |
| **`AppTraces`** | All backend execution logs, circuit breaker state transitions, agent handoffs |
| **`AppDependencies`** | Outbound API calls to Azure OpenAI, Azure AI Search, Cosmos DB, Teams Webhooks |
| **`AppRequests`** | Inbound HTTP & WebSocket requests to FastAPI and Next.js frontend |
| **`AppExceptions`** | Stack traces, caught exceptions, and timeout events |
| **`OrbitSystemAlerts_CL`** | Custom SRE alerting logs (P99 SLA breaches, circuit breaker trips, injection alerts) |

---

## ⚡ 2. Azure Functions Triggers & Custom Condition Guide

### A. Triggers Catalog
Orbit's Azure Functions (`functions/function_app.py`) uses the Python v2 programming model:

1. **HTTP Webhook Trigger** (`@app.route(route="email_webhook", methods=["POST"])`):
   - Ingests incoming emails directly from Microsoft Graph API webhooks and Event Grid.
2. **HTTP Action Execution Trigger** (`@app.route(route="execute_action", methods=["POST"])`):
   - Serverless microservice that executes back-office actions (Corporate Actions, SSI updates, Trade Linkage, ITSM).
3. **Timer Trigger: SLA Cutoff Monitor** (`@app.timer_trigger(schedule="0 */15 * * * *", arg_name="timer")`):
   - Runs every 15 minutes to monitor T+1 settlement deadlines and escalate pending HITL approvals.
4. **Continuous Automated Inbox Sync Timer Trigger** (`@app.timer_trigger(schedule="0 */1 * * * *", arg_name="timer", run_on_startup=True)`):
   - Runs every 1 minute in Azure serverless to continuously poll `orbit25690@outlook.com` via Microsoft Graph API and process incoming emails automatically with zero manual intervention.
5. **Continuous Async Background Daemon (FastAPI Lifespan)**:
   - When the backend is running, an async background task (`auto_poll_mailbox_worker`) wakes up every 30 seconds to fetch, deduplicate, and process new unread emails from `orbit25690@outlook.com`.
6. **Cosmos DB Change Feed Trigger** (Optional Event-Driven Extension):
   - `@app.cosmos_db_trigger(arg_name="documents", database_name="mailminddb", container_name="emails", connection="AZURE_COSMOS_CONNECTION")`

---

### B. Where the Code Lives
- **Azure Function Serverless Code**: [`functions/function_app.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/functions/function_app.py)
- **Local Backend Action Handlers**: [`backend/actions/`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/actions/)
  - `corporate_action.py` (Corporate Actions execution)
  - `settlement.py` (SSI resubmission & TARGET2 routing)
  - `trade_linkage.py` (Trading desk book allocation)
  - `instrument_correction.py` (ISIN/CUSIP remapping & ISO 6166 validation)
  - `ticket_creator.py` (ServiceNow ITSM incident creation)
- **Action Dispatcher & Router**: [`backend/agents/action_executor.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/agents/action_executor.py)

---

### C. How to Write Custom Conditions (Step-by-Step)

#### Example 1: Add a Rule in Azure Functions (`functions/function_app.py`)
To add a condition that rejects settlements over \$10,000,000 without VP authorization:

1. Open [`functions/function_app.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/functions/function_app.py).
2. Inside `execute_action()`, locate `elif action_type == "SETTLEMENT":`.
3. Add your custom condition:

```python
elif action_type == "SETTLEMENT":
    amount = float(payload.get("amount", 0.0))
    vp_approved = payload.get("vp_approved", False)
    
    # 🔴 CUSTOM CONDITION: Block high-exposure settlements without VP signoff
    if amount > 10_000_000 and not vp_approved:
        return func.HttpResponse(
            json.dumps({
                "status": "REJECTED",
                "reason": "Trades exceeding $10M require Vice President level authorization."
            }),
            status_code=403,
            mimetype="application/json"
        )
    
    # Proceed with execution if condition passes
    result = {
        "action_id": f"SET-{uuid.uuid4().hex[:8].upper()}",
        "status": "EXECUTED",
        "trade_id": payload.get("trade_id"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

---

#### Example 2: Add a Rule in Backend Action Handler (`backend/actions/settlement.py`)
1. Open [`backend/actions/settlement.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/actions/settlement.py).
2. Edit the `execute` method:

```python
def execute(self, request: ActionRequest) -> ActionResult:
    payload = request.payload or {}
    currency = payload.get("currency", "USD")

    # 🔴 CUSTOM CONDITION: Enforce valid TARGET2 currencies
    if currency not in ["EUR", "USD", "GBP", "CHF"]:
        return ActionResult(
            action_id=f"SET-FAIL-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.FAILED,
            result_data={"error": f"Currency {currency} not supported for automated TARGET2 routing."},
            error_message="Unsupported settlement currency",
            executed_at=datetime.utcnow().isoformat()
        )
```

---

### D. How to Add a Brand New Action Handler

1. **Create the handler file** in `backend/actions/collateral_margin.py`:
   ```python
   from backend.models.action_models import ActionRequest, ActionResult, ActionStatus
   import uuid
   from datetime import datetime

   class CollateralMarginHandler:
       def execute(self, request: ActionRequest) -> ActionResult:
           payload = request.payload or {}
           margin_call_id = f"MRG-{uuid.uuid4().hex[:6].upper()}"
           
           return ActionResult(
               action_id=f"MRG-{request.trace_id[:8]}",
               action_type=request.action_type,
               status=ActionStatus.SUCCESS,
               result_data={
                   "margin_call_id": margin_call_id,
                   "pledged_amount": payload.get("amount", 0.0),
                   "status": "MARGIN_PLEDGED"
               },
               executed_at=datetime.utcnow().isoformat()
           )
   ```

2. **Register the handler** in [`backend/agents/action_executor.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/agents/action_executor.py):
   ```python
   from backend.actions.collateral_margin import CollateralMarginHandler

   class ActionExecutorAgent:
       def __init__(self):
           self.handlers = {
               "CORPORATE_ACTION": CorporateActionHandler(),
               "SETTLEMENT": SettlementHandler(),
               "TRADE_LINKAGE": TradeLinkageHandler(),
               "INSTRUMENT_CORRECTION": InstrumentCorrectionHandler(),
               "SUPPORT_TICKET": TicketCreatorHandler(),
               "COLLATERAL_MARGIN": CollateralMarginHandler(),  # 👈 Added new handler
           }
   ```

---

## 🎨 3. UI / Dashboard Architecture & Customization

### A. UI File Map
The user interface is built with **Next.js 14 App Router, React 18, TailwindCSS, and Lucide Icons**.

```
dashboard/
├── src/
│   ├── app/
│   │   ├── layout.tsx                # Global HTML root layout, fonts, and metadata
│   │   ├── page.tsx                  # Main single-page dashboard container & tab state
│   │   ├── globals.css               # Tailwind & custom CSS variables
│   │   └── globals.source.css        # Source Tailwind directives
│   ├── components/
│   │   ├── Sidebar.tsx               # Dynamic navigation sidebar with active link events
│   │   ├── StatsCards.tsx            # Top KPI metrics (Processed, Auto-Executed, PII, Latency)
│   │   ├── EmailFeed.tsx             # Real-time list of ingested financial emails
│   │   ├── EmailDetailModal.tsx      # Comprehensive inspector (PII, Agent Graph, JSON payload)
│   │   ├── AgentPipeline.tsx         # Visual multi-agent workflow visualizer (Classifier->Risk)
│   │   ├── RiskGauge.tsx             # Interactive risk scoring breakdown gauge
│   │   ├── ApprovalQueue.tsx         # Human-in-the-Loop (HITL) supervisor approval queue
│   │   ├── SOPBrowser.tsx            # Interactive Standard Operating Procedures knowledge viewer
│   │   ├── AuditTrail.tsx            # Regulatory compliance log (FINRA/MiFID II)
│   │   ├── ObservabilityDashboard.tsx# SRE Telemetry, P99 Latency, Circuit Breakers, Alert Engine
│   │   ├── GuardrailPlayground.tsx   # Interactive PII sanitization & prompt injection sandbox
│   │   ├── DailyOpsReport.tsx        # Ops summary generator & PDF/email export
│   │   └── DemoButton.tsx            # One-click demo scenario trigger button
│   └── lib/
│       ├── api.ts                    # Backend API and WebSocket client
│       └── demoData.ts               # Pre-configured capital markets scenarios and SOPs
```

---

### B. How to Modify Components & Add New Tabs

#### 1. Add a New Navigation Tab to Sidebar
Open [`dashboard/src/components/Sidebar.tsx`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/dashboard/src/components/Sidebar.tsx) and add an item to `NAV_ITEMS`:
```typescript
{
  id: 'collateral',
  label: 'Collateral & Margin',
  tab: 'collateral',
  sectionId: 'collateral-section',
  icon: <DollarSign size={18} />,
  color: 'text-amber-400'
}
```

#### 2. Render Your New Tab View in `page.tsx`
Open [`dashboard/src/app/page.tsx`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/dashboard/src/app/page.tsx):
```tsx
{/* Render when activeTab === 'collateral' */}
{activeTab === 'collateral' && (
  <div id="collateral-section" className="space-y-6">
    <CollateralManagementPanel />
  </div>
)}
```

---

### C. Where to Edit Live/Demo Data
To modify or add test emails, modify [`dashboard/src/lib/demoData.ts`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/dashboard/src/lib/demoData.ts) or [`backend/data/sample_emails.json`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/data/sample_emails.json).

---

## 💻 4. Local Development & Restarting Applications

### A. Run Backend API (FastAPI)
```bash
# 1. Activate virtual environment
source .venv/bin/activate  # or create: python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start Backend Server with Auto-Reload on Port 8000
uvicorn backend.main:app --reload --port 8000
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### B. Run UI Dashboard (Next.js)
```bash
cd dashboard

# 1. Install Node dependencies
npm install

# 2. Start Next.js Development Server on Port 3000
npm run dev
```
- Live Dashboard: [http://localhost:3000](http://localhost:3000)

---

### C. Run with Docker Compose (Everything in 1 Command)
```bash
# Build and run all services in background
docker-compose up --build -d

# View real-time logs
docker-compose logs -f

# Restart services
docker-compose restart
```

---

### D. Run Automated Test Suite
```bash
# Execute full 52-test test suite
python3 -m pytest backend/tests/ -v
```

---

## 🚀 5. Hosting & Cloud Deployment Guide (Azure)

### A. Deploy Frontend to Azure Static Web Apps
```bash
cd dashboard

# 1. Build optimized static production bundle
npm run build

# 2. Copy routing configuration to build output
cp staticwebapp.config.json out/

# 3. Deploy to Azure Static Web Apps (using deployment token)
npx --yes @azure/static-web-apps-cli deploy ./out \
  --deployment-token <AZURE_SWA_DEPLOYMENT_TOKEN> \
  --env production
```
- **Live URL**: [https://ambitious-moss-048f25a0f.5.azurestaticapps.net](https://ambitious-moss-048f25a0f.5.azurestaticapps.net)

---

### B. Deploy Azure Functions
```bash
cd functions

# Deploy serverless app directly using Azure Functions Core Tools
func azure functionapp publish mailmind-functions-3207 --python
```

---

### C. Deploy Backend to Azure Container Apps
```bash
# 1. Build and push Docker container to Azure Container Registry
az acr build --registry mailmindacr --image orbit-backend:v1 .

# 2. Update Azure Container App
az containerapp update \
  --name orbit-api \
  --resource-group rg-mailmind \
  --image mailmindacr.azurecr.io/orbit-backend:v1
```

---

## 📬 6. Mock Data Files Map & Live Outlook (`orbit25690@outlook.com`) Integration

### A. Complete Mock Data Files Directory
If you want to view, modify, or add new mock scenarios, here is where all mock data is defined:

| Mock Data Type | Exact File Path | What is Stored |
| :--- | :--- | :--- |
| **Ingested Emails (Backend)** | [`backend/data/sample_emails.json`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/data/sample_emails.json) | The 5 core raw email payloads (SAP Dividend, JPM Failed Settlement, Apple Trade Link, ISIN Mismatch, HR Ticket). |
| **Dashboard UI Demo Records** | [`dashboard/src/lib/demoData.ts`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/dashboard/src/lib/demoData.ts) | Pre-computed pipeline steps, PII masks, risk scores, SOP cards, and execution results for instantaneous UI rendering. |
| **SOP Knowledge Base** | [`backend/services/search_service.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/services/search_service.py) | Institutional rules for `SOP-CA-001`, `SOP-SET-003`, `SOP-TL-001`, `SOP-REF-002`, and `SOP-SUP-001`. |
| **Reference Data Registry** | [`backend/services/search_service.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/services/search_service.py) | Master data for SAP SE (`DE0007164600`), Apple (`US0378331005`), SocGen Bond (`XS0987654321`), JPM, BNP. |
| **SRE Alert History** | [`backend/services/alerting_service.py`](file:///Users/ummadi/.gemini/antigravity/scratch/mailmind/backend/services/alerting_service.py) | Historical SRE alerts (P99 SLA warnings, circuit breaker resets, prompt injection flags). |

---

### B. Why is the Live Outlook Inbox Empty by Default?
In local and demo mode, Orbit operates with **resilient deterministic fixtures** (`sample_emails.json` & `demoData.ts`). This guarantees:
1. **Zero External Blocker**: Judges and testers can evaluate the entire multi-agent pipeline immediately without waiting for real-world SMTP email delivery latency.
2. **Offline Compatibility**: Works seamlessly without requiring Microsoft 365 Tenant Admin consent for external Entra ID apps.

---

### C. How to Ingest Live Emails from `orbit25690@outlook.com` via Graph API

To run the live email ingestion flow:

#### Step 1: Send a Test Email
Send an email to **`orbit25690@outlook.com`** from any email provider (Gmail, Outlook, etc.) with a capital markets subject, for example:
- **Subject**: `URGENT: FAILED SETTLEMENT - T+1 SSI CORRECTION (TRD-998822)`
- **Body**: `Please update IBAN DE89370400440532013000 to COBADEFF account for JPMorgan trade USD 2,450,000.`

#### Step 2: Configure Graph API Credentials in `.env`
Ensure your Microsoft Entra ID credentials are set:
```ini
GRAPH_TENANT_ID=<your-azure-ad-tenant-id>
GRAPH_CLIENT_ID=<your-app-client-id>
GRAPH_CLIENT_SECRET=<your-client-secret>
GRAPH_MAILBOX_USER=orbit25690@outlook.com
```

#### Step 3: Run the Ingestion Bridge Script
Run the automated live mailbox ingestion script:
```bash
python3 scripts/send_and_process_outlook.py
```
This script:
1. Connects to `https://graph.microsoft.com/v1.0/users/orbit25690@outlook.com/messages`.
2. Reads the unread emails from the inbox.
3. Streams them through the **PII Shield -> Classifier -> Parser -> Decision RAG -> Risk Scorer -> Action Execution / Teams HITL** pipeline.
4. Updates the live dashboard and Cosmos DB in real-time.

---

## 🏛️ 7. Capital Markets Action Layer REST API Reference (`/api/v1/...`)

Orbit exposes a domain-rich **Standardized Action Layer** documenting all core back-office actions across 8 key Société Générale topic areas.

### 🌐 Interactive API Documentation & Live Cloud Endpoints
- **Live Interactive Swagger UI**: [https://mailmind-functions-3207.azurewebsites.net/docs](https://mailmind-functions-3207.azurewebsites.net/docs)
- **Live ReDoc Technical Specification**: [https://mailmind-functions-3207.azurewebsites.net/redoc](https://mailmind-functions-3207.azurewebsites.net/redoc)
- **Live OpenAPI 3.1 JSON Schema**: [https://mailmind-functions-3207.azurewebsites.net/openapi.json](https://mailmind-functions-3207.azurewebsites.net/openapi.json)
- **Live Next.js Dashboard Swagger Hub**: [https://ambitious-moss-048f25a0f.5.azurestaticapps.net](https://ambitious-moss-048f25a0f.5.azurestaticapps.net) (Click **⚡ OpenAPI / Swagger Hub** tab)
- **Local Dev Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs) (or ReDoc at [http://localhost:8000/redoc](http://localhost:8000/redoc))

---

### 📑 8 Core Domain Topics & Endpoints Matrix

| # | Topic Domain | Method & Path | Description | Example Request / Query |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Trade Linkage** | `POST /api/v1/linkage/create` <br>`POST /api/v1/linkage/verify` <br>`GET /api/v1/linkage/{galaxyId}` | Block trade-to-Galaxy ID allocation and TARGET2 settlement verification. | `POST /api/v1/linkage/create` <br>`{"trade_id": "TRD-2026-88712", "isin": "US0378331005", "desk_book": "EQ-US-FLOW"}` |
| **2** | **ELIOT System Failures** | `POST /api/v1/eliot/resolve-failure` <br>`GET /api/v1/eliot/unmatched-trades` <br>`POST /api/v1/eliot/resubmit/{tradeId}` | ELIOT front-to-back trading system matching breaks, exception remediation, and engine resubmission. | `POST /api/v1/eliot/resolve-failure` <br>`{"trade_id": "TRD-ELIOT-99214", "exception_code": "ELIOT_MATCH_BREAK_404"}` |
| **3** | **Cash Flow (CF) Issues** | `POST /api/v1/cf-issue/reconcile` <br>`GET /api/v1/cf-issue/{cashFlowId}` <br>`POST /api/v1/cf-issue/adjust` | Nostro/Vostro dividend entitlement break reconciliation and automated ledger adjustment. | `POST /api/v1/cf-issue/reconcile` <br>`{"clearing_account": "ACC: 884729104829", "expected_amount": 30800.0, "settled_amount": 30800.0}` |
| **4** | **Instrument Creation** | `POST /api/v1/instruments/create` <br>`GET /api/v1/instruments/{isin}` <br>`PATCH /api/v1/instruments/{isin}/update` | Master reference data onboarding, ISIN ISO 6166 checksum validation, and CUSIP/SEDOL mapping. | `POST /api/v1/instruments/create` <br>`{"isin": "FR0000120271", "security_name": "TotalEnergies SE", "asset_class": "EQUITY"}` |
| **5** | **Warrants Creation** | `POST /api/v1/warrants/issue` <br>`GET /api/v1/warrants/{warrantId}` | Structured warrant issuance, strike/barrier termsheet registration, and Greeks calculation. | `POST /api/v1/warrants/issue` <br>`{"underlying_isin": "US0378331005", "strike_price": 220.0, "expiry_date": "2026-12-18"}` |
| **6** | **Price Queries** | `GET /api/v1/pricing/quote/{isin}` <br>`POST /api/v1/pricing/batch-query` | Real-time composite bid/ask market data quotes and multi-asset portfolio batch valuation. | `GET /api/v1/pricing/quote/US0378331005` <br>Returns: `{"bid": 224.50, "ask": 224.55, "mid": 224.525}` |
| **7** | **Refinancing Rates** | `POST /api/v1/refinancing/rates/update` <br>`GET /api/v1/refinancing/rates/latest` | Central bank and money market benchmark curve publishing (€STR, SOFR, EURIBOR). | `POST /api/v1/refinancing/rates/update` <br>`{"benchmark_code": "SOFR", "rate_percent": 5.33, "spread_bps": 12.5}` |
| **8** | **KPIs & Metrics** | `GET /api/v1/kpi/stp-rate` <br>`GET /api/v1/kpi/operations-summary` | Straight-Through Processing (STP) metrics, SLA compliance, and daily Ops transaction statistics. | `GET /api/v1/kpi/stp-rate` <br>Returns: `{"stp_rate_percentage": 94.2}` |

---

### 📦 Standard JSON Response Pattern

All Action Layer endpoints return a clean, deterministic schema:
```json
{
  "status": "success",
  "message": "Linkage successfully created and verified in Front-Office Booking Feeder",
  "galaxy_id": "SG828282",
  "timestamp": "2026-10-08T09:15:00Z",
  "details": {
    "trade_id": "TRD-2026-88712",
    "isin": "US0378331005",
    "allocated_book": "EQ-US-FLOW",
    "amount": 1500000.0,
    "currency": "USD",
    "settlement_status": "MATCHED"
  }
}
```

---

*Handy Reference for Société Générale Hackathon Team Orbit.*


