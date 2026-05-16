# 🏛️ Alpha Chi Omega: Autonomous Financial Audit Pipeline

## 📑 Executive Summary
The **AXO Financial Audit Agent** is a sophisticated automation suite developed to streamline collegiate chapter financial operations. By leveraging **Microsoft AutoGen**, **Google Cloud APIs**, and **Computer Vision (OCR)**, the system eliminates manual data entry by autonomously fetching, auditing, and categorizing invoices into a structured, Billhighway-ready ledger.

This project represents a transition from manual administrative tasks to **Strategic Financial Oversight**, ensuring 100% accuracy in General Ledger (GL) mapping and real-time expenditure tracking for the VP Finance.

---

## 🎯 Strategic Value & Business Case
In a high-volume financial environment like a UT Austin Greek organization, manual entry leads to two primary risks: **Latency** (delayed reports) and **Classification Error** (hallucinated GL codes). 

This pipeline mitigates these risks via:
* **Operational Efficiency:** Reduces invoice processing time from hours to seconds.
* **Audit Integrity:** Implements a "Hard-Coded" GL Directory, forbidding the AI from "inventing" codes.
* **Complex Business Logic:** Handles nuanced vendor rules, such as utility splits and conditional price-capping for maintenance.
* **Data Transparency:** Produces professional, CSS-styled PDF audit trails for every batch processed.

---

## 🤖 The AutoGen "Multi-Agent" Workflow
This system utilizes an **Agentic Orchestration** framework. Unlike standard scripts, AutoGen creates a "virtual team" that collaborates to ensure accuracy through internal peer review.

### 1. 🕵️ The Financial Auditor (The Executive)
* **Role:** Analyzes incoming billing content and maps it to precise GL Codes.
* **Knowledge Base:** Holds the "Single Source of Truth" directory. 
* **Reasoning:** It performs complex logic, such as:
    * **COA Split:** Identifying a "City of Austin" bill and mathematically splitting it between **8025 (Electric)** and **8030 (Water/Sewer)**.
    * **Cothrons Verification:** Checking if security invoices match the contracted **$330.31** amount; otherwise, flagging it as a repair.
    * **Noise Filtering:** Ignoring the "AAA Tech notes" on Oliver Termite bills to prevent misclassification into the "AAA Filter" GL code.

### 2. 📊 The Data Formatter (The Specialist)
* **Role:** Acts as the bridge between raw AI reasoning and structured accounting files.
* **Constraints:** Enforces strict Markdown and PDF formatting.
* **Output:** Ensures that the final data is a clean, numerical table that can be instantly uploaded to Billhighway.

---

## 📂 Master GL Directory & Business Logic
The system is governed by the following strict mapping rules:

| GL Code | Category | Description / Specific Logic |
| :--- | :--- | :--- |
| **8010** | Lease Payment | Lease Payment to LHC/NHC/University (LHCB) |
| **8024** | Gas | Texas Gas Service |
| **8025** | Electric | City of Austin (Electric only), AAA Filter Service |
| **8030** | Water/Sewer | City of Austin (Everything but electric), Global Water Tech |
| **8040** | Telephone | Apogee Telecom |
| **8050** | Maintenance | General fixes, plumbing, building repairs |
| **8060** | Supplies | Laurel's house purchases and general tools |
| **8070** | Cleaning/Pest | Shining Cleaning, Oliver Termite (Note: Ignore 'AAA' text; Note for Virginia: Leave check in cubby) |
| **8080** | Cable/Internet | Campus Connect/Apogee, Boldyn |
| **8090** | Linens | Sheet and towel services |
| **8160** | Trash | Central Texas Refuse, Break it Down, Republic |
| **8170** | Laundry | CSC, AutoChlor |
| **8175** | Housing Fee | Housing Commitment Fee Refund |
| **8224** | Security | GuardTexas, AllSafe, Cothrons (Note: Flag if amount != $330.31) |
| **9000** | Kitchen Supplies | College Fresh "Bill Back" invoices |
| **9050** | Food | Upper Crust Monthly Bills |
| **9060** | Tax | Sales & Usage Tax (National Statements) |
| **9350** | Kitchen Ops | Liquid Environmental (Grease disposal) |

---

## 🛠️ Technical Architecture
* **Orchestration:** `autogen-agentchat` (Microsoft Research)
* **Language Model:** `gpt-4o-mini` (Vision-enabled for scanned receipts)
* **API Integration:** `google-api-python-client` (Gmail & Drive)
* **OCR Engine:** `PyMuPDF` (High-res 300 DPI rendering)
* **Reporting:** `WeasyPrint` & `Markdown`

---

## 🚀 Installation & Security
1. **Environment Setup:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

2. **Credential Storage:**
    - Place `credentials.json` in the root (OAuth 2.0 Client ID).
    - Create a `.env` file with your `GITHUB_TOKEN`.

3. **Execution:**
    ```bash
    python agent.py