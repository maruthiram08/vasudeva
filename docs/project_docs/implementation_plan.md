# STAR Framework Feature - Implementation Plan

Enhance Vasudeva to include relevant stories from sacred texts explained using the STAR framework when providing guidance.

---

## Overview

**Current Behavior**:
- User asks question → Gets wisdom guidance
- "View Sacred Wisdom Sources" shows raw text passages
- No narrative or story format

**Proposed Enhancement**:
- Identify relevant stories/instances from sacred texts
- Present them using STAR framework:
  - **S**ituation: The context/dilemma faced
  - **T**ask: What needed to be done
  - **A**ction: What the character did
  - **R**esult: The outcome and lesson learned
- Make wisdom more relatable and actionable

---

## User Review Required

> [!IMPORTANT]
> **Response Structure Change**
> 
> The guidance response will now include:
> 1. Main wisdom guidance (current format)
> 2. **NEW**: Relevant story in STAR format (if applicable)
> 3. Source passages (existing)
> 
> This may slightly increase API response time due to more detailed LLM processing.

---

## Proposed Changes

### Backend Modifications

#### [MODIFY] [vasudeva_rag.py](file:///Users/maruthi/Desktop/MainDirectory/vasudeva/backend/vasudeva_rag.py)

**Changes to `setup_qa_chain()` method**:

Enhanced prompt template to:
1. Search for relevant stories/instances in the wisdom texts
2. Format stories using STAR framework
3. Include both direct guidance AND story narrative

**New Prompt Structure**:
```python
wisdom_prompt_template = """You are Vasudeva (Krishna)...

Your response should have TWO parts:

PART 1: Direct Guidance
- Address them as "Dear Partha,"
- Provide compassionate wisdom
- 3-6 sentences

PART 2: Relevant Story (if applicable)
If the wisdom texts contain a relevant story, present it as:

**Story from the Sacred Texts:**

**Situation:** [Describe the context/dilemma]
**Task:** [What needed to be addressed]
**Action:** [What the character did]
**Result:** [The outcome and lesson]

Format your response as JSON:
{
  "guidance": "...",
  "story": {
    "situation": "...",
    "task": "...",
    "action": "...",
    "result": "...",
    "source": "Which text (e.g., Bhagavad Gita Chapter X)"
  } OR null if no relevant story
}
"""
```

**Changes to `get_guidance()` method**:
- Parse JSON response from LLM
- Extract both guidance and story components
- Include in response object

---

### Frontend Modifications

#### [MODIFY] [App.jsx](file:///Users/maruthi/Desktop/MainDirectory/vasudeva/frontend/src/App.jsx)

**New UI Components**:

1. **Story Card Section** (between guidance and sources):
   ```jsx
   {guidance.story && (
     <StoryCard story={guidance.story} />
   )}
   ```

2. **STAR Framework Display**:
   - Each component (S-T-A-R) in separate visual blocks
   - Icons for each section
   - Smooth animations
   - Gradient backgrounds

**Visual Design**:
- Use accordion or card layout
- Different colors/icons for S-T-A-R
- Highlight key lessons
- Link to full source text

---

## Implementation Approach

### Phase 1: Backend Enhancement
1. Update prompt template in `setup_qa_chain()`
2. Modify response parsing in `get_guidance()`
3. Add JSON parsing with fallback
4. Test with various question types

### Phase 2: Frontend Enhancement
1. Create `StoryCard` component
2. Add STAR framework visual sections
3. Implement animations
4. Update styling

### Phase 3: Refinement
1. Test with multiple scenarios
2. Handle edge cases (no story found)
3. Optimize prompt for better story extraction
4. Polish UI/UX

---

## Response Structure

### Current Response
```json
{
  "problem": "I'm anxious about my future",
  "guidance": "Dear Partha, ...",
  "sources": [{"text": "...", "metadata": {...}}],
  "model": "gpt-4o-mini"
}
```;

### New Response
```json
{
  "problem": "I'm anxious about my future",
  "guidance": "Dear Partha, ...",
  "story": {
    "situation": "Arjuna stood on the battlefield...",
    "task": "He had to fulfill his duty as a warrior...",
    "action": "Krishna counseled him to focus on dharma...",
    "result": "Arjuna overcame his anxiety and fought...",
    "source": "Bhagavad Gita, Chapter 2",
    "character": "Arjuna",
    "lesson": "Focus on duty, not outcomes"
  },
  "sources": [...],
  "model": "gpt-4o-mini"
}
```

---

## UI Mockup

```
┌─────────────────────────────────────┐
│ 💬 Vasudeva's Guidance              │
│                                     │
│ Dear Partha,                        │
│ [Wisdom guidance text...]           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 📖 A Story from the Sacred Texts    │
│                                     │
│ 🎭 Situation                        │
│ [Description of context]            │
│                                     │
│ 🎯 Task                             │
│ [What needed to be done]            │
│                                     │
│ ⚡ Action                           │
│ [What was done]                     │
│                                     │
│ ✨ Result & Lesson                  │
│ [Outcome and wisdom]                │
│                                     │
│ 📚 Source: Bhagavad Gita Ch. 2      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ▼ View Original Text Passages (5)   │
└─────────────────────────────────────┘
```

---

## Example Use Cases

### Query: "I'm anxious about my career decision"

**Story Extracted**: Arjuna's dilemma on the battlefield

- **Situation**: Arjuna faced a moral crisis before battle
- **Task**: Had to choose between duty and emotions
- **Action**: Krishna taught him about dharma and detachment
- **Result**: Found clarity by focusing on duty, not outcomes

### Query: "How do I deal with attachment to material things?"

**Story Extracted**: King Bharata and the deer

- **Situation**: A king renounced everything but became attached to a deer
- **Task**: Needed to achieve true detachment
- **Action**: Learned that any attachment, even to dharma, binds
- **Result**: Understanding that liberation comes from complete surrender

---

## Technical Considerations

### LLM Response
- Use JSON mode or structured output
- Fallback to plain text if JSON parsing fails
- Handle cases where no relevant story exists

### Performance
- Story extraction adds ~1-2 seconds to response time
- Consider caching common stories
- Monitor token usage (may increase by 20-30%)

### Edge Cases
- No relevant story found → Show only guidance
- Multiple relevant stories → Pick most relevant one
- Story parsing fails → Gracefully degrade

---

## Verification Plan

### Testing Scenarios
1. **With Clear Story Match**:
   - Query: "I'm conflicted between duty and emotion"
   - Expected: Arjuna's story from Bhagavad Gita

2. **Abstract Concepts**:
   - Query: "What is the nature of reality?"
   - Expected: Philosophical guidance, possibly Sankhya philosophy story

3. **Modern Problems**:
   - Query: "I'm stressed about my job"
   - Expected: Guidance + relevant story about work/duty

4. **No Story Match**:
   - Query: "Technical question about code"
   - Expected: Guidance only, story = null

---

## Success Criteria

✅ LLM successfully identifies relevant stories 80%+ of time  
✅ STAR framework is clear and well-structured  
✅ UI displays stories in engaging, readable format  
✅ Response time acceptable (< 5 seconds)  
✅ Graceful degradation when no story found  
✅ Source attribution is accurate

---

## Next Steps

Once approved:
1. Implement backend prompt enhancement
2. Test story extraction with sample queries
3. Build frontend Story Card component
4. Integrate and test end-to-end
5. Gather feedback and refine
