# DiVeL -- Digital Evidence Locker

## Blockchain & GenAI Powered Digital Evidence Management and Intelligence Platform

DiVeL is a cloud-native Digital Evidence Management System designed for
law enforcement agencies, forensic laboratories, and judicial
organizations. It provides secure evidence storage, blockchain-backed
integrity verification, AI-powered evidence summarization, and an
intelligent investigation assistant using Amazon Bedrock.

------------------------------------------------------------------------
## Features

- Secure Digital Evidence Storage
- Blockchain-based Evidence Integrity Verification
- AI-powered Evidence Summarization
- Intelligent Investigation Assistant
- Case Management
- Evidence Upload & Tracking
- SHA-256 Hash Verification
- Immutable Blockchain Anchoring
- Amazon S3 Storage
- DynamoDB Metadata Storage
- Role-Based Authentication
- Audit Logging
- REST APIs

# Overall System Architecture

``` text
                         ┌──────────────────────────────┐
                         │        React Frontend        │
                         │                              │
                         │ • Case Management            │
                         │ • Evidence Upload            │
                         │ • Dashboard                  │
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
 Store Metadata Only
 processing_status = NOT_SUPPORTED
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
POST /assistant/chat
       │
       ▼
FastAPI
       │
       ▼
Amazon Nova Lite
(Intent Classification)
       │
       ▼
Query Router
       │
 ┌─────┴─────────────────────┐
 │                           │
 ▼                           ▼
DynamoDB                 Amazon Nova Lite
Statistics               Evidence Reasoning
& Case Search            (Stored Summaries)
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

-   React
-   TypeScript
-   Vite
-   Axios

## Backend

-   FastAPI
-   Python
-   Pydantic
-   Boto3

## Cloud

-   Amazon S3
-   Amazon DynamoDB
-   AWS Lambda
-   Amazon API Gateway
-   Amazon Bedrock
-   AWS IAM
-   AWS CloudWatch
-   AWS KMS

## AI

-   Amazon Nova Lite (`amazon.nova-lite-v1:0`)
-   Amazon Bedrock Converse API

## Blockchain

-   Solidity
-   Hardhat
-   Ethereum Sepolia

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

------------------------------------------------------------------------

# Repository Structure

``` text
DiVeL
├── backend
│   ├── app
│   │   ├── api
│   │   ├── services
│   │   ├── models
│   │   ├── core
│   │   └── utils
│   └── requirements.txt
├── frontend
│   ├── src
│   ├── components
│   ├── pages
│   └── services
├── blockchain
│   ├── contracts
│   ├── scripts
│   └── hardhat.config.js
└── README.md
```

------------------------------------------------------------------------

# Running the Project

## Backend

``` powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

``` powershell
cd frontend
npm install
npm run dev
```

------------------------------------------------------------------------

# API Endpoints

  Method   Endpoint
  -------- ---------------------------
  POST     `/api/v1/evidence/upload`
  GET      `/api/v1/cases`
  POST     `/api/v1/assistant/chat`

------------------------------------------------------------------------

# Security Features

-   SHA-256 evidence hashing
-   Blockchain integrity verification
-   Immutable evidence metadata
-   IAM-based authorization
-   Encryption at rest and in transit
-   Audit-ready architecture

------------------------------------------------------------------------

# Future Enhancements

-   OCR for image evidence
-   Video understanding
-   Knowledge Graph generation
-   Semantic search with vector database
-   Investigation timeline generation
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
# License

This project is intended for educational, research, and demonstration
purposes.
