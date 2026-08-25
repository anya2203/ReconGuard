"""ReconGuard Evaluation Module.

Provides evaluation harness and benchmarking against ground truth datasets.
Maintains strict isolation from production matching components.
"""

from app.evaluation.evaluator import ReconciliationEvaluator

__all__ = ["ReconciliationEvaluator"]

