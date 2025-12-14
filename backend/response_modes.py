"""
Vasudeva Response Mode Engine - Option B MVP
Implements deterministic intent-to-mode routing with contract enforcement.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import re


class Intent(Enum):
    """5-Intent Classification System"""
    I1_REFLECTIVE = "I1_REFLECTIVE"      # Emotional support, perspective
    I2_PRACTICAL = "I2_PRACTICAL"         # Actionable guidance
    I3_COMPARATIVE = "I3_COMPARATIVE"     # Interfaith/comparative
    I4_REFUSAL = "I4_REFUSAL"            # Unethical requests
    I5_EXIT = "I5_EXIT"                  # Crisis/safety exit


class ResponseMode(Enum):
    """Response modes mapped from intents"""
    REFLECTIVE = "reflective"
    PRACTICAL = "practical"
    COMPARATIVE = "comparative"
    REFUSAL = "refusal"
    EXIT = "exit"


@dataclass
class ModeContract:
    """Defines constraints for each response mode"""
    mode: ResponseMode
    max_words: int
    rag_enabled: bool
    story_allowed: bool
    tone: List[str]
    forbidden_phrases: List[str]
    required_structure: Optional[List[str]] = None


# =============================================================================
# MODE CONTRACTS - Enforced at runtime
# =============================================================================

MODE_CONTRACTS: Dict[ResponseMode, ModeContract] = {
    ResponseMode.REFLECTIVE: ModeContract(
        mode=ResponseMode.REFLECTIVE,
        max_words=150,
        rag_enabled=True,
        story_allowed=False,  # DISABLED per Option B
        tone=["warm", "non-prescriptive", "empathetic"],
        forbidden_phrases=[
            "Dear Partha",
            "you should",
            "you must",
            "ultimate truth",
            "I am Krishna",
            "I am God",
            "trust in me",
            "I am with you",
            "surrender to me",
            "my child",
        ]
    ),
    
    ResponseMode.PRACTICAL: ModeContract(
        mode=ResponseMode.PRACTICAL,
        max_words=100,
        rag_enabled=True,
        story_allowed=False,  # DISABLED per Option B
        tone=["clear", "neutral", "helpful"],
        forbidden_phrases=[
            "Dear Partha",
            "karma will",
            "the divine",
            "cosmic",
            "spiritually",
            "trust in me",
            "I am with you",
            "my child",
        ]
    ),
    
    ResponseMode.COMPARATIVE: ModeContract(
        mode=ResponseMode.COMPARATIVE,
        max_words=120,
        rag_enabled=False,
        story_allowed=False,
        tone=["descriptive", "balanced", "academic"],
        forbidden_phrases=[
            "Dear Partha",
            "ultimate truth",
            "all paths lead",
            "same truth",
            "superior",
            "inferior",
            "better than",
            "greater than",
        ]
    ),
    
    ResponseMode.REFUSAL: ModeContract(
        mode=ResponseMode.REFUSAL,
        max_words=60,
        rag_enabled=False,
        story_allowed=False,
        tone=["firm", "non-judgmental", "constructive"],
        forbidden_phrases=[
            "Dear Partha",
            "dharma",
            "karma",
            "spiritually wrong",
            "you should be ashamed",
        ],
        required_structure=[
            "I cannot help with",
            "However",
        ]
    ),
    
    ResponseMode.EXIT: ModeContract(
        mode=ResponseMode.EXIT,
        max_words=80,
        rag_enabled=False,
        story_allowed=False,
        tone=["grounded", "brief", "supportive"],
        forbidden_phrases=[
            "Dear Partha",
            "story",
            "once upon",
            "ancient wisdom",
            "should reflect",
            "consider this",
        ],
        required_structure=[
            "not equipped",
            "reach out",
        ]
    ),
}


# =============================================================================
# INTENT TO MODE MAPPING
# =============================================================================

INTENT_TO_MODE: Dict[str, ResponseMode] = {
    "I1_REFLECTIVE": ResponseMode.REFLECTIVE,
    "I2_PRACTICAL": ResponseMode.PRACTICAL,
    "I3_COMPARATIVE": ResponseMode.COMPARATIVE,
    "I4_REFUSAL": ResponseMode.REFUSAL,
    "I5_EXIT": ResponseMode.EXIT,
    
    # Legacy category names (for backward compatibility)
    "emotional_support": ResponseMode.REFLECTIVE,
    "philosophical": ResponseMode.REFLECTIVE,
    "practical": ResponseMode.PRACTICAL,
    "philosophical_comparison": ResponseMode.COMPARATIVE,
    "unethical_behavior": ResponseMode.REFUSAL,
    "safety_circuit_breaker": ResponseMode.EXIT,
    "crisis_safety": ResponseMode.EXIT,
}


# =============================================================================
# MODE DISPATCHER
# =============================================================================

class ModeDispatcher:
    """
    Routes intents to response modes and enforces contracts.
    """
    
    def __init__(self):
        self.contracts = MODE_CONTRACTS
        self.intent_map = INTENT_TO_MODE
    
    def get_mode(self, intent_category: str) -> ResponseMode:
        """Map intent category to response mode."""
        mode = self.intent_map.get(intent_category)
        if mode is None:
            print(f"⚠️ Unknown intent '{intent_category}', defaulting to REFLECTIVE")
            return ResponseMode.REFLECTIVE
        return mode
    
    def get_contract(self, mode: ResponseMode) -> ModeContract:
        """Get the contract for a mode."""
        return self.contracts[mode]
    
    def validate_response(self, response: str, mode: ResponseMode) -> Dict[str, Any]:
        """
        Validate a response against its mode contract.
        
        Returns:
            dict with 'valid', 'violations', 'corrected_response'
        """
        contract = self.get_contract(mode)
        violations = []
        corrected = response
        
        # Check word limit
        word_count = len(response.split())
        if word_count > contract.max_words:
            violations.append({
                "type": "word_limit",
                "detail": f"Response has {word_count} words, max is {contract.max_words}",
                "severity": "warning"
            })
            # Truncate to limit
            words = response.split()[:contract.max_words]
            corrected = " ".join(words)
            if not corrected.endswith("."):
                corrected += "..."
        
        # Check forbidden phrases
        response_lower = response.lower()
        for phrase in contract.forbidden_phrases:
            if phrase.lower() in response_lower:
                violations.append({
                    "type": "forbidden_phrase",
                    "detail": f"Contains forbidden phrase: '{phrase}'",
                    "severity": "error"
                })
                # Remove forbidden phrase
                corrected = re.sub(
                    re.escape(phrase), 
                    "", 
                    corrected, 
                    flags=re.IGNORECASE
                ).strip()
        
        # Check required structure (if defined)
        if contract.required_structure:
            for required in contract.required_structure:
                if required.lower() not in response_lower:
                    violations.append({
                        "type": "missing_structure",
                        "detail": f"Missing required phrase: '{required}'",
                        "severity": "warning"
                    })
        
        return {
            "valid": len([v for v in violations if v["severity"] == "error"]) == 0,
            "violations": violations,
            "corrected_response": corrected,
            "original_word_count": word_count,
            "mode": mode.value,
        }
    
    def should_use_rag(self, mode: ResponseMode) -> bool:
        """Check if RAG retrieval is allowed for this mode."""
        return self.get_contract(mode).rag_enabled
    
    def should_include_story(self, mode: ResponseMode) -> bool:
        """Check if stories are allowed for this mode."""
        return self.get_contract(mode).story_allowed
    
    def get_mode_info(self, mode: ResponseMode) -> Dict[str, Any]:
        """Get all info about a mode for prompt construction."""
        contract = self.get_contract(mode)
        return {
            "mode": mode.value,
            "max_words": contract.max_words,
            "rag_enabled": contract.rag_enabled,
            "story_allowed": contract.story_allowed,
            "tone": contract.tone,
            "forbidden_phrases": contract.forbidden_phrases,
        }


# =============================================================================
# SYSTEM PROMPTS BY MODE (Phase 4: Enhanced with examples and guardrails)
# =============================================================================

MODE_PROMPTS: Dict[ResponseMode, str] = {
    ResponseMode.REFLECTIVE: """You are a thoughtful companion offering perspective.

