"""Tests for ReconGuard Synthetic Data Generator and Ground Truth Dataset.

Verifies:
- Deterministic generation & seed reproducibility
- Ground-truth ID format (GT-XXXXXX) & uniqueness
- Ground-truth referential join to business identifiers (order_id)
- Ground-truth explicit linked payment/settlement IDs
- Relational integrity across orders, payments, settlements, invoices, adjustments
- Target distribution (78% deterministic resolution, 12% deterministic escalation, 10% AI investigation)
- AI split (AI-resolvable vs AI-escalation)
- Multi-order settlement batching
- Refund scenario generation & adjustment records
- Fixed anchor timestamp rules
- Dataset validation logic and failure detection
"""

import csv
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.data_generator import (
    DEFAULT_ANCHOR_DATETIME,
    DEFAULT_SEED,
    DEFAULT_TOTAL_CASES,
    ExpectedOutcome,
    ReconciliationDataGenerator,
    ResolutionClass,
    ScenarioType,
    validate_dataset,
)


@pytest.fixture
def generator() -> ReconciliationDataGenerator:
    """Fixture returning a fresh generator instance with default settings."""
    gen = ReconciliationDataGenerator(
        seed=DEFAULT_SEED,
        total_cases=DEFAULT_TOTAL_CASES,
        anchor_datetime=DEFAULT_ANCHOR_DATETIME,
    )
    gen.generate_all()
    return gen


def test_deterministic_generation_same_seed():
    """Verify that running the generator twice with the same seed produces identical data."""
    gen1 = ReconciliationDataGenerator(seed=42, total_cases=1000)
    gen1.generate_all()

    gen2 = ReconciliationDataGenerator(seed=42, total_cases=1000)
    gen2.generate_all()

    # Compare orders
    assert len(gen1.orders) == len(gen2.orders)
    for o1, o2 in zip(gen1.orders, gen2.orders):
        assert o1 == o2

    # Compare payments
    assert len(gen1.payments) == len(gen2.payments)
    for p1, p2 in zip(gen1.payments, gen2.payments):
        assert p1 == p2

    # Compare settlements
    assert len(gen1.settlements) == len(gen2.settlements)
    for s1, s2 in zip(gen1.settlements, gen2.settlements):
        assert s1 == s2

    # Compare adjustments
    assert len(gen1.adjustments) == len(gen2.adjustments)
    for a1, a2 in zip(gen1.adjustments, gen2.adjustments):
        assert a1 == a2

    # Compare ground truth
    assert len(gen1.ground_truth) == len(gen2.ground_truth)
    for gt1, gt2 in zip(gen1.ground_truth, gen2.ground_truth):
        assert gt1 == gt2


def test_ground_truth_id_format_and_uniqueness(generator: ReconciliationDataGenerator):
    """Verify GT IDs follow GT-000001 to GT-001000 format and are strictly unique."""
    gt_list = generator.ground_truth
    assert len(gt_list) == DEFAULT_TOTAL_CASES

    seen_ids = set()
    for idx, gt in enumerate(gt_list, start=1):
        expected_id = f"GT-{idx:06d}"
        assert gt.ground_truth_id == expected_id
        assert gt.ground_truth_id not in seen_ids
        seen_ids.add(gt.ground_truth_id)


def test_ground_truth_joins_to_order_id(generator: ReconciliationDataGenerator):
    """Verify ground truth joins cleanly to order_id business identifiers."""
    order_ids = {o.order_id for o in generator.orders}
    assert len(order_ids) == DEFAULT_TOTAL_CASES

    for gt in generator.ground_truth:
        assert gt.order_id in order_ids, f"GT case {gt.ground_truth_id} has invalid order_id {gt.order_id}"


def test_ground_truth_linked_ids_integrity(generator: ReconciliationDataGenerator):
    """Verify ground truth contains valid explicit linked payment and settlement IDs."""
    payment_ids = {p.payment_id for p in generator.payments}
    settle_ids = {s.settlement_id for s in generator.settlements}

    for gt in generator.ground_truth:
        # All linked payment IDs must exist in payments
        for pid in gt.linked_payment_ids:
            assert pid in payment_ids, f"GT {gt.ground_truth_id} has invalid linked payment {pid}"

        # All linked settlement IDs must exist in settlements
        for sid in gt.linked_settlement_ids:
            assert sid in settle_ids, f"GT {gt.ground_truth_id} has invalid linked settlement {sid}"


