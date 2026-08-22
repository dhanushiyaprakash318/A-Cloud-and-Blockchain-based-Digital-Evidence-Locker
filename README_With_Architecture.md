# DiVeL -- Digital Evidence Locker

## Blockchain & GenAI Powered Digital Evidence Management and Intelligence Platform

DiVeL is a cloud-native Digital Evidence Management System designed for
law enforcement agencies, forensic laboratories, and judicial
organizations. It provides secure evidence storage, blockchain-backed
integrity verification, AI-powered evidence summarization and case
intelligence, deepfake/media forensics, and an investigation assistant
chatbot — all behind a role-based (Police / Forensics / Judge) web
portal.

The system is built to run in two modes:

- **Full cloud mode** -- backed by AWS (S3, DynamoDB, Lambda, Bedrock)
  and an Ethereum blockchain, as described in the architecture
  diagrams below.
- **Local/offline mode** -- if AWS credentials or a blockchain RPC
  endpoint are not configured, the backend automatically falls back to
  a local JSON-file database and a local blockchain ledger, so the
  application still runs end-to-end for development and demos.

------------------------------------------------------------------------
## Features

- Secure Digital Evidence Storage (Amazon S3 / local disk fallback)
- Blockchain-based Evidence Integrity Verification (Ethereum, via web3.py)
- AI-powered Evidence Summarization (Amazon Bedrock / Google Gemini / local Ollama)
- Retrieval-Augmented Chat Assistant over case & evidence data (ChromaDB + Sentence-Transformers)
- Case Management Dashboard with filters, search, and case cards
- Evidence Upload & Tracking (documents, images, video, audio)
- Interactive Knowledge Graph of cases, accused, and evidence
- Geographic Heatmap of case locations
- AI-based Deepfake / Manipulated Media Detection for uploaded images & videos
- SHA-256 Hash Verification of every evidence file
- Immutable Blockchain Anchoring of evidence hashes
- DynamoDB Metadata Storage (with local-mode fallback)
- Role-Based Authentication (Police, Forensics, Judge)
- Audit Logging
- REST APIs (FastAPI, with Swagger/OpenAPI docs)

# Overall System Architecture

``` text
                         ┌──────────────────────────────┐
                         │        React Frontend        │
                         │                              │
                         │ • Case Management            │
                         │ • Evidence Upload            │
                         │ • Dashboard                  │
                         │ • Knowledge Graph & Heatmap  │
                         │ • Deepfake Detection UI      │
                         │ • AI Chat Assistant          │
                         └──────────────┬───────────────┘
                                        │
                                 HTTP/REST APIs
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │       FastAPI Backend        │
                         │                              │
                         │ • Authentication            │
                         │ • Business Logic            │
                         │ • Text Extraction           │
                         │ • AI Integration            │
                         └──────┬───────────┬──────────┘
                                │           │
                Upload Evidence  │           │ AI Queries
                                ▼           ▼
                  ┌──────────────────┐  ┌──────────────────┐
                  │    Amazon S3     │  │ Amazon Bedrock   │
                  │ Evidence Storage │  │ Amazon Nova Lite │
                  └────────┬─────────┘  └────────┬─────────┘
                           │                     │
                           ▼                     │
                 ┌──────────────────┐           │
                 │ API Gateway      │           │
                 └────────┬─────────┘           │
                          ▼                     │
                 ┌──────────────────┐           │
                 │ AWS Lambda       │           │
                 │ SHA-256 Hashing  │           │
                 │ Blockchain Anchor│           │
                 └──────┬─────┬─────┘           │
                        │     │                 │
                        ▼     ▼                 ▼
             ┌──────────────┐      ┌────────────────────────┐
             │ DynamoDB     │◄────►│ AI Summaries & Chat    │
             │ Metadata     │      │ Responses              │
             └──────────────┘      └────────────────────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ Ethereum Sepolia     │
             │ Smart Contract        │
             └──────────────────────┘
```

A separate, standalone **Deepfake Detection microservice** (FastAPI +
PyTorch/transformers) runs alongside the main backend and is called by
the frontend whenever an image or video is attached as evidence.

------------------------------------------------------------------------

# Evidence Upload Workflow

