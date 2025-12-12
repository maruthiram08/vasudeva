# Feedback System & Adaptive Story Generation - Implementation Plan

## Executive Summary

Implement a feedback-driven continuous improvement system that:
1. Captures user feedback with specific downvote reasons
2. Classifies questions and stories by type/category
3. Uses feedback data to refine prompts and strategies
4. Adapts story generation approach based on question type

---

## Phase 1: Feedback System (Week 1-2)

### 1.1 Frontend - Feedback UI

**Upvote/Downvote Component**:
```jsx
// After each response (guidance + story)
<div className="feedback-section">
  <button onClick={handleUpvote}>
    👍 Helpful
  </button>
  <button onClick={handleDownvote}>
    👎 Not Helpful
  </button>
</div>
```

**Downvote Reasons Modal**:
```jsx
// When user clicks downvote
<Modal>
  <h3>What went wrong?</h3>
  <RadioGroup>
    ○ Story is inaccurate or fabricated
    ○ Facts are incorrect
    ○ Story not relevant to my question
    ○ Guidance too generic
    ○ Missing important context
    ○ Story is incomplete
    ○ Language/tone not appropriate
    ○ Other: [text input]
  </RadioGroup>
  <button>Submit Feedback</button>
</Modal>
```

**Design**:
- Subtle, non-intrusive placement
- Optional text field for detailed feedback
- Thank you message after submission

---

### 1.2 Backend - Feedback API

**Database Schema**:
```sql
CREATE TABLE feedback (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMP,
  
  -- Request data
  question TEXT,
  question_category VARCHAR(50),  -- Classified
  question_type VARCHAR(50),      -- Classified
  
  -- Response data
  guidance TEXT,
  story_title VARCHAR(200),
  story_character VARCHAR(100),
  story_source VARCHAR(200),
  story_narrative TEXT,
  
  -- Feedback
  vote VARCHAR(10),  -- 'upvote' or 'downvote'
  downvote_reason VARCHAR(100),
  detailed_feedback TEXT,
  
  -- Metadata
  response_time_ms INT,
  fact_check_issues_count INT,
  story_regenerated BOOLEAN,
  
  -- Session
  session_id VARCHAR(100)
);

CREATE INDEX idx_vote ON feedback(vote);
CREATE INDEX idx_category ON feedback(question_category);
CREATE INDEX idx_reason ON feedback(downvote_reason);
```

**API Endpoint**:
```python
@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Store user feedback for continuous improvement.
    
    Request:
    {
      "session_id": "...",
      "question": "...",
      "guidance": "...",
      "story": {...},
      "vote": "upvote" | "downvote",
      "downvote_reason": "story_inaccurate" | "facts_incorrect" | ...,
      "detailed_feedback": "..."
    }
    """
    # Classify question (see Phase 2)
    question_category = classify_question_category(feedback.question)
    question_type = classify_question_type(feedback.question)
    
    # Store in database
    db.insert_feedback({
        ...feedback,
        "question_category": question_category,
        "question_type": question_type,
        "timestamp": now()
    })
    
    return {"status": "success"}
```

---

## Phase 2: Question Classification (Week 2-3)

### 2.1 Question Categories

**Emotional Categories**:
- `grief_loss` - Death, separation, letting go
- `anger_conflict` - Anger, betrayal, conflict
- `anxiety_fear` - Worry, uncertainty, fear
- `confusion_doubt` - Indecision, confusion, doubt
- `desire_attachment` - Craving, attachment, addiction
- `duty_dharma` - Moral dilemmas, duty conflicts
- `relationships` - Friendship, family, love issues
- `career_purpose` - Life direction, purpose, career

**Question Types**:
- `how_to_deal` - "How do I deal with X?"
- `why_happened` - "Why did this happen to me?"
- `what_should_do` - "What should I do?"
- `is_it_okay` - "Is it okay to...?"
- `how_to_overcome` - "How to overcome X?"
- `understanding` - "Help me understand..."

### 2.2 Classification Implementation

**LLM-Based Classifier**:
```python
def classify_question(question: str) -> Dict[str, str]:
    """Classify question category and type."""
    
    prompt = f"""Classify this question:

Question: {question}

Return JSON:
{{
  "category": "grief_loss | anger_conflict | anxiety_fear | ...",
  "type": "how_to_deal | why_happened | what_should_do | ...",
  "keywords": ["keyword1", "keyword2", ...],
  "emotional_intensity": "low | medium | high"
}}
"""
    
    response = llm.invoke(prompt, temperature=0)
    return json.loads(response)
```

**Rule-Based Classifier** (faster, backup):
```python
CATEGORY_KEYWORDS = {
    "grief_loss": ["death", "died", "loss", "gone", "passed away", "left me"],
    "anger_conflict": ["angry", "betrayed", "fight", "conflict", "argument"],
    ...
}

def classify_by_keywords(question: str) -> str:
    question_lower = question.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        scores[category] = score
    return max(scores, key=scores.get)
```

---

## Phase 3: Story Classification (Week 3)

### 3.1 Story Categories

