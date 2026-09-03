import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CreditCard,
  FileCheck,
  Landmark,
  Scale,
  ShoppingCart,
  ShieldAlert,
  Info,
  Bot,
  UserCheck,
} from "lucide-react";
import { api } from "../services/api";
import { Card } from "../components/common/Card";
import { DecisionBadge, PriorityBadge } from "../components/common/Badge";
import { formatINR } from "../components/common/FormatMoney";
import { ErrorState, LoadingState } from "../components/common/States";
import { InvestigationWorkflow } from "../components/investigation/InvestigationWorkflow";
import { AuditTrailTimeline } from "../components/audit/AuditTrailTimeline";
import { AIBoundaryPanel } from "../components/investigation/AIBoundaryPanel";
import type { CaseAuditTrail, CaseDetail, EvidenceResponse, InvestigationResponse } from "../types/api";

export const CaseDetailPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [evidenceData, setEvidenceData] = useState<EvidenceResponse | null>(null);
  const [existingInvestigation, setExistingInvestigation] = useState<InvestigationResponse | null>(null);
  const [auditTrail, setAuditTrail] = useState<CaseAuditTrail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showEvidenceRaw, setShowEvidenceRaw] = useState<boolean>(false);

  const loadCase = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const [cRes, evRes, auditRes] = await Promise.all([
        api.getCaseDetail(caseId),
        api.getCaseEvidence(caseId).catch(() => null),
        api.getAuditTrail(caseId).catch(() => null),
      ]);
      setCaseData(cRes);
      setEvidenceData(evRes);
      setAuditTrail(auditRes);

      // Check if investigation exists
      try {
        const invRes = await api.getInvestigation(caseId);
        setExistingInvestigation(invRes);
      } catch {
        setExistingInvestigation(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load case details";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCase();
  }, [caseId]);

  if (loading) return <LoadingState message="Loading case details & transaction chain..." />;
  if (error || !caseData) return <ErrorState message={error || "Case not found"} onRetry={loadCase} />;

  const tx = caseData.transaction_chain;

  // Discrepancy inspection
  const paymentUtr = tx?.payments?.[0]?.utr;
  const settlementUtr = tx?.settlements?.[0]?.utr;
  const isReferenceMismatch = caseData.exception_type === "REFERENCE_MISMATCH" && paymentUtr && settlementUtr;

  // Expected vs actual calculations
  const orderAmt = tx?.order?.amount ?? 0;
  const settlementAmt = tx?.settlements?.[0]?.net_amount ?? tx?.settlements?.[0]?.amount ?? 0;
  const varianceAmt = caseData.financial_impact;

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to="/cases"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Case Explorer
        </Link>

        {existingInvestigation && (
          <Link
            to={`/investigations/${caseData.case_id}`}
            className="text-xs text-sky-600 hover:underline font-medium"
          >
            Standalone Audit Page →
          </Link>
        )}
      </div>

      {/* Executive Case Summary Snapshot */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="font-mono font-bold text-lg text-slate-900">{caseData.case_id}</span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-mono text-slate-600">Order: {caseData.order_id}</span>
              <DecisionBadge decision={caseData.decision} />
              <PriorityBadge priority={caseData.priority} />
            </div>
            <div className="text-xs text-slate-500">
              Exception: <strong className="text-slate-800 font-semibold">{caseData.exception_type.replace(/_/g, " ")}</strong>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {caseData.decision === "AUTO_RESOLVE" && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-xs font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Auto-Resolved Deterministically
              </span>
            )}
            {caseData.decision === "AI_INVESTIGATION" && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded text-xs font-medium">
                <Bot className="w-3.5 h-3.5" /> Autonomous AI Investigation
              </span>
            )}
            {caseData.decision === "HUMAN_REVIEW" && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded text-xs font-medium">
                <UserCheck className="w-3.5 h-3.5" /> Operations Desk Review Required
              </span>
            )}
            {caseData.decision === "ESCALATE" && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-medium">
                <ShieldAlert className="w-3.5 h-3.5" /> Escalated to Dispute Desk
              </span>
            )}
          </div>
        </div>

        {/* Financial Exposure & Variance Matrix */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
            <span className="text-slate-500 text-[11px]">Expected Order Amount</span>
            <div className="font-bold text-slate-900 font-mono text-sm mt-0.5">
              {formatINR(orderAmt)}
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
            <span className="text-slate-500 text-[11px]">Settlement Payout / Amount</span>
            <div className="font-bold text-slate-900 font-mono text-sm mt-0.5">
              {settlementAmt > 0 ? formatINR(settlementAmt) : "Pending / None"}
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
            <span className="text-slate-500 text-[11px]">Identified Financial Variance</span>
            <div className={`font-bold font-mono text-sm mt-0.5 ${varianceAmt > 0 ? "text-rose-700" : "text-emerald-700"}`}>
              {formatINR(varianceAmt)}
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
            <span className="text-slate-500 text-[11px]">Control Action Status</span>
            <div className="font-bold text-slate-800 text-xs mt-0.5">
              {caseData.requires_human ? "Pending Human Action" : "System Governed"}
            </div>
          </div>
        </div>
      </div>

      {/* Discrepancy Callout for Reference Typo (Hero CASE-000921) */}
      {isReferenceMismatch && (
        <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-lg text-xs space-y-2">
          <div className="flex items-center gap-2 font-semibold text-amber-900">
            <Info className="w-4 h-4 text-amber-600" />
            <span>Discrepancy Pinpoint: UTR Reference Character Transposition Detected</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="p-2.5 bg-white border border-amber-200 rounded">
              <span className="text-slate-500 text-[11px]">Payment Gateway UTR:</span>
              <div className="font-mono font-bold text-slate-900 text-xs mt-0.5">{paymentUtr}</div>
            </div>
            <div className="p-2.5 bg-white border border-amber-200 rounded">
              <span className="text-slate-500 text-[11px]">Bank Settlement UTR:</span>
              <div className="font-mono font-bold text-slate-900 text-xs mt-0.5">{settlementUtr}</div>
            </div>
          </div>
          <p className="text-amber-800 text-[11px] leading-relaxed">
            Order amount and timestamps align exactly, but character transposition (<strong className="font-mono">...12</strong> vs <strong className="font-mono">...21</strong>) prevented exact 1:1 automated matching. Routed to AI Investigator for autonomous evidence corroboration.
          </p>
        </div>
      )}

      {/* Transaction Chain Section */}
      <Card
        title="Transaction Lifecycle Chain"
        subtitle="Multi-entity trace from checkout order through gateway capture, bank settlement, invoice, and adjustments"
      >
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
          {/* 1. ORDER */}
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800 pb-1.5 border-b border-slate-200">
              <span className="flex items-center gap-1.5">
                <ShoppingCart className="w-3.5 h-3.5 text-slate-500" /> ORDER
              </span>
              {tx?.order ? (
                <span className="text-[10px] text-emerald-600 font-mono font-medium">FOUND</span>
              ) : (
                <span className="text-[10px] text-slate-400 font-mono">ABSENT</span>
              )}
            </div>
            {tx?.order ? (
              <div className="space-y-1 text-xs">
                <div className="text-slate-500 text-[11px]">ID: <span className="font-mono text-slate-800">{tx.order.order_id}</span></div>
                <div className="text-slate-500 text-[11px]">Amount: <span className="font-mono font-semibold text-slate-900">{formatINR(tx.order.amount)}</span></div>
                <div className="text-slate-500 text-[11px]">Status: <span className="font-medium text-slate-700">{tx.order.status || "COMPLETED"}</span></div>
                <div className="text-slate-500 text-[11px]">Customer: <span className="font-mono text-slate-600">{tx.order.customer_id || "N/A"}</span></div>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">Not available in operational feed</p>
            )}
          </div>

          {/* 2. PAYMENT */}
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800 pb-1.5 border-b border-slate-200">
              <span className="flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5 text-slate-500" /> PAYMENT
              </span>
              {tx?.payments && tx.payments.length > 0 ? (
                <span className="text-[10px] text-emerald-600 font-mono font-medium">{tx.payments.length} RECORD</span>
              ) : (
                <span className="text-[10px] text-rose-500 font-mono font-medium">MISSING</span>
              )}
            </div>
            {tx?.payments && tx.payments.length > 0 ? (
              tx.payments.map((p) => (
                <div key={p.payment_id} className="space-y-1 text-xs">
                  <div className="text-slate-500 text-[11px]">ID: <span className="font-mono text-slate-800">{p.payment_id}</span></div>
                  <div className="text-slate-500 text-[11px]">Amount: <span className="font-mono font-semibold text-slate-900">{formatINR(p.amount)}</span></div>
                  {p.utr && <div className="text-slate-500 text-[11px]">UTR: <span className="font-mono text-slate-700">{p.utr}</span></div>}
                </div>
              ))
            ) : (
              <p className="text-xs text-rose-500 italic">No payment record found</p>
            )}
          </div>

          {/* 3. SETTLEMENT */}
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800 pb-1.5 border-b border-slate-200">
              <span className="flex items-center gap-1.5">
                <Landmark className="w-3.5 h-3.5 text-slate-500" /> SETTLEMENT
              </span>
              {tx?.settlements && tx.settlements.length > 0 ? (
                <span className="text-[10px] text-emerald-600 font-mono font-medium">{tx.settlements.length} RECORD</span>
              ) : (
                <span className="text-[10px] text-amber-500 font-mono font-medium">UNSETTLED</span>
              )}
            </div>
            {tx?.settlements && tx.settlements.length > 0 ? (
              tx.settlements.map((s) => (
                <div key={s.settlement_id} className="space-y-1 text-xs">
                  <div className="text-slate-500 text-[11px]">ID: <span className="font-mono text-slate-800">{s.settlement_id}</span></div>
                  <div className="text-slate-500 text-[11px]">Net: <span className="font-mono font-semibold text-slate-900">{formatINR(s.net_amount)}</span></div>
                  {s.utr && <div className="text-slate-500 text-[11px]">UTR: <span className="font-mono text-slate-700">{s.utr}</span></div>}
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 italic">No bank payout settlement linked</p>
            )}
          </div>

          {/* 4. INVOICE */}
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800 pb-1.5 border-b border-slate-200">
              <span className="flex items-center gap-1.5">
                <FileCheck className="w-3.5 h-3.5 text-slate-500" /> INVOICE
              </span>
              {tx?.invoice ? (
                <span className="text-[10px] text-emerald-600 font-mono font-medium">ISSUED</span>
              ) : (
                <span className="text-[10px] text-rose-500 font-mono font-medium">MISSING</span>
              )}
            </div>
            {tx?.invoice ? (
              <div className="space-y-1 text-xs">
                <div className="text-slate-500 text-[11px]">ID: <span className="font-mono text-slate-800">{tx.invoice.invoice_id}</span></div>
                <div className="text-slate-500 text-[11px]">Amount: <span className="font-mono font-semibold text-slate-900">{formatINR(tx.invoice.amount)}</span></div>
                <div className="text-slate-500 text-[11px]">Tax: <span className="font-mono text-slate-600">{formatINR(tx.invoice.tax_amount)}</span></div>
              </div>
            ) : (
              <p className="text-xs text-rose-500 italic">Invoice not yet issued / missing</p>
            )}
          </div>

          {/* 5. ADJUSTMENTS */}
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800 pb-1.5 border-b border-slate-200">
              <span className="flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-slate-500" /> ADJUSTMENTS
              </span>
              {tx?.adjustments && tx.adjustments.length > 0 ? (
                <span className="text-[10px] text-amber-600 font-mono font-medium">{tx.adjustments.length} RECORD</span>
              ) : (
                <span className="text-[10px] text-slate-400 font-mono">NONE</span>
              )}
            </div>
            {tx?.adjustments && tx.adjustments.length > 0 ? (
              tx.adjustments.map((a) => (
                <div key={a.adjustment_id} className="space-y-1 text-xs">
                  <div className="text-slate-500 text-[11px]">ID: <span className="font-mono text-slate-800">{a.adjustment_id}</span></div>
                  <div className="text-slate-500 text-[11px]">Type: <span className="font-medium text-amber-700">{a.type}</span></div>
                  <div className="text-slate-500 text-[11px]">Amount: <span className="font-mono font-semibold text-slate-900">{formatINR(a.amount)}</span></div>
                  {a.reason && <div className="text-slate-500 text-[11px]">Reason: <span className="text-slate-600">{a.reason}</span></div>}
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 italic">No disputes, refunds, or fee adjustments</p>
            )}
          </div>
        </div>
      </Card>

      {/* AI Boundary & Permissions Panel */}
      <AIBoundaryPanel />

      {/* AI Investigation Workflow (If AI_INVESTIGATION case or already investigated) */}
      {(caseData.decision === "AI_INVESTIGATION" || existingInvestigation) && (
        <InvestigationWorkflow
          caseData={caseData}
          existingInvestigation={existingInvestigation}
          onInvestigationComplete={(res) => {
            setExistingInvestigation(res);
            if (caseId) {
              api.getAuditTrail(caseId).then(setAuditTrail).catch(() => null);
            }
          }}
        />
      )}

      {/* Audit Trail & Financial Control Evidence Timeline */}
      <AuditTrailTimeline events={auditTrail?.events || []} />

      {/* Policy Rationale & Explanation Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Deterministic Policy Routing Rationale">
          <div className="space-y-3.5 text-xs">
            <div>
              <span className="text-slate-500 font-medium">Routing Determination:</span>
              <p className="text-slate-800 font-medium mt-0.5">{caseData.reason || "Deterministic match verified."}</p>
            </div>
            <div>
              <span className="text-slate-500 font-medium">Detailed Explanation:</span>
              <p className="text-slate-700 bg-slate-50 border border-slate-200 rounded p-2.5 mt-0.5 leading-relaxed">
                {caseData.explanation}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="p-2.5 bg-slate-50 border border-slate-100 rounded">
                <span className="text-[11px] text-slate-500">Matching Strategy:</span>
                <div className="font-mono font-semibold text-slate-800">{caseData.match_method}</div>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-100 rounded">
                <span className="text-[11px] text-slate-500">Match Confidence:</span>
                <div className="font-mono font-semibold text-slate-800">{(caseData.match_confidence * 100).toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </Card>

        <Card title="Recommended Operational Next Action">
          <div className="space-y-4 text-xs">
            <div>
              <span className="text-slate-500 font-medium">Standard Operating Procedure:</span>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded mt-1 font-medium text-slate-800 leading-relaxed">
                {caseData.next_action}
              </div>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Requires AI Investigation:</span>
                <span className="font-semibold">{caseData.requires_ai ? "Yes" : "No"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Requires Human Review:</span>
                <span className="font-semibold">{caseData.requires_human ? "Yes" : "No"}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Deterministic Evidence Drawer */}
      {evidenceData && (
        <Card
          title="Deterministic Match Evidence"
          subtitle="Exact corroboration parameters from ReconciliationEngine"
          headerAction={
            <button
              type="button"
              onClick={() => setShowEvidenceRaw(!showEvidenceRaw)}
              className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 font-medium cursor-pointer"
            >
              {showEvidenceRaw ? "Hide Evidence Details" : "Show Evidence Details"}
              {showEvidenceRaw ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          }
        >
          {showEvidenceRaw && (
            <div className="space-y-3">
              <pre className="p-3 bg-slate-900 text-slate-100 rounded text-xs font-mono overflow-x-auto max-h-80">
                {JSON.stringify(evidenceData.evidence, null, 2)}
              </pre>
            </div>
          )}
          {!showEvidenceRaw && (
            <p className="text-xs text-slate-500">
              Match status: <strong className="text-slate-700">{evidenceData.match_status}</strong> via{" "}
              <strong className="text-slate-700">{evidenceData.match_method}</strong> ({evidenceData.explanation})
            </p>
          )}
        </Card>
      )}
    </div>
  );
};
