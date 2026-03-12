"""
ragas_eval.py
─────────────
Evaluation harness for the Financial Research Agent.

Runs 10 hand-labeled test cases through the pipeline and scores:
  1. Structural completeness  — does the memo have all 6 required sections?
  2. Factual grounding        — do key expected facts appear in the memo?
  3. Hallucination guard      — does the memo contain any forbidden phrases?
  4. Length adequacy          — is the memo long enough to be useful?
  5. Valuation correctness    — is the regime, verdict, and math correct?
  6. Faithfulness (Ragas)     — is the memo grounded in the retrieved context?
  7. Answer relevancy (Ragas) — does the memo answer the research question?

Usage:
  # Run all 10 cases (costs ~$0.10 in API credits)
  python evals/ragas_eval.py

  # Run a single ticker for quick testing
  python evals/ragas_eval.py --ticker AAPL

  # Skip Ragas LLM scoring (faster, free)
  python evals/ragas_eval.py --no-ragas

Results saved to: evals/results/eval_results_{timestamp}.json
Summary printed to terminal.
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_test_cases(path: str = None) -> list:
    path = path or Path(__file__).parent / "test_cases.json"
    with open(path) as f:
        return json.load(f)


def run_pipeline(ticker: str) -> dict:
    """Run the full research pipeline for a ticker. Returns final state."""
    from src.graph.graph import build_research_graph
    from src.validator import validate_ticker

    is_valid, company_name = validate_ticker(ticker)
    if not is_valid:
        raise ValueError(f"Invalid ticker: {ticker}")

    graph = build_research_graph()
    initial_state = {
        "ticker":           ticker,
        "company_name":     company_name,
        "news_results":     None,
        "filing_excerpt":   None,
        "filing_date":      None,
        "financial_data":   None,
        "risk_assessment":  None,
        "valuation_result": None,
        "investment_memo":  None,
        "errors":           []
    }
    return graph.invoke(initial_state)


# ── Individual scorers ────────────────────────────────────────────────────────

def score_structural_completeness(memo: str, expected_sections: list) -> dict:
    """Check that all required sections appear in the memo."""
    found    = [s for s in expected_sections if f"## {s}" in memo or s in memo]
    missing  = [s for s in expected_sections if s not in found]
    score    = len(found) / len(expected_sections) if expected_sections else 0
    return {
        "score":   round(score, 3),
        "found":   found,
        "missing": missing,
        "pass":    score == 1.0
    }


def score_factual_grounding(memo: str, expected_facts: list) -> dict:
    """Check that key expected facts appear in the memo (case-insensitive)."""
    memo_lower = memo.lower()
    found   = [f for f in expected_facts if f.lower() in memo_lower]
    missing = [f for f in expected_facts if f.lower() not in memo_lower]
    score   = len(found) / len(expected_facts) if expected_facts else 0
    return {
        "score":   round(score, 3),
        "found":   found,
        "missing": missing,
        "pass":    score >= 0.75   # 75% of facts must appear
    }


def score_hallucination_guard(memo: str, forbidden: list) -> dict:
    """Check that forbidden phrases do NOT appear in the memo."""
    memo_lower  = memo.lower()
    violations  = [p for p in forbidden if p.lower() in memo_lower]
    score       = 1.0 if not violations else 0.0
    return {
        "score":      score,
        "violations": violations,
        "pass":       score == 1.0
    }


def score_length_adequacy(memo: str, min_length: int) -> dict:
    """Check that memo meets minimum length threshold."""
    length = len(memo)
    score  = min(1.0, length / min_length)
    return {
        "score":      round(score, 3),
        "length":     length,
        "min_length": min_length,
        "pass":       length >= min_length
    }


def score_valuation_correctness(result: dict, expected_regime: str) -> dict:
    """Check valuation result has correct structure and valid verdict."""
    vr = result.get("valuation_result")
    if not vr:
        return {"score": 0.0, "pass": False, "reason": "valuation_result is None"}

    checks = {
        "has_regime":         "regime" in vr,
        "correct_regime":     vr.get("regime") == expected_regime,
        "has_verdict":        vr.get("verdict") in ("UNDERVALUED", "FAIRLY VALUED", "OVERVALUED"),
        "has_weighted_value": isinstance(vr.get("weighted_fair_value"), (int, float)),
        "has_models":         len(vr.get("models", [])) > 0,
        "has_range":          len(vr.get("valuation_range", [])) == 2,
        "math_correct":       _check_upside_math(vr),
    }

    passed = sum(checks.values())
    score  = round(passed / len(checks), 3)
    return {
        "score":   score,
        "checks":  checks,
        "regime":  vr.get("regime"),
        "verdict": vr.get("verdict"),
        "pass":    score >= 0.70
    }


def _check_upside_math(vr: dict) -> bool:
    """Verify upside_pct matches weighted_fair_value and current_price."""
    try:
        wfv   = float(vr["weighted_fair_value"])
        price = float(vr["current_price"])
        reported = float(vr["upside_pct"])
        expected = round((wfv - price) / price * 100, 1)
        return abs(reported - expected) < 0.5
    except Exception:
        return False


# ── Ragas scoring ─────────────────────────────────────────────────────────────

def score_ragas(result: dict, ticker: str) -> dict:
    """
    Score faithfulness and answer relevancy using Ragas.
    Faithfulness:     is the memo grounded in the retrieved context?
    Answer relevancy: does the memo answer the investment research question?
    """
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from datasets import Dataset

        memo    = result.get("investment_memo", "")
        filing  = result.get("filing_excerpt", "") or ""
        news    = result.get("news_results", []) or []
        fin     = result.get("financial_data", {}) or {}

        # Build context from all retrieved sources
        context_parts = []
        if filing:
            context_parts.append(f"SEC 10-K Filing:\n{filing[:1500]}")
        if news:
            news_text = "\n".join([f"- {n['title']}" for n in news[:5]])
            context_parts.append(f"Recent News:\n{news_text}")
        if fin:
            context_parts.append(
                f"Financial Data: Revenue={fin.get('revenue_ttm','N/A')}, "
                f"Net Income={fin.get('net_income','N/A')}, "
                f"Margin={fin.get('operating_margin','N/A')}"
            )

        context = "\n\n".join(context_parts) if context_parts else "No context available."

        # Build Ragas dataset
        data = {
            "question":  [f"Write an institutional investment memo for {ticker}"],
            "answer":    [memo],
            "contexts":  [[context]],
            "ground_truth": [f"A professional investment memo for {ticker} with financial analysis and valuation."]
        }
        dataset = Dataset.from_dict(data)

        scores = evaluate(dataset, metrics=[faithfulness, answer_relevancy])

        return {
            "faithfulness":     round(float(scores["faithfulness"]),     3),
            "answer_relevancy": round(float(scores["answer_relevancy"]), 3),
            "pass": (
                float(scores["faithfulness"])     >= 0.70 and
                float(scores["answer_relevancy"]) >= 0.70
            )
        }

    except Exception as e:
        return {
            "faithfulness":     None,
            "answer_relevancy": None,
            "pass":             None,
            "error":            str(e)
        }


# ── Single case evaluator ─────────────────────────────────────────────────────

def evaluate_case(tc: dict, run_ragas: bool = True) -> dict:
    """Run the full pipeline for one test case and score it."""
    ticker = tc["ticker"]
    print(f"\n{'='*60}")
    print(f"Evaluating TC{tc['id'][-2:]}: {ticker} — {tc['description']}")
    print(f"{'='*60}")

    result = {
        "id":          tc["id"],
        "ticker":      ticker,
        "description": tc["description"],
        "timestamp":   datetime.now().isoformat(),
        "scores":      {},
        "passed":      False,
        "error":       None
    }

    try:
        # Run the full pipeline
        pipeline_result = run_pipeline(ticker)
        memo = pipeline_result.get("investment_memo", "")

        print(f"   ✅ Pipeline complete — memo: {len(memo)} chars")

        # Score 1: Structural completeness
        s1 = score_structural_completeness(memo, tc["expected_sections"])
        result["scores"]["structural_completeness"] = s1
        print(f"   📋 Structure:    {s1['score']:.0%} {'✅' if s1['pass'] else '❌'} "
              f"(missing: {s1['missing'] or 'none'})")

        # Score 2: Factual grounding
        s2 = score_factual_grounding(memo, tc["expected_facts"])
        result["scores"]["factual_grounding"] = s2
        print(f"   📊 Facts:        {s2['score']:.0%} {'✅' if s2['pass'] else '❌'} "
              f"(missing: {s2['missing'] or 'none'})")

        # Score 3: Hallucination guard
        s3 = score_hallucination_guard(memo, tc["should_not_contain"])
        result["scores"]["hallucination_guard"] = s3
        print(f"   🚫 Hallucination:{s3['score']:.0%} {'✅' if s3['pass'] else '❌'} "
              f"(violations: {s3['violations'] or 'none'})")

        # Score 4: Length adequacy
        s4 = score_length_adequacy(memo, tc["min_memo_length"])
        result["scores"]["length_adequacy"] = s4
        print(f"   📏 Length:       {s4['score']:.0%} {'✅' if s4['pass'] else '❌'} "
              f"({s4['length']} chars, min {s4['min_length']})")

        # Score 5: Valuation correctness
        s5 = score_valuation_correctness(pipeline_result, tc["expected_regime"])
        result["scores"]["valuation_correctness"] = s5
        print(f"   💰 Valuation:    {s5['score']:.0%} {'✅' if s5['pass'] else '❌'} "
              f"(regime: {s5.get('regime')}, verdict: {s5.get('verdict')})")

        # Score 6: Ragas (optional — costs API credits)
        if run_ragas:
            print(f"   🔍 Running Ragas scoring...")
            s6 = score_ragas(pipeline_result, ticker)
            result["scores"]["ragas"] = s6
            if s6.get("error"):
                print(f"   ⚠️  Ragas error: {s6['error']}")
            else:
                print(f"   🎯 Ragas:        faithfulness={s6['faithfulness']:.2f}, "
                      f"relevancy={s6['answer_relevancy']:.2f} "
                      f"{'✅' if s6['pass'] else '❌'}")

        # Overall pass: all non-ragas scores must pass
        core_passes = [s1["pass"], s2["pass"], s3["pass"], s4["pass"], s5["pass"]]
        result["passed"] = all(core_passes)
        result["memo_preview"] = memo[:300] + "..." if len(memo) > 300 else memo

        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"\n   {status}: {ticker}")

    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False
        print(f"   ❌ Pipeline error: {e}")

    return result


# ── Summary report ────────────────────────────────────────────────────────────

def print_summary(results: list):
    print(f"\n{'='*60}")
    print("EVALUATION SUMMARY")
    print(f"{'='*60}")

    total   = len(results)
    passed  = sum(1 for r in results if r["passed"])
    errored = sum(1 for r in results if r.get("error"))

    print(f"Total cases:  {total}")
    print(f"Passed:       {passed}/{total} ({passed/total:.0%})")
    print(f"Failed:       {total - passed - errored}/{total}")
    print(f"Errors:       {errored}/{total}")

    # Per-metric averages
    metrics = ["structural_completeness", "factual_grounding",
               "hallucination_guard", "length_adequacy", "valuation_correctness"]

    print(f"\nAverage scores per metric:")
    for metric in metrics:
        scores = [r["scores"][metric]["score"]
                  for r in results
                  if metric in r.get("scores", {})]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"  {metric:<30} {avg:.1%}")

    # Ragas averages (if run)
    ragas_results = [r["scores"]["ragas"] for r in results
                     if "ragas" in r.get("scores", {}) and not r["scores"]["ragas"].get("error")]
    if ragas_results:
        avg_faith   = sum(r["faithfulness"]     for r in ragas_results) / len(ragas_results)
        avg_rel     = sum(r["answer_relevancy"]  for r in ragas_results) / len(ragas_results)
        print(f"\nRagas scores (n={len(ragas_results)}):")
        print(f"  {'faithfulness':<30} {avg_faith:.1%}")
        print(f"  {'answer_relevancy':<30} {avg_rel:.1%}")

    # Per-case summary table
    print(f"\nPer-case results:")
    print(f"  {'ID':<6} {'Ticker':<8} {'Struct':<8} {'Facts':<8} {'Hallu':<8} {'Length':<8} {'Valua':<8} {'Result'}")
    print(f"  {'-'*70}")
    for r in results:
        s = r.get("scores", {})
        def fmt(key):
            if key not in s:
                return " N/A  "
            return f" {s[key]['score']:.0%}  " if s[key]["score"] is not None else " N/A  "
        status = "✅ PASS" if r["passed"] else ("💥 ERR " if r.get("error") else "❌ FAIL")
        print(f"  {r['id']:<6} {r['ticker']:<8}"
              f"{fmt('structural_completeness')}"
              f"{fmt('factual_grounding')}"
              f"{fmt('hallucination_guard')}"
              f"{fmt('length_adequacy')}"
              f"{fmt('valuation_correctness')}"
              f" {status}")


def save_results(results: list, output_dir: str = None):
    output_dir = output_dir or Path(__file__).parent / "results"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"eval_results_{timestamp}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {path}")
    return str(path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate the Financial Research Agent")
    parser.add_argument("--ticker",   type=str, help="Run a single ticker only (e.g. AAPL)")
    parser.add_argument("--no-ragas", action="store_true", help="Skip Ragas LLM scoring")
    parser.add_argument("--cases",    type=str, help="Path to custom test_cases.json")
    args = parser.parse_args()

    run_ragas = not args.no_ragas
    test_cases = load_test_cases(args.cases)

    # Filter to single ticker if specified
    if args.ticker:
        test_cases = [tc for tc in test_cases if tc["ticker"] == args.ticker.upper()]
        if not test_cases:
            print(f"No test case found for ticker: {args.ticker}")
            sys.exit(1)

    print(f"\n🧪 Financial Research Agent — Eval Harness")
    print(f"   Cases: {len(test_cases)}")
    print(f"   Ragas: {'enabled' if run_ragas else 'disabled (--no-ragas)'}")
    print(f"   Estimated cost: ~${len(test_cases) * 0.01:.2f} (Gemini API)\n")

    results = []
    for tc in test_cases:
        result = evaluate_case(tc, run_ragas=run_ragas)
        results.append(result)

    print_summary(results)
    save_results(results)

    # Exit with non-zero if any cases failed (useful for CI)
    passed = sum(1 for r in results if r["passed"])
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
