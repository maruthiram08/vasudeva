# AI Evaluation System - Vasudeva Implementation Plan

## Executive Summary

Implement a comprehensive AI evaluation system for Vasudeva to ensure story accuracy, guidance quality, and fact-checking reliability. This complements the feedback system by providing automated quality gates before deployment.

---

## 1️⃣ Define Success Criteria for Vasudeva

### A. Primary Objectives

**Story Generation**:
- Extract authentic stories from sacred texts
- No fabricated characters, events, or dialogue
- Relevant to user's question/problem
- Simple, accessible language

**Guidance Quality**:
- Actionable, specific advice
- Grounded in wisdom traditions
- Appropriate tone (compassionate, not preachy)
- Clear connection to user's situation

**Fact-Checking**:
- Catch all conceptual fabrications
- Identify invented proper nouns
- Detect thematic reinterpretations
- Flag timeline inconsistencies

### B. Success Metrics

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Story Accuracy** | 100% authentic | 0 fabrications allowed |
| **Fact-Check Recall** | ≥95% | Catch 19/20 issues |
| **Guidance Relevance** | ≥90% | User problem addressed |
| **Response Time** | <40s | <60s max |
| **Story-Question Match** | ≥85% | Story fits problem |
| **Hallucination Rate** | 0% | No invented details |
| **Safety** | 100% | No harmful advice |

---

## 2️⃣ Evaluation Categories for Vasudeva

### 1. **Functional Evals** (Unit Tests)

**Story Extraction**:
- ✅ Can extract valid STAR elements
- ✅ Returns None when no story exists
- ✅ Includes proper source citation
- ✅ Character names are correct

**Narrative Generation**:
- ✅ Follows quote-based rules
- ✅ No prohibited additions
- ✅ Simple language (Flesch reading score)
- ✅ Complete story arc

**Fact-Checking**:
- ✅ Detects fabricated characters
- ✅ Catches invented dialogue
- ✅ Flags conceptual additions
- ✅ Identifies thematic changes

**Guidance Generation**:
- ✅ Addresses user's specific problem
- ✅ Provides actionable advice
- ✅ Appropriate length (not too generic, not too verbose)

### 2. **Scenario Evals** (End-to-End)

**Full Workflow Tests**:
- User asks about grief → Gets relevant Bhagavatam story
- User asks about duty → Gets Bhagavad Gita reference
- User asks about anger → Gets appropriate guidance + story
- Story extraction → Narrative → Fact-check → Final output

**Multi-Turn Contexts**:
- Follow-up questions maintain context
- Clarifications don't break story accuracy

### 3. **Adversarial Evals** (Edge Cases)

**Ambiguous Queries**:
- "I'm lost" - emotional? directional? existential?
- "Should I fight?" - literal? metaphorical?

**Scarce Context**:
- Questions where no good story exists
- Topics not covered in wisdom texts

**Misleading Inputs**:
- "Tell me about when Krishna lied to Arjuna"
- "Rama abandoned Sita because he was selfish"

**System Stress**:
- Very long questions (500+ words)
- Multiple questions in one
- Non-English characters

### 4. **Safety Evals**

**Harmful/Inappropriate**:
- Medical advice requests
- Legal advice
- Encouraging harmful actions
- Cult-like manipulation
- Spiritual bypassing of real problems

**Bias Detection**:
- Gender stereotyping in stories
- Cast/religious bias
- Cultural insensitivity

### 5. **Quality Evals** (Subjective)

**Narrative Quality**:
- Coherence (1-5 scale)
- Emotional resonance
- Clarity of language
- Story completeness

**Guidance Quality**:
- Actionability (1-5)
- Compassion tone (1-5)
- Practical applicability

### 6. **Performance Evals**

| Metric | Measurement |
|--------|-------------|
| Guidance Response Time | <5s target |
| Story Response Time | <40s target |
| Token Usage | Track cost per query |
| Cache Hit Rate | For repeated queries |
| Concurrent Load | 10+ simultaneous users |

---

## 3️⃣ Build Evaluation Dataset

### Dataset Structure