``` text
Officer
   │
   ▼
Upload Evidence
   │
   ▼
FastAPI
   │
   ▼
Upload Original File to Amazon S3
   │
   ├────────────► API Gateway
   │                 │
   │                 ▼
   │           AWS Lambda
   │                 │
   │      • Download from S3
   │      • Compute SHA-256
   │      • Store Metadata
   │      • Anchor Hash on Ethereum
   │                 │
   │                 ▼
   │            DynamoDB
   │
   ▼
File Type Check
   │
   ├── PDF / DOCX / TXT
   │        │
   │        ▼
   │   Extract Text
   │        │
   │        ▼
   │ Amazon Nova Lite
   │        │
   │        ▼
   │ Store Summary in DynamoDB
   │
   └── Image / Video
            │
            ▼
   Deepfake Detection Service
   (EfficientNet-B0 + Swin + Xception + ResNet ensemble)
            │
            ▼
   REAL / FAKE verdict shown before upload is allowed to proceed
```

------------------------------------------------------------------------

# AI Chat Assistant Workflow

``` text
Officer Question
       │
       ▼
React Chat UI
       │
       ▼
POST /api/v1/ai/query
       │
       ▼
FastAPI
       │
       ▼
Intent Detection + Retrieval
(DynamoDB lookups, ChromaDB vector search over case/evidence text)
       │
       ▼
Amazon Nova Lite (Bedrock Converse API)
       │
 ┌─────┴─────────────────────┐
 │                           │
 ▼                           ▼
Exact DB Answers          LLM-Generated Answer
(counts, accused lists,   (with disclaimer when
case search results)      falling back beyond the DB)
 │                           │
 └──────────────┬────────────┘
                ▼
         Natural Language Response
                │
                ▼
            React Frontend
```

------------------------------------------------------------------------

# Technology Stack

## Frontend

-   React + TypeScript
-   Vite
-   Tailwind CSS + shadcn/ui (Radix primitives)
-   Axios
-   React Router

## Backend

-   FastAPI
-   Python 3.11
-   Pydantic / pydantic-settings
-   Boto3 (AWS SDK)
-   web3.py (Ethereum integration)
-   ChromaDB + Sentence-Transformers (RAG vector store for chat assistant)
-   PyMuPDF / python-docx (evidence text extraction)

## Deepfake Detection Service

-   FastAPI microservice (independent process, port 8001)
-   PyTorch + Torchvision + Transformers
-   Hybrid ensemble: EfficientNet-B0, Swin Transformer, Xception, ResNet-34
-   OpenCV / MoviePy for video frame extraction

## Cloud (optional, for full production mode)

-   Amazon S3
-   Amazon DynamoDB
-   AWS Lambda
-   Amazon API Gateway
-   Amazon Bedrock
-   AWS IAM
-   AWS CloudWatch
-   AWS KMS

## AI

-   Amazon Nova Lite (`amazon.nova-lite-v1:0`) via Amazon Bedrock Converse API -- chat assistant
-   Google Gemini -- evidence/case summarization (`AI_PROVIDER=gemini`)
-   Local Ollama (e.g. Llama 3) -- optional fully offline summarization fallback

## Blockchain

-   Solidity
-   Hardhat
-   Ethereum Sepolia (or a local Hardhat node for development)

------------------------------------------------------------------------

# AWS Services

  Service            Purpose
  ------------------ ------------------------------------------------
  Amazon S3          Secure evidence storage
  DynamoDB           Case metadata, evidence metadata, AI summaries
  API Gateway        Invokes Lambda
  AWS Lambda         SHA-256 generation and blockchain integration
  Amazon Bedrock     Managed GenAI service
  Amazon Nova Lite   Summarization, intent classification, chat
  IAM                Secure access control
  CloudWatch         Logs and monitoring
  KMS                Encryption
  Ethereum Sepolia   Tamper-proof integrity verification

> All AWS/blockchain integrations are optional for local development.
> If `backend/.env` has no AWS credentials, the backend automatically
> switches to a local JSON-file database; if no blockchain RPC/private
> key is reachable, evidence hashing still runs but is not anchored
> on-chain.

------------------------------------------------------------------------

# Repository Structure

``` text
A-Cloud-and-Blockchain-based-Digital-Evidence-Locker
├── backend                      # FastAPI main API (port 8046)
│   ├── app
│   │   ├── api                  # auth, cases, evidence, ai_chat, assistant, bedrock, init
│   │   ├── services             # database, storage, blockchain, ai, rag/, ...
│   │   ├── models
│   │   └── core                 # config.py (Settings), security.py
│   ├── contracts                 # compiled ABI used by blockchain.py
│   ├── seed_complex_cases.py     # auto-seeds demo data on first run
│   ├── .env.example
│   └── requirements.txt
├── frontend                      # React + Vite app (port 5173)
│   ├── src
│   │   ├── pages                 # Dashboard, CaseDetail, KnowledgeGraph, Heatmap,
│   │   │                         # DeepfakeDetection, Chatbot, EvidenceUpload, Login
│   │   ├── components
│   │   └── services              # api.ts (backend + deepfake HTTP clients)
│   ├── .env.development
│   └── package.json
├── DeepfakeDetector               # Standalone deepfake microservice (port 8001)
│   ├── backend                    # main.py, routes.py, predictor.py, models/
│   └── requirements.txt
├── blockchain                     # Hardhat project
│   ├── contracts/EvidenceRegistry.sol
│   ├── scripts/deploy.js
│   └── hardhat.config.js
├── assets                         # Diagrams / screenshots used in docs
├── start_windows.bat              # Convenience launcher (backend + frontend only)
├── start_app.sh                   # Convenience launcher for macOS/Linux/WSL
├── SETUP_GUIDE.md                 # Troubleshooting deep-dive
└── README_With_Architecture.md    # This file
```

