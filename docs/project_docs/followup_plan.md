# Follow-up Questions Feature - Approach Plan

## Current State

**Problem**: After getting wisdom guidance, users only see "Start Fresh Chat" option. No way to ask follow-up questions with context.

**User Experience Gap**:
- User asks: "How do I deal with anger?"
- Gets guidance + story
- Wants to ask: "But what if the person keeps provoking me?"
- Has to start fresh, losing all context

---

## Proposed Solution

### 1. UI/UX Changes

#### Current Flow
```
[Question] → [Guidance + Story] → [Start Fresh Chat Button]
```

#### New Flow
```
[Question] → [Guidance + Story] → [Ask Follow-up] or [Start Fresh Chat]
                                         ↓
                                  [Follow-up Question Input]
                                         ↓
                                  [Contextual Response]
```

**UI Elements to Add**:

1. **After Guidance Display**:
   ```jsx
   <div className="flex gap-3">
     <button className="primary">
       💬 Ask a Follow-up Question
     </button>
     <button className="secondary">
       🔄 Start Fresh Chat
     </button>
   </div>
   ```

2. **Follow-up Input State**:
   - Show input field below guidance
   - Pre-populate with "You asked: [original question]" context
   - Allow user to type follow-up
   - Smaller, inline style (not full-page like initial question)

---

## 2. Context Management Strategy

### Option A: Conversation History (Simple) ⭐ RECOMMENDED for MVP

**Frontend State**:
```javascript
const [conversation, setConversation] = useState([
  {
    type: 'user',
    question: 'How do I deal with anger?',
    timestamp: '...'
  },
  {
    type: 'assistant',
    guidance: '...',
    story: {...},
    timestamp: '...'
  },
  {
    type: 'user',
    question: 'But what if they keep provoking me?',
    isFollowUp: true
  },
  {
    type: 'assistant',
    guidance: '...',
    story: null  // No story for follow-ups
  }
]);
```

**Backend API Update**:
```python
POST /api/guidance
{
  "problem": "But what if they keep provoking me?",
  "conversation_history": [
    {"role": "user", "content": "How do I deal with anger?"},
    {"role": "assistant", "content": "Dear Partha, ..."}
  ]
}
```

**Pros**: Simple, full context, works with OpenAI format
**Cons**: Token costs grow

---

## 3. RAG Considerations for Follow-ups

**Challenge**: Follow-up questions are vague ("What if they keep doing it?")

**Solution**: Context-Aware RAG
```python
def get_guidance_with_context(problem, conversation_history=None):
    if conversation_history:
        # Enrich query with context
        context_query = f"""
        Previous: {conversation_history[-2]['content']}
        Follow-up: {problem}
        """
        # Skip story for follow-ups
        return {"guidance": ..., "story": None}
    else:
        # Full response with story
        return {"guidance": ..., "story": {...}}
```

---

## 4. Prompt Engineering for Follow-ups

```python
wisdom_prompt = f"""
You are Vasudeva (Krishna) in an ongoing conversation.

{f"PREVIOUS: User asked '{prev_question}' and you advised: '{prev_guidance[:200]}...'" if is_followup else ""}

Current Question: {question}

{"This is a follow-up - be direct and reference previous teachings" if is_followup else "Provide comprehensive guidance with story"}

Your guidance:
"""
```

---

## 5. Recommended MVP Implementation

### Must-Have for Phase 1

**UI**:
- ✅ "Ask Follow-up" button after guidance
- ✅ Inline input field
- ✅ Display follow-up response below

**State**:
- ✅ Store last Q&A  in React state
- ✅ Send as context with follow-up

**Backend**:
- ✅ Accept optional `conversation_history`
- ✅ Include in prompt
- ✅ Skip story for follow-ups

**Limitations (MVP)**:
- Only 1-level follow-up (not multi-turn chat)
- No persistence (lost on refresh)
- Full context sent (no summarization)

**Dev Time**: 4-6 hours  
**Token Cost**: +50-100% per follow-up

---

## 6. API Design

**Extend existing endpoint**:
```python
class GuidanceRequest(BaseModel):
    problem: str
    include_sources: bool = True
    conversation_history: Optional[List[Dict]] = None  # NEW

@app.post("/api/guidance")
async def get_guidance(request: GuidanceRequest):
    is_followup = bool(request.conversation_history)
    
    guidance = vasudeva.get_guidance(
        problem=request.problem,
        context=request.conversation_history,
        skip_story=is_followup  # No story for follow-ups
    )
    
    return guidance
```

---

## 7. User Experience Flow

**Turn 1**:
```
User: "How do I deal with anger?"
↓
[Guidance + Story]
[💬 Ask Follow-up] [🔄 Start Fresh]
```

**Turn 2** (clicks follow-up):
```
Previously: "How do I deal with anger?"
[Input: "But what if they keep provoking me?"]
[Send]
```

**Turn 3**:
```
Original: "How do I deal with anger?"
[Previous Guidance - minimized]

Follow-up: "But what if they keep provoking me?"
[New Guidance - focused, no new story]

[💬 Ask Another] [🔄 Start Fresh]
```

---

## 8. Token Optimization

**Problem**: Context grows with each turn

**Solutions**:
1. **Rolling window**: Last 2 messages only
2. **Summarization**: Compress old context  
3. **Smart context**: Key points only

**For MVP**: Accept higher cost, optimize later

---

## 9. Future Enhancements

**Phase 2**: Multi-turn chat interface
**Phase 3**: Conversation persistence, summarization
**Advanced**: "Tell me more about that story", topic threading

---

## Summary

**Start with**: Stateless, single-level follow-up

**Key Points**:
1. Add "Ask Follow-up" CTA
2. Send last Q&A as context
3. Skip story for follow-ups
4. Frontend state management (no backend storage)
5. Optimize later if needed

**Ready to implement Phase 1!**