def test_foreign_key_referential_integrity(generator: ReconciliationDataGenerator):
    """Verify that all child tables reference valid order IDs in the parent orders table."""
    order_ids = {o.order_id for o in generator.orders}

    # Payments
    for p in generator.payments:
        assert p.order_id in order_ids, f"Payment {p.payment_id} references invalid order {p.order_id}"

    # Invoices
    for inv in generator.invoices:
        assert inv.order_id in order_ids, f"Invoice {inv.invoice_id} references invalid order {inv.order_id}"


def test_refund_scenario_and_adjustments(generator: ReconciliationDataGenerator):
    """Verify that REFUND scenario is generated with proper operational and ground truth records."""
    summary = generator.get_summary()
    assert summary["scenario_counts"].get(ScenarioType.REFUND.value) == 24

    refund_gts = [gt for gt in generator.ground_truth if gt.expected_scenario == ScenarioType.REFUND.value]
    assert len(refund_gts) == 24

    # Verify refund adjustments exist
    refund_adjs = [adj for adj in generator.adjustments if adj.type == "REFUND"]
    assert len(refund_adjs) == 24

    payment_ids = {p.payment_id for p in generator.payments}
    for adj in refund_adjs:
        assert adj.amount < 0.0  # Must be negative amount representing refund
        assert adj.related_id in payment_ids  # Must reference valid payment
        assert "refund" in (adj.reason or "").lower()

    for gt in refund_gts:
        assert gt.expected_outcome == ExpectedOutcome.ADJUSTED.value
        assert gt.expected_resolution_class == ResolutionClass.DETERMINISTIC_ESCALATION.value
        assert gt.expected_human_escalation is True
        assert gt.expected_ai_investigation is False
        assert len(gt.linked_payment_ids) == 1
        assert len(gt.linked_settlement_ids) == 1


def test_target_distribution_and_percentages(generator: ReconciliationDataGenerator):
    """Verify exact 78% / 12% / 10% distribution across resolution classes."""
    summary = generator.get_summary()
    dist = summary["distribution"]

    det_res = dist["deterministic_resolution"]
    det_esc = dist["deterministic_escalation"]
    ai_inv = dist["ai_investigation"]

    # Exact case counts
    assert det_res["count"] == 780
    assert det_esc["count"] == 120
    assert ai_inv["count"] == 100

    # Percentages
    assert det_res["percentage"] == 78.0
    assert det_esc["percentage"] == 12.0
    assert ai_inv["percentage"] == 10.0
    assert summary["total_cases"] == 1000


def test_ai_investigation_sub_split(generator: ReconciliationDataGenerator):
    """Verify AI investigation cases include both AI-resolvable and AI-escalation cases."""
    summary = generator.get_summary()
    ai_dist = summary["distribution"]["ai_investigation"]

    ai_resolvable = ai_dist["ai_resolvable"]
    ai_escalation = ai_dist["ai_escalation"]

    # Both categories must exist with 50 cases each (5% each)
    assert ai_resolvable["count"] == 50
    assert ai_resolvable["percentage"] == 5.0

    assert ai_escalation["count"] == 50
    assert ai_escalation["percentage"] == 5.0

    # Detailed ground truth check
    for gt in generator.ground_truth:
        if gt.expected_resolution_class == ResolutionClass.AI_INVESTIGATION.value:
            assert gt.expected_ai_investigation is True
            # Resolvable cases must not require human escalation
            if gt.expected_scenario in [
                ScenarioType.ROUNDING_MISMATCH.value,
                ScenarioType.REFERENCE_TYPO.value,
                ScenarioType.MISSING_INVOICE.value,
            ]:
                assert gt.expected_human_escalation is False
            # Escalation cases must require human escalation
            elif gt.expected_scenario in [
                ScenarioType.AMBIGUOUS_CANDIDATE.value,
                ScenarioType.INSUFFICIENT_EVIDENCE.value,
                ScenarioType.MISSING_SETTLEMENT.value,
            ]:
                assert gt.expected_human_escalation is True


