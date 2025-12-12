# Vasudeva Evaluation System

## Overview

Simple, practical evaluation system to ensure story accuracy and guidance quality.

## Quick Start

```bash
cd eval_system
python run_evals.py
```

## Structure

```
eval_system/
├── tests/
│   └── critical_tests.json   # 15 critical test cases
├── results/
│   └── [timestamp]_report.txt  # Test results
└── run_evals.py              # Eval runner script
```

## Test Categories

### Story Accuracy (6 tests)
- Regression tests for Shakuntala fabrication issue
- Character name validation
- No divine additions

### Edge Cases (4 tests)
- Short/long/ambiguous queries
- No story scenarios

### Fact-Checking (3 tests)
- No invented dialogue
- Valid source citations
- Timeline accuracy

### Safety (2 tests)
- No medical advice
- Compassionate guidance

## Checks Implemented

**Rule-Based**:
- Forbidden phrase detection (exact match)
- Required content validation
- Response time limits
- Empty response detection
- Character/source presence

## Current Tests

Total: 15 critical tests
- Focus: Story accuracy & known regressions
- No LLM judges (keeps it fast & cheap)
- Simple rule-based checks

## Adding New Tests

Edit `tests/critical_tests.json`:

```json
{
  "id": "my_new_test",
  "category": "story_accuracy",
  "problem": "User's question here",
  "checks": {
    "forbidden_phrases": ["phrase to avoid"],
    "required_one_of": ["expected content"],
    "max_response_time_seconds": 45
  }
}
```

## Success Criteria

- ✅ ≥80% tests passing
- ✅ Catches Shakuntala fabrication
- ✅ <3 minutes total run time

## Reports

Results saved to `results/[timestamp]_report.txt`

Example output:
```
Total:   15
Passed:  12 ✅
Failed:  3 ❌
Pass Rate: 80.0%
```

## Next Steps

1. Run initial eval suite
2. Fix any failures
3. Add more tests from user feedback
4. Weekly eval runs
