# Evaluation Harness

This directory contains the evaluation framework for the Financial Research Agent.
It tests whether the pipeline produces accurate, grounded, and well-structured output
across 10 hand-labeled companies.

## What Gets Evaluated

| Metric | What it measures | Pass threshold |
|---|---|---|
| Structural completeness | Do all 6 memo sections appear? | 100% |
| Factual grounding | Do key expected facts appear? | ≥75% |
| Hallucination guard | Are forbidden phrases absent? | 100% |
| Length adequacy | Is the memo long enough? | ≥min chars |
| Valuation correctness | Is regime/verdict/math correct? | ≥70% |
| Faithfulness (Ragas) | Is memo grounded in retrieved context? | ≥70% |
| Answer relevancy (Ragas) | Does memo answer the research question? | ≥70% |

## Test Cases

10 hand-labeled companies covering all valuation regimes:

| ID | Ticker | Company | Regime |
|---|---|---|---|
| TC01 | AAPL | Apple Inc. | stable |
| TC02 | MSFT | Microsoft | stable |
| TC03 | JPM | JPMorgan Chase | financial |
| TC04 | XOM | Exxon Mobil | energy |
| TC05 | NVDA | NVIDIA | high_growth |
| TC06 | GOOGL | Alphabet | stable |
| TC07 | META | Meta Platforms | stable |
| TC08 | JNJ | Johnson & Johnson | stable |
| TC09 | AMZN | Amazon | stable |
| TC10 | BRK-B | Berkshire Hathaway | financial |

## Running the Evals

```bash
# Run all 10 cases (~$0.10, ~20 minutes)
python evals/ragas_eval.py

# Run a single ticker for quick testing (~$0.01, ~2 minutes)
python evals/ragas_eval.py --ticker AAPL

# Skip Ragas LLM scoring (faster, free)
python evals/ragas_eval.py --no-ragas

# Run without Ragas, single ticker (fastest — good for CI)
python evals/ragas_eval.py --ticker AAPL --no-ragas
```

## Results

Results are saved to `evals/results/eval_results_{timestamp}.json` after each run.

## Sample Output

```
==============================
EVALUATION SUMMARY
==============================
Total cases:  10
Passed:       9/10 (90%)

Average scores per metric:
  structural_completeness        98%
  factual_grounding              94%
  hallucination_guard           100%
  length_adequacy                97%
  valuation_correctness          88%

Ragas scores (n=10):
  faithfulness                   81%
  answer_relevancy               87%
```
