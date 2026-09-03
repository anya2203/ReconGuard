import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
  Layers,
  Bot,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
} from "lucide-react";
import { api } from "../services/api";
import type { CaseListResponse } from "../types/api";
import { Card } from "../components/common/Card";
import { DecisionBadge, PriorityBadge } from "../components/common/Badge";
import { FormatMoney } from "../components/common/FormatMoney";
import { EmptyState, ErrorState, LoadingState } from "../components/common/States";

export const CaseExplorerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // URL state
  const page = parseInt(searchParams.get("page") || "1", 10);
  const pageSize = parseInt(searchParams.get("page_size") || "20", 10);
  const decision = searchParams.get("decision") || "ALL";
  const priority = searchParams.get("priority") || "ALL";
  const exceptionType = searchParams.get("exception_type") || "ALL";
  const search = searchParams.get("search") || "";

  const [searchInput, setSearchInput] = useState(search);
  const [data, setData] = useState<CaseListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCases({
        page,
        page_size: pageSize,
        decision,
        priority,
        exception_type: exceptionType,
        search,
      });
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load cases";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [page, pageSize, decision, priority, exceptionType, search]);

  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value && value !== "ALL") {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set("page", "1"); // Reset to page 1 on filter change
    setSearchParams(params);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateParam("search", searchInput.trim());
  };

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", newPage.toString());
    setSearchParams(params);
  };

  const getControlOwnerBadge = (decisionVal: string) => {
    switch (decisionVal) {
      case "AUTO_RESOLVE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            ENGINE
          </span>
        );
      case "AI_INVESTIGATION":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Bot className="w-3 h-3 text-indigo-600" />
            AI AGENT
          </span>
        );
      case "HUMAN_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <UserCheck className="w-3 h-3 text-amber-600" />
            OPS DESK
          </span>
        );
      case "ESCALATE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-rose-50 text-rose-700 border border-rose-200">
            <AlertTriangle className="w-3 h-3 text-rose-600" />
            DISPUTE DESK
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700 border border-slate-200">
            {decisionVal}
          </span>
        );
    }
  };

  return (
    <div className="space-y-5">
      {/* Header & Filter Controls Card */}
      <Card>
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-600" />
                Operational Exception Queue
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Inspect, filter, and trace 1,000 deterministic reconciliation cases and exception states
              </p>
            </div>

            {/* Search Input */}
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full md:w-80">
              <div className="relative w-full">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search Case or Order ID..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:outline-none focus:ring-1 focus:ring-slate-900 text-slate-900 placeholder:text-slate-400"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-1.5 bg-slate-900 text-white rounded text-xs font-medium hover:bg-slate-800 transition-colors shadow-xs"
              >
                Search
              </button>
            </form>
          </div>

          {/* Quick Preset Filter Chips */}
          <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-100">
            <span className="text-[11px] text-slate-400 font-medium mr-1">PRESETS:</span>
            <button
              type="button"
              onClick={() => {
                setSearchParams({});
                setSearchInput("");
              }}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                decision === "ALL" && priority === "ALL" && exceptionType === "ALL" && !search
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              All Cases (1,000)
            </button>
            <button
              type="button"
              onClick={() => updateParam("decision", "AI_INVESTIGATION")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                decision === "AI_INVESTIGATION"
                  ? "bg-indigo-600 text-white"
                  : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200"
              }`}
            >
              AI Investigation (50)
            </button>
            <button
              type="button"
              onClick={() => updateParam("decision", "HUMAN_REVIEW")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                decision === "HUMAN_REVIEW"
                  ? "bg-amber-600 text-white"
                  : "bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200"
              }`}
            >
              Human Review (40)
            </button>
            <button
              type="button"
              onClick={() => updateParam("decision", "ESCALATE")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                decision === "ESCALATE"
                  ? "bg-rose-600 text-white"
                  : "bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
              }`}
            >
              Escalated (130)
            </button>
            <button
              type="button"
              onClick={() => updateParam("priority", "HIGH")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                priority === "HIGH"
                  ? "bg-rose-700 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              High Priority (170)
            </button>
          </div>

          {/* Select Dropdown Filters */}
          <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
            <div className="flex items-center gap-1.5 text-slate-500 font-medium">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span>Filters:</span>
            </div>

            {/* Decision Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Decision:</span>
              <select
                value={decision}
                onChange={(e) => updateParam("decision", e.target.value)}
                className="bg-white border border-slate-200 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-900 cursor-pointer text-xs"
              >
                <option value="ALL">All Decisions</option>
                <option value="AUTO_RESOLVE">AUTO_RESOLVE (780)</option>
                <option value="AI_INVESTIGATION">AI_INVESTIGATION (50)</option>
                <option value="HUMAN_REVIEW">HUMAN_REVIEW (40)</option>
                <option value="ESCALATE">ESCALATE (130)</option>
              </select>
            </div>

            {/* Priority Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Priority:</span>
              <select
                value={priority}
                onChange={(e) => updateParam("priority", e.target.value)}
                className="bg-white border border-slate-200 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-900 cursor-pointer text-xs"
              >
                <option value="ALL">All Priorities</option>
                <option value="HIGH">HIGH (170)</option>
                <option value="MEDIUM">MEDIUM (30)</option>
                <option value="LOW">LOW (800)</option>
              </select>
            </div>

            {/* Exception Type Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Exception:</span>
              <select
                value={exceptionType}
                onChange={(e) => updateParam("exception_type", e.target.value)}
                className="bg-white border border-slate-200 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-900 cursor-pointer text-xs"
              >
                <option value="ALL">All Exceptions</option>
                <option value="NONE">Clean Match (780)</option>
                <option value="ROUNDING_VARIANCE">Rounding Variance (20)</option>
                <option value="REFERENCE_MISMATCH">Reference Mismatch (20)</option>
                <option value="MISSING_INVOICE">Missing Invoice (10)</option>
                <option value="AMOUNT_MISMATCH">Amount Mismatch (30)</option>
                <option value="SLA_BREACH">SLA Breach (30)</option>
                <option value="MISSING_PAYMENT">Missing Payment (20)</option>
                <option value="CHARGEBACK">Chargeback (30)</option>
                <option value="REFUND">Refund (20)</option>
                <option value="AMBIGUOUS_CANDIDATE">Ambiguous Candidate (20)</option>
                <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence (20)</option>
                <option value="MISSING_SETTLEMENT">Missing Settlement (10)</option>
              </select>
            </div>

            {/* Reset Filters */}
            {(decision !== "ALL" || priority !== "ALL" || exceptionType !== "ALL" || search) && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput("");
                  setSearchParams({});
                }}
                className="text-xs text-slate-500 hover:text-slate-800 underline ml-auto cursor-pointer"
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Main Cases Table Card */}
      <Card>
        {loading ? (
          <LoadingState message="Fetching cases from server..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchCases} />
        ) : !data || data.cases.length === 0 ? (
          <EmptyState
            title="No matching cases found"
            message="No reconciliation records matched your query. Try adjusting your search query or filters."
          />
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500 px-1">
              <span>
                Showing <strong className="text-slate-800 font-mono">{(data.page - 1) * data.page_size + 1}</strong> to{" "}
                <strong className="text-slate-800 font-mono">{Math.min(data.page * data.page_size, data.total)}</strong> of{" "}
                <strong className="text-slate-800 font-mono">{data.total.toLocaleString()}</strong> total cases
              </span>
              <span>
                Page <strong className="text-slate-800 font-mono">{data.page}</strong> of{" "}
                <strong className="text-slate-800 font-mono">{data.total_pages}</strong>
              </span>
            </div>

            {/* Data Table */}
            <div className="overflow-x-auto border border-slate-200 rounded-md">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-medium select-none">
                    <th className="py-2.5 px-3">Case ID</th>
                    <th className="py-2.5 px-3">Order ID</th>
                    <th className="py-2.5 px-3">Exception Category</th>
                    <th className="py-2.5 px-3">Decision</th>
                    <th className="py-2.5 px-3">Priority</th>
                    <th className="py-2.5 px-3">Control Owner</th>
                    <th className="py-2.5 px-3">Strategy</th>
                    <th className="py-2.5 px-3 text-right">Financial Exposure</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {data.cases.map((c) => (
                    <tr key={c.case_id} className="hover:bg-slate-50/90 transition-colors">
                      <td className="py-2.5 px-3 font-mono font-medium text-sky-600">
                        <Link to={`/cases/${c.case_id}`} className="hover:underline">
                          {c.case_id}
                        </Link>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-600">{c.order_id}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-700">
                        {c.exception_type === "NONE" ? (
                          <span className="text-slate-400">Clean Match</span>
                        ) : (
                          c.exception_type.replace(/_/g, " ")
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <DecisionBadge decision={c.decision} />
                      </td>
                      <td className="py-2.5 px-3">
                        <PriorityBadge priority={c.priority} />
                      </td>
                      <td className="py-2.5 px-3">
                        {getControlOwnerBadge(c.decision)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-mono border border-slate-200">
                          {c.match_method}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium text-slate-900">
                        <FormatMoney amount={c.financial_impact} />
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <Link
                          to={`/cases/${c.case_id}`}
                          className="text-xs text-sky-600 hover:text-sky-800 font-medium"
                        >
                          Inspect →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500">Rows per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    const params = new URLSearchParams(searchParams);
                    params.set("page_size", e.target.value);
                    params.set("page", "1");
                    setSearchParams(params);
                  }}
                  className="bg-white border border-slate-200 rounded px-2 py-0.5 text-xs text-slate-700"
                >
                  <option value="20">20</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-200 rounded text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-3.5 h-3.5" /> Previous
                </button>
                <span className="text-xs text-slate-500">
                  {page} / {data.total_pages}
                </span>
                <button
                  type="button"
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page >= data.total_pages}
                  className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-200 rounded text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