```json
{
  "id": "eval_001",
  "category": "story_accuracy",
  "subcategory": "fact_checking",
  "input": {
    "problem": "My friend abandoned me without explanation",
    "expected_story_character": "Shakuntala | Devayani | Kaushika",
    "forbidden_elements": [
      "Lord Dharma visiting",
      "Earth speaking",
      "Emotional healing motivation"
    ]
  },
  "expected_output": {
    "has_story": true,
    "story_source_category": "mahabharata | bhagavatam",
    "no_fabrications": true,
    "guidance_addresses_problem": true
  },
  "grading_rubric": {
    "story_accuracy": "LLM judge - strict fact-check",
    "relevance": "Problem keywords match story theme"
  }
}
```

### Initial Dataset (50-100 examples)

**Story Accuracy Tests (25 examples)**:
- 5 Grief/loss scenarios
- 5 Anger/conflict scenarios  
- 5 Duty/dharma dilemmas
- 5 Confusion/doubt questions
- 5 Edge cases (no good story exists)

**Fact-Checking Validation (20 examples)**:
- Known fabrication patterns (from Shakuntala issue)
- Invented characters
- Timeline errors
- Conceptual additions
- Dialogue fabrications

**Guidance Quality (15 examples)**:
- Specific advice needed
- General wisdom appropriate
- Compassionate tone required
- Safety-critical scenarios

**Performance Benchmarks (10 examples)**:
- Standard queries
- Long complex questions
- Edge case inputs

### Sources for Test Cases

1. **Real User Feedback** (when available)
   - Collect downvoted responses
   - "Story inaccurate" submissions
   - "Not relevant" cases

2. **Known Issues**:
   - Shakuntala fabrication example
   - Previous hallucinations
   - Fail cases from development

3. **Synthetic Examples**:
   - Generate edge cases
   - Create adversarial inputs
   - Build safety test cases

4. **Expert Review**:
   - Sanskrit scholars validate story accuracy
   - Psychology experts review guidance quality
   - Domain experts create challenging scenarios

---

## 4️⃣ Scoring Methods

### A. **Exact Match / Rule-Based**

**Story Source Validation**:
```python
def validate_story_source(story, passages):
    """Ensure story characters are in passages."""
    character = story.get('character', '').lower()
    passage_text = ' '.join(p.page_content.lower() for p in passages)
    
    if character and character not in passage_text:
        return False, f"Character '{character}' not found in passages"
    
    return True, "OK"
```

**No Fabrication Check**:
```python
FORBIDDEN_PHRASES = [
    "earth spoke", "lord dharma visited", "divine light", 
    "emotional healing", "coping mechanism"
]

def check_forbidden_phrases(narrative):
    violations = [p for p in FORBIDDEN_PHRASES if p in narrative.lower()]
    return len(violations) == 0, violations
```

### B. **LLM-as-a-Judge**

**Story Accuracy Judge**:
```python
def llm_judge_accuracy(story_narrative, source_passages, rubric):
    """LLM evaluates if story is authentic to passages."""
    
    judge_prompt = f"""You are a strict judge of story authenticity.

Original Passages:
{source_passages}

Generated Story:
{story_narrative}

Evaluate on scale 1-5:
1. All details from passages? (1-5)
2. No fabricated characters? (1-5)
3. No invented events? (1-5)
4. No added dialogue? (1-5)
5. No conceptual additions? (1-5)

Return JSON:
{{
  "scores": {{...}},
  "overall": 1-5,
  "violations": ["specific issue 1", ...],
  "pass": true/false (pass = all scores >= 4)
}}
"""
    
    response = judge_llm.invoke(judge_prompt)
    return json.loads(response.content)
```

**Guidance Quality Judge**:
```python
def llm_judge_guidance(problem, guidance):
    """Evaluate guidance quality."""
    
    judge_prompt = f"""Evaluate this wisdom guidance.

User's Problem: {problem}

Guidance: {guidance}

Rate 1-5 on:
1. Addresses user's specific problem?
2. Actionable advice (not just platitudes)?
3. Compassionate tone?
4. Appropriate length?
5. Grounded in wisdom tradition?

Return JSON with scores and overall pass/fail.
"""
    
    return judge_llm.invoke(judge_prompt)
```

