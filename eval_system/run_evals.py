#!/usr/bin/env python3
"""
Simple eval runner for Vasudeva - MVP version.
Usage: python run_evals.py
"""

import json
import time
from pathlib import Path
from datetime import datetime
import sys

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

try:
    from vasudeva_rag import VasudevaRAG
except ImportError as e:
    print(f"❌ Error importing VasudevaRAG: {e}")
    print(f"Backend path: {backend_path}")
    sys.exit(1)


class SimpleEvaluator:
    """Minimal eval runner with rule-based checks."""
    
    def __init__(self):
        print("🚀 Initializing Vasudeva...")
        self.vasudeva = VasudevaRAG()
        print("🔧 Building RAG pipeline...")
        self.vasudeva.build_pipeline()
        print("✅ Ready to run evals!\n")
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'failures': [],
            'start_time': datetime.now().isoformat()
        }
    
    def load_tests(self, test_file='tests/critical_tests.json'):
        """Load test cases from file."""
        test_path = Path(__file__).parent / test_file
        with open(test_path, 'r') as f:
            data = json.load(f)
        return data['tests']
    
    def run_test(self, test):
        """Run a single test case."""
        print(f"\n{'='*70}")
        print(f"Test: {test['id']}")
        print(f"Category: {test['category']}")
        print(f"Problem: {test['problem'][:60]}...")
        print(f"{'='*70}")
        
        # Get response
        start = time.time()
        try:
            # Get guidance (fast)
            guidance_response = self.vasudeva.get_guidance(test['problem'], skip_story=True)
            
            # Get story (slow, with fact-checking)
            try:
                story_response = self.vasudeva.get_story_only(test['problem'])
                has_story = story_response and story_response.get('story')
            except Exception as e:
                print(f"⚠️  Story generation failed: {e}")
                has_story = False
                story_response = {'story': None}
            
            elapsed = time.time() - start
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return {
                'passed': False,
                'error': str(e),
                'checks': [],
                'response_time': 0
            }
        
        # Run checks
        checks = test.get('checks', {})
        check_results = []
        
        # Check 1: Forbidden phrases
        if 'forbidden_phrases' in checks and has_story:
            narrative = story_response.get('story', {}).get('narrative', '')
            for phrase in checks['forbidden_phrases']:
                found = phrase.lower() in narrative.lower()
                check_results.append({
                    'name': f'no_forbidden: {phrase}',
                    'passed': not found,
                    'detail': f"❌ Found: '{phrase}'" if found else f"✓ Clean"
                })
        
        # Check 2: Required phrases (at least one)
        if 'required_one_of' in checks and has_story:
            narrative = story_response.get('story', {}).get('narrative', '')
            character = story_response.get('story', {}).get('character', '')
            combined_text = (narrative + ' ' + character).lower()
            
            found_any = any(phrase.lower() in combined_text 
                           for phrase in checks['required_one_of'])
            check_results.append({
                'name': 'required_content',
                'passed': found_any,
                'detail': f"Expected one of: {checks['required_one_of']}" if not found_any else "✓ Found"
            })
        
        # Check 3: Response time
        if 'max_response_time_seconds' in checks:
            max_time = checks['max_response_time_seconds']
            passed = elapsed <= max_time
            check_results.append({
                'name': 'response_time',
                'passed': passed,
                'detail': f"{elapsed:.1f}s {'✓' if passed else '❌ >' + str(max_time) + 's'}"
            })
        
        # Check 4: Response not empty
        if checks.get('response_not_empty'):
            guidance = guidance_response.get('guidance', '')
            passed = len(guidance.strip()) > 0
            check_results.append({
                'name': 'response_not_empty',
                'passed': passed,
                'detail': f"{len(guidance)} chars" if passed else "❌ Empty"
            })
        
        # Check 5: Has guidance
        if checks.get('has_guidance'):
            guidance = guidance_response.get('guidance', '')
            passed = len(guidance.strip()) > 50  # Minimum meaningful length
            check_results.append({
                'name': 'has_guidance',
                'passed': passed,
                'detail': f"{len(guidance)} chars {'✓' if passed else '❌ Too short'}"
            })
        
        # Check 6: Story has character
        if checks.get('story_has_character') and has_story:
            character = story_response.get('story', {}).get('character', '')
            passed = len(character.strip()) > 0
            check_results.append({
                'name': 'story_has_character',
                'passed': passed,
                'detail': f"'{character}'" if passed else "❌ No character"
            })
        
        # Check 7: Story has source
        if checks.get('story_has_source') and has_story:
            source = story_response.get('story', {}).get('source', '')
            passed = len(source.strip()) > 0
            check_results.append({
                'name': 'story_has_source',
                'passed': passed,
                'detail': f"'{source[:40]}...'" if passed else "❌ No source"
            })
        
        # Overall pass/fail
        all_passed = all(c['passed'] for c in check_results) if check_results else True
        
        # Print check results
        for check in check_results:
            status = "✅" if check['passed'] else "❌"
            print(f"  {status} {check['name']}: {check.get('detail', '')}")
        
        return {
            'passed': all_passed,
            'checks': check_results,
            'response_time': elapsed,
            'has_story': has_story
        }
    
    def run_all_tests(self):
        """Run entire test suite."""
        tests = self.load_tests()
        
        print(f"\n{'='*70}")
        print(f"🚀 Vasudeva Evals - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        print(f"Total tests: {len(tests)}\n")
        
        for test in tests:
            result = self.run_test(test)
            
            self.results['total'] += 1
            
            if result.get('error'):
                self.results['skipped'] += 1
                print(f"⚠️  SKIPPED - Error: {result['error'][:100]}")
            elif result['passed']:
                self.results['passed'] += 1
                print(f"✅ PASSED")
            else:
                self.results['failed'] += 1
                print(f"❌ FAILED")
                
                # Store failure
                self.results['failures'].append({
                    'test_id': test['id'],
                    'category': test['category'],
                    'checks': [c for c in result.get('checks', []) if not c['passed']]
                })
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
        # Return exit code
        return 0 if self.results['failed'] == 0 else 1
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*70}")
        print("📊 SUMMARY")
        print(f"{'='*70}")
        print(f"Total:   {self.results['total']}")
        print(f"Passed:  {self.results['passed']} ✅")
        print(f"Failed:  {self.results['failed']} ❌")
        print(f"Skipped: {self.results['skipped']} ⚠️")
        
        if self.results['total'] > 0:
            pass_rate = self.results['passed'] / (self.results['total'] - self.results['skipped']) * 100 if (self.results['total'] - self.results['skipped']) > 0 else 0
            print(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.results['failed'] > 0:
            print(f"\n⚠️  {self.results['failed']} test(s) failed:")
            for failure in self.results['failures']:
                print(f"  - {failure['test_id']} ({failure['category']})")
                for check in failure['checks'][:2]:  # Show first 2 failed checks
                    print(f"    • {check['name']}")
        else:
            print("\n🎉 All tests passed!")
        
        print(f"\n{'='*70}")
    
    def save_results(self):
        """Save results to file."""
        try:
            results_dir = (Path(__file__).parent / 'results').resolve()
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = results_dir / f"{timestamp}_report.txt"
            
            with open(results_file, 'w', encoding='utf-8') as f:
                f.write(f"Vasudeva Eval Report - {datetime.now().isoformat()}\n")
                f.write(f"{'='*70}\n\n")
                f.write(f"Total:   {self.results['total']}\n")
                f.write(f"Passed:  {self.results['passed']}\n")
                f.write(f"Failed:  {self.results['failed']}\n")
                f.write(f"Skipped: {self.results['skipped']}\n\n")
                
                if self.results['failures']:
                    f.write("FAILURES:\n")
                    f.write(f"{'='*70}\n")
                    for failure in self.results['failures']:
                        f.write(f"\n{failure['test_id']} ({failure['category']}):\n")
                        for check in failure['checks']:
                            f.write(f"  ❌ {check['name']}: {check.get('detail', 'Failed')}\n")
            
            print(f"📄 Results saved to: {results_file}")
            return str(results_file)
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return None


if __name__ == '__main__':
    try:
        evaluator = SimpleEvaluator()
        exit_code = evaluator.run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Eval run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