**By Source Text**:
- `bhagavad_gita` - Battlefield, duty, yoga
- `srimad_bhagavatam` - Krishna leela, devotional
- `ramayana` - Dharma, loyalty, relationships
- `mahabharata` - Complex dharma, politics
- `upanishads` - Philosophy, self-knowledge

**By Theme**:
- `duty_vs_desire` - Dharmic conflict
- `devotion_surrender` - Bhakti, surrender to divine
- `detachment_renunciation` - Letting go
- `knowledge_wisdom` - Jnana, understanding
- `courage_valor` - Facing challenges
- `patience_perseverance` - Endurance
- `humility_pride` - Ego lessons

### 3.2 Automatic Story Tagging

```python
def tag_story(story_data: Dict, source_passages: List) -> Dict:
    """Automatically tag story with categories."""
    
    # Extract source
    source_text = story_data.get('source', '')
    if 'bhagavad gita' in source_text.lower():
        source_category = 'bhagavad_gita'
    elif 'bhagavatam' in source_text.lower():
        source_category = 'srimad_bhagavatam'
    # ...
    
    # Classify theme using LLM
    theme = classify_story_theme(story_data['narrative'])
    
    return {
        **story_data,
        'source_category': source_category,
        'theme': theme,
        'character_type': extract_character_type(story_data['character'])
    }
```

---

## Phase 4: Feedback Analytics Dashboard (Week 4)

### 4.1 Key Metrics to Track

**Overall Metrics**:
- Upvote rate by category: `upvotes / total_votes`
- Most common downvote reasons
- Response time vs satisfaction correlation

**By Question Category**:
```sql
SELECT 
  question_category,
  COUNT(*) as total,
  SUM(CASE WHEN vote='upvote' THEN 1 ELSE 0 END) as upvotes,
  ROUND(100.0 * upvotes / total, 2) as upvote_rate
FROM feedback
GROUP BY question_category
ORDER BY upvote_rate DESC;
```

**By Story Source**:
- Which sources get more upvotes?
- Which sources have "story_inaccurate" issues?

**By Question-Story Match**:
```sql
-- Do certain question types work better with certain story sources?
SELECT 
  question_category,
  story_source_category,
  AVG(CASE WHEN vote='upvote' THEN 1 ELSE 0 END) as success_rate
FROM feedback
WHERE story_title IS NOT NULL
GROUP BY question_category, story_source_category;
```

### 4.2 Analytics Insights

**Identify Patterns**:
1. "grief_loss" questions → Bhagavatam stories = 85% upvote
2. "duty_dharma" questions → Bhagavad Gita = 90% upvote
3. "anger_conflict" questions → Ramayana stories = 70% upvote
4. Stories with fact-check issues → 40% downvote

**Action Items**:
- Prefer certain sources for certain question types
- Tighten fact-checking for problematic sources
- Adjust prompts based on common feedback

---

## Phase 5: Adaptive Strategy Selection (Week 5-6)

### 5.1 Multi-Strategy Framework

**Strategy Registry**:
```python
STRATEGIES = {
    "quote_based_strict": {
        "temperature": 0.3,
        "prohibitions": "strict",
        "fact_check": True,
        "best_for": ["grief_loss", "duty_dharma"],
        "upvote_rate": 0.85
    },
    
    "narrative_flowing": {
        "temperature": 0.5,
        "prohibitions": "moderate",
        "fact_check": True,
        "best_for": ["relationships", "anxiety_fear"],
        "upvote_rate": 0.78
    },
    
    "minimal_factual": {
        "temperature": 0.2,
        "prohibitions": "very_strict",
        "fact_check": True,
        "best_for": ["confusion_doubt"],
        "upvote_rate": 0.82,
        "notes": "Short, factual, no embellishment"
    },
    
    "devotional_expressive": {
        "temperature": 0.4,
        "prohibitions": "moderate",
        "fact_check": True,
        "best_for": ["desire_attachment"],
        "upvote_rate": 0.75,
        "notes": "More emotional, bhakti-focused"
    }
}
```

### 5.2 Strategy Selection Logic

```python
def select_story_strategy(
    question: str,
    question_category: str,
    question_type: str
) -> Dict:
    """Select best strategy based on question analysis."""
    
    # Get historical performance
    performance = db.query("""
        SELECT strategy, AVG(upvote) as success_rate
        FROM feedback
        WHERE question_category = ?
        GROUP BY strategy
        ORDER BY success_rate DESC
        LIMIT 1
    """, question_category)
    
    if performance:
        best_strategy = performance[0]['strategy']
        return STRATEGIES[best_strategy]
    
    # Fallback to default mapping
    default_map = {
        "grief_loss": "quote_based_strict",
        "anger_conflict": "narrative_flowing",
        "duty_dharma": "quote_based_strict",
        "confusion_doubt": "minimal_factual",
        ...
    }
    
    strategy_name = default_map.get(question_category, "quote_based_strict")
    return STRATEGIES[strategy_name]
```

### 5.3 Dynamic Prompt Generation

