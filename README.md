Smart BOE
AI-Assisted SEE Examination Question Paper Verification System
Smart BOE is a decision-support system that helps the Board of Examination (BOE) verify Semester End Examination (SEE) question papers against the prescribed syllabus and textbook. It is not a question-generation tool — the BOE uploads an already-prepared question paper, and the system checks it for syllabus/textbook alignment, Course Outcome (CO) and Bloom's Taxonomy alignment, semantic duplication between questions, and marks/section correctness.
The AI produces a recommendation only. The BOE remains the final authority and can accept, reject, or override any AI result.
---
Features
🔐 Single-account authenticated access (backend-enforced)
📄 Upload question paper, syllabus, and prescribed textbook together
🧾 Supports 50-mark and 100-mark SEE patterns (configurable, not hardcoded)
🤖 Multi-agent verification pipeline:
QP Agent — parses question paper structure, sections, and marks
Syllabus + Textbook Agent — RAG-based evidence retrieval and verification
CO + Bloom Agent — Course Outcome and Bloom's Taxonomy alignment
Duplication Agent — semantic duplicate detection across questions
Coordinating Agent — orchestrates all agents and aggregates results
✅ Deterministic marks & section validator (no LLM involved)
🗄️️ Full persistence — every paper, agent result, and BOE decision is stored and retrievable
📊 Dashboard of previously verified papers
📝 Question-wise evidence, explanations, and BOE decision recording
📑 PDF verification report generation
---
Tech Stack
Frontend: React (JavaScript) + Vite  
Backend: Python + FastAPI  
Database: SQLite  
Vector DB: ChromaDB  
Document Processing: PyMuPDF (PDF), python-docx (DOCX), Tesseract OCR (scanned docs)  
Embeddings / Similarity: Sentence Transformers  
LLM: Gemini API / GPT API  
Reports: ReportLab
---
Project Structure
```text
smart-boe/
├── backend/    # FastAPI app, agents, RAG pipeline, DB
├── frontend/   # React + Vite UI
└── README.md
```
---
Setup
Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in secrets/API keys
uvicorn app.main:app --reload
```
Frontend
```bash
cd frontend
npm install
npm run dev
```
---
Environment Variables
Create a `.env` file in `backend/` based on `.env.example`:
```env
BOE_USERNAME=boe_admin
BOE_PASSWORD_HASH=<bcrypt-hash>
JWT_SECRET=<your-secret>
LLM_API_KEY=<your-llm-api-key>
```
> Never commit `.env` or expose API keys in frontend code.
---
Workflow
Log in with the single BOE admin account
Start a new SEE verification
Upload the question paper, syllabus, and textbook
Select the SEE pattern (50 or 100 marks)
Click Verify Paper
Review the overall paper summary and question-wise results
Record BOE decisions (Accept / Reject / Override) per question
Generate the final PDF report
---
Status
🚧 Under active development — final-year engineering project.
---
License
For academic use.