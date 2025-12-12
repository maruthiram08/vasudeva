#!/usr/bin/env python3
"""
Quick test to verify Vasudeva initialization works.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from vasudeva_rag import VasudevaRAG

print("="*70)
print("Testing Vasudeva Initialization")
print("="*70)

try:
    # Initialize
    print("\n1. Creating VasudevaRAG instance...")
    vasudeva = VasudevaRAG()
    print("   ✅ Instance created")
    
    # Build pipeline
    print("\n2. Building pipeline...")
    vasudeva.build_pipeline()
    print("   ✅ Pipeline built")
    
    # Test get_guidance
    print("\n3. Testing get guidance...")
    result = vasudeva.get_guidance("How do I deal with anger?", skip_story=True)
    print(f"   ✅ Got guidance: {len(result['guidance'])} chars")
    
    # Test get_story_only  
    print("\n4. Testing get story...")
    story_result = vasudeva.get_story_only("I feel abandoned")
    print(f"   ✅ Got story: {story_result.get('story') is not None}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - Vasudeva is working!")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
