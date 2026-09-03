import React, { useState } from "react";
import {
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileSearch,
  Lock,
  RefreshCw,
  Terminal,
  AlertCircle,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { api } from "../../services/api";
import type { CaseDetail, InvestigationResponse } from "../../types/api";

interface InvestigationWorkflowProps {
  caseData: CaseDetail;
  existingInvestigation: InvestigationResponse | null;
  onInvestigationComplete: (result: InvestigationResponse) => void;
}

export const InvestigationWorkflow: React.FC<InvestigationWorkflowProps> = ({
  caseData,
  existingInvestigation,
  onInvestigationComplete,
}) => {
  const [provider, setProvider] = useState<string>("demo_replay");
  const [status, setStatus] = useState<"idle" | "investigating" | "completed" | "failed">(
    existingInvestigation ? "completed" : "idle"
  );
  const [result, setResult] = useState<InvestigationResponse | null>(existingInvestigation);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [expandedToolIndex, setExpandedToolIndex] = useState<number | null>(null);

  const handleRunInvestigation = async () => {
    setStatus("investigating");
    setErrorMessage(null);
    try {
      const res = await api.investigateCase(caseData.case_id, provider);
      setResult(res);
      const isOk = res.investigation_status === "COMPLETED";
      setStatus(isOk ? "completed" : "failed");
      onInvestigationComplete(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Investigation failed to execute.";
      setErrorMessage(msg);
      setStatus("failed");
    }
  };

  const getProviderBadge = (p: string) => {
    switch (p.toLowerCase()) {
      case "demo_replay":
      case "replay":
        return (
          <span className="px-2 py-0.5 bg-sky-100 text-sky-800 rounded font-mono font-semibold text-[10px] border border-sky-200">
            DEMO REPLAY (PRE-RECORDED)
          </span>
        );
      case "gemini":
        return (
          <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded font-mono font-semibold text-[10px] border border-purple-200">
            LIVE GEMINI (GENAI SDK)
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono font-semibold text-[10px] border border-slate-200">
            MOCK PROVIDER (OFFLINE)
          </span>
        );
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-indigo-100 text-indigo-700 flex items-center justify-center">
            <Bot className="w-4 h-4 text-indigo-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">AI Investigator Workflow</h3>
            <p className="text-xs text-slate-500">Autonomous read-only evidence corroboration & root-cause analysis</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 border border-slate-200 rounded text-[11px] font-medium text-slate-600">
          <Lock className="w-3 h-3 text-indigo-600" />
          <span>Strictly Read-Only (0 Write Tools)</span>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* STATE 1: IDLE / READY */}
        {status === "idle" && (
          <div className="space-y-4">
            <div className="p-4 bg-sky-50/40 border border-sky-100 rounded-md space-y-2 text-xs">
              <div className="font-semibold text-sky-900 flex items-center gap-1.5">
                <FileSearch className="w-4 h-4 text-sky-600" />
                Case Eligible for AI Investigation
              </div>
              <p className="text-slate-700 leading-relaxed">
                Deterministic policy routed <strong className="font-mono">{caseData.case_id}</strong> to AI investigation because{" "}
                {caseData.reason.toLowerCase() || "a manageable reference or amount discrepancy was detected"}. The investigator will autonomously inspect orders, payments, settlements, invoices, and adjustments.
              </p>
            </div>

            {/* Provider Selection Bar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 bg-slate-50 border border-slate-200 rounded-md text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                <span className="text-slate-700 font-semibold">Select Provider:</span>
                <div className="flex flex-wrap items-center gap-1 bg-white border border-slate-200 rounded p-0.5">
                  <button
                    type="button"
                    onClick={() => setProvider("demo_replay")}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                      provider === "demo_replay"
                        ? "bg-slate-900 text-white shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Demo Replay (Judge Walkthrough)
                  </button>
                  <button
                    type="button"
                    onClick={() => setProvider("mock")}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                      provider === "mock"
                        ? "bg-slate-900 text-white shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Mock Provider (Offline Eval)
                  </button>
                  <button
                    type="button"
                    onClick={() => setProvider("gemini")}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                      provider === "gemini"
                        ? "bg-slate-900 text-white shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Live Gemini (Subject to Quotas)
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={handleRunInvestigation}
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-medium transition-colors shadow-xs cursor-pointer shrink-0"
              >
                <Zap className="w-3.5 h-3.5" />
                Run AI Investigation
              </button>
            </div>
          </div>
        )}

        {/* STATE 2: INVESTIGATING */}
        {status === "investigating" && (
          <div className="p-8 flex flex-col items-center justify-center text-center space-y-3 bg-slate-50/50 border border-slate-100 rounded-md">
            <RefreshCw className="w-7 h-7 text-indigo-600 animate-spin" />
            <div>
              <h4 className="text-sm font-semibold text-slate-900">Executing Read-Only AI Investigation...</h4>
              <p className="text-xs text-slate-500 mt-1 max-w-md">
                Querying operational tables via read-only tools and evaluating entity linkages across gateway payments and bank settlements.
              </p>
            </div>
            <div className="text-[11px] text-slate-400 font-mono">Provider: {provider}</div>
          </div>
        )}

        {/* STATE 3: COMPLETED */}
        {status === "completed" && result && (
          <div className="space-y-5">
            {/* Finding Card */}
            <div className="p-4 bg-emerald-50/30 border border-emerald-200 rounded-md space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-emerald-100 text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="font-semibold text-emerald-900 text-sm">
                    {result.finding.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {getProviderBadge(result.provider_used)}
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-mono font-semibold text-xs">
                    Confidence: {(result.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Root Cause Text */}
              <div className="text-xs space-y-1">
                <span className="text-slate-500 font-medium">Corroborated Root Cause:</span>
                <div className="p-3 bg-white border border-slate-200 rounded text-slate-800 leading-relaxed whitespace-pre-line font-sans">
                  {result.root_cause}
                </div>
              </div>

              {/* Supporting Entity Linkages */}
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <span className="text-slate-500 font-medium">Supporting Entities:</span>
                {result.supporting_payment_ids?.map((pid) => (
                  <span key={pid} className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-[11px] font-mono">
                    {pid}
                  </span>
                ))}
                {result.supporting_settlement_ids?.map((sid) => (
                  <span key={sid} className="px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded text-[11px] font-mono">
                    {sid}
                  </span>
                ))}
                {result.supporting_invoice_id && (
                  <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[11px] font-mono">
                    {result.supporting_invoice_id}
                  </span>
                )}
              </div>

              {/* Advisory Recommendation */}
              <div className="pt-2 border-t border-emerald-100/60 text-xs">
                <span className="text-slate-500 font-medium">Advisory Next Step:</span>
                <p className="mt-0.5 text-slate-800 font-medium leading-relaxed">
                  {result.recommendation}
                </p>
              </div>
            </div>

            {/* Read-Only Safety Banner */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-600">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>
                  <strong>Safety Status:</strong> Ready for human review. No financial records were altered.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setStatus("idle")}
                className="text-sky-600 hover:text-sky-800 font-medium cursor-pointer underline text-[11px]"
              >
                Re-run / Switch Provider
              </button>
            </div>

            {/* Tool Trace Audit Trail */}
            {result.tool_trace && result.tool_trace.length > 0 && (
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                  <span className="flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-slate-500" />
                    Tool Execution Trace ({result.tool_trace.length} operational steps executed)
                  </span>
                </div>

                <div className="space-y-2">
                  {result.tool_trace.map((step, idx) => {
                    const isExpanded = expandedToolIndex === idx;
                    return (
                      <div
                        key={idx}
                        className="border border-slate-200 rounded bg-white hover:border-slate-300 transition-colors"
                      >
                        <div
                          onClick={() => setExpandedToolIndex(isExpanded ? null : idx)}
                          className="p-2.5 bg-slate-50/70 flex items-center justify-between cursor-pointer select-none text-xs"
                        >
                          <div className="flex items-center gap-2.5">
                            <span className="w-5 h-5 rounded bg-slate-200 text-slate-700 flex items-center justify-center font-mono font-bold text-[10px]">
                              {String(idx + 1).padStart(2, "0")}
                            </span>
                            <span className="font-mono font-medium text-slate-900">{step.tool_name}</span>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-emerald-600 font-medium flex items-center gap-0.5">
                              <CheckCircle2 className="w-2.5 h-2.5" /> executed
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                            )}
                          </div>
                        </div>

                        {isExpanded && (
                          <div className="p-3 border-t border-slate-100 bg-white space-y-2 text-xs">
                            <div>
                              <div className="text-[10px] text-slate-500 font-medium mb-0.5">Arguments:</div>
                              <pre className="p-2 bg-slate-900 text-slate-100 rounded text-[10px] font-mono overflow-x-auto">
                                {JSON.stringify(step.arguments, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div className="text-[10px] text-slate-500 font-medium mb-0.5">Result Payload:</div>
                              <pre className="p-2 bg-slate-900 text-slate-100 rounded text-[10px] font-mono overflow-x-auto max-h-48">
                                {JSON.stringify(step.result_summary, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* STATE 4: FAILED / SAFE HUMAN ESCALATION */}
        {status === "failed" && (
          <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-md space-y-3 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-amber-200 text-amber-900 font-semibold">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                <span>AI Inconclusive / Provider Failure $\rightarrow$ Safe Human Review Escalated</span>
              </div>
              <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-mono text-[10px] uppercase">
                {result?.investigation_status || "PROVIDER_ERROR"}
              </span>
            </div>

            <div className="space-y-1 text-amber-800">
              <div className="font-medium text-slate-800">Failure Explanation:</div>
              <p className="leading-relaxed bg-white border border-amber-200 rounded p-2.5">
                {errorMessage || result?.failure_reason || result?.root_cause || "Provider returned an error or rate limit. The financial case remains strictly under human operations control."}
              </p>
            </div>

            <div className="p-2.5 bg-emerald-50/60 border border-emerald-200 rounded text-emerald-900 text-[11px] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                <strong>Safety Invariant Preserved:</strong> AI failure did NOT alter or auto-resolve the financial decision. Zero financial writes occurred.
              </span>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-amber-200 text-amber-900">
              <span>Control Desk: <strong>OPERATIONS_DESK</strong></span>
              <button
                type="button"
                onClick={() => {
                  setProvider("demo_replay");
                  setStatus("idle");
                }}
                className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-medium cursor-pointer"
              >
                Switch to Demo Replay
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
