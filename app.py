"""
Enhanced Vasudeva Web Application with Mental Wellness Support
Beautiful, calming interface with empathetic responses.
"""

import streamlit as st
from vasudeva_rag import VasudevaRAG
import time
from pathlib import Path
import random

# Page configuration
st.set_page_config(
    page_title="Vasudeva - Your Wisdom Guide 🕉️",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Calming quotes for mental wellness
CALMING_QUOTES = [
    "Take a deep breath. You are exactly where you need to be. 🌸",
    "Every challenge is an opportunity for growth. 🌱",
    "Peace comes from within. Do not seek it without. 🕊️",
    "The present moment is all we truly have. 🌅",
    "Your journey is unique and beautiful. 🦋",
    "Gentle progress is still progress. 🌺",
]

# Mental wellness prompts for when no specific wisdom is found
WELLNESS_CATEGORIES = {
    "anxiety": [
        "Remember to breathe deeply. Anxiety is temporary, but your strength is permanent.",
        "Ground yourself in the present moment. Notice 5 things you can see, 4 you can touch, 3 you can hear.",
        "Your worries do not define your future. Take each moment as it comes."
    ],
    "purpose": [
        "Your purpose unfolds gradually. Trust the journey and embrace where you are now.",
        "Meaning comes from action. Start with what brings you joy today.",
        "You are already enough. Purpose is discovered through living authentically."
    ],
    "relationships": [
        "Healthy boundaries are an act of self-love and respect for others.",
        "Compassion starts with understanding. See others through the lens of their struggles.",
        "True connection requires vulnerability. It's okay to be authentic."
    ],
    "general": [
        "This too shall pass. Every season of life has its lessons.",
        "Be gentle with yourself. You're doing the best you can with what you know.",
        "Progress isn't linear. Honor your journey, with all its ups and downs."
    ]
}

# Custom CSS for beautiful, calming UI
st.markdown("""
<style>
    /* Soft, calming gradient background */
    .stApp {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Main container with frosted glass effect */
    .main-container {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-radius: 30px;
        padding: 3rem;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
        margin: 2rem auto;
        max-width: 900px;
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    /* Elegant title */
    .title {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: 2px;
    }
    
    .subtitle {
        text-align: center;
        color: #764ba2;
        font-size: 1.3rem;
        margin-bottom: 2rem;
        font-style: italic;
        font-weight: 300;
    }
    
    /* Calming input area */
    .stTextArea textarea {
        border-radius: 20px;
        border: 2px solid rgba(102, 126, 234, 0.3);
        font-size: 1.1rem;
        padding: 1.2rem;
        background: rgba(255, 255, 255, 0.9);
        transition: all 0.3s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Soft button styling */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 30px;
        padding: 0.9rem 2.5rem;
        font-size: 1.15rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease;
        width: 100%;
        letter-spacing: 1px;
    }
    
    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5);
    }
    
    /* Beautiful guidance card */
    .guidance-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(240,248,255,0.9) 100%);
        border-radius: 20px;
        padding: 2.5rem;
        margin: 2rem 0;
        border-left: 6px solid #764ba2;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        animation: fadeIn 0.6s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .guidance-text {
        font-size: 1.25rem;
        line-height: 1.9;
        color: #2d3748;
        font-weight: 400;
        letter-spacing: 0.3px;
    }
    
    /* Source cards with gentle styling */
    .source-card {
        background: rgba(255, 255, 255, 0.7);
        border-radius: 15px;
        padding: 1.2rem;
        margin: 0.7rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        transition: all 0.3s ease;
    }
    
    .source-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    
    /* Calming info box */
    .info-box {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-left: 5px solid #667eea;
        border-right: 5px solid #764ba2;
    }
    
    /* Wellness tip box */
    .wellness-tip {
        background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
        border-radius: 15px;
        padding: 1.2rem;
        margin: 1rem 0;
        text-align: center;
        font-style: italic;
        color: #2d3748;
        box-shadow: 0 4px 12px rgba(253, 203, 110, 0.3);
    }
    
    /* Loading animation */
    .loading-text {
        text-align: center;
        color: #764ba2;
        font-size: 1.2rem;
        font-style: italic;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Breathing circle animation for relaxation */
    .breathing-circle {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 50%;
        margin: 2rem auto;
        animation: breathe 4s ease-in-out infinite;
        opacity: 0.3;
    }
    
    @keyframes breathe {
        0%, 100% { transform: scale(1); opacity: 0.3; }
        50% { transform: scale(1.2); opacity: 0.6; }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_vasudeva():
    """Initialize and cache the Vasudeva RAG pipeline."""
    try:
        vasudeva = VasudevaRAG(
            documents_dir="documents",
            vector_db_dir="vasudeva_db",
            temperature=0.7
        )
        vasudeva.build_pipeline(force_rebuild=False)
        return vasudeva, None
    except Exception as e:
        return None, str(e)


def get_wellness_category(question: str) -> str:
    """Determine the wellness category based on keywords."""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['anxious', 'anxiety', 'fear', 'worried', 'stress', 'panic']):
        return 'anxiety'
    elif any(word in question_lower for word in ['purpose', 'meaning', 'lost', 'direction', 'why', 'goal']):
        return 'purpose'
    elif any(word in question_lower for word in ['relationship', 'people', 'friend', 'family', 'conflict', 'alone']):
        return 'relationships'
    else:
        return 'general'


def display_guidance(result, show_wellness_tip=False):
    """Display the guidance in a beautiful card with optional wellness tip."""
    if show_wellness_tip:
        category = get_wellness_category(result['question'])
        wellness_tip = random.choice(WELLNESS_CATEGORIES[category])
        
        st.markdown(f"""
        <div class="wellness-tip">
            💝 {wellness_tip}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="guidance-card">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <span style="font-size: 3rem;">🕉️</span>
        </div>
        <div class="guidance-text">
            {result['guidance']}
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_sources(sources):
    """Display wisdom sources in elegant cards."""
    if sources:
        st.markdown("### 📚 Wisdom Sources")
        for i, source in enumerate(sources[:3], 1):
            with st.expander(f"📖 Source {i}: {source['source']} - Page {source['page']}"):
                st.markdown(f"*{source['text'][:400]}...*")


def show_breathing_exercise():
    """Display a simple breathing exercise."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h3 style="color: #764ba2;">🌬️ Take a Moment to Breathe</h3>
        <div class="breathing-circle"></div>
        <p style="color: #667eea; font-style: italic;">
            Breathe in for 4 seconds... Hold for 4... Exhale for 4...
        </p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    
    # Header
    st.markdown("""
    <div class="main-container">
        <h1 class="title">Vasudeva</h1>
        <p class="subtitle">✨ Ancient Wisdom for Modern Life ✨</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize Vasudeva
    with st.spinner("🔮 Awakening ancient wisdom..."):
        vasudeva, error = initialize_vasudeva()
    
    if error:
        st.error(f"""
        ❌ **Could not initialize Vasudeva**
        
        {error}
        
        **Please ensure:**
        1. Your wisdom texts (PDFs) are in the `documents/` folder
        2. Your `.env` file contains `OPENAI_API_KEY=your_key`
        3. All dependencies are installed: `pip install -r requirements.txt`
        """)
        
        # Show breathing exercise even if initialization fails
        show_breathing_exercise()
        return
    
    # Success message with calming quote
    calming_quote = random.choice(CALMING_QUOTES)
    st.success(f"✅ {calming_quote}")
    
    # Main container
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col2:
        # Info box
        st.markdown("""
        <div class="info-box">
            💭 <strong>Share what's on your heart.</strong><br><br>
            Whether you seek guidance, comfort, or wisdom - Vasudeva is here to listen 
            and offer support drawn from timeless teachings.<br><br>
            🌸 Remember: Your feelings are valid, and seeking wisdom is a sign of strength.
        </div>
        """, unsafe_allow_html=True)
        
        # Question input
        user_question = st.text_area(
            "What's on your mind?",
            placeholder="I'm feeling anxious about...\nI'm struggling with...\nHow can I find...\nI need guidance on...",
            height=150,
            label_visibility="collapsed"
        )
        
        # Options in an elegant row
        col_opt1, col_opt2, col_opt3 = st.columns(3)
        with col_opt1:
            show_sources = st.checkbox("📚 Show sources", value=False)
        with col_opt2:
            show_similar = st.checkbox("🔍 Related wisdom", value=False)
        with col_opt3:
            show_wellness = st.checkbox("💝 Wellness tip", value=True)
        
        # Submit button
        if st.button("🙏 Seek Guidance from Vasudeva"):
            if not user_question.strip():
                st.warning("⚠️ Please share your question or concern.")
            else:
                # Show loading animation
                with st.spinner("🔮 Consulting ancient wisdom..."):
                    time.sleep(0.8)  # Brief pause for calming effect
                    
                    try:
                        # Get guidance
                        result = vasudeva.get_guidance(
                            user_question,
                            return_sources=show_sources
                        )
                        
                        # Display guidance
                        st.markdown("---")
                        display_guidance(result, show_wellness_tip=show_wellness)
                        
                        # Display sources if requested
                        if show_sources and "wisdom_sources" in result:
                            display_sources(result["wisdom_sources"])
                        
                        # Show similar wisdom if requested
                        if show_similar:
                            st.markdown("### 🔍 Related Wisdom")
                            similar_wisdom = vasudeva.find_relevant_wisdom(user_question, k=3)
                            
                            for wisdom in similar_wisdom:
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong>📖 {wisdom['source']} - Page {wisdom['page']}</strong><br><br>
                                    <em>{wisdom['text'][:300]}...</em>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Breathing reminder
                        if show_wellness:
                            show_breathing_exercise()
                        
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
                        # Still offer support
                        st.markdown("""
                        <div class="wellness-tip">
                            💝 Even when technology fails, remember: You have inner wisdom and strength. 
                            Take a moment to breathe and trust yourself.
                        </div>
                        """, unsafe_allow_html=True)
        
        # Example questions with better categorization
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 💡 Example Topics")
        
        example_cols = st.columns(3)
        examples = [
            ("🌊 Inner Peace", "I'm feeling overwhelmed. How can I find inner peace?"),
            ("🎯 Life Purpose", "I feel lost and unsure of my purpose."),
            ("🤝 Relationships", "How do I deal with difficult people?")
        ]
        
        for i, (label, question) in enumerate(examples):
            with example_cols[i]:
                if st.button(label, key=f"example_{i}"):
                    st.session_state.example_question = question
                    st.rerun()
        
        # Handle example button clicks
        if "example_question" in st.session_state:
            st.info(f"💭 {st.session_state.example_question}")
            del st.session_state.example_question
    
    # Footer with calming message
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <p style="color: #764ba2; font-size: 1.1rem; opacity: 0.8;">
            <em>🙏 May you find peace, wisdom, and compassion on your journey 🌸</em>
        </p>
        <p style="color: #667eea; font-size: 0.9rem; opacity: 0.6; margin-top: 1rem;">
            Remember: Seeking guidance is an act of courage. You are not alone.
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
