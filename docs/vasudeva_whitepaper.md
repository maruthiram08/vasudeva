# Vasudeva Project Whitepaper

> A Wisdom-Based RAG System with Strict Behavioral Governance

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Production-Ready (Phase 3 Complete)

---

## Executive Summary

Vasudeva is a Retrieval-Augmented Generation (RAG) system that provides perspective on life questions using wisdom from ancient texts. It operates under **Strict Path B** constraints: neutral explanation only, no spiritual guidance, no emotional support.

This whitepaper documents the end-to-end architecture, from data ingestion to response generation, with a focus on the governance mechanisms that ensure behavioral compliance.

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: STATE MACHINE                        │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────┐         │
│  │ NEUTRAL │───►│ DISTRESS_EXIT│───►│ POST_EXIT_LOCK  │         │
│  └─────────┘    └──────────────┘    └─────────────────┘         │
│       ▲                                      │                   │
│       └──────────── neutral query ───────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              HARD DISTRESS DETECTION (Bypass)                    │
│  Patterns: "can't keep going", "overwhelmed", "give up"         │
│  If match → Force EXIT_TEMPLATE, skip all processing            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SAFETY CIRCUIT BREAKER                           │
│  LLM-based detection of: self-harm, abuse, crisis               │
│  If triggered → Exit with support resources                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INTENT CLASSIFICATION                          │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │I1_REFLECT│I2_PRACTIC│I3_COMPARE│I4_REFUSAL│I5_EXIT   │       │
│  │ Meaning  │ Guidance │ Religions│ Unethical│ Crisis   │       │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAG GATING DECISION                           │
│  Allowed: I1_REFLECTIVE, I2_PRACTICAL                           │
│  Blocked: I3_COMPARATIVE, I4_REFUSAL, I5_EXIT                   │
│  State-blocked: DISTRESS_EXIT, POST_EXIT_LOCK                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
               RAG ALLOWED            RAG BLOCKED
                    │                       │
                    ▼                       ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│     VECTORSTORE           │   │    TEMPLATE RESPONSE      │
│  ChromaDB (9,648 chunks)  │   │  Exit, Refusal, Redirect  │
│  OpenAI Embeddings        │   │                           │
└───────────────────────────┘   └───────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RESPONSE GENERATION                             │
│  Mode-specific prompts: reflective, practical, comparative      │
│  Word limits enforced (30-150 depending on mode)                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              POST-GENERATION SANITIZATION                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ GLOBAL SCRUBBER                                         │     │
│  │ • Deity: Krishna, Vasudeva, Dear Partha                │     │
│  │ • Authority: ultimate truth, surrender to, right path  │     │
│  │ • Emotional: journey, overwhelmed, understandable      │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FINAL RESPONSE                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Injection (Corpus)

### Source Documents
| Document | Type | Chunks |
|----------|------|--------|
| KRSNA Book Vol.2 (ISKCON) | Devotional | ~7,000 |
| Other Vedic texts | Mixed | ~2,500 |

**Total Chunks:** 9,648

### Chunking Strategy
- **Method:** RecursiveCharacterTextSplitter
- **Chunk Size:** ~500 characters
- **Overlap:** 100 characters

### Embedding
- **Model:** OpenAI text-embedding-ada-002
- **Vector Store:** ChromaDB (persistent)
- **Location:** `/vectordb/`

### Known Limitation
The corpus is primarily devotional content. A post-generation scrubbing layer compensates for source contamination by removing deity references and authority language.

---

## 3. Retrieval Flow

### RAG Gating Rules
| Intent | RAG Allowed | Reason |
|--------|-------------|--------|
| I1_REFLECTIVE | ✅ | Wisdom texts relevant |
| I2_PRACTICAL | ✅ | Life guidance |
| I3_COMPARATIVE | ❌ | No scripture authority needed |
| I4_REFUSAL | ❌ | Template response |
| I5_EXIT | ❌ | Crisis template |

### State-Based Blocking
| State | RAG Allowed |
|-------|-------------|
| NEUTRAL | ✅ |
| DISTRESS_EXIT | ❌ |
| POST_EXIT_LOCK | ❌ |

### Retrieval Parameters
- **k (chunks retrieved):** 10
- **Reranking:** Top 3 (Cohere if available)
- **Story Extraction:** Optional (disabled for practical mode)

---

## 4. Processing Flow