```python
def generate_narrative_prompt(
    story_data: Dict,
    user_problem: str,
    strategy: Dict
) -> str:
    """Generate prompt based on selected strategy."""
    
    base_prohibitions = {...}  # Current prohibitions
    
    if strategy['prohibitions'] == 'very_strict':
        prohibitions = base_prohibitions + [
            "No emotional interpretations",
            "Quote passages directly",
            "Keep narrative under 3 sentences"
        ]
    elif strategy['prohibitions'] == 'moderate':
        prohibitions = base_prohibitions  # Standard
    
    temperature = strategy['temperature']
    
    prompt = f"""Create a story using strategy: {strategy['name']}
    
    PROHIBITIONS: {prohibitions}
    
    TEMPERATURE: {temperature}
    
    [rest of prompt...]
    """
    
    return prompt
```

---

## Phase 6: Continuous Refinement Loop (Ongoing)

### 6.1 A/B Testing Framework

```python
def ab_test_strategies(question_category: str):
    """Test multiple strategies for same category."""
    
    # For 20% of requests in this category, use alternative strategy
    if random.random() < 0.2:
        strategy = select_alternative_strategy(question_category)
        metadata['ab_test'] = True
        metadata['strategy_tested'] = strategy['name']
    else:
        strategy = select_best_strategy(question_category)
        metadata['ab_test'] = False
    
    return strategy
```

### 6.2 Weekly Refinement Process

**Every Week**:
1. **Analyze Feedback**:
   ```sql
   -- Get worst performing categories
   SELECT question_category, downvote_reason, COUNT(*)
   FROM feedback
   WHERE vote = 'downvote'
   AND timestamp > NOW() - INTERVAL '7 days'
   GROUP BY question_category, downvote_reason
   ORDER BY COUNT(*) DESC
   LIMIT 10;
   ```

2. **Identify Issues**:
   - If "story_inaccurate" is common → tighten fact-checking
   - If "not_relevant" is common → improve story selection
   - If "incomplete" is common → adjust narrative length

3. **Adjust Prompts**:
   - Update prohibitions
   - Modify fact-checking criteria
   - Change temperature/strategy

4. **Re-evaluate**:
   - Monitor next week's metrics
   - Compare before/after upvote rates

---

## Phase 7: Advanced Features (Future)

### 7.1 User Preferences

```python
# Remember user preferences
user_preferences = {
    "story_style": "concise" | "detailed" | "poetic",
    "preferred_sources": ["bhagavad_gita", "upanishads"],
    "language_level": "simple" | "scholarly"
}
```

### 7.2 Contextual Story Selection

```python
# Prefer stories that worked well for similar questions
similar_questions = find_similar_questions(current_question)
successful_stories = get_upvoted_stories(similar_questions)
prioritize_similar_stories(successful_stories)
```

### 7.3 Explanation Mode

```python
# On downvote, offer to explain story selection
if downvote_reason == "not_relevant":
    return {
        "explanation": "This story was chosen because...",
        "offer_alternative": True
    }
```

---

## Data Points to Capture

### Minimum Viable Data (Phase 1):
1. `vote` - upvote/downvote
2. `downvote_reason` - specific reason
3. `question` - user's question
4. `story_title` - which story was shown
5. `timestamp` - when

### Enhanced Data (Phase 2-3):
6. `question_category` - emotional category
7. `question_type` - question format
8. `story_source_category` - Gita, Bhagavatam, etc.
9. `story_theme` - detachment, courage, etc.
10. `fact_check_issues_count` - how many issues found
11. `story_regenerated` - was story regenerated?
12. `response_time_ms` - performance metric

### Advanced Data (Phase 4+):
13. `strategy_used` - which narrative strategy
14. `ab_test_variant` - A/B testing flag
15. `user_session_data` - preferences, history
16. `similar_question_match` - relevance score

---

## Success Metrics

**Short-term (1 month)**:
- Collect 500+ feedbacks
- Identify top 3 downvote reasons
- Achieve >60% upvote rate

**Medium-term (3 months)**:
- Upvote rate >75% 
- <10% "story_inaccurate" downvotes
- Strategy selection working for 5+ categories

**Long-term (6 months)**:
- Upvote rate >85%
- Adaptive strategies outperform single approach by 15%
- User retention improved by 30%

---

## Implementation Priority

### Must Have (MVP):
1. ✅ Frontend feedback UI (upvote/downvote)
2. ✅ Backend feedback API + database
3. ✅ Question classification (category)
4. ✅ Basic analytics (upvote rate by category)

### Should Have:
5. Story classification (theme, source)
6. Multi-strategy framework
7. Strategy selection logic
8. A/B testing

### Nice to Have:
9. User preferences
10. Explanation mode
11. Advanced analytics dashboard
12. Auto-refinement based on feedback

---

## Next Steps

1. **Review this plan** - confirm approach
2. **Start Phase 1** - implement feedback UI/API
3. **Set up database** - create feedback table
4. **Define downvote reasons** - finalize list
5. **Build analytics** - start tracking metrics

Ready to proceed? 🚀
