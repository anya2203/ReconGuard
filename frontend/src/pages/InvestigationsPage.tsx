import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, ArrowRight, FileSearch } from "lucide-react";
import { api } from "../services/api";
import type { InvestigationResponse } from "../types/api";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { EmptyState, ErrorState, LoadingState } from "../components/common/States";

export const InvestigationsPage: React.FC = () => {
  const [investigations, setInvestigations] = useState<InvestigationResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getInvestigations();
      setInvestigations(res.investigations || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load investigations";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div>
          <h1 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Bot className="w-4 h-4 text-sky-600" />
            AI Investigation Registry
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Historical investigation findings, autonomous evidence corroboration traces, and advisory recommendations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/cases?decision=AI_INVESTIGATION"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-medium transition-colors shadow-xs"
          >
            Explore 50 AI-Eligible Cases
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Main Investigations Content */}
      <Card>
        {loading ? (
          <LoadingState message="Loading AI investigation records..." />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : investigations.length === 0 ? (
          <EmptyState
            title="No completed investigations yet"
            message="No cases have been investigated yet in this session. Navigate to an AI-eligible case in the Case Explorer to trigger an investigation."
            icon={<FileSearch className="w-6 h-6 text-slate-400" />}
          />
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500 px-1">
              <span>
                Total Investigations Recorded: <strong className="text-slate-800 font-mono">{investigations.length}</strong>
              </span>
              <span className="text-[11px] text-slate-400">Strictly Read-Only Analysis</span>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-md">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-medium">
                    <th className="py-2.5 px-3">Case ID</th>
                    <th className="py-2.5 px-3">Order ID</th>
                    <th className="py-2.5 px-3">Finding</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Confidence</th>
                    <th className="py-2.5 px-3">Provider</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {investigations.map((inv) => (
                    <tr key={inv.case_id} className="hover:bg-slate-50/90 transition-colors">
                      <td className="py-2.5 px-3 font-mono font-medium text-sky-600">
                        <Link to={`/investigations/${inv.case_id}`} className="hover:underline">
                          {inv.case_id}
                        </Link>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-600">{inv.order_id}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-800">
                        {inv.finding.replace(/_/g, " ")}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge
                          variant={inv.investigation_status === "COMPLETED" ? "auto_resolve" : "escalate"}
                        >
                          {inv.investigation_status}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                        {(inv.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px]">
                        {inv.provider_used || "mock"}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <Link
                          to={`/investigations/${inv.case_id}`}
                          className="text-xs text-sky-600 hover:text-sky-800 font-medium"
                        >
                          Audit Trace →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