def test_all_13_scenarios_covered(generator: ReconciliationDataGenerator):
    """Verify all 13 defined scenarios are generated with correct case counts."""
    counts = generator.get_summary()["scenario_counts"]

    expected_counts = {
        ScenarioType.EXACT_MATCH.value: 720,
        ScenarioType.MULTI_ORDER_SETTLEMENT.value: 60,
        ScenarioType.AMOUNT_MISMATCH.value: 24,
        ScenarioType.DELAYED_SETTLEMENT.value: 24,
        ScenarioType.MISSING_PAYMENT.value: 24,
        ScenarioType.CHARGEBACK_ADJUSTMENT.value: 24,
        ScenarioType.REFUND.value: 24,
        ScenarioType.ROUNDING_MISMATCH.value: 20,
        ScenarioType.REFERENCE_TYPO.value: 20,
        ScenarioType.MISSING_INVOICE.value: 10,
        ScenarioType.AMBIGUOUS_CANDIDATE.value: 20,
        ScenarioType.INSUFFICIENT_EVIDENCE.value: 20,
        ScenarioType.MISSING_SETTLEMENT.value: 10,
    }

    assert len(counts) == 13
    for scenario_name, expected_count in expected_counts.items():
        assert counts.get(scenario_name) == expected_count, (
            f"Scenario {scenario_name} count {counts.get(scenario_name)} != {expected_count}"
        )


def test_multi_order_settlement_batching(generator: ReconciliationDataGenerator):
    """Verify multi-order settlement batches accurately aggregate multiple payments."""
    batch_settlements = [s for s in generator.settlements if "BATCH" in s.settlement_id]
    assert len(batch_settlements) == 20  # 20 batches of 3 = 60 orders

    for bs in batch_settlements:
        # Find all payments sharing this settlement UTR
        matching_payments = [p for p in generator.payments if p.utr == bs.utr]
        assert len(matching_payments) == 3

        total_pay_amount = sum(p.amount for p in matching_payments)
        expected_fees = sum(round(p.amount * 0.02, 2) for p in matching_payments)
        expected_net_settlement = round(total_pay_amount - expected_fees, 2)

        assert bs.amount == expected_net_settlement
        assert bs.fees == round(expected_fees, 2)


def test_ambiguous_candidate_multiple_linked_payments(generator: ReconciliationDataGenerator):
    """Verify ambiguous candidate cases link to multiple candidate payments in ground truth."""
    ambig_gts = [gt for gt in generator.ground_truth if gt.expected_scenario == ScenarioType.AMBIGUOUS_CANDIDATE.value]
    assert len(ambig_gts) == 20

    for gt in ambig_gts:
        assert len(gt.linked_payment_ids) == 2, f"Expected 2 candidate payments in GT {gt.ground_truth_id}"
        assert len(gt.linked_settlement_ids) == 1


def test_fixed_anchor_timestamps(generator: ReconciliationDataGenerator):
    """Verify all timestamps derive deterministically from the fixed anchor datetime."""
    anchor_iso = DEFAULT_ANCHOR_DATETIME.isoformat()

    for o in generator.orders:
        assert o.created_at >= anchor_iso
        dt = datetime.fromisoformat(o.created_at)
        assert dt.year == 2026
        assert dt.month == 8

    for p in generator.payments:
        assert p.created_at >= anchor_iso
        dt = datetime.fromisoformat(p.created_at)
        assert dt.year == 2026
        assert dt.month == 8


def test_validation_function_success_and_failure(tmp_path: Path):
    """Verify that validate_dataset returns True on valid data and False on corrupted data."""
    # 1. Generate clean dataset into temporary directory
    gen = ReconciliationDataGenerator(seed=42, total_cases=1000)
    gen.generate_all()
    gen.save_to_disk(tmp_path)

    is_valid, errors = validate_dataset(tmp_path)
    assert is_valid is True
    assert len(errors) == 0

    # 2. Corrupt one file (remove orders.csv) and verify validation failure
    orders_file = tmp_path / "generated" / "orders.csv"
    orders_file.unlink()

    is_valid_corrupt, errors_corrupt = validate_dataset(tmp_path)
    assert is_valid_corrupt is False
    assert any("Missing required file" in e for e in errors_corrupt)


def test_cli_execution_and_validate_flag():
    """Verify CLI execution for generation and validation."""
    # Validate CLI
    res_val = subprocess.run(
        [sys.executable, "-m", "app.services.data_generator", "--validate"],
        capture_output=True,
        text=True,
    )
    assert res_val.returncode == 0
    assert "Validation SUCCESSFUL" in res_val.stdout
