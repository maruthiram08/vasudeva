# Vasudeva: Project Handoff Documentation
*For AI Agents & Developers taking over the project.*

## 1. Project Context
**Vasudeva** is a RAG-based AI Wisdom Guidance System that uses semantic search on sacred texts (Gita, Ramayana, etc.) to provide mental wellness advice.

### Key Differentiators
- **Hybrid Fact-Checking**: A "Critic" loop verifies every extracted story against the source PDF to prevent hallucinations.
- **Async Architecture**: Guidance streams in <1s; deeply researched stories fade in 5-8s later.
- **Safety**: 22 automated eval tests ensure no toxicity or spiritual bypassing.

---

## 2. Quick Start
**Backend (FastAPI)**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python api.py
# Runs on localhost:8000
```

**Frontend (React)**
```bash
cd frontend
npm install
npm run dev
# Runs on localhost:5173
```

**Evals (Quality Gate)**
```bash
cd eval_system
python run_evals.py
# Must pass 22/22 tests before committing
```

---

## 3. Architecture & Critical Paths

### Core Logical Flow
1. **User Query** -> `api.py` (/guidance)
2. **Retrieval** -> `vasudeva_rag.py` (ChromaDB search)
3. **Generation** -> `GPT-4o-mini` (Two-pass: Guidance + Story)
4. **Verification** -> `_fact_check_narrative` method (Self-correction)

### Critical Files
| File Path | Purpose |
| :--- | :--- |
| `backend/vasudeva_rag.py` | **THE BRAIN**. Contains RAG logic, prompt templates, and fact-checking loop. |
| `backend/api.py` | API Wrapper. Handles async extraction and feedback endpoints. |
| `frontend/src/App.jsx` | Main UI. Handles the "Streaming + Fade-In" UX logic. |
| `eval_system/run_evals.py` | The Quality Gate. Determines if code is safe to ship. |
| `backend/feedback_utils.py` | Handles the "Helpful/Not Helpful" data logging. |

---

## 4. Documentation Index
*Located in `vasudeva/docs/project_docs/`*

- `project_whitepaper.pdf`: **Board-Level Overview**. Use this to explain "Why Vasudeva" to non-techs.
- `implementation_plan.md`: Technical architecture decisions.
- `evals_plan.md`: Logic behind the 22 safety tests.
- `feedback_system_plan.md`: Design of the RLHF (Reinforcement Learning) loop.

---

## 5. Active Roadmap (Next Steps)
1. **Follow-up Questions**: Allow users to ask detailed follow-ups on the displayed story.
    * *Status*: Planned. See `followup_plan.md`.
2. **Analytics Dashboard**: Visualize the Feedback data (Upvotes vs Downvotes).
    * *Status*: Data collection live; Dashboard UI needed.

---

## 6. Known "Gotchas"
- **PDF Parsing**: If you change the chunking size in `vasudeva_rag.py`, you MUST re-build the vector DB.
- **Async Timing**: The frontend expects the `story` object to arrive asynchronously. Do not block the main guidance stream.
- **Eval Cost**: Running the full 22-test suite takes ~7 mins and costs ~$0.15 per run.

---
*End of Handoff. Good luck!*
