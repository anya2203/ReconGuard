"""Deterministic Policy Engine for ReconGuard.

Applies explainable business rules to Master Reconciliation Engine match results.
Maps each match result to a definitive business decision (AUTO_RESOLVE, AI_INVESTIGATION,
HUMAN_REVIEW, ESCALATE), assigns priority risk tiers, and generates auditable explanations.
Operates exclusively on operational evidence with zero ground-truth leakage.
"""

from typing import Any

from app.matching.types import MatchMethod, MatchResult, MatchStatus
from app.policy.types import CasePriority, ExceptionCase, ExceptionType, PolicyDecision


class PolicyEngine:
    """Deterministic policy engine evaluating reconciliation match results into actionable cases."""

    def __init__(
        self,
        high_impact_threshold: float = 5000.0,
        medium_impact_threshold: float = 1000.0,
    ):
        self.high_impact_threshold = high_impact_threshold
        self.medium_impact_threshold = medium_impact_threshold

    def evaluate(self, match_result: MatchResult) -> ExceptionCase:
        """Evaluate a single match result against deterministic policy rules."""
        evidence_dict = (
            match_result.evidence.to_dict()
            if hasattr(match_result.evidence, "to_dict")
            else (match_result.evidence or {})
        )
        failed_checks = evidence_dict.get("failed_checks", [])
        reason_lower = (match_result.reason or "").lower()

        # 1. Clean Exact 1:1 Match -> AUTO_RESOLVE
        if (
            match_result.status == MatchStatus.MATCHED
            and match_result.match_method == MatchMethod.EXACT
        ):
            decision = PolicyDecision.AUTO_RESOLVE
            exception_type = ExceptionType.NONE
            priority = CasePriority.LOW
            requires_ai = False
            requires_human = False
            explanation = (
                "Order, payment, settlement, and invoice verified with 100% exact "
                "1:1 field congruence within SLA. Eligible for straight-through auto-resolution."
            )
            next_action = "Straight-through reconciliation complete; close case."

        # 2. Multi-Order Aggregation Match -> AUTO_RESOLVE
        elif (
            match_result.status == MatchStatus.MATCHED
            and match_result.match_method == MatchMethod.AGGREGATION
        ):
            decision = PolicyDecision.AUTO_RESOLVE
            exception_type = ExceptionType.NONE
            priority = CasePriority.LOW
            requires_ai = False
            requires_human = False
            explanation = (
                f"Order successfully reconciled as part of multi-order settlement "
                f"batch with verified gross amount and fee invariant."
            )
            next_action = "Batch payout reconciliation verified; close case."

        # 3. Fuzzy Matched Cases -> AI_INVESTIGATION (Micro-variances)
        elif (
            match_result.status == MatchStatus.MATCHED
            and match_result.match_method == MatchMethod.FUZZY
        ):
            ref_sim = evidence_dict.get("reference_similarity", 1.0)
            amt_diff = evidence_dict.get("amount_difference", 0.0)

            if ref_sim < 1.0:
                decision = PolicyDecision.AI_INVESTIGATION
                exception_type = ExceptionType.REFERENCE_MISMATCH
                priority = CasePriority.MEDIUM
                requires_ai = True
                requires_human = False
                explanation = (
                    f"Candidate matched with reference similarity {ref_sim:.2f}; "
                    f"UTR/reference contains character transposition or typo. "
                    f"Requires AI investigation to corroborate counterparty context."
                )
                next_action = (
                    "Route to AI Investigator for multi-field contextual verification "
                    "of reference typo and automated ledger linking."
                )
            else:
                decision = PolicyDecision.AI_INVESTIGATION
                exception_type = ExceptionType.ROUNDING_VARIANCE
                priority = CasePriority.LOW if amt_diff < 1.0 else CasePriority.MEDIUM
                requires_ai = True
                requires_human = False
                explanation = (
                    f"High-confidence match with micro-amount variance of "
                    f"INR {amt_diff:.2f} (itemized GST/paisa rounding). "
                    f"Requires AI investigation to justify variance and post rounding adjustment."
                )
                next_action = (
                    "Route to AI Investigator for itemized GST rounding variance "
                    "root-cause analysis and automated adjustment booking."
                )

        # 4. Missing Invoice with Corroborated Payment & Settlement -> AI_INVESTIGATION
        elif "invoice_exists" in failed_checks or (
            match_result.status == MatchStatus.DISCREPANCY
            and "invoice record is missing" in reason_lower
        ):
            decision = PolicyDecision.AI_INVESTIGATION
            exception_type = ExceptionType.MISSING_INVOICE
            priority = CasePriority.MEDIUM
            requires_ai = True
            requires_human = False
            explanation = (
                "Payment and bank settlement corroborated successfully, but tax invoice "
                "is missing from billing feed. Requires AI verification to schedule invoice backfill."
            )
            next_action = (
                "Route to AI Investigator to verify payment/settlement corroboration "
                "and trigger invoice backfill workflow."
            )

        # 5. Ambiguous Candidates (Duplicate Payments / Retries) -> HUMAN_REVIEW or ESCALATE
        elif match_result.status == MatchStatus.AMBIGUOUS:
            if "multi-order batch payout" in reason_lower:
                decision = PolicyDecision.ESCALATE
                exception_type = ExceptionType.MISSING_SETTLEMENT
                priority = CasePriority.HIGH
                requires_ai = False
                requires_human = True
                explanation = (
                    "Payment UTR collided with multi-order batch settlement, but order "
                    "was excluded from batch aggregation. Bank payout is missing."
                )
                next_action = "Escalate to bank operations for missing bank payout resolution."
            else:
                decision = PolicyDecision.HUMAN_REVIEW
                exception_type = ExceptionType.AMBIGUOUS_CANDIDATE
                priority = CasePriority.HIGH
                requires_ai = False
                requires_human = True
                explanation = (
                    f"Multiple ({len(match_result.payment_ids)}) candidate payments detected "
                    f"for single order (customer retry ambiguity). Manual ops verification required."
                )
                next_action = (
                    "Escalate to operations desk to review candidate payments, "
                    "confirm valid capture, and initiate duplicate refund if necessary."
                )

        # 6. Insufficient Evidence / Abandoned Checkout -> HUMAN_REVIEW
        elif "order_completed_status" in failed_checks or "abandoned" in reason_lower:
            decision = PolicyDecision.HUMAN_REVIEW
            exception_type = ExceptionType.INSUFFICIENT_EVIDENCE
            priority = (
                CasePriority.HIGH
                if match_result.financial_impact >= self.high_impact_threshold
                else CasePriority.MEDIUM
            )
            requires_ai = False
            requires_human = True
            explanation = (
                "Order record is incomplete/abandoned with unlinked debit activity. "
                "Insufficient metadata for automated resolution."
            )
            next_action = "Route to operations to verify abandoned order status against merchant logs."

        # 7. Active Adjustments (Chargebacks & Refunds) -> ESCALATE
        elif "no_adjustments_present" in failed_checks or "adjustment" in reason_lower:
            if "chargeback" in reason_lower:
                decision = PolicyDecision.ESCALATE
                exception_type = ExceptionType.CHARGEBACK
                priority = CasePriority.HIGH
                requires_ai = False
                requires_human = True
                explanation = (
                    f"Active chargeback dispute logged (INR {match_result.financial_impact:.2f}). "
                    f"Requires dispute management and representment workflow."
                )
                next_action = "Escalate to dispute desk for chargeback defense and liability management."
            elif "refund" in reason_lower:
                decision = PolicyDecision.ESCALATE
                exception_type = ExceptionType.REFUND
                priority = CasePriority.HIGH
                requires_ai = False
                requires_human = True
                explanation = (
                    f"Active refund debit logged (INR {match_result.financial_impact:.2f}). "
                    f"Requires merchant fund debit verification."
                )
                next_action = "Escalate to merchant operations to verify customer refund debit."
            else:
                decision = PolicyDecision.ESCALATE
                exception_type = ExceptionType.UNCLASSIFIED_DISCREPANCY
                priority = CasePriority.HIGH
                requires_ai = False
                requires_human = True
                explanation = "Unclassified adjustment logged against transaction."
                next_action = "Escalate to finance operations for ledger review."

        # 8. Amount Mismatch -> ESCALATE
        elif "payment_amount_match" in failed_checks or "amount mismatch" in reason_lower:
            decision = PolicyDecision.ESCALATE
            exception_type = ExceptionType.AMOUNT_MISMATCH
            priority = CasePriority.HIGH
            requires_ai = False
            requires_human = True
            explanation = (
                f"Significant monetary discrepancy between order and captured payment "
                f"(Impact: INR {match_result.financial_impact:.2f})."
            )
            next_action = "Escalate to finance operations to investigate transaction pricing mismatch."

        # 9. SLA Breach / Delayed Settlement -> ESCALATE
        elif "settlement_sla_policy" in failed_checks or "sla" in reason_lower:
            decision = PolicyDecision.ESCALATE
            exception_type = ExceptionType.SLA_BREACH
            priority = CasePriority.HIGH
            requires_ai = False
            requires_human = True
            explanation = (
                "Settlement exceeded contractual SLA turnaround time (>5 days). "
                "Bank payout delayed."
            )
            next_action = "Escalate to banking operations for delayed settlement investigation."

        # 10. Missing Payment -> ESCALATE
        elif (
            "payment_exists" in failed_checks
            or "no captured payment" in reason_lower
            or len(match_result.payment_ids) == 0
        ):
            decision = PolicyDecision.ESCALATE
            exception_type = ExceptionType.MISSING_PAYMENT
            priority = CasePriority.HIGH
            requires_ai = False
            requires_human = True
            explanation = (
                f"Fulfilled order with zero captured gateway payment "
                f"(Exposure: INR {match_result.financial_impact:.2f}). Possible dropped webhook."
            )
            next_action = "Escalate to gateway operations to verify uncaptured transaction."

        # 11. Missing Settlement -> ESCALATE
        elif "no bank settlement" in reason_lower or "settlement_exists" in failed_checks:
            decision = PolicyDecision.ESCALATE
            exception_type = ExceptionType.MISSING_SETTLEMENT
            priority = CasePriority.HIGH
            requires_ai = False
            requires_human = True
            explanation = (
                f"Captured payment has no corresponding bank payout record "
                f"(Exposure: INR {match_result.financial_impact:.2f})."
            )
            next_action = "Escalate to bank operations for missing bank payout resolution."

        # 12. Fallback Safe Escalation
        else:
            decision = PolicyDecision.ESCALATE
            exception_type = ExceptionType.UNCLASSIFIED_DISCREPANCY
            priority = CasePriority.HIGH
            requires_ai = False
            requires_human = True
            explanation = f"Unresolved reconciliation status: {match_result.status.value}. {match_result.reason}"
            next_action = "Escalate to operations for manual review."

        case_id = f"CASE-{match_result.order_id.replace('ORD-', '')}"

        return ExceptionCase(
            case_id=case_id,
            order_id=match_result.order_id,
            decision=decision,
            exception_type=exception_type,
            priority=priority,
            financial_impact=match_result.financial_impact,
            payment_ids=list(match_result.payment_ids),
            settlement_ids=list(match_result.settlement_ids),
            invoice_id=match_result.invoice_id,
            adjustment_ids=list(match_result.adjustment_ids),
            match_method=match_result.match_method.value,
            match_confidence=match_result.confidence,
            evidence=evidence_dict,
            reason=match_result.reason,
            explanation=explanation,
            next_action=next_action,
            requires_ai=requires_ai,
            requires_human=requires_human,
        )

    def evaluate_all(self, match_results: list[MatchResult]) -> list[ExceptionCase]:
        """Evaluate a list of match results in deterministic order."""
        return [self.evaluate(r) for r in match_results]