CONSTRAINTS:
- Maximum 150 words
- NO "Dear Partha" or deity roleplay
- NO prescriptive advice ("you should", "you must")
- Warm, empathetic, non-prescriptive tone
- Focus on acknowledging feelings and offering gentle perspective
- NO stories unless explicitly requested

STRUCTURE:
1. Brief acknowledgment of their feelings (1-2 sentences)
2. A perspective or reflection (not advice)
3. A gentle, open-ended thought

FORBIDDEN: "Dear Partha", "I am Krishna", "you should", "you must", "ultimate truth"

EXAMPLE TONE: "That sounds really difficult. Times of loss often bring questions about meaning. What feels most important to you right now?" """,

    ResponseMode.PRACTICAL: """You are a helpful guide offering practical perspective.

CONSTRAINTS:
- Maximum 100 words
- NO religious framing or deity references
- NO cosmic consequences ("karma will...")
- Clear, neutral, helpful tone
- Focus on practical options and trade-offs
- NO stories

STRUCTURE:
1. Brief acknowledgment (1 sentence)
2. 2-3 practical considerations
3. Neutral framing of options (not "you should")

FORBIDDEN: "Dear Partha", "karma will", "spiritually", "divine", "cosmic"

EXAMPLE TONE: "Here are some things to consider: First, [X]. Second, [Y]. The choice depends on what matters most to you." """,

    ResponseMode.COMPARATIVE: """You are an objective scholar describing different perspectives.

