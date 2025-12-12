"""
Feedback utilities for storing and analyzing user feedback.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# Data directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"


def classify_question(question: str) -> Dict[str, str]:
    """
    Classify question into category and type.
    
    Args:
        question: User's question
        
    Returns:
        Dict with category, type, and keywords
    """
    try:
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        
        prompt = f"""Classify this question into emotional category and question type.

Question: {question}

Categories:
- grief_loss: Death, separation, letting go
- anger_conflict: Anger, betrayal, conflict
- anxiety_fear: Worry, uncertainty, fear
- confusion_doubt: Indecision, confusion, doubt
- desire_attachment: Craving, attachment, addiction
- duty_dharma: Moral dilemmas, duty conflicts
- relationships: Friendship, family, love issues
- career_purpose: Life direction, purpose, career

Types:
- how_to_deal: "How do I deal with X?"
- why_happened: "Why did this happen to me?"
- what_should_do: "What should I do?"
- is_it_okay: "Is it okay to...?"
- how_to_overcome: "How to overcome X?"
- understanding: "Help me understand..."

Return JSON:
{{
  "category": "...",
  "type": "...",
  "keywords": ["keyword1", "keyword2"]
}}
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return json.loads(response.content)
        
    except Exception as e:
        print(f"⚠️  Question classification failed: {e}")
        return {
            "category": "general",
            "type": "general",
            "keywords": []
        }


def store_feedback(feedback_data: Dict[str, Any]) -> str:
    """
    Store feedback to JSONL file.
    
    Args:
        feedback_data: Feedback data dictionary
        
    Returns:
        Feedback ID
    """
    # Generate ID
    feedback_id = str(uuid.uuid4())
    
    # Add metadata
    feedback_entry = {
        "id": feedback_id,
        "timestamp": datetime.now().isoformat(),
        **feedback_data
    }
    
    # Append to file
    with open(FEEDBACK_FILE, 'a') as f:
        f.write(json.dumps(feedback_entry) + '\n')
    
    print(f"💾 Stored feedback: {feedback_id}")
    return feedback_id


def get_feedback_stats() -> Dict[str, Any]:
    """
    Get basic feedback statistics.
    
    Returns:
        Dict with total count, upvotes, downvotes, and upvote rate
    """
    if not FEEDBACK_FILE.exists():
        return {
            "total": 0,
            "upvotes": 0,
            "downvotes": 0,
            "upvote_rate": 0.0
        }
    
    total = 0
    upvotes = 0
    downvotes = 0
    
    with open(FEEDBACK_FILE, 'r') as f:
        for line in f:
            feedback = json.loads(line)
            total += 1
            if feedback.get('vote') == 'upvote':
                upvotes += 1
            elif feedback.get('vote') == 'downvote':
                downvotes += 1
    
    upvote_rate = (upvotes / total * 100) if total > 0 else 0.0
    
    return {
        "total": total,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "upvote_rate": round(upvote_rate, 2)
    }


def get_downvote_reasons() -> Dict[str, int]:
    """
    Get count of downvote reasons.
    
    Returns:
        Dict mapping reasons to counts
    """
    if not FEEDBACK_FILE.exists():
        return {}
    
    reasons = {}
    
    with open(FEEDBACK_FILE, 'r') as f:
        for line in f:
            feedback = json.loads(line)
            if feedback.get('vote') == 'downvote' and feedback.get('downvote_reason'):
                reason = feedback['downvote_reason']
                reasons[reason] = reasons.get(reason, 0) + 1
    
    return dict(sorted(reasons.items(), key=lambda x: x[1], reverse=True))
