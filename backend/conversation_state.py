"""
Conversation State Machine for Vasudeva (Path B - Strict Option B)

This module implements a minimal state machine to enforce emotional boundaries
across multi-turn conversations. It ensures:
- Hard exit on distress detection
- No re-engagement after exit
- Clean recovery to neutral state

States:
    NEUTRAL: Normal operation, all modes allowed
    DISTRESS_EXIT: Distress detected, only exit template allowed
    POST_EXIT_LOCK: After exit, emotional queries blocked until neutral query
"""

from enum import Enum
from typing import List, Optional
import re


class ConversationState(Enum):
    """Conversation states for Path B enforcement."""
    NEUTRAL = "neutral"
    DISTRESS_EXIT = "distress_exit"
    POST_EXIT_LOCK = "post_exit_lock"


# ============================================================================
# FROZEN TEMPLATES (DO NOT MODIFY)
# ============================================================================

EXIT_TEMPLATE = (
    "I'm sorry you're feeling this way. I'm not able to help with emotional "
    "or mental health support. It may help to reach out to someone you trust "
    "or a qualified professional who can support you directly."
)

REFUSAL_TEMPLATE = (
    "I can't help with that. I'm not able to assist with requests that "
    "involve harm or wrongdoing."
)

POST_EXIT_REDIRECT = (
    "I can help with factual or philosophical questions. What would you like to know?"
)


# ============================================================================
# HARD DISTRESS TRIGGERS (Bypass Classifier)
# ============================================================================

HARD_DISTRESS_TRIGGERS = [
    r"\b(can'?t handle|cannot handle)\b",
    r"\b(don'?t know how much longer|do not know how much longer)\b",
    r"\b(i'?m overwhelmed|i am overwhelmed)\b",
    r"\b(i'?m exhausted|i am exhausted)\b",
    r"\b(feel broken|feeling broken)\b",
    r"\b(want to disappear)\b",
    r"\b(can'?t go on|cannot go on)\b",
    r"\b(can'?t keep going|cannot keep going)\b",
    r"\b(i'?m losing it|i am losing it)\b",
    r"\b(everything is falling apart)\b",
    r"\b(no point in trying)\b",
    r"\b(i give up)\b",
    r"\b(what'?s the point)\b",
    r"\b(i'?m done|i am done)\b",
    r"\b(i can'?t do this anymore)\b",
]


# ============================================================================
# EMOTIONAL LANGUAGE BLOCKLIST (Post-Generation Scrubber)
# ============================================================================

EMOTIONAL_BLOCKLIST = [
    r"I understand how you feel",
    r"That sounds hard",
    r"You'?re not alone",
    r"It'?s natural to feel",
    r"It'?s understandable to feel",
    r"It'?s completely understandable",
    r"completely understandable",
    r"Take a deep breath",
    r"Try to calm",
    r"I'?m here for you",
    r"support you on your journey",
    r"on your journey",
    r"your journey",
    r"I'?m here to support",
    r"I'?m here to help you through",
    r"breathe deeply",
    r"ground yourself",
    r"find peace",
    r"inner peace",
    r"you can get through this",
    r"you will get through",
    r"everything will be okay",
    r"it will be okay",
    r"I believe in you",
    r"stay strong",
    r"you are strong",
    r"you are not alone",
]


