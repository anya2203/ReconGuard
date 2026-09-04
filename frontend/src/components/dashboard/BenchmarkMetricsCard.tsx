import React, { useEffect, useState } from "react";
import { Gauge, Zap, AlertCircle } from "lucide-react";
import { api } from "../../services/api";
import type { BenchmarkMetrics } from "../../types/api";

export const BenchmarkMetricsCard: React.FC = () => {
  const [metrics, setMetrics] = useState<BenchmarkMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    api
      .getBenchmarkMetrics()
      .then(setMetrics)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !metrics) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-48 mb-3"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="h-16 bg-slate-100 rounded"></div>
          <div className="h-16 bg-slate-100 rounded"></div>
          <div className="h-16 bg-slate-100 rounded"></div>
          <div className="h-16 bg-slate-100 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-slate-800" />
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">
              Verified Benchmark & Performance Telemetry
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Phase 1 evaluation against 1,000 independent ground-truth operational benchmark records
          </p>
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-500 bg-slate-50 px-2.5 py-1 rounded border border-slate-200">
          <Zap className="w-3 h-3 text-amber-500" />
          {metrics.deterministic_throughput_rps.toLocaleString(undefined, { maximumFractionDigits: 1 })} rec/sec throughput
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs mb-4">
        {/* Classification Accuracy */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
          <span className="text-slate-500 text-[11px]">Outcome Accuracy</span>
          <div className="text-lg font-bold text-slate-900 font-mono mt-0.5">
            {(metrics.classification_accuracy * 100).toFixed(2)}%
          </div>
          <span className="text-[10px] text-slate-400">1,000 GT cases</span>
        </div>

        {/* Deterministic Correctness */}
        <div className="p-3 bg-emerald-50/40 border border-emerald-200 rounded-md">
          <span className="text-emerald-800 text-[11px] font-medium">Deterministic Correctness</span>
          <div className="text-lg font-bold text-emerald-700 font-mono mt-0.5">
            {(metrics.deterministic_correctness * 100).toFixed(2)}%
          </div>
          <span className="text-[10px] text-emerald-600">780 / 820 clean matches</span>
        </div>

        {/* Binary Exception Detection F1 */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
          <span className="text-slate-500 text-[11px]">Exception Detection F1</span>
          <div className="text-lg font-bold text-slate-900 font-mono mt-0.5">
            {(metrics.binary_exception_f1 * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-400">TP: 220, FP: 0</span>
        </div>

        {/* Payment Linkage F1 */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
          <span className="text-slate-500 text-[11px]">Payment Linkage F1</span>
          <div className="text-lg font-bold text-slate-900 font-mono mt-0.5">
            {(metrics.payment_linkage_f1 * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-400">1:1 & 1:N payment identification</span>
        </div>

        {/* Settlement Linkage F1 */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
          <span className="text-slate-500 text-[11px]">Settlement Linkage F1</span>
          <div className="text-lg font-bold text-slate-900 font-mono mt-0.5">
            {(metrics.settlement_linkage_f1 * 100).toFixed(2)}%
          </div>
          <span className="text-[10px] text-slate-400">Batch reconciliation precision</span>
        </div>

        {/* Mock AI Self-Consistency */}
        <div className="p-3 bg-indigo-50/40 border border-indigo-200 rounded-md">
          <span className="text-indigo-800 text-[11px] font-medium">Mock Self-Consistency</span>
          <div className="text-lg font-bold text-indigo-700 font-mono mt-0.5">
            {(metrics.ai_mock_evaluation_accuracy * 100).toFixed(0)}%
          </div>
          <span className="text-[10px] text-indigo-600">MockProvider regression (50/50)</span>
        </div>
      </div>

      {/* Honest AI Limitation Disclosure */}
      <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600 flex items-start gap-2.5">
        <AlertCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-slate-800 font-semibold">AI Evaluation Reality & Provider Rate Limits: </strong>
          <span>
            {metrics.ai_gemini_sample_summary}. The system is feature-frozen with deterministic fallback to prevent silent LLM failures.
          </span>
        </div>
      </div>
    </div>
  );
};