------------------------------------------------------------------------

# Prerequisites

-   **Python** 3.11+ (verify with `python --version` or `py --version` on Windows)
-   **Node.js** 18+ and **npm**
-   **Git**
-   Optional, only for full cloud mode:
    -   An AWS account with S3 + DynamoDB access and an IAM access key
    -   A funded Ethereum Sepolia wallet + RPC URL (e.g. Alchemy/Infura), **or**
        Hardhat installed locally to run a throwaway local chain

------------------------------------------------------------------------

# Environment Configuration

The backend reads a single `.env` file from the **project root**
(`backend/app/core/config.py` looks in the repo root, `backend/`, and
`blockchain/`). Copy the example and fill in only what you have —
everything else safely falls back to local mode:

```bash
cp backend/.env.example .env
```

```ini
# AWS Configuration (optional — omit to use local JSON-file storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-north-1
S3_BUCKET_NAME=
DYNAMODB_TABLE_CASES=cases
DYNAMODB_TABLE_EVIDENCE=evidence

# Blockchain Configuration (optional — omit to skip on-chain anchoring)
# Default hardhat/ganache local URL
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
BLOCKCHAIN_CONTRACT_ADDRESS=
BLOCKCHAIN_PRIVATE_KEY=

# AI Configuration
GEMINI_API_KEY=
AI_PROVIDER=gemini        # gemini | local (Ollama)

# Security
SECRET_KEY=supersecretkeydefaultsfortestingonly
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

The Amazon Bedrock chat assistant uses your AWS credentials directly
(no separate key needed) — if they're absent, chat falls back to a
plain database-lookup answer with no LLM narration.

------------------------------------------------------------------------

# Running the Project

The application has **three independent services**. Run each in its
own terminal.

## 1. Backend API (port 8046)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1          # PowerShell
# venv\Scripts\activate.bat          # cmd.exe
# source venv/bin/activate           # macOS/Linux

pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8046
```

On first run the database is empty, so the backend automatically
seeds a set of demo cases (`seed_complex_cases.py`) — look for
`DATABASE EMPTY - SEEDING WITH INITIAL DATA` in the logs.

## 2. Frontend (port 5173)

```powershell
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173**. The frontend expects the backend at
`http://localhost:8046` and the deepfake service at
`http://localhost:8001` — both configurable in `frontend/.env.development`.

## 3. Deepfake Detection microservice (port 8001)

Required for the "Deepfake" tab and for the mandatory image/video
check during evidence upload — if this isn't running, uploading any
photo or video evidence will fail with a *"Missing required fields:
Deepfake check"* validation error.

```powershell
cd DeepfakeDetector/backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --port 8001
```

The first request downloads the `dima806/deepfake_vs_real_image_detection`
model from Hugging Face, so an internet connection is needed at least once.

## 4. (Optional) Local blockchain node

Only needed if you want real on-chain anchoring without a Sepolia
wallet:

```bash
cd blockchain
npm install
npm run node                 # starts a local Hardhat chain on :8545
# in a second terminal:
npm run deploy:local         # deploys EvidenceRegistry.sol, writes deployed-address.json
```

Copy the deployed address and one of the printed private keys into
`.env` as `BLOCKCHAIN_CONTRACT_ADDRESS` and `BLOCKCHAIN_PRIVATE_KEY`,
then restart the backend.

## Quickest path (Windows, backend + frontend only)

`start_windows.bat` automates steps 1 and 2 (venv creation, `pip
install`, `npm install`, and launching both servers in new windows).
It does **not** start the Deepfake Detection service — start that one
manually if you need image/video evidence checks.

------------------------------------------------------------------------