class StateManager:
    """
    Manages conversation state transitions for Path B enforcement.
    
    Usage:
        state_mgr = StateManager()
        
        # On each turn:
        if state_mgr.check_hard_distress(user_query):
            state_mgr.transition("distress_detected")
            return EXIT_TEMPLATE
        
        response = generate_response(...)
        
        if state_mgr.state == ConversationState.DISTRESS_EXIT:
            state_mgr.transition("exit_response_sent")
    """
    
    def __init__(self):
        self.state = ConversationState.NEUTRAL
        self._turn_count = 0
        self._last_trigger = None
    
    def transition(self, trigger: str) -> ConversationState:
        """
        Transition to a new state based on trigger.
        
        Triggers:
            "distress_detected" -> DISTRESS_EXIT
            "exit_response_sent" -> POST_EXIT_LOCK
            "neutral_query" -> NEUTRAL (only from POST_EXIT_LOCK)
        """
        old_state = self.state
        
        if trigger == "distress_detected":
            self.state = ConversationState.DISTRESS_EXIT
        elif trigger == "exit_response_sent":
            self.state = ConversationState.POST_EXIT_LOCK
        elif trigger == "neutral_query" and self.state == ConversationState.POST_EXIT_LOCK:
            self.state = ConversationState.NEUTRAL
        
        if old_state != self.state:
            print(f"🔄 State Transition: {old_state.value} -> {self.state.value} (trigger: {trigger})")
        
        self._last_trigger = trigger
        self._turn_count += 1
        
        return self.state
    
    def get_allowed_modes(self) -> List[str]:
        """Return list of allowed response modes for current state."""
        if self.state == ConversationState.NEUTRAL:
            return ["practical", "reflective", "comparative", "refusal", "greeting", "exit"]
        elif self.state == ConversationState.DISTRESS_EXIT:
            return ["exit_only"]
        elif self.state == ConversationState.POST_EXIT_LOCK:
            return ["refusal", "neutral_redirect", "practical"]
        return []
    
    def is_rag_allowed(self) -> bool:
        """Check if RAG retrieval is allowed in current state."""
        return self.state == ConversationState.NEUTRAL
    
    def check_hard_distress(self, query: str) -> bool:
        """
        Check if query contains hard distress triggers.
        If True, caller MUST force DISTRESS_EXIT state (bypass classifier).
        """
        query_lower = query.lower()
        for pattern in HARD_DISTRESS_TRIGGERS:
            if re.search(pattern, query_lower):
                print(f"🚨 HARD DISTRESS DETECTED: Pattern '{pattern}' matched")
                return True
        return False
    
    def check_emotional_language(self, text: str) -> bool:
        """
        Check if response contains emotional language from blocklist.
        Used for post-generation scrubbing.
        """
        text_lower = text.lower()
        for pattern in EMOTIONAL_BLOCKLIST:
            if re.search(pattern, text_lower, re.IGNORECASE):
                print(f"⚠️ EMOTIONAL LANGUAGE DETECTED: Pattern '{pattern}'")
                return True
        return False
    
    def enforce_state_response(self, response: str) -> str:
        """
        Enforce state-appropriate response.
        
        - In DISTRESS_EXIT: Always return EXIT_TEMPLATE
        - In POST_EXIT_LOCK: Block emotional language, use redirect
        - In NEUTRAL: Return response as-is (scrubbers still apply separately)
        """
        if self.state == ConversationState.DISTRESS_EXIT:
            print("🛡️ ENFORCING EXIT TEMPLATE (DISTRESS_EXIT state)")
            return EXIT_TEMPLATE
        
        if self.state == ConversationState.POST_EXIT_LOCK:
            if self.check_emotional_language(response):
                print("🛡️ BLOCKING EMOTIONAL RESPONSE (POST_EXIT_LOCK state)")
                return POST_EXIT_REDIRECT
        
        return response
    
    def is_neutral_query(self, query: str) -> bool:
        """
        Determine if a query is neutral (factual/philosophical) vs emotional.
        Used to decide if we can transition from POST_EXIT_LOCK to NEUTRAL.
        """
        # Emotional indicators that keep us in POST_EXIT_LOCK
        emotional_indicators = [
            r"\b(feel|feeling|felt)\b",
            r"\b(overwhelm|anxious|scared|afraid|worried)\b",
            r"\b(help me calm|calm down|calm me)\b",
            r"\b(struggling|suffering)\b",
            r"\b(can'?t cope|cannot cope)\b",
            r"\b(support me|be there for me)\b",
        ]
        
        query_lower = query.lower()
        for pattern in emotional_indicators:
            if re.search(pattern, query_lower):
                return False
        
        # Neutral indicators that allow transition back
        neutral_indicators = [
            r"\b(explain|what is|what does|define|describe)\b",
            r"\b(how does|why does|what are)\b",
            r"\b(tell me about|teach me)\b",
            r"\b(stoicism|philosophy|wisdom|buddhism|hinduism)\b",
        ]
        
        for pattern in neutral_indicators:
            if re.search(pattern, query_lower):
                return True
        
        # Default: stay locked if uncertain
        return False
    
    def reset(self):
        """Reset state machine to initial state (for testing)."""
        self.state = ConversationState.NEUTRAL
        self._turn_count = 0
        self._last_trigger = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_exit_template() -> str:
    """Return the frozen exit template."""
    return EXIT_TEMPLATE


def get_refusal_template() -> str:
    """Return the frozen refusal template."""
    return REFUSAL_TEMPLATE


def get_post_exit_redirect() -> str:
    """Return the post-exit redirect message."""
    return POST_EXIT_REDIRECT
