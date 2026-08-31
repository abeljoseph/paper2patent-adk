"""Golden Dataset Evaluation & Benchmark Harness for Paper2Patent ADK Agent."""

import json
import os
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from src.agents.coordinator import Paper2PatentCoordinator


class EvaluationMetricSummary(BaseModel):
    """Aggregate benchmark results across golden evaluation dataset."""
    total_test_cases: int
    passed_cases: int
    domain_classification_accuracy: float
    claim_count_compliance_rate: float
    fto_range_compliance_rate: float
    statutory_verdict_match_rate: float
    overall_pass_rate: float
    case_results: List[Dict[str, Any]] = Field(default_factory=list)


class GoldenDatasetEvaluator:
    """Benchmark runner evaluating agent outputs against ground-truth golden dataset."""

    def __init__(self, dataset_path: str = "tests/golden_dataset/golden_papers.json"):
        self.dataset_path = dataset_path
        self.coordinator = Paper2PatentCoordinator()

    def run_benchmark(self) -> EvaluationMetricSummary:
        """Run full evaluation suite across all golden benchmark papers."""
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Golden dataset not found at {self.dataset_path}")

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

        case_results = []
        domain_matches = 0
        claim_matches = 0
        fto_matches = 0
        verdict_matches = 0

        for case in cases:
            res = self.coordinator.run_pipeline(paper_text=case["raw_text"])

            # 1. Domain Match
            dom_ok = res.domain == case["domain_expected"]
            if dom_ok:
                domain_matches += 1

            # 2. Claim Count Compliance
            claims_ok = res.total_claims_drafted >= case["min_claims_expected"]
            if claims_ok:
                claim_matches += 1

            # 3. FTO Range Compliance
            fto_ok = case["expected_fto_min"] <= res.fto_score <= case["expected_fto_max"]
            if fto_ok:
                fto_matches += 1

            # 4. Statutory Verdict Match
            verdict_ok = res.verdict in case["expected_statutory_verdict"]
            if verdict_ok:
                verdict_matches += 1

            case_passed = all([dom_ok, claims_ok, fto_ok, verdict_ok])

            case_results.append({
                "case_id": case["id"],
                "passed": case_passed,
                "domain_match": dom_ok,
                "claim_count_match": claims_ok,
                "fto_range_match": fto_ok,
                "verdict_match": verdict_ok,
                "fto_score": res.fto_score,
                "total_claims": res.total_claims_drafted,
            })

        total = len(cases)
        passed_count = sum(1 for c in case_results if c["passed"])

        return EvaluationMetricSummary(
            total_test_cases=total,
            passed_cases=passed_count,
            domain_classification_accuracy=round(domain_matches / total, 4),
            claim_count_compliance_rate=round(claim_matches / total, 4),
            fto_range_compliance_rate=round(fto_matches / total, 4),
            statutory_verdict_match_rate=round(verdict_matches / total, 4),
            overall_pass_rate=round(passed_count / total, 4),
            case_results=case_results,
        )


if __name__ == "__main__":
    evaluator = GoldenDatasetEvaluator()
    summary = evaluator.run_benchmark()
    print(json.dumps(summary.model_dump(), indent=2))
