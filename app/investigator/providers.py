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
                    f"Order '{order_id}' amount ({order_res.get('amount')}) and settlement "
                    f"amount ({settlement_res.get('amount')}) differ by <= ₹0.50 due to standard rounding."
                ),
                evidence={
                    "order_amount": order_res.get("amount"),
                    "payment_amount": payment_res.get("amount"),
                    "settlement_amount": settlement_res.get("amount"),
                    "variance": abs((order_res.get("amount") or 0) - (settlement_res.get("amount") or 0)),
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

        # 2. Reference Mismatch / Typo Case (Hero Case)
        elif ext == "REFERENCE_MISMATCH":
            pay_utr = payment_res.get("utr")
            set_utr = settlement_res.get("utr")
            return InvestigationResult(
                case_id=context.case_id,
                order_id=order_id,
                finding=FindingTaxonomy.VERIFIED_REFERENCE_TYPO,
                root_cause=(
                    f"Payment UTR '{pay_utr}' and Settlement UTR '{set_utr}' exhibit "
                    f"character transposition / typo in gateway record, but exact amounts "
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
            confidence=0.0,
            recommendation="Evidence is inconclusive. Recommend escalation to operations desk for manual investigation. No financial action was taken by the investigator.",
            requires_human_review=True,
            investigation_status=InvestigationStatus.INCONCLUSIVE,
            error_category="INCONCLUSIVE",
            failure_reason="Operational evidence is insufficient to determine root cause.",
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
            investigation_status=InvestigationStatus.ITERATION_LIMIT,
            error_category="ITERATION_LIMIT",
            failure_reason="Maximum investigation tool execution iterations exceeded.",
            tool_trace=tool_trace,
            provider_used=self.provider_name,
        )


class DemoReplayProvider(LLMProvider):
    """Pre-recorded deterministic replay provider for buildathon judge demonstration.

    Explicitly labeled as DEMO REPLAY so it is never confused with a live Gemini model response.
    """

    @property
    def provider_name(self) -> str:
        return "demo_replay"

    def investigate(
        self,
        context: InvestigationContext,
        tools: InvestigationToolRegistry,
        max_iterations: int = 6,
    ) -> InvestigationResult:
        """Execute deterministic replay investigation clearly labeled as demonstration."""
        mock = MockProvider()
        result = mock.investigate(context, tools, max_iterations=max_iterations)
        result.provider_used = self.provider_name
        return result


class GeminiProvider(LLMProvider):
    """Real Gemini LLM provider using Google GenAI SDK with structured function calling."""

    _ALLOWED_FINDINGS = [
        FindingTaxonomy.VERIFIED_ROUNDING_VARIANCE.value,
        FindingTaxonomy.VERIFIED_REFERENCE_TYPO.value,
        FindingTaxonomy.MISSING_INVOICE_CONFIRMED.value,
        FindingTaxonomy.INCONCLUSIVE.value,
    ]

    _DEFAULT_MODEL_NAME = "gemini-2.5-flash"

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = (
            model_name
            or os.environ.get("GEMINI_MODEL_NAME")
            or self._DEFAULT_MODEL_NAME
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        """Check if Gemini credentials are configured."""
        return bool(self.api_key)

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """Remove a leading/trailing markdown code fence if the model added one anyway."""
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:]
        return stripped.strip()

    def _safe_fallback_result(
        self,
        context: InvestigationContext,
        tool_trace: list[ToolCallRecord],
        root_cause: str,
        raw_text_excerpt: str = "",
        status: InvestigationStatus = InvestigationStatus.INCONCLUSIVE,
        error_category: str | None = None,
    ) -> InvestigationResult:
        """Build the deterministic, non-guessing fallback used whenever Gemini's
        output cannot be safely parsed as structured JSON. Never infers a financial
        finding from partial/unparseable text."""
        evidence: dict[str, Any] = {"tool_calls_executed": len(tool_trace)}
        if raw_text_excerpt:
            evidence["unparsed_raw_response_excerpt"] = raw_text_excerpt[:500]
        return InvestigationResult(
            case_id=context.case_id,
            order_id=context.order_id,
            finding=FindingTaxonomy.INCONCLUSIVE,
            root_cause=root_cause,
            evidence=evidence,
            confidence=0.0,
            recommendation=(
                "Recommend escalation to human operations review; AI investigator could not "
                "produce a validated structured finding. No financial action was taken by the investigator."
            ),
            requires_human_review=True,
            investigation_status=status,
            error_category=error_category or status.value,
            failure_reason=root_cause,
            tool_trace=tool_trace,
            provider_used=self.provider_name,
        )

    def investigate(
        self,
        context: InvestigationContext,
        tools: InvestigationToolRegistry,
        max_iterations: int = 6,
    ) -> InvestigationResult:
        """Execute real Gemini tool-calling investigation loop with graceful fallback."""
        tool_trace: list[ToolCallRecord] = []

        if not self.is_available:
            return self._safe_fallback_result(
                context, tool_trace,
                root_cause="GeminiProvider is not available: GEMINI_API_KEY environment variable is not configured.",
                status=InvestigationStatus.CONFIGURATION_ERROR,
                error_category="CONFIGURATION_ERROR",
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return self._safe_fallback_result(
                context, tool_trace,
                root_cause="google-genai SDK is not installed in the environment.",
                status=InvestigationStatus.CONFIGURATION_ERROR,
                error_category="CONFIGURATION_ERROR",
            )

        system_instruction = (
            "You are ReconGuard AI Investigator, an expert financial reconciliation agent. "
            "Your role is strictly READ-ONLY. You investigate financial reconciliation discrepancy cases "
            "using available tools to lookup orders, payments, settlements, invoices, and adjustments. "
            "You must corroborate complete evidence chains before reaching a conclusion. "
            "You must never attempt write operations, never take financial actions, and never claim "
            "that you created, booked, refunded, modified, or closed anything. "
            "All recommendations must explicitly state that no financial action was taken by the investigator."
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
            f"Please lookup relevant records and corroborate the evidence chain using the available tools."
        )

        try:
            client = genai.Client(api_key=self.api_key)
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
            iteration_count = 0
            for _ in range(max_iterations):
                iteration_count += 1
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

            if response.function_calls and len(tool_trace) >= max_iterations:
                return self._safe_fallback_result(
                    context, tool_trace,
                    root_cause="Gemini investigation exceeded maximum allowed tool iterations without resolving.",
                    status=InvestigationStatus.ITERATION_LIMIT,
                    error_category="ITERATION_LIMIT",
                )

            # Finalization phase: force genuine schema-validated JSON output
            response_schema = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "finding": types.Schema(
                        type=types.Type.STRING,
                        enum=self._ALLOWED_FINDINGS,
                    ),
                    "root_cause": types.Schema(type=types.Type.STRING),
                    "evidence_summary": types.Schema(type=types.Type.STRING),
                    "confidence": types.Schema(type=types.Type.NUMBER),
                    "recommendation": types.Schema(type=types.Type.STRING),
                    "requires_human_review": types.Schema(type=types.Type.BOOLEAN),
                },
                required=[
                    "finding",
                    "root_cause",
                    "confidence",
                    "recommendation",
                    "requires_human_review",
                ],
            )

            finalize_prompt = (
                "Based only on the evidence you gathered via tool calls above, produce your final "
                "structured finding now. Respond with a single JSON object matching the required schema. "
                "'finding' must be one of the allowed enum values. 'confidence' must be a number between "
                "0.0 and 1.0 reflecting your actual certainty given the evidence, not a placeholder. "
                "'requires_human_review' must be true unless the evidence chain is fully corroborated. "
                "'recommendation' must explicitly state that no financial action was taken by the investigator. "
                "If the evidence is insufficient or contradictory, set finding to INCONCLUSIVE, confidence to "
                "a low value, and requires_human_review to true — do not guess."
            )

            final_response = chat.send_message(
                finalize_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_final_text = self._strip_code_fence(final_response.text or "")

            if not raw_final_text:
                return self._safe_fallback_result(
                    context, tool_trace,
                    root_cause="Gemini returned an empty final response; no structured finding could be extracted.",
                    status=InvestigationStatus.MALFORMED_RESPONSE,
                    error_category="MALFORMED_RESPONSE",
                )

            try:
                parsed = json.loads(raw_final_text)
            except json.JSONDecodeError:
                return self._safe_fallback_result(
                    context, tool_trace,
                    root_cause="Gemini's final response was not valid JSON; falling back to a safe inconclusive result rather than guessing.",
                    raw_text_excerpt=raw_final_text,
                    status=InvestigationStatus.MALFORMED_RESPONSE,
                    error_category="MALFORMED_RESPONSE",
                )

            if not isinstance(parsed, dict) or "finding" not in parsed:
                return self._safe_fallback_result(
                    context, tool_trace,
                    root_cause="Gemini's final JSON response was missing required fields; falling back to a safe inconclusive result.",
                    raw_text_excerpt=raw_final_text,
                    status=InvestigationStatus.MALFORMED_RESPONSE,
                    error_category="MALFORMED_RESPONSE",
                )

            finding_str = str(parsed.get("finding", "")).strip().upper()
            try:
                finding = FindingTaxonomy(finding_str)
                if finding.value not in self._ALLOWED_FINDINGS:
                    raise ValueError(f"'{finding_str}' is not an allowed model-produced finding.")
            except ValueError:
                return self._safe_fallback_result(
                    context, tool_trace,
                    root_cause=f"Gemini returned an unrecognized finding label ('{finding_str}'); falling back to a safe inconclusive result.",
                    raw_text_excerpt=raw_final_text,
                    status=InvestigationStatus.MALFORMED_RESPONSE,
                    error_category="MALFORMED_RESPONSE",
                )

            try:
                confidence = float(parsed.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))

            requires_human_review = bool(parsed.get("requires_human_review", True))

            root_cause = str(parsed.get("root_cause") or "").strip()
            if not root_cause:
                root_cause = "Gemini investigation completed but did not provide a root cause narrative."

            recommendation = str(parsed.get("recommendation") or "").strip()
            if "no financial action was taken" not in recommendation.lower():
                recommendation = (
                    (recommendation + " " if recommendation else "")
                    + "No financial action was taken by the investigator."
                ).strip()

            evidence = {
                "evidence_summary": str(parsed.get("evidence_summary") or ""),
                "structured_response": parsed,
            }

            return InvestigationResult(
                case_id=context.case_id,
                order_id=context.order_id,
                finding=finding,
                root_cause=root_cause,
                evidence=evidence,
                confidence=confidence,
                recommendation=recommendation,
                requires_human_review=requires_human_review,
                supporting_payment_ids=context.payment_ids,
                supporting_settlement_ids=context.settlement_ids,
                supporting_invoice_id=context.invoice_id,
                investigation_status=InvestigationStatus.COMPLETED,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )
        except Exception as e:
            err_msg = str(e)
            err_lower = err_msg.lower()
            if "429" in err_msg or "resource_exhausted" in err_lower or "quota" in err_lower or "rate limit" in err_lower:
                status = InvestigationStatus.RATE_LIMITED
                category = "RATE_LIMITED"
                root_cause = f"Gemini provider rate limit reached (HTTP 429 / Resource Exhausted): {err_msg[:200]}"
            elif "timeout" in err_lower or "timed out" in err_lower:
                status = InvestigationStatus.TIMEOUT
                category = "TIMEOUT"
                root_cause = f"Gemini provider connection timed out: {err_msg[:200]}"
            elif "api_key" in err_lower or "credential" in err_lower or "unauthorized" in err_lower or "401" in err_msg or "403" in err_msg:
                status = InvestigationStatus.CONFIGURATION_ERROR
                category = "CONFIGURATION_ERROR"
                root_cause = "Gemini provider authentication/configuration error."
            else:
                status = InvestigationStatus.PROVIDER_ERROR
                category = "PROVIDER_ERROR"
                root_cause = f"Gemini provider error: {err_msg[:200]}"

            return InvestigationResult(
                case_id=context.case_id,
                order_id=context.order_id,
                finding=FindingTaxonomy.INCONCLUSIVE,
                root_cause=root_cause,
                evidence={"error_category": category, "error_detail": err_msg[:500]},
                confidence=0.0,
                recommendation="Recommend escalation to human operations review due to provider error. No financial action was taken by the investigator.",
                requires_human_review=True,
                investigation_status=status,
                error_category=category,
                failure_reason=root_cause,
                tool_trace=tool_trace,
                provider_used=self.provider_name,
            )
