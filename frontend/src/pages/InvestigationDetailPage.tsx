import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Lock,
  Terminal,
} from "lucide-react";
import { api } from "../services/api";
import type { InvestigationResponse } from "../types/api";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { ErrorState, LoadingState } from "../components/common/States";

export const InvestigationDetailPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<InvestigationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedToolIndex, setExpandedToolIndex] = useState<number | null>(null);

  const loadData = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getInvestigation(caseId);
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load investigation details";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  if (loading) return <LoadingState message="Loading AI investigation findings & tool trace..." />;
  if (error || !data) return <ErrorState message={error || "Investigation record not found"} onRetry={loadData} />;

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to="/investigations"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Investigations Registry
        </Link>
        <Link
          to={`/cases/${data.case_id}`}
          className="text-xs text-sky-600 hover:underline font-medium"
        >
          View Case & Transaction Chain →
        </Link>
      </div>

      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-lg font-bold text-slate-900 font-mono tracking-tight">{data.case_id}</h1>
            <span className="text-slate-300">•</span>
            <span className="text-xs font-mono text-slate-600">Order: {data.order_id}</span>
            <Badge variant={data.investigation_status === "COMPLETED" ? "auto_resolve" : "escalate"}>
              {data.investigation_status}
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Provider: <strong className="text-slate-700 font-mono">{data.provider_used}</strong> • Confidence:{" "}
            <strong className="text-slate-900 font-mono">{(data.confidence * 100).toFixed(0)}%</strong> • Safety:{" "}
            <strong className="text-emerald-700 font-medium">Read-Only Corroboration</strong>
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
          <Lock className="w-3.5 h-3.5 text-sky-600" />
          <span>No Financial Mutation Occurred</span>
        </div>
      </div>

      {/* Finding & Recommendation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Finding & Root Cause */}
        <Card title="Corroborated Investigation Finding">
          <div className="space-y-3.5 text-xs">
            <div>
              <span className="text-slate-500 font-medium">Taxonomy Classification:</span>
              <div className="mt-1 font-semibold text-slate-900 text-sm">{data.finding.replace(/_/g, " ")}</div>
            </div>

            <div>
              <span className="text-slate-500 font-medium">Root Cause Analysis:</span>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded mt-1 text-slate-800 leading-relaxed whitespace-pre-line font-sans">
                {data.root_cause}
              </div>
            </div>

            {/* Supporting IDs */}
            <div className="pt-2 border-t border-slate-100 space-y-1.5">
              <div className="text-slate-500 font-medium">Supporting Entities Linked:</div>
              <div className="flex flex-wrap gap-2">
                {data.supporting_payment_ids?.map((pid) => (
                  <span key={pid} className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-[11px] font-mono">
                    {pid}
                  </span>
                ))}
                {data.supporting_settlement_ids?.map((sid) => (
                  <span key={sid} className="px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded text-[11px] font-mono">
                    {sid}
                  </span>
                ))}
                {data.supporting_invoice_id && (
                  <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[11px] font-mono">
                    {data.supporting_invoice_id}
                  </span>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Advisory Recommendation */}
        <Card title="Advisory Next Step Recommendation">
          <div className="space-y-4 text-xs">
            <div>
              <span className="text-slate-500 font-medium">Recommended Action:</span>
              <div className="p-3.5 bg-sky-50/50 border border-sky-200 rounded mt-1 text-slate-800 leading-relaxed font-medium">
                {data.recommendation}
              </div>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Requires Human Review:</span>
                <span className="font-semibold">{data.requires_human_review ? "Yes" : "No"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Confidence Score:</span>
                <span className="font-mono font-semibold">{(data.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>

            <div className="p-3 bg-amber-50/60 border border-amber-200 rounded text-[11px] text-amber-800 leading-relaxed">
              <strong>Operational Safeguard:</strong> The AI investigator functions strictly as an evidence corroborator.
              No payment modifications, refunds, or invoice generations are triggered by this analysis.
            </div>
          </div>
        </Card>
      </div>

      {/* AI Tool Execution Trace (Audit Trail) */}
      <Card
        title="AI Tool Execution Audit Trail"
        subtitle="Ordered, timestamped sequence of read-only operational tools executed by the agent"
      >
        {data.tool_trace && data.tool_trace.length > 0 ? (
          <div className="space-y-3">
            {data.tool_trace.map((step, idx) => {
              const isExpanded = expandedToolIndex === idx;
              return (
                <div
                  key={idx}
                  className="border border-slate-200 rounded-md overflow-hidden bg-white hover:border-slate-300 transition-colors"
                >
                  <div
                    onClick={() => setExpandedToolIndex(isExpanded ? null : idx)}
                    className="p-3 bg-slate-50/70 flex items-center justify-between cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded bg-slate-200 text-slate-700 flex items-center justify-center font-mono font-bold text-xs">
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <div className="flex items-center gap-2">
                        <Terminal className="w-3.5 h-3.5 text-slate-500" />
                        <span className="font-mono font-semibold text-xs text-slate-900">{step.tool_name}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> executed
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-4 border-t border-slate-100 bg-white space-y-3 text-xs">
                      <div>
                        <div className="text-[11px] text-slate-500 font-medium mb-1">Tool Input Arguments:</div>
                        <pre className="p-2.5 bg-slate-900 text-slate-100 rounded text-[11px] font-mono overflow-x-auto">
                          {JSON.stringify(step.arguments, null, 2)}
                        </pre>
                      </div>

                      <div>
                        <div className="text-[11px] text-slate-500 font-medium mb-1">Tool Result Payload:</div>
                        <pre className="p-2.5 bg-slate-900 text-slate-100 rounded text-[11px] font-mono overflow-x-auto max-h-60">
                          {JSON.stringify(step.result_summary, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic">No tool calls recorded in trace.</p>
        )}
      </Card>
    </div>
  );
};

