# 🏥 OPD Claim Adjudication System


An AI-powered automation tool built for the **Plum AI Automation Engineer Intern Assignment**. This system automates the end-to-end adjudication process for Outpatient Department (OPD) insurance claims, combining deterministic policy rules with Large Language Models (LLMs) for document understanding.

---

## 📋 Table of Contents
- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Decision Logic](#-decision-logic)
- [Tech Stack](#-tech-stack)
- [Setup & Installation](#-setup--installation)
- [API Documentation](#-api-documentation)
- [Assumptions](#-assumptions)

---

## 🚀 Overview

The **OPD Claim Adjudication Tool** streamlines the manual review of insurance claims. Users upload medical documents (bills, prescriptions), and the system:
1.  **Extracts Data**: Uses Vision LLMs to read handwritten and printed text.
2.  **Validates Policy**: Checks waiting periods, sub-limits, and exclusions.
3.  **Detects Fraud**: Flags duplicate claims or suspicious patterns.
4.  **Adjudicates**: Returns an instant `APPROVED`, `REJECTED`, or `PARTIAL` decision with detailed reasoning.

---

## 🏗 Architecture

The system follows a modern client-server architecture:

*(Place your architecture diagram here. Suggested flow: React UI -> FastAPI Server -> Adjudication Engine -> AI Service -> LLM Provider)*

### Core Components:
1.  **Frontend**: React + Vite application for claim submission and result visualization.
2.  **Backend API**: FastAPI service managing uploads, database transactions, and routing.
3.  **Adjudication Engine**: The brain of the system (`adjudication_engine.py`). It orchestrates the validation waterfall.
4.  **AI Service**: Handles document processing and "Medical Necessity" reasoning using LLMs.

---

## ✨ Features

- **📄 Universal Document Support**: Processes both Images (JPG/PNG) and PDFs.
- **🧠 Hybrid Intelligence**: Combines rigid policy rules (JSON) with flexible AI reasoning.
- **🛡️ Fraud Guard**: Automatically detects multiple claims filed for the same day.
- **💰 Smart Calculations**: Handles Network Discounts (20%), Co-pays (10%), and partial approvals automatically.
- **🔍 Granular Feedback**: Rejection reasons are specific (e.g., "Day 15 of 30-day waiting period") rather than generic.

---

## 🧠 Decision Logic

The `AdjudicationEngine` processes claims through a strict waterfall model. If a claim fails a critical step, it is rejected immediately.

*(Place your logic flowchart here)*

**Step-by-Step Evaluation:**
1.  **Fraud Check**: Is this a duplicate claim for the same treatment date?
2.  **AI Extraction**: Extract Member Name, Diagnosis, Procedures, and Amounts.
3.  **Eligibility**: Is the policy active? Is the **Waiting Period** served?
4.  **Identity Match**: Does the name on the document fuzzy-match the policyholder?
5.  **Coverage & Limits**:
    - Is the treatment excluded?
    - Has the **Annual Limit** or **Sub-limit** been exceeded?
    - Is **Pre-Auth** required (e.g., for MRI/CT)?
6.  **Medical Necessity**: Does the diagnosis justify the treatment? (AI Analysis).
7.  **Final Calculation**: Apply Network Discounts -> Deduct Co-pay -> Calculate Final Payout.

---

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (via SQLAlchemy)
- **PDF Processing**: PyMuPDF (`fitz`)
- **Validation**: Pydantic
- **AI Integration**: HTTPX (Async) connecting to LLM APIs

### Frontend
- **Framework**: React.js (Vite)
- **Styling**: Tailwind CSS
- **State Management**: React Hooks

---

## ⚡ Setup & Installation

### Prerequisites
- Node.js (v16+)
- Python (v3.9+)
- API Key for LLM (OpenAI/OpenRouter)

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Edit .env and add your AI_API_KEY
```

## 🚀 Getting Started

### 1. Backend Setup

Run the server:

```bash
python main.py
# Server starts at http://localhost:8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
# App opens at http://localhost:5173
```

---

## 📡 API Documentation

### `POST /api/v1/claims/submit`

Submits a new claim for adjudication.

**Form Data:**
* `member_id` (string)
* `member_name` (string)
* `treatment_date` (YYYY-MM-DD)
* `documents` (List[File])

**Response:** Returns `AdjudicationResult` with decision, approved amount, and reasoning.

---

### `GET /api/v1/claims/history`

Retrieves a list of past claims.

**Query Params:** `member_id` (optional)

---

### `GET /api/v1/claims/{claim_id}`

Retrieves detailed breakdown of a specific claim.

---

## 📝 Assumptions

1. **Policy Source:** The system loads a single policy configuration (`policy_terms.json`) at startup. Multi-policy support would require database scaling.
2. **Currency:** All monetary values are processed in INR (₹).
3. **Date Format:** The system standardizes all extracted dates to `YYYY-MM-DD` for comparison.
4. **Network Hospitals:** Network status is determined by string matching the hospital name against the list in `policy_terms.json`.

---

Built with ❤️ for Plum.