# Verifying Your Setup

  Check                         Command
  ------------------------------ --------------------------------------------------
  Backend is up                 `curl http://127.0.0.1:8046/`
  Backend DB status              `curl http://127.0.0.1:8046/api/v1/init/status`
  API docs (Swagger)             open `http://127.0.0.1:8046/docs`
  Frontend is up                 open `http://localhost:5173`
  Deepfake service is up         `curl http://127.0.0.1:8001/health`

------------------------------------------------------------------------

# Demo Login Credentials

The auth service ships with three built-in demo accounts (see
`backend/app/api/auth.py`) — use these to log into the frontend:

  Role        Username     Password
  ----------- ------------ ---------------
  Police      `polaris`    `polaris123`
  Forensics   `forensics`  `forensics123`
  Judge       `judge`      `judge123`

Change or remove these before any real deployment.

------------------------------------------------------------------------

# API Endpoints

All routes are prefixed with `/api/v1`.

  Method   Endpoint                                Purpose
  -------- --------------------------------------- ----------------------------------
  POST     `/auth/login`                            Log in, returns a JWT + role
  GET      `/cases`                                 List cases (with filters)
  POST     `/cases`                                 Create a case
  GET      `/cases/{case_id}`                       Get one case
  PUT      `/cases/{case_id}`                        Update a case
  DELETE   `/cases/{case_id}`                        Delete a case
  GET      `/cases/{case_id}/knowledge-graph`         Graph data for the Knowledge Graph view
  POST     `/cases/{case_id}/summarize`               Trigger an AI case summary
  GET      `/evidence/{case_id}`                     List evidence for a case
  POST     `/evidence/upload`                         Upload evidence (multipart)
  GET      `/evidence/{evidence_id}/blockchain`        Blockchain anchor details
  GET      `/evidence/{evidence_id}/verify`            Re-verify hash against blockchain
  POST     `/ai/query`                                Chat assistant Q&A
  POST     `/assistant/chat`                           Alternate assistant endpoint
  POST     `/bedrock/classify`                         Low-level Bedrock classification call
  GET      `/init/status`                              DB seed status / health
  POST     `/init/seed`                                 Manually re-seed demo data
  POST     `/init/clear`                                Clear all data (use with caution)

Deepfake microservice (separate base URL, `http://localhost:8001`, no `/api/v1` prefix):

  Method   Endpoint            Purpose
  -------- ------------------- --------------------------------
  POST     `/predict/image`     REAL/FAKE verdict for an image
  POST     `/predict/video`     REAL/FAKE verdict for a video
  POST     `/predict/url`       Phishing/risk check for a URL
  GET      `/health`            Service + model status

------------------------------------------------------------------------

# Security Features

-   SHA-256 evidence hashing
-   Blockchain integrity verification
-   Immutable evidence metadata
-   IAM-based authorization
-   Encryption at rest and in transit
-   Role-based JWT authentication (Police / Forensics / Judge)
-   Audit-ready architecture

------------------------------------------------------------------------

# Future Enhancements

-   OCR for scanned/handwritten image evidence
-   Deeper video understanding (beyond deepfake classification)
-   Semantic search across the full evidence corpus
-   Investigation timeline auto-generation
-   Multi-language AI assistant

------------------------------------------------------------------------
# AWS Services Used

## Amazon S3

### Purpose

Amazon S3 (Simple Storage Service) is used to securely store all original digital evidence uploaded by investigators.

### Stores

- PDF Documents
- DOCX Documents
- Text Files
- Images
- Videos
- Audio Files
- Other Digital Evidence

### Why S3?

- Highly durable object storage (99.999999999% durability)
- Scalable storage without capacity planning
- Secure access using IAM policies
- Supports server-side encryption
- Easy integration with Lambda and FastAPI
- Stores the original evidence without modification

---

## Amazon DynamoDB

### Purpose

Amazon DynamoDB is the primary NoSQL database used to store metadata related to cases and evidence.

### Stores

#### Case Metadata

- Case ID
- Case Number
- Crime Type
- Investigation Status
- Officer Details
- FIR Information
- Date of Offence
- Date Reported
- District

#### Evidence Metadata

- Evidence ID
- File Name
- File Type
- SHA-256 Hash
- S3 Object Key
- Upload Timestamp
- Blockchain Transaction Hash
- Processing Status
- AI Summary
- Text Extraction Status

### Why DynamoDB?

- Fully managed serverless NoSQL database
- Very low latency
- Highly scalable
- Seamless integration with AWS services
- Ideal for metadata and case management

---

## AWS Lambda

### Purpose

AWS Lambda automatically performs evidence integrity verification immediately after an upload.

### Responsibilities