CONSTRAINTS:
- Maximum 120 words
- NO ranking religions or declaring truth
- NO forced syncretism ("all paths lead to the same truth")
- NO "Dear Partha" or divine authority
- Descriptive, balanced, academic tone
- NO stories

STRUCTURE:
1. Brief, neutral description of each perspective (1-2 sentences each)
2. Acknowledge differences without judgment
3. Do NOT offer an opinion or verdict

STRICTLY FORBIDDEN:
- "ultimate truth"
- "superior" / "inferior" / "greater" / "better than"
- "all paths lead to the same"
- "they are essentially the same"
- Any verdict on which is "correct"

EXAMPLE TONE: "In Hindu philosophy, Krishna is understood as... In Christian theology, Jesus is viewed as... These represent distinct theological frameworks." """,

    ResponseMode.REFUSAL: """You are declining an inappropriate request constructively.

CONSTRAINTS:
- Maximum 60 words
- NO moralizing or lectures
- NO religious references
- Firm but non-judgmental tone
- NO stories

EXACT STRUCTURE (follow precisely):
1. "I cannot help with [specific request]."
2. One sentence explaining why (briefly)
3. "However, I can help you with [constructive alternative]."

Keep it SHORT. Do not elaborate beyond this structure.

FORBIDDEN: "Dear Partha", "dharma", "karma", "morally wrong", lectures

EXAMPLE: "I cannot help with writing your essay. This would undermine your learning. However, I can help you brainstorm ideas or create an outline." """,

    ResponseMode.EXIT: """You are providing a brief, grounded safety response.

CONSTRAINTS:
- Maximum 80 words
- NO advice or philosophy
- NO stories or extended engagement
- Grounded, human, supportive tone
- NO follow-up questions about the distress

EXACT STRUCTURE (follow precisely):
1. Brief acknowledgment of difficulty (1 sentence)
2. "I'm not equipped to help with this directly."
3. Suggest reaching out to someone who can help (friend, family, professional)

Do NOT offer perspectives or wisdom. Keep it SHORT and GROUNDED.

FORBIDDEN: "Dear Partha", "story", "ancient wisdom", "consider this", "reflect on"

EXAMPLE: "I hear that you're going through something really difficult. I'm not equipped to help with this directly, but please consider reaching out to someone you trust - a friend, family member, or a professional who can provide proper support." """,
}


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

dispatcher = ModeDispatcher()


def get_dispatcher() -> ModeDispatcher:
    """Get the singleton dispatcher instance."""
    return dispatcher