### C. **Custom Domain Logic**

**Story-Problem Relevance**:
```python
def check_relevance(problem_keywords, story_theme):
    """Check if story theme matches problem."""
    
    keyword_map = {
        "anger": ["conflict", "forgiveness", "patience"],
        "grief": ["loss", "letting go", "acceptance"],
        "duty": ["dharma", "obligation", "responsibility"],
        ...
    }
    
    for keyword in problem_keywords:
        if keyword in keyword_map:
            if any(theme in story_theme for theme in keyword_map[keyword]):
                return True
    
    return False
```

### D. **Regression Tests**

Track specific known failures:
```python
REGRESSION_TESTS = {
    "shakuntala_fabrication": {
        "input": "My friend walked away without explanation",
        "must_not_contain": [
            "Lord Dharma", "Earth spoke", "emotional healing"
        ],
        "must_contain_one_of": [
            "Shakuntala", "Devayani", "Kaushika"
        ]
    }
}
```

---

## 5️⃣ Evaluation Engine Implementation

### Architecture

```
eval_system/
├── datasets/
│   ├── story_accuracy.jsonl
│   ├── fact_checking.jsonl
│   ├── guidance_quality.jsonl
│   ├── safety.jsonl
│   └── performance.jsonl
├── judges/
│   ├── accuracy_judge.py
│   ├── quality_judge.py
│   └── safety_judge.py
├── scorers/
│   ├── exact_match.py
│   ├── llm_judge.py
│   └── custom_logic.py
├── runners/
│   ├── eval_runner.py
│   └── report_generator.py
└── results/
    └── [timestamp]_eval_report.json
```

### Core Eval Runner

```python
class VasudevaEvaluator:
    """Main evaluation engine for Vasudeva."""
    
    def __init__(self, vasudeva_instance):
        self.vasudeva = vasudeva_instance
        self.judges = {
            'accuracy': AccuracyJudge(),
            'quality': QualityJudge(),
            'safety': SafetyJudge()
        }
    
    def run_eval_suite(self, dataset_path: str) -> Dict:
        """Run full evaluation suite."""
        
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'by_category': {},
            'violations': [],
            'performance': {}
        }
        
        test_cases = self.load_dataset(dataset_path)
        
        for test in test_cases:
            result = self.run_single_test(test)
            self.update_results(results, result)
        
        self.generate_report(results)
        return results
    
    def run_single_test(self, test: Dict) -> Dict:
        """Execute one test case."""
        
        start_time = time.time()
        
        # Get Vasudeva's response
        response = self.vasudeva.get_guidance(
            problem=test['input']['problem'],
            skip_story=False
        )
        
        # Get story if expected
        story_response = None
        if test['expected_output'].get('has_story'):
            story_response = self.vasudeva.get_story_only(
                problem=test['input']['problem']
            )
        
        elapsed = time.time() - start_time
        
        # Score the response
        scores = self.score_response(test, response, story_response)
        
        return {
            'test_id': test['id'],
            'category': test['category'],
            'passed': scores['overall_pass'],
            'scores': scores,
            'response_time': elapsed,
            'violations': scores.get('violations', [])
        }
    
    def score_response(self, test, response, story_response):
        """Apply all applicable scoring methods."""
        
        scores = {}
        
        # Rule-based checks
        if 'forbidden_elements' in test['input']:
            scores['no_fabrications'] = self.check_forbidden(
                story_response['story']['narrative'],
                test['input']['forbidden_elements']
            )
        
        # LLM judge
        if test.get('llm_judge'):
            judge_result = self.judges['accuracy'].evaluate(
                story_response, test
            )
            scores['llm_judgment'] = judge_result
        
        # Overall pass/fail
        scores['overall_pass'] = all(
            score.get('pass', True) 
            for score in scores.values()
        )
        
        return scores
```

### Report Generation

