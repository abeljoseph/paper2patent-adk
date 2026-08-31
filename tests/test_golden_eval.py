"""Golden Dataset Regression Test Suite for Agent Assessor Benchmarks."""

import pytest
from src.eval.benchmark import GoldenDatasetEvaluator


def test_golden_dataset_regression():
    evaluator = GoldenDatasetEvaluator(dataset_path="tests/golden_dataset/golden_papers.json")
    summary = evaluator.run_benchmark()

    assert summary.total_test_cases >= 3
    assert summary.domain_classification_accuracy >= 0.99
    assert summary.claim_count_compliance_rate >= 0.99
    assert summary.fto_range_compliance_rate >= 0.99
    assert summary.overall_pass_rate >= 0.99