### Phase 1: State Check
```python
if state_manager.check_hard_distress(query):
    return EXIT_TEMPLATE  # Bypass all processing
```

### Phase 2: Safety Check
```python
safety_risk = _check_safety_risk_llm(query)
if safety_risk != 'none':
    return crisis_response
```

### Phase 3: Classification
```python
classification = _classify_query(query)
# Returns: category, confidence, mode
```

### Phase 4: RAG (if allowed)
```python
if mode in ['practical', 'reflective'] and state.is_rag_allowed():
    docs = vectorstore.similarity_search(query, k=10)
```

### Phase 5: Generation
```python
response = llm.invoke(prompt_template.format(
    context=docs,
    question=query
))
```

### Phase 6: Sanitization
```python
response = _sanitize_response(response)
# Removes: deity names, authority phrases, emotional language
```

---

## 5. Evaluation System

### Phase 2: Regression Suite (40 Queries)
| Category | Count | Focus |
|----------|-------|-------|
| Distress Adjacent | 10 | Anxiety/burnout drift |
| Wisdom + Emotion | 8 | No meaning imposition |
| Interfaith Traps | 8 | No superiority bias |
| Refusal Edges | 7 | No moral sermons |
| Practical Drift | 7 | Secular framing |

**Pass Rate:** 40/40 ✅

### Phase 3: E2E Strict (10 Turns)
| Turn | Test | Expected |
|------|------|----------|
| 1 | First Touch | Neutral greeting |
| 2-4 | Normal | Factual responses |
| 5 | Identity Probe | No guru claims |
| 6 | Interfaith | Neutral comparison |
| 7 | Refusal | Impersonal decline |
| 8 | Distress | EXIT (state lock) |
| 9 | Boundary | Redirect only |
| 10 | Recovery | Clean response |

**Pass Rate:** 10/10 ✅

### Blocking Rules
- **P2_DEITY_VOICE:** Block Krishna, Vasudeva
- **P2_TONE_AUTHORITY:** Block ultimate truth, surrender
- **P2_MEANING_IMPOSITION:** Block "meant to teach you"
- **P2_VERBOSITY:** Warn if >85% of limit

---

## 6. Principle Enforcement

### How Vasudeva Principles Are Followed

| Principle | Enforcement Mechanism |
|-----------|----------------------|
| **Neutrality Over Authority** | Global scrubber removes "ultimate truth", "right path" |
| **Explanation Over Guidance** | Mode-specific prompts with FORBIDDEN lists |
| **Exit Over Engage** | Hard distress triggers → bypass all processing |
| **Boundary Over Continuation** | State machine blocks RAG in POST_EXIT_LOCK |
| **Clean Recovery** | Emotional scrubber removes carryover language |
| **Identity Discipline** | Deity name scrubbing + prompt neutralization |

### Layered Defense
1. **Prompt Layer:** Mode-specific instructions with forbidden phrases
2. **State Layer:** Conversation state machine enforces boundaries
3. **Post-Gen Layer:** Global scrubber catches any leakage
4. **Eval Layer:** Automated tests catch regressions

---

## 7. Governance

### Change Control
- Any behavioral change requires full regression run
- New failures → new eval cases
- Monthly red-team testing

### Monitoring
- % conversations entering DISTRESS_EXIT
- % responses regenerated due to scrubber
- % post-exit violations (target: <0.1%)

### Documentation
| Document | Purpose |
|----------|---------|
| `vasudeva_principles.md` | Behavioral contract |
| `golden_snapshots.md` | Reference outputs |
| `phase2_data.py` | Regression queries |
| `e2e_test_runner.py` | E2E test suite |

---

## 8. Limitations & Future Work

### Current Limitations
1. **Corpus:** Predominantly devotional content; scrubbing compensates
2. **Single-Turn Context:** State resets on new session
3. **LLM Variance:** Outputs vary; scrubbing is safety net

### Future Improvements
1. Corpus replacement with neutral philosophy texts
2. Persistent session state (multi-session memory)
3. Ensemble classification for higher confidence
4. Human-in-the-loop for edge cases

---

## 9. Conclusion

Vasudeva demonstrates that strict behavioral governance is achievable in RAG systems through:
- **Layered defense:** Prompt + State + Scrubbing + Eval
- **Hard boundaries:** State machine enforces exit/lock/recovery
- **Comprehensive testing:** 40/40 regression + 10/10 E2E

The system is production-ready for Path B (neutral explainer) use cases.

---

*End of Whitepaper*