- Downloads evidence from Amazon S3
- Computes SHA-256 hash
- Generates immutable evidence fingerprint
- Stores metadata in DynamoDB
- Anchors evidence hash on Ethereum Sepolia blockchain

### Why Lambda?

- Serverless execution
- Automatically scales
- No infrastructure management
- Event-driven architecture
- Cost-effective pay-per-use model

---

## Amazon API Gateway

### Purpose

Amazon API Gateway securely invokes the Lambda function after evidence upload.

### Responsibilities

- Exposes secure REST endpoint
- Routes requests to Lambda
- Handles request validation
- Provides secure communication between FastAPI and Lambda

### Why API Gateway?

- Secure REST APIs
- Easy Lambda integration
- Highly scalable
- Built-in monitoring
- Supports authentication and authorization

---

## Amazon Bedrock

### Purpose

Amazon Bedrock provides Generative AI capabilities for evidence understanding and intelligent question answering.

### Responsibilities

- Generates AI summaries of uploaded evidence
- Performs intent classification for officer questions
- Generates conversational responses
- Provides intelligent reasoning using stored evidence summaries

### Why Bedrock?

- Fully managed Generative AI platform
- No infrastructure management
- Secure AWS-native integration
- Supports enterprise-grade AI applications

---

## Amazon Nova Lite

### Purpose

Amazon Nova Lite is the foundation model used through Amazon Bedrock.

### Responsibilities

- Summarizes extracted evidence text
- Classifies officer intent
- Generates natural language responses
- Answers investigation-related questions
- Produces concise case summaries

### Why Nova Lite?

- Optimized for conversational AI
- Fast response generation
- Cost-effective compared to larger models
- High-quality reasoning for investigation assistance

---

## AWS Identity and Access Management (IAM)

### Purpose

IAM controls authentication and authorization across all AWS services used in DiVeL.

### Responsibilities

- Controls access to Amazon S3
- Controls access to DynamoDB
- Grants Lambda execution permissions
- Secures Bedrock access
- Enforces least-privilege permissions

### Why IAM?

- Fine-grained access control
- Secure authentication
- Role-based authorization
- Enterprise security best practices

---

## Amazon CloudWatch

### Purpose

Amazon CloudWatch is used for monitoring, logging, and troubleshooting the application.

### Responsibilities

- Lambda execution logs
- API Gateway logs
- Performance monitoring
- Error tracking
- Request monitoring
- Operational metrics

### Why CloudWatch?

- Centralized logging
- Real-time monitoring
- Performance insights
- Simplifies debugging and maintenance

---

## AWS Key Management Service (KMS)

### Purpose

AWS KMS manages encryption keys used to protect sensitive evidence and application data.

### Responsibilities

- Encrypts stored data
- Manages encryption keys
- Protects sensitive metadata
- Supports secure AWS integrations

### Why KMS?

- Secure key management
- Automatic key rotation
- AWS-native encryption
- Compliance with security standards

---

## Ethereum Sepolia Blockchain

### Purpose

Ethereum Sepolia is used to provide immutable proof of evidence integrity.

### Responsibilities

- Stores SHA-256 evidence hashes
- Generates blockchain transaction hashes
- Enables tamper detection
- Provides immutable audit trail

### Why Ethereum Sepolia?

- Immutable blockchain ledger
- Tamper-proof evidence verification
- Transparent integrity validation
- Smart contract support using Solidity

---

## Hardhat

### Purpose

Hardhat is the blockchain development framework used to develop, deploy, and test Ethereum smart contracts.

### Responsibilities

- Smart contract development
- Local blockchain testing
- Contract deployment
- Interaction with Ethereum Sepolia

### Why Hardhat?

- Developer-friendly framework
- Local blockchain simulation
- Easy contract deployment
- Excellent debugging support

------------------------------------------------------------------------

# Troubleshooting

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for a deeper troubleshooting
guide. The most common issues:

-   **"Missing required fields: Deepfake check"** on evidence upload
    → the Deepfake Detection microservice (step 3 above) isn't
    running on port 8001.
-   **Port already in use** → find and kill the process:
    `netstat -ano | findstr :8046` then `taskkill /PID <pid> /F`
    (swap the port number for 5173 or 8001 as needed).
-   **Cases dashboard is empty** → check backend logs for the seeding
    message, or manually trigger it: `curl -X POST http://127.0.0.1:8046/api/v1/init/seed`.
-   **CORS errors in the browser console** → confirm the frontend is
    running on `http://localhost:5173` (the backend's CORS allow-list
    in `backend/main.py` is currently limited to that origin plus
    `*.vercel.app`).

# License

This project is intended for educational, research, and demonstration
purposes.