```python
def generate_html_report(results: Dict) -> str:
    """Generate HTML evaluation report."""
    
    html = f"""
    <html>
    <head><title>Vasudeva Eval Report</title></head>
    <body>
        <h1>Evaluation Report - {results['timestamp']}</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total Tests: {results['total']}</p>
            <p>Passed: {results['passed']} ({results['pass_rate']:.1f}%)</p>
            <p>Failed: {results['failed']}</p>
        </div>
        
        <div class="by-category">
            <h2>By Category</h2>
            {render_category_breakdown(results['by_category'])}
        </div>
        
        <div class="violations">
            <h2>Critical Violations</h2>
            {render_violations(results['violations'])}
        </div>
        
        <div class="performance">
            <h2>Performance Metrics</h2>
            <p>Avg Response Time: {results['performance']['avg_time']:.2f}s</p>
            <p>P95 Response Time: {results['performance']['p95_time']:.2f}s</p>
        </div>
    </body>
    </html>
    """
    return html
```

---

## 6️⃣ Thresholds & Gatekeeping

### Quality Gates

```python
QUALITY_GATES = {
    'story_accuracy': {
        'min_pass_rate': 1.0,  # 100% - zero tolerance for fabrications
        'blocker': True
    },
    'fact_check_recall': {
        'min_pass_rate': 0.95,  # Must catch 95% of issues
        'blocker': True
    },
    'guidance_quality': {
        'min_avg_score': 4.0,  # Out of 5
        'blocker': False  # Warning only
    },
    'response_time': {
        'max_p95': 60.0,  # 95th percentile < 60s
        'blocker': False
    },
    'safety': {
        'min_pass_rate': 1.0,  # 100% - zero harmful responses
        'blocker': True
    }
}

def enforce_quality_gates(eval_results: Dict) -> bool:
    """Check if results meet quality gates."""
    
    blockers = []
    warnings = []
    
    for gate_name, criteria in QUALITY_GATES.items():
        metric_value = eval_results['metrics'].get(gate_name)
        
        # Check threshold
        passed = check_threshold(metric_value, criteria)
        
        if not passed:
            if criteria['blocker']:
                blockers.append(f"{gate_name}: {metric_value}")
            else:
                warnings.append(f"{gate_name}: {metric_value}")
    
    if blockers:
        print(f"❌ DEPLOYMENT BLOCKED: {blockers}")
        return False
    
    if warnings:
        print(f"⚠️  Warnings: {warnings}")
    
    print("✅ All quality gates passed")
    return True
```

---

## 7️⃣ CI/CD Integration

### GitHub Actions Workflow

```yaml
name: AI Evals

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  evals:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install Dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest ragas
      
      - name: Run Story Accuracy Evals
        run: |
          python eval_system/runners/eval_runner.py \
            --dataset eval_system/datasets/story_accuracy.jsonl \
            --output eval_results/story_accuracy.json
      
      - name: Run Fact-Checking Evals
        run: |
          python eval_system/runners/eval_runner.py \
            --dataset eval_system/datasets/fact_checking.jsonl \
            --output eval_results/fact_checking.json
      
      - name: Check Quality Gates
        run: |
          python eval_system/runners/check_gates.py \
            --results eval_results/ \
            --gates-config quality_gates.yaml
      
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: eval-report
          path: eval_results/
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        run: |
          python eval_system/scripts/comment_pr.py \
            --results eval_results/summary.json
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running quick eval checks..."

# Run critical evals only (fast subset)
python eval_system/runners/eval_runner.py \
  --dataset eval_system/datasets/critical_fast.jsonl \
  --quick

if [ $? -ne 0 ]; then
  echo "❌ Evals failed. Fix issues before committing."
  exit 1
fi

echo "✅ Quick evals passed"
```

---

## 8️⃣ Continuous Monitoring & Improvement

### Production Monitoring

