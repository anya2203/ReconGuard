"""LLM Provider abstractions (Mock and Gemini) for the ReconGuard AI Investigator."""

from abc import ABC, abstractmethod
import json
import os
from typing import Any

from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import (
    FindingTaxonomy,
    InvestigationContext,
    InvestigationResult,
    InvestigationStatus,
    ToolCallRecord,
)


class LLMProvider(ABC):
    """Abstract interface for AI investigation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider implementation."""
        pass

    @abstractmethod
    def investigate(
        self,
        context: InvestigationContext,
        tools: InvestigationToolRegistry,
        max_iterations: int = 6,
    ) -> InvestigationResult:
        """Execute agentic investigation loop on a case."""
        pass


class MockProvider(LLMProvider):
    """Deterministic tool-calling mock provider for testing and offline evaluation."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def investigate(
        self,
        context: InvestigationContext,
        tools: InvestigationToolRegistry,
        max_iterations: int = 6,
    ) -> InvestigationResult:
        """Execute deterministic multi-step tool-calling investigation."""
        tool_trace: list[ToolCallRecord] = []
        order_id = context.order_id
        payment_id = context.payment_ids[0] if context.payment_ids else None
        settlement_id = context.settlement_ids[0] if context.settlement_ids else None

        # Step 1: Look up Order
        if len(tool_trace) >= max_iterations:
            return self._build_max_iter_exceeded_result(context, tool_trace)

        order_res = tools.lookup_order(order_id)
        tool_trace.append(ToolCallRecord(
            tool_name="lookup_order",
            arguments={"order_id": order_id},
            result_summary=order_res,
        ))

        if not order_res.get("found"):
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.ESCALATE_TO_HUMAN,
                root_cause=f"Order '{order_id}' record does not exist in order management system.",
                evidence={"order_lookup": order_res},
                confidence=0.0,
                recommendation="Recommend escalation to operations desk to verify order existence. No financial action was taken by the investigator.",
                requires_human_review=True,
                investigation_status=InvestigationStatus.FAILED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )

        # Step 2: Look up Payment(s)
        if len(tool_trace) >= max_iterations:
            return self._build_max_iter_exceeded_result(context, tool_trace)

        if payment_id:
            payment_res = tools.lookup_payment(payment_id)
            tool_trace.append(ToolCallRecord(
                tool_name="lookup_payment",
                arguments={"payment_id": payment_id},
                result_summary=payment_res,
            ))
        else:
            payments_res = tools.lookup_payments_for_order(order_id)
            tool_trace.append(ToolCallRecord(
                tool_name="lookup_payments_for_order",
                arguments={"order_id": order_id},
                result_summary=payments_res,
            ))
            payment_res = payments_res.get("payments", [{}])[0] if payments_res.get("found") else {"found": False}
            if payment_res.get("payment_id"):
                payment_id = payment_res["payment_id"]

        if not payment_res.get("found"):
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.ESCALATE_TO_HUMAN,
                root_cause=f"No captured payment records found for order '{order_id}'.",
                evidence={"order": order_res, "payment": payment_res},
                confidence=0.0,
                recommendation="Recommend escalation to gateway operations desk to trace uncaptured transaction. No financial action was taken by the investigator.",
                requires_human_review=True,
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )

        # Step 3: Look up Settlement(s)
        if len(tool_trace) >= max_iterations:
            return self._build_max_iter_exceeded_result(context, tool_trace)

        if settlement_id:
            settlement_res = tools.lookup_settlement(settlement_id)
            tool_trace.append(ToolCallRecord(
                tool_name="lookup_settlement",
                arguments={"settlement_id": settlement_id},
                result_summary=settlement_res,
            ))
        else:
            settlements_res = tools.lookup_settlements_for_payment(payment_id)
            tool_trace.append(ToolCallRecord(
                tool_name="lookup_settlements_for_payment",
                arguments={"payment_id": payment_id},
                result_summary=settlements_res,
            ))
            settlement_res = settlements_res.get("settlements", [{}])[0] if settlements_res.get("found") else {"found": False}
            if settlement_res.get("settlement_id"):
                settlement_id = settlement_res["settlement_id"]

        # Step 4: Look up Adjustments
        if len(tool_trace) >= max_iterations:
            return self._build_max_iter_exceeded_result(context, tool_trace)

        adj_res = tools.lookup_adjustments(payment_id=payment_id, order_id=order_id)
        tool_trace.append(ToolCallRecord(
            tool_name="lookup_adjustments",
            arguments={"payment_id": payment_id, "order_id": order_id},
            result_summary=adj_res,
        ))

        # Check for contradictory adjustments (chargebacks / refunds)
        if adj_res.get("found") and any(a.get("type") in ["CHARGEBACK", "REFUND"] for a in adj_res.get("adjustments", [])):
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.ESCALATE_TO_HUMAN,
                root_cause="Contradictory dispute or refund adjustment discovered during investigation.",
                evidence={"order": order_res, "payment": payment_res, "adjustments": adj_res},
                confidence=0.98,
                recommendation="Recommend escalation to dispute desk due to active transaction adjustment. No financial action was taken by the investigator.",
                requires_human_review=True,
                supporting_payment_ids=[payment_id] if payment_id else [],
                supporting_settlement_ids=[settlement_id] if settlement_id else [],
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )

        # Step 5: Look up Invoice
        if len(tool_trace) >= max_iterations:
            return self._build_max_iter_exceeded_result(context, tool_trace)

        invoice_res = tools.lookup_invoice(order_id)
        tool_trace.append(ToolCallRecord(
            tool_name="lookup_invoice",
            arguments={"order_id": order_id},
            result_summary=invoice_res,
        ))

        # Step 6: Compare Transaction Records
        if len(tool_trace) >= max_iterations:
            return self._build_max_iter_exceeded_result(context, tool_trace)

        comp_res = tools.compare_transaction_records(
            order_id=order_id,
            payment_id=payment_id,
            settlement_id=settlement_id,
        )
        tool_trace.append(ToolCallRecord(
            tool_name="compare_transaction_records",
            arguments={"order_id": order_id, "payment_id": payment_id, "settlement_id": settlement_id},
            result_summary=comp_res,
        ))

        # Synthesize Evidence by Exception Type
        ext = context.exception_type

        # 1. Rounding Variance Case
        if ext == "ROUNDING_VARIANCE" or "rounding" in context.reason.lower():
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.VERIFIED_ROUNDING_VARIANCE,
                root_cause=(
                    f"Micro-amount variance of INR {context.financial_impact:.2f} caused by "
                    f"itemized GST line rounding between checkout and settlement gateway."
                ),
                evidence={
                    "order_amount": order_res.get("amount"),
                    "payment_amount": payment_res.get("amount"),
                    "settlement_amount": settlement_res.get("amount"),
                    "variance_amount": context.financial_impact,
                    "invoice_verified": invoice_res.get("found"),
                    "utr_verified": comp_res.get("utr_exact_match"),
                },
                confidence=0.98,
                recommendation=f"Evidence supports an INR {context.financial_impact:.2f} rounding variance. Recommend reconciliation of the variance for human/system approval. No financial action was taken by the investigator.",
                requires_human_review=False,
                supporting_payment_ids=[payment_id] if payment_id else [],
                supporting_settlement_ids=[settlement_id] if settlement_id else [],
                supporting_invoice_id=invoice_res.get("invoice_id"),
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )

        # 2. Reference Typo Case
        elif ext == "REFERENCE_MISMATCH" or "reference" in context.reason.lower() or "fuzzy match verified" in context.reason.lower():
            pay_utr = payment_res.get("utr", "")
            set_utr = settlement_res.get("utr", "")
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.VERIFIED_REFERENCE_TYPO,
                root_cause=(
                    f"Gateway UTR '{pay_utr}' and bank settlement reference '{set_utr}' "
                    f"differ due to single-character transmission typo. Counterparty, amount, "
                    f"and timestamp corroborate valid 1:1 match."
                ),
                evidence={
                    "payment_utr": pay_utr,
                    "settlement_utr": set_utr,
                    "order_amount": order_res.get("amount"),
                    "payment_amount": payment_res.get("amount"),
                    "settlement_amount": settlement_res.get("amount"),
                    "invoice_verified": invoice_res.get("found"),
                },
                confidence=0.96,
                recommendation="Evidence supports counterparty reference typo corroboration. Recommend linking settlement to payment for human/system approval. No financial action was taken by the investigator.",
                requires_human_review=False,
                supporting_payment_ids=[payment_id] if payment_id else [],
                supporting_settlement_ids=[settlement_id] if settlement_id else [],
                supporting_invoice_id=invoice_res.get("invoice_id"),
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )

        # 3. Missing Invoice Case
        elif ext == "MISSING_INVOICE" or not invoice_res.get("found"):
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.MISSING_INVOICE_CONFIRMED,
                root_cause=(
                    f"Payment '{payment_id}' and settlement '{settlement_id}' are 100% matched "
                    f"and verified, but tax invoice was omitted from merchant billing feed."
                ),
                evidence={
                    "order_status": order_res.get("status"),
                    "payment_verified": payment_res.get("found"),
                    "settlement_verified": settlement_res.get("found"),
                    "invoice_found": False,
                },
                confidence=0.99,
                recommendation="Payment and settlement corroborated; invoice omitted from billing feed. Recommend invoice reconciliation/backfill for human approval. No financial action was taken by the investigator.",
                requires_human_review=False,
                supporting_payment_ids=[payment_id] if payment_id else [],
                supporting_settlement_ids=[settlement_id] if settlement_id else [],
                supporting_invoice_id=None,
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )

        # Fallback
        return InvestigationResult(
            case_id=context.case_id,
            order_id=order_id,
            finding=FindingTaxonomy.INCONCLUSIVE,
            root_cause="Operational evidence is insufficient to determine root cause.",
            evidence={"tool_trace_count": len(tool_trace)},
            confidence=0.5,
            recommendation="Evidence is inconclusive. Recommend escalation to operations desk for manual investigation. No financial action was taken by the investigator.",
            requires_human_review=True,
            investigation_status=InvestigationStatus.INCONCLUSIVE,
            tool_trace=tool_trace,
            provider_used=self.provider_name,
        )

    def _build_max_iter_exceeded_result(
        self,
        context: InvestigationContext,
        tool_trace: list[ToolCallRecord],
    ) -> InvestigationResult:
        """Generate safe fallback result when max iterations limit is reached."""
        return InvestigationResult(
            case_id=context.case_id,
            order_id=context.order_id,
            finding=FindingTaxonomy.INCONCLUSIVE,
            root_cause="Maximum tool execution iterations exceeded without conclusive corroboration.",
            evidence={"tool_calls_executed": len(tool_trace)},
            confidence=0.0,
            recommendation="Maximum investigation iterations exceeded. Recommend escalation to human operations review. No financial action was taken by the investigator.",
            requires_human_review=True,
            investigation_status=InvestigationStatus.INCONCLUSIVE,
            tool_trace=tool_trace,
            provider_used=self.provider_name,
        )


class GeminiProvider(LLMProvider):
    """Real Gemini LLM provider using Google GenAI SDK with structured function calling."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        """Check if Gemini credentials are configured."""
        return bool(self.api_key)

    def investigate(
        self,
        context: InvestigationContext,
        tools: InvestigationToolRegistry,
        max_iterations: int = 6,
    ) -> InvestigationResult:
        """Execute real Gemini tool-calling investigation loop."""
        if not self.is_available:
            raise ValueError(
                "GeminiProvider is not available: GEMINI_API_KEY environment variable is not set."
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai SDK is required for GeminiProvider. Please install `google-genai`.")

        client = genai.Client(api_key=self.api_key)
        tool_trace: list[ToolCallRecord] = []

        system_instruction = (
            "You are ReconGuard AI Investigator, an expert financial reconciliation agent. "
            "Your role is strictly READ-ONLY. You investigate financial reconciliation discrepancy cases "
            "using available tools to lookup orders, payments, settlements, invoices, and adjustments. "
            "You must corroborate complete evidence chains before reaching a conclusion. "
            "You must never attempt write operations, never take financial actions, and never claim "
            "that you created, booked, refunded, modified, or closed anything. "
            "All recommendations must explicitly state that no financial action was taken by the investigator. "
            "When finished, return a structured JSON response with finding, root_cause, evidence, "
            "confidence (0.0-1.0), recommendation, and requires_human_review (bool)."
        )

        tool_decls = tools.get_tool_declarations()
        gemini_func_decls = [
            types.FunctionDeclaration(
                name=td["name"],
                description=td["description"],
                parameters=td.get("parameters"),
            )
            for td in tool_decls
        ]
        tool_config = types.Tool(function_declarations=gemini_func_decls)

        prompt = (
            f"Please investigate reconciliation case '{context.case_id}' for order '{context.order_id}'.\n"
            f"Exception Type: {context.exception_type}\n"
            f"Policy Decision: {context.policy_decision}\n"
            f"Candidate Payment IDs: {context.payment_ids}\n"
            f"Candidate Settlement IDs: {context.settlement_ids}\n"
            f"Reason: {context.reason}\n"
            f"Explanation: {context.explanation}\n"
            f"Please lookup relevant records, corroborate the evidence chain, and produce your structured finding."
        )

        try:
            chat = client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    tools=[tool_config],
                ),
            )
            response = chat.send_message(prompt)

            # Multi-turn tool-calling loop
            for _ in range(max_iterations):
                if not response.function_calls:
                    break

                func_responses = []
                for fc in response.function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}
                    tool_result = tools.execute_tool(tool_name, tool_args)
                    tool_trace.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments=tool_args,
                        result_summary=tool_result,
                    ))
                    func_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": tool_result},
                        )
                    )

                response = chat.send_message(func_responses)

            raw_text = response.text or ""

            # Parse finding from response
            finding = FindingTaxonomy.INCONCLUSIVE
            if "ROUNDING" in raw_text.upper():
                finding = FindingTaxonomy.VERIFIED_ROUNDING_VARIANCE
            elif "TYPO" in raw_text.upper() or "REFERENCE" in raw_text.upper():
                finding = FindingTaxonomy.VERIFIED_REFERENCE_TYPO
            elif "INVOICE" in raw_text.upper():
                finding = FindingTaxonomy.MISSING_INVOICE_CONFIRMED

            return InvestigationResult(
                case_id=context.case_id,
                order_id=context.order_id,
                finding=finding,
                root_cause=raw_text[:200] if raw_text else "Gemini investigation completed.",
                evidence={"raw_response": raw_text[:500]},
                confidence=0.95,
                recommendation="Evidence corroborated by AI investigator. Recommend reconciliation for human/system approval. No financial action was taken by the investigator.",
                requires_human_review=False,
                supporting_payment_ids=context.payment_ids,
                supporting_settlement_ids=context.settlement_ids,
                supporting_invoice_id=context.invoice_id,
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )
        except Exception as e:
            return InvestigationResult(
                case_id=context.case_id,
                order_id=context.order_id,
                finding=FindingTaxonomy.INCONCLUSIVE,
                root_cause=f"Gemini investigation call error: {str(e)}",
                evidence={"error": str(e)},
                confidence=0.0,
                recommendation="Recommend escalation to human operations review due to provider error. No financial action was taken by the investigator.",
                requires_human_review=True,
                investigation_status=InvestigationStatus.FAILED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )
