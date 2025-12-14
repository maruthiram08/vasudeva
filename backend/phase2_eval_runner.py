#!/usr/bin/env python3
"""
Phase 2 Eval Runner - Durability & Hardening
Executes 40-query regression suite and applies blocking eval rules.
"""

import sys
import json
import re
import datetime
from vasudeva_rag import VasudevaRAG
from phase2_data import PHASE2_QUERIES, EVAL_RULES

class Phase2Evaluator:
    def __init__(self):
        self.rag = VasudevaRAG(vector_db_dir="/Users/ram/Desktop/vasudeva/vectordb")
        try:
            # Use build_pipeline to ensure vectorstore triggers load
            self.rag.build_pipeline(force_rebuild=False)
        except Exception as e:
            print(f"⚠️ Pipeline setup warning: {e}")
        self.results = []
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "blocking_failures": []
        }

    def check_blocking_rules(self, query, response_text, category_key):
        """Apply all blocking rules to the response."""
        failures = []
        
        # 1. Global Rules (Apply to everything)
        # Tone Authority
        for phrase in EVAL_RULES["P2_TONE_AUTHORITY"]["forbidden"]:
            if re.search(r'\b' + re.escape(phrase) + r'\b', response_text, re.IGNORECASE):
                failures.append(f"P2_TONE_AUTHORITY: Found forbidden phrase '{phrase}'")

        # Deity Voice
        for phrase in EVAL_RULES["P2_DEITY_VOICE"]["forbidden"]:
             if re.search(r'\b' + re.escape(phrase) + r'\b', response_text, re.IGNORECASE):
                failures.append(f"P2_DEITY_VOICE: Found forbidden phrase '{phrase}'")

        # 2. Context Specific Rules
        # Meaning Imposition (Distress)
        if category_key == "distress_adjacent":
             for phrase in EVAL_RULES["P2_MEANING_IMPOSITION"]["forbidden"]:
                if re.search(r'\b' + re.escape(phrase) + r'\b', response_text, re.IGNORECASE):
                    failures.append(f"P2_MEANING_IMPOSITION: Found '{phrase}' in distress context")

        # Interfaith Superiority
        if category_key == "interfaith_traps":
             for phrase in EVAL_RULES["P2_INTERFAITH_SUPERIORITY"]["forbidden"]:
                if re.search(r'\b' + re.escape(phrase) + r'\b', response_text, re.IGNORECASE):
                    failures.append(f"P2_INTERFAITH_SUPERIORITY: Found '{phrase}' in interfaith context")

        return failures

    def check_soft_warnings(self, response_text, response_mode):
        """Apply warning rules."""
        warnings = []
        
        # Verbosity Warning
        word_count = len(response_text.split())
        limit = 150 # Default max
        if response_mode == "I5_EXIT" or response_mode == "I4_REFUSAL":
            limit = 80
        
        threshold = limit * EVAL_RULES["P2_VERBOSITY_WARNING"]["threshold_percent"]
        if word_count > threshold:
            warnings.append(f"P2_VERBOSITY_WARNING: {word_count} words (Limit {limit})")
            
        return warnings

    def run_suite(self, smoke_mode=False):
        print(f"🚀 Starting Phase 2 Eval Suite ({datetime.datetime.now()})")
        if smoke_mode:
            print("💨 SMOKE MODE: Running 1 query per category")
        print("=" * 60)

        for category, queries in PHASE2_QUERIES.items():
            print(f"\n📂 Category: {category}")
            current_queries = queries[:1] if smoke_mode else queries
            for query in current_queries:
                self.stats["total"] += 1
                
                # Run RAG
                print(f"  Running: '{query[:50]}...'")
                try:
                    # We classify internally, but here we just want the final output
                    # Note: trace_id is auto-generated
                    if "cheat" in query or "plagiarize" in query:
                         # Manual classification check helpful but let's trust get_guidance
                         pass

                    # Using get_guidance directly
                    result = self.rag.get_guidance(query)
                    response_text = result.get("guidance", "")
                    # Extract mode from result if available, or infer?
                    # VasudevaRAG.get_guidance doesn't return mode explicitly in dict key usually
                    # BUT we can infer or if we modify RAG to return it.
                    # For now, let's look at text length to infer verbosity limits
                    
                    # Hack: Check traces if we need exact mode, but text analysis is enough for Phase 2 blocking
                    
                    # 1. Blocking Checks
                    blocking_failures = self.check_blocking_rules(query, response_text, category)
                    
                    # 2. Soft Warnings
                    # Infer mode roughly for limits
                    inferred_limit_mode = "DEFAULT"
                    if "assist with" in response_text and "involves" in response_text: inferred_limit_mode = "I4_REFUSAL"
                    if "trained to provide" in response_text: inferred_limit_mode = "I5_EXIT"
                    
                    warnings = self.check_soft_warnings(response_text, inferred_limit_mode)

                    status = "PASS"
                    if blocking_failures:
                        status = "FAIL"
                        self.stats["failed"] += 1
                        self.stats["blocking_failures"].extend(blocking_failures)
                    else:
                        self.stats["passed"] += 1
                    
                    if warnings:
                        self.stats["warnings"] += len(warnings)

                    # Log Result
                    log_icon = "✅" if status == "PASS" else "❌"
                    print(f"    {log_icon} {status}")
                    if blocking_failures:
                        for f in blocking_failures: print(f"       🛑 {f}")
                    if warnings:
                        for w in warnings: print(f"       ⚠️  {w}")

                    self.results.append({
                        "query": query,
                        "category": category,
                        "status": status,
                        "response_preview": response_text[:100],
                        "failures": blocking_failures,
                        "warnings": warnings
                    })

                except Exception as e:
                    print(f"    💀 CRITICAL ERROR: {e}")
                    self.stats["failed"] += 1
                    self.results.append({
                        "query": query,
                        "status": "ERROR",
                        "error": str(e)
                    })

        # Save Report
        self.save_report()
        self.print_summary()

    def save_report(self):
        output_file = "phase2_results.json"
        with open(output_file, "w") as f:
            json.dump({
                "timestamp": datetime.datetime.now().isoformat(),
                "summary": self.stats,
                "details": self.results
            }, f, indent=2)
        print(f"\n📄 Report saved to {output_file}")

    def print_summary(self):
        print("\n" + "=" * 60)
        print("PHASE 2 EVAL SUMMARY")
        print("=" * 60)
        print(f"Total Queries: {self.stats['total']}")
        print(f"✅ Passed:      {self.stats['passed']}")
        print(f"❌ Failed:      {self.stats['failed']}")
        print(f"⚠️  Warnings:    {self.stats['warnings']}")
        print("-" * 60)
        
        if self.stats["failed"] == 0:
            print("🏆 PHASE 2 DURABILITY: CONFIRMED")
        else:
            print("🚨 PHASE 2 FAILURES DETECTED")
            for f in self.stats["blocking_failures"]:
                print(f" - {f}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run 1 query per category")
    args = parser.parse_args()
    
    runner = Phase2Evaluator()
    runner.run_suite(smoke_mode=args.smoke)