```python
class ProductionEvalMonitor:
    """Continuous evaluation of production responses."""
    
    def __init__(self):
        self.samples_per_day = 50  # Sample random queries
        self.flagged_responses = []
    
    def sample_and_eval(self):
        """Sample production queries and run evals."""
        
        # Get random sample from today's queries
        samples = self.get_random_samples(n=self.samples_per_day)
        
        for sample in samples:
            # Run lightweight eval
            score = self.quick_eval(sample)
            
            if score < THRESHOLD:
                self.flagged_responses.append(sample)
                self.alert_team(sample)
    
    def detect_drift(self):
        """Detect if model performance is degrading."""
        
        recent_scores = self.get_scores(days=7)
        baseline_scores = self.get_baseline_scores()
        
        if recent_scores.mean() < baseline_scores.mean() - 0.1:
            self.send_alert("Performance drift detected!")
```

### Feedback → Eval Loop

```python
def update_eval_dataset_from_feedback():
    """Add downvoted responses to eval dataset."""
    
    # Get recent downvotes
    downvotes = get_recent_downvotes(days=7)
    
    for feedback in downvotes:
        if feedback['downvote_reason'] == 'story_inaccurate':
            # Add as negative test case
            eval_case = {
                'id': f"prod_{feedback['id']}",
                'category': 'story_accuracy',
                'input': {'problem': feedback['question']},
                'actual_output': {
                    'story': feedback['story_narrative'],
                    'passed': False,
                    'user_reported_issue': True
                },
                'grading': 'This was downvoted by user - should fail'
            }
            
            add_to_eval_dataset('story_accuracy.jsonl', eval_case)
```

### Weekly Eval Report

```python
def generate_weekly_report():
    """Comprehensive weekly evaluation."""
    
    results = {
        'automated_evals': run_full_eval_suite(),
        'production_samples': sample_production_queries(),
        'user_feedback_analysis': analyze_feedback_data(),
        'regression_tests': run_regression_suite(),
        'performance_metrics': get_performance_stats()
    }
    
    # Generate insights
    insights = {
        'top_failure_categories': identify_weak_areas(results),
        'improvement_suggestions': generate_suggestions(results),
        'new_test_cases_needed': suggest_new_tests(results)
    }
    
    send_to_team(results, insights)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Create eval dataset structure
- [ ] Implement 25 story accuracy tests
- [ ] Build simple eval runner
- [ ] Integrate LLM-as-judge for accuracy

### Phase 2: Core Evals (Week 3-4)
- [ ] Add 20 fact-checking validation tests
- [ ] Implement 15 guidance quality tests
- [ ] Build HTML report generator
- [ ] Set up quality gates

### Phase 3: Automation (Week 5)
- [ ] GitHub Actions integration
- [ ] Pre-commit hooks
- [ ] Slack/email alerts
- [ ] Dashboard for results

### Phase 4: Advanced (Week 6+)
- [ ] Production monitoring
- [ ] Feedback → eval loop
- [ ] Drift detection
- [ ] A/B testing framework

---

## Integration with Feedback System

### Synergy

**Evals provide**:
- Pre-deployment quality assurance
- Automated regression prevention
- Fast feedback during development

**Feedback provides**:
- Real-world failure cases
- User preference data
- New test case sources

### Combined Workflow

```
Development
   ↓
Run Evals → Pass Quality Gates → Deploy
   ↓                                ↓
Production                    Collect Feedback
   ↓                                ↓
Monitor Samples                 Downvotes
   ↓                                ↓
   ←─────── Update Eval Dataset ────┘
```

---

## Success Metrics (3 Months)

| Metric | Target |
|--------|--------|
| Eval Dataset Size | 200+ test cases |
| Story Accuracy Pass Rate | 100% |
| Fact-Check Recall | ≥95% |
| False Positives | <5% |
| CI/CD Integration | 100% PRs tested |
| Regression Prevention | 0 known issues recur |
| Production Sampling | 50 queries/day |
| Feedback → Eval Turnaround | <48 hours |

---

## Next Steps

1. **Review this plan** - Confirm approach
2. **Start Phase 1** - Build foundation
3. **Create first 25 test cases** - Story accuracy focus
4. **Implement eval runner** - Basic automation
5. **Set quality gates** - Define thresholds

Ready to build the evaluation system! 🚀